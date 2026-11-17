"""Minimal mock of the backend API contract (Part 3)."""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field, model_validator

PROCESSING_DELAY = float(os.getenv("MOCK_PROCESSING_DELAY", "0.3"))
SLOW_EXTRA_DELAY = float(os.getenv("MOCK_SLOW_EXTRA_DELAY", "1.5"))
DATA_API_TIMEOUT = float(os.getenv("MOCK_DATA_API_TIMEOUT", "2.0"))

app = FastAPI(title="Kamleon backend mock")

measurements: dict[str, dict] = {}
duplicate_index: dict[tuple, str] = {}
devices: dict[str, dict] = {}
# asyncio keeps only weak references to tasks; hold them until they finish.
background_tasks: set = set()


class SensorData(BaseModel):
    volume: float = Field(gt=0)        # assumption: zero volume is not a measurement
    ph: float = Field(ge=0, le=14)     # the pH scale itself, not a clinical threshold
    temperature: float                 # no range in the contract, so none invented


class MeasurementIn(BaseModel):
    deviceId: str = Field(min_length=1)
    userId: Optional[str] = None
    sessionId: str = Field(min_length=1)
    startedAt: datetime
    completedAt: datetime
    sensorData: SensorData

    @model_validator(mode="after")
    def completed_after_started(self):
        # assumption: the contract doesn't state it, but a measurement can't end before it starts
        if self.completedAt <= self.startedAt:
            raise ValueError("completedAt must be after startedAt")
        return self


class ModeIn(BaseModel):
    mode: str


class FirmwareIn(BaseModel):
    version: str = Field(min_length=1)


async def fake_data_api(sensor_data: dict, behaviour: Optional[str]) -> dict:
    await asyncio.sleep(PROCESSING_DELAY)
    if behaviour == "slow":
        await asyncio.sleep(SLOW_EXTRA_DELAY)
    if behaviour == "timeout":
        await asyncio.sleep(DATA_API_TIMEOUT * 10)
    if behaviour == "malformed":
        return {"hydration": "not-a-number"}
    # Placeholder: the real model belongs to the data team. Different readings must
    # give different results, so swapped results are detectable (TC-03, TC-04).
    volume = sensor_data["volume"]
    return {"hydration": int(volume) % 101, "volume": volume}


def is_valid_result(result: dict) -> bool:
    return (
        isinstance(result.get("hydration"), (int, float))
        and isinstance(result.get("volume"), (int, float))
    )


async def process_measurement(measurement_id: str, behaviour: Optional[str]) -> None:
    m = measurements[measurement_id]
    try:
        result = await asyncio.wait_for(
            fake_data_api(m["sensorData"], behaviour), timeout=DATA_API_TIMEOUT
        )
    except asyncio.TimeoutError:
        m["status"] = "failed"
        return
    if is_valid_result(result):
        m["result"] = result
        m["status"] = "completed"
    else:
        m["status"] = "failed"


@app.post(
    "/api/v1/measurements",
    status_code=201,
    responses={200: {"description": "Measurement already received; original ID returned"}},
)
async def create_measurement(
    body: MeasurementIn,
    response: Response,
    # Test-only: simulates Data API problems for this request only (slow, malformed, timeout).
    # Per request, so tests stay independent. Not part of the contract; a real backend ignores it.
    x_mock_data_api: Optional[str] = Header(default=None),
):
    # assumption: same device + session + start time = the same measurement (no idempotency key)
    key = (body.deviceId, body.sessionId, body.startedAt)
    if key in duplicate_index:
        original_id = duplicate_index[key]
        response.status_code = 200
        return {"measurementId": original_id, "status": measurements[original_id]["status"]}

    measurement_id = f"MEAS-{uuid.uuid4().hex[:12]}"
    measurements[measurement_id] = {
        "measurementId": measurement_id,
        "deviceId": body.deviceId,
        "userId": body.userId,
        "status": "processing",
        "result": None,
        "sensorData": body.sensorData.model_dump(),
    }
    duplicate_index[key] = measurement_id

    task = asyncio.create_task(process_measurement(measurement_id, x_mock_data_api))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return {"measurementId": measurement_id, "status": "processing"}


@app.get("/api/v1/measurements/{measurement_id}")
async def get_measurement(measurement_id: str):
    m = measurements.get(measurement_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return {k: m[k] for k in ("measurementId", "deviceId", "userId", "status", "result")}


def get_or_register_device(device_id: str) -> dict:
    # assumption: the contract has no way to register a device, so any ID is accepted
    if device_id not in devices:
        devices[device_id] = {
            "deviceId": device_id,
            "status": "online",
            "mode": "normal",
            "firmwareVersion": "1.4.2",
            "lastSeen": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    return devices[device_id]


@app.get("/api/v1/devices/{device_id}")
async def get_device(device_id: str):
    return get_or_register_device(device_id)


@app.post("/api/v1/devices/{device_id}/mode")
async def change_mode(device_id: str, body: ModeIn):
    if body.mode not in ("normal", "maintenance"):
        raise HTTPException(status_code=422, detail="mode must be normal or maintenance")
    device = get_or_register_device(device_id)
    device["mode"] = body.mode
    return {"deviceId": device_id, "mode": body.mode}


@app.post("/api/v1/devices/{device_id}/firmware-update")
async def start_firmware_update(device_id: str, body: FirmwareIn):
    get_or_register_device(device_id)
    return {"deviceId": device_id, "status": "update_started", "targetVersion": body.version}
