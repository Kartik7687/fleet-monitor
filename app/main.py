import logging
import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException

from app.models import DeviceCreate, DeviceOut, HeartbeatIn, SummaryOut
from app.store import DeviceAlreadyExists, DeviceNotFound, DeviceStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fleet")


def create_app(store: Optional[DeviceStore] = None) -> FastAPI:
    store = store or DeviceStore(timeout_seconds=int(os.getenv("OFFLINE_TIMEOUT_SECONDS", "30")))
    app = FastAPI(title="Mini Device Fleet Monitor")

    @app.post("/devices", response_model=DeviceOut, status_code=201)
    def register_device(body: DeviceCreate):
        try:
            device = store.register(body.id, body.name)
        except DeviceAlreadyExists:
            raise HTTPException(status_code=409, detail=f"Device '{body.id}' already exists")
        log.info("registered %s", body.id)
        return device

    @app.post("/devices/{device_id}/heartbeat", response_model=DeviceOut)
    def heartbeat(device_id: str, body: HeartbeatIn):
        try:
            return store.heartbeat(
                device_id, body.timestamp, body.status, body.cpu_usage, body.signal_strength
            )
        except DeviceNotFound:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    @app.get("/devices", response_model=list[DeviceOut])
    def list_devices(status: Optional[Literal["ONLINE", "OFFLINE"]] = None):
        return store.list(status)

    @app.get("/devices/{device_id}", response_model=DeviceOut)
    def get_device(device_id: str):
        try:
            return store.get(device_id)
        except DeviceNotFound:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    @app.get("/summary", response_model=SummaryOut)
    def summary():
        return store.summary()

    return app


app = create_app()