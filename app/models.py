from datetime import datetime
from typing import Literal, Optional

from pydantic import AwareDatetime, BaseModel, Field


class DeviceCreate(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=128)


class HeartbeatIn(BaseModel):
    timestamp: AwareDatetime
    status: str = Field(min_length=1, max_length=32)
    cpu_usage: Optional[float] = Field(default=None, ge=0, le=100)
    signal_strength: Optional[float] = None


class DeviceOut(BaseModel):
    id: str
    name: str
    status: Literal["ONLINE", "OFFLINE"]
    last_heartbeat: Optional[datetime] = None
    reported_status: Optional[str] = None
    cpu_usage: Optional[float] = None
    signal_strength: Optional[float] = None


class SummaryOut(BaseModel):
    total: int
    online: int
    offline: int