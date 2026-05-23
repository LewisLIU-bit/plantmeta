import argparse
import math
import random
import time
from typing import Any

import httpx


DEFAULT_ENDPOINT = "http://127.0.0.1:8000/api/sensor/upload"


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def soil_raw_from_percent(percent: float) -> int:
    raw_dry = 3200
    raw_wet = 1200
    raw = raw_dry - (percent / 100) * (raw_dry - raw_wet)
    return int(raw + random.uniform(-30, 30))


def build_payload(profile: str, step: int) -> dict[str, Any]:
    base = {
        "device_id": "plant_box_01",
        "plant_id": "pothos_01",
        "pump_status": "off",
    }

    if profile == "normal":
        soil = 50 + math.sin(step / 2.8) * 5 + random.uniform(-1.2, 1.2)
        light = 760 + math.sin(step / 3.4) * 160 + random.uniform(-45, 45)
        temperature = 25 + math.sin(step / 5) * 1.4 + random.uniform(-0.4, 0.4)
        humidity = 56 + math.sin(step / 4.2) * 5 + random.uniform(-1.5, 1.5)
    elif profile == "dry":
        trend = max(18, 48 - step * 1.8)
        soil = trend + math.sin(step / 1.7) * 2.2 + random.uniform(-1.0, 1.0)
        light = 740 + math.sin(step / 3) * 130 + random.uniform(-40, 40)
        temperature = 26 + math.sin(step / 4) * 1.2 + random.uniform(-0.4, 0.4)
        humidity = 48 + math.sin(step / 3.5) * 4 + random.uniform(-1.5, 1.5)
    elif profile == "wet":
        soil = 84 + math.sin(step / 2) * 4 + random.uniform(-1.2, 1.2)
        light = 670 + math.sin(step / 3.2) * 110 + random.uniform(-35, 35)
        temperature = 24 + math.sin(step / 4.5) * 1.0 + random.uniform(-0.4, 0.4)
        humidity = 69 + math.sin(step / 3.8) * 5 + random.uniform(-1.5, 1.5)
    elif profile == "strong_light":
        soil = 46 + math.sin(step / 2.5) * 5 + random.uniform(-1.2, 1.2)
        light = 2700 + math.sin(step / 2.6) * 350 + random.uniform(-80, 80)
        temperature = 29 + math.sin(step / 4) * 1.4 + random.uniform(-0.4, 0.4)
        humidity = 46 + math.sin(step / 4.2) * 5 + random.uniform(-1.5, 1.5)
    elif profile == "cold":
        soil = 50 + math.sin(step / 2.6) * 5 + random.uniform(-1.2, 1.2)
        light = 610 + math.sin(step / 3.4) * 120 + random.uniform(-40, 40)
        temperature = 12 + math.sin(step / 3.8) * 1.2 + random.uniform(-0.3, 0.3)
        humidity = 55 + math.sin(step / 4) * 5 + random.uniform(-1.5, 1.5)
    elif profile == "fault":
        soil = random.choice([-8, 135, random.uniform(35, 55)])
        light = random.uniform(400, 900)
        temperature = random.choice([random.uniform(-20, -12), random.uniform(65, 80), 25])
        humidity = random.choice([-5, 120, random.uniform(40, 60)])
    else:
        raise ValueError(f"Unknown profile: {profile}")

    soil = round(clamp(soil, -20, 140), 1)
    return {
        **base,
        "soil_moisture_raw": soil_raw_from_percent(soil),
        "soil_moisture_percent": soil,
        "light_lux": round(light, 1),
        "air_temperature": round(temperature, 1),
        "air_humidity": round(humidity, 1),
    }


def send_payload(client: httpx.Client, endpoint: str, payload: dict[str, Any]) -> None:
    response = client.post(endpoint, json=payload, timeout=5)
    response.raise_for_status()
    print(f"upload: {payload}")
    print(f"control: {response.json()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate an ESP32 uploading PlantMeta sensor data.")
    parser.add_argument(
        "profile",
        choices=["normal", "dry", "wet", "strong_light", "cold", "fault"],
        help="Sensor scenario to simulate.",
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Sensor upload API endpoint.")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between uploads.")
    parser.add_argument("--count", type=int, default=0, help="Number of uploads. Use 0 to run forever.")
    args = parser.parse_args()

    sent = 0
    with httpx.Client() as client:
        while args.count == 0 or sent < args.count:
            payload = build_payload(args.profile, sent)
            try:
                send_payload(client, args.endpoint, payload)
            except httpx.HTTPError as exc:
                print(f"request failed: {exc}")
            sent += 1
            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)


if __name__ == "__main__":
    main()
