from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.store import DeviceStore


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 9, 21, 10, 30, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, seconds: float):
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def client(clock):
    return TestClient(create_app(DeviceStore(timeout_seconds=30, clock=clock)))


HB = {"timestamp": "2026-09-21T10:30:00Z", "status": "OK"}