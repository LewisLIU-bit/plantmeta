from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models import AdviceRecordDB, SensorRecordDB, WateringEventDB
from app.services.advice import generate_advice
from app.services.rules import build_rule_result
from app.config import AUTHORIZED_CODES


PlantStatus = Literal["normal", "watch", "danger", "fault"]
PumpStatus = Literal["off", "on"]
Command = Literal["none", "water", "stop"]
WaterMode = Literal["manual", "auto", "demo"]


class SensorUpload(BaseModel):
    device_id: str = Field(..., examples=["plant_box_01"])
    plant_id: str = Field(..., examples=["pothos_01"])
    soil_moisture_raw: int = Field(..., ge=0, examples=[2380])
    soil_moisture_percent: float = Field(..., examples=[42.5])
    light_lux: float = Field(..., ge=0, examples=[680])
    air_temperature: float = Field(..., examples=[24.8])
    air_humidity: float = Field(..., examples=[56.2])
    pump_status: PumpStatus = Field("off", examples=["off"])


class SensorRecord(SensorUpload):
    id: int
    timestamp: datetime
    status: PlantStatus
    message: str

    model_config = {"from_attributes": True}


class ControlResponse(BaseModel):
    status: PlantStatus
    command: Command
    pump_duration_ms: int
    led_status: Literal["green", "yellow", "red", "blue"]
    message: str


class ManualWaterRequest(BaseModel):
    duration_ms: int = Field(1000, ge=100, le=10000, examples=[1000])
    reason: str = Field("Manual watering requested by user.", max_length=255)
    code: str


class AutoWaterRequest(BaseModel):
    enabled: bool


class AutoWaterResponse(BaseModel):
    auto_watering_enabled: bool


class WateringEvent(BaseModel):
    id: int
    timestamp: datetime
    mode: WaterMode
    duration_ms: int
    reason: str

    model_config = {"from_attributes": True}


class AdviceRecord(BaseModel):
    id: int
    timestamp: datetime
    plant_id: str
    input_summary: str
    advice: str
    model_name: str

    model_config = {"from_attributes": True}


app = FastAPI(title="PlantMeta API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://plantmeta-web.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

auto_watering_enabled = False


@app.get("/")
def read_root():
    return {"message": "PlantMeta backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/sensor/upload", response_model=ControlResponse)
def upload_sensor_data(data: SensorUpload, db: Session = Depends(get_db)):
    rule_result = build_rule_result(data)
    record = SensorRecordDB(
        **data.model_dump(),
        timestamp=datetime.now(timezone.utc),
        status=rule_result.status,
        message=rule_result.message,
    )
    db.add(record)
    db.commit()
    return ControlResponse(
        status=rule_result.status,
        command=rule_result.command,
        pump_duration_ms=rule_result.pump_duration_ms,
        led_status=rule_result.led_status,
        message=rule_result.message,
    )


@app.get("/api/latest", response_model=SensorRecord)
def get_latest_sensor_record(db: Session = Depends(get_db)):
    record = db.scalars(select(SensorRecordDB).order_by(desc(SensorRecordDB.id))).first()
    if record is None:
        raise HTTPException(status_code=404, detail="No sensor data has been uploaded yet.")
    return record


@app.get("/api/history", response_model=list[SensorRecord])
def get_sensor_history(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    records = db.scalars(
        select(SensorRecordDB)
        .order_by(desc(SensorRecordDB.id))
        .limit(limit)
    ).all()
    return list(reversed(records))


@app.post("/api/water/manual")
def trigger_manual_watering(
    request: ManualWaterRequest,
    db: Session = Depends(get_db)
):

    if request.code not in AUTHORIZED_CODES:
        raise HTTPException(
            status_code=403,
            detail="邀请码无效"
        )

    event = WateringEventDB(
        timestamp=datetime.now(timezone.utc),
        mode="manual",
        duration_ms=request.duration_ms,
        reason=request.reason,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


@app.post("/api/water/auto", response_model=AutoWaterResponse)
def set_auto_watering(request: AutoWaterRequest):
    global auto_watering_enabled
    auto_watering_enabled = request.enabled
    return AutoWaterResponse(auto_watering_enabled=auto_watering_enabled)


@app.get("/api/events", response_model=list[WateringEvent])
def get_events(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    events = db.scalars(
        select(WateringEventDB)
        .order_by(desc(WateringEventDB.id))
        .limit(limit)
    ).all()
    return list(reversed(events))


@app.post("/api/advice", response_model=AdviceRecord)
def create_advice(db: Session = Depends(get_db)):
    latest = db.scalars(select(SensorRecordDB).order_by(desc(SensorRecordDB.id))).first()
    if latest is None:
        raise HTTPException(status_code=404, detail="No sensor data has been uploaded yet.")

    advice, input_summary, model_name = generate_advice(latest)
    record = AdviceRecordDB(
        timestamp=datetime.now(timezone.utc),
        plant_id=latest.plant_id,
        input_summary=input_summary,
        advice=advice,
        model_name=model_name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@app.post("/api/auth")
def auth(data: dict):
    code = data.get("code")

    if code in AUTHORIZED_CODES:
        return {"ok": True}

    return {"ok": False}
