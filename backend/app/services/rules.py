from dataclasses import dataclass
from typing import Literal, Protocol


PlantStatus = Literal["normal", "watch", "danger", "fault"]
Command = Literal["none", "water", "stop"]
LedStatus = Literal["green", "yellow", "red", "blue"]


class SensorLike(Protocol):
    soil_moisture_percent: float
    light_lux: float
    air_temperature: float
    air_humidity: float


@dataclass(frozen=True)
class RuleResult:
    status: PlantStatus
    message: str
    command: Command
    pump_duration_ms: int
    led_status: LedStatus


def evaluate_plant_status(data: SensorLike) -> tuple[PlantStatus, str]:
    if not 0 <= data.soil_moisture_percent <= 100:
        return "fault", "土壤湿度百分比超出合理范围，请检查传感器或上传数据。"
    if not 0 <= data.air_humidity <= 100:
        return "fault", "空气湿度超出合理范围，请检查温湿度传感器。"
    if data.air_temperature < -10 or data.air_temperature > 60:
        return "fault", "环境温度读数异常，请检查温湿度传感器。"

    if data.soil_moisture_percent < 15:
        return "danger", "土壤湿度明显偏低，植物处于缺水风险状态，建议少量浇水并继续观察。"
    if data.soil_moisture_percent < 25:
        return "watch", "土壤湿度略低，建议关注后续变化，必要时少量补水。"
    if data.soil_moisture_percent > 85:
        return "danger", "土壤湿度过高，建议暂停浇水并保持通风。"
    if data.soil_moisture_percent > 75:
        return "watch", "土壤湿度偏高，暂时不建议继续浇水。"
    if data.light_lux < 100:
        return "watch", "当前光照偏弱，建议移到明亮散射光位置。"
    if data.light_lux > 2000:
        return "watch", "当前光照偏强，建议避免长时间直射阳光。"
    if data.air_temperature < 15 or data.air_temperature > 32:
        return "watch", "当前温度不在绿萝较舒适范围内，建议调整摆放位置。"

    return "normal", "当前绿萝状态正常，环境数据处于适宜范围。"


def build_rule_result(data: SensorLike) -> RuleResult:
    status, message = evaluate_plant_status(data)

    if status == "fault":
        return RuleResult(status, message, "stop", 0, "red")
    if status == "danger":
        return RuleResult(status, message, "none", 0, "red")
    if status == "watch":
        return RuleResult(status, message, "none", 0, "yellow")
    return RuleResult(status, message, "none", 0, "green")


def build_template_advice(record: SensorLike, status: str, message: str) -> str:
    if status == "fault":
        return "当前传感器数据存在异常，建议先检查接线、电源和传感器读数，暂时不要自动浇水。"
    if record.soil_moisture_percent < 15:
        return "当前土壤湿度明显偏低，建议少量浇水，并在接下来一段时间观察湿度是否回升。"
    if record.soil_moisture_percent > 85:
        return "当前土壤湿度偏高，建议暂停浇水，保持通风，避免根部长期处于过湿环境。"
    if record.light_lux < 100:
        return "当前光照偏弱，建议把绿萝移到明亮散射光位置，避免长期处于阴暗环境。"
    if record.light_lux > 2000:
        return "当前光照偏强，建议避免长时间直射阳光，以免叶片被晒伤。"
    if record.air_temperature < 15 or record.air_temperature > 32:
        return "当前温度不在绿萝较舒适范围内，建议调整摆放位置，减少温度波动。"
    if status == "watch":
        return f"当前绿萝需要关注：{message} 建议继续观察数据变化，不要频繁大量浇水。"
    return "当前绿萝状态整体正常，继续保持适量散射光和稳定浇水节奏即可。"
