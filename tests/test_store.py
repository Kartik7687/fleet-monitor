import threading
from datetime import datetime, timezone

from app.store import DeviceStore


def test_concurrent_heartbeats_are_safe():
    store = DeviceStore()
    for i in range(10):
        store.register(f"d{i}", f"Device {i}")
    ts = datetime.now(timezone.utc)

    def worker(i):
        for _ in range(200):
            store.heartbeat(f"d{i}", ts, "OK")
            store.summary()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert store.summary() == {"total": 10, "online": 10, "offline": 0}