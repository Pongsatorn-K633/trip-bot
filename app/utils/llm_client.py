import json
import os
from openai import OpenAI
from pathlib import Path

# ---------------------------------------------------------------------------
# Itinerary — loaded once at startup, injected into every system prompt
# ---------------------------------------------------------------------------
_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "tokyo-matsumoto.json"

with open(_DATA_PATH, encoding="utf-8") as _f:
    _ITINERARY: dict = json.load(_f)

_ITINERARY_TEXT = json.dumps(_ITINERARY, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# Typhoon API config
# ---------------------------------------------------------------------------
_MODEL  = "typhoon-v2.5-30b-a3b-instruct"
_CLIENT = OpenAI(
    api_key=os.getenv("TYPHOON_API_KEY", ""),
    base_url="https://api.opentyphoon.ai/v1",
)

_SYSTEM_PROMPT = f"""คุณเป็นผู้ช่วยท่องเที่ยวภาษาไทย ชื่อ "ทริปบอท"

ทริปนี้อยู่ในช่วงวันที่ 29 พฤษภาคม – 8 มิถุนายน 2569 (ค.ศ. 2026)

กฎ:
- ตอบตามข้อมูลกำหนดการด้านล่างเท่านั้น
- ห้ามแต่งหรือเพิ่มข้อมูลที่ไม่มีในกำหนดการ
- ตอบเป็นภาษาไทย กระชับและชัดเจน
- ถ้าไม่มีข้อมูลที่ถามให้บอกตรงๆ ว่าไม่มีข้อมูล
กำหนดการทริป:
{_ITINERARY_TEXT}"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _find_map_url(location: str) -> str | None:
    loc = location.lower()
    for day_events in _ITINERARY.values():
        for event in day_events:
            dest = event.get("destination", "").lower()
            if loc in dest or dest in loc:
                return event.get("map_url")
    return None


def ask(user_text: str) -> str:
    # Code-level map lookup — bypass LLM entirely
    stripped = user_text.strip()
    if stripped.lower().startswith("map "):
        location = stripped[4:].strip()
        url = _find_map_url(location)
        if url:
            return f"แผนที่ {location}:\n{url}"
        return f"ไม่พบข้อมูลแผนที่สำหรับ '{location}' ในกำหนดการทริปนี้ครับ"

    try:
        response = _CLIENT.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_text},
            ],
            temperature=0.6,
            max_completion_tokens=4096,
            top_p=0.6,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"ขออภัยค่ะ เกิดข้อผิดพลาด: {e}"
