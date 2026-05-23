from typing import Any

import httpx

from backend.app.db import settings
from backend.app.services.rules import build_template_advice


def build_advice_input_summary(record: Any) -> str:
    return (
        f"植物：{record.plant_id}；"
        f"土壤湿度：{record.soil_moisture_percent}%；"
        f"光照：{record.light_lux} lux；"
        f"温度：{record.air_temperature}℃；"
        f"空气湿度：{record.air_humidity}%；"
        f"系统状态：{record.status}；"
        f"规则判断：{record.message}"
    )


def build_prompt(record: Any) -> str:
    return f"""
你是一个植物养护助手。请根据以下状态生成简洁、友好、可执行的中文建议。

{build_advice_input_summary(record)}

输出要求：
1. 不超过 120 字；
2. 先说明当前状态；
3. 再给出具体建议；
4. 不要编造没有提供的传感器信息；
5. 不要直接下达硬件控制指令。
""".strip()


def generate_advice(record: Any) -> tuple[str, str, str]:
    input_summary = build_advice_input_summary(record)
    fallback = build_template_advice(record, record.status, record.message)

    if not settings.llm_api_key:
        return fallback, input_summary, "template-fallback"

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "你是一个谨慎、可靠的植物养护建议助手。"},
            {"role": "user", "content": build_prompt(record)},
        ],
        "temperature": 0.4,
        "max_tokens": 180,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(settings.llm_base_url, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            return fallback, input_summary, "template-fallback"
        return content, input_summary, settings.llm_model
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return fallback, input_summary, "template-fallback"
