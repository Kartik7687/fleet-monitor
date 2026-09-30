import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

DEFAULT_TIMEOUT_SECONDS = 30


class DeviceAlreadyExists(Exception):
    pass


class DeviceNotFound(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Device:
    id: str
    name: str
    last_seen: Optional[datetime] = None        # server receive time, drives ONLINE/OFFLINE
    last_heartbeat: Optional[datetime] = None   # timestamp reported by the device
    reported_status: Optional[str] = None
    cpu_usage: Optional[float] = None
    signal_strength: Optional[float] = None


class DeviceStore:
    """Thread-safe in-memory device registry.

    Status is derived at read time from `last_seen`, so there is no
    background job and no stale state.
    """

    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        clock: Callable[[], datetime] = utcnow,
    ):
        self._timeout = timedelta(seconds=timeout_seconds)
        self._clock = clock
        self._devices: dict[str, _Device] = {}
        self._lock = threading.Lock()

    def register(self, device_id: str, name: str) -> dict:
        with self._lock:
            if device_id in self._devices:
                raise DeviceAlreadyExists(device_id)
            device = _Device(id=device_id, name=name)
            self._devices[device_id] = device
            return self._view(device, self._clock())

    def heartbeat(
        self,
        device_id: str,
        timestamp: datetime,
        status: str,
        cpu_usage: Optional[float] = None,
        signal_strength: Optional[float] = None,
    ) -> dict:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                raise DeviceNotFound(device_id)
            now = self._clock()
            device.last_seen = now
            device.last_heartbeat = timestamp
            device.reported_status = status
            device.cpu_usage = cpu_usage
            device.signal_strength = signal_strength
            return self._view(device, now)

    def get(self, device_id: str) -> dict:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                raise DeviceNotFound(device_id)
            return self._view(device, self._clock())

    def list(self, status: Optional[str] = None) -> list[dict]:
        with self._lock:
            now = self._clock()
            views = [self._view(d, now) for d in self._devices.values()]
        if status:
            views = [v for v in views if v["status"] == status]
        return views

    def summary(self) -> dict:
        with self._lock:
            now = self._clock()  # single "now" so counts are consistent
            online = sum(1 for d in self._devices.values() if self._is_online(d, now))
            total = len(self._devices)
        return {"total": total, "online": online, "offline": total - online}

    def _is_online(self, device: _Device, now: datetime) -> bool:
        return device.last_seen is not None and (now - device.last_seen) <= self._timeout

    def _view(self, device: _Device, now: datetime) -> dict:
        return {
            "id": device.id,
            "name": device.name,
            "status": "ONLINE" if self._is_online(device, now) else "OFFLINE",
            "last_heartbeat": device.last_heartbeat,
            "reported_status": device.reported_status,
            "cpu_usage": device.cpu_usage,
            "signal_strength": device.signal_strength,
        }