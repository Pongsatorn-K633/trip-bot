import json
import os
from openai import OpenAI
from pathlib import Path

# ---------------------------------------------------------------------------
# Itinerary — loaded once at startup, injected into every system prompt
# ---------------------------------------------------------------------------
_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "tokyo-nagano.json"

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

def _all_destinations() -> list[dict]:
    """Return unique destinations with map_url from the itinerary."""
    seen, result = set(), []
    for day_events in _ITINERARY.values():
        for event in day_events:
            dest_obj = event.get("destination", {})
            name = dest_obj.get("name", "")
            if name and name not in seen:
                seen.add(name)
                result.append(dest_obj)
    return result


def _find_map_url(location: str) -> tuple[str, str] | None:
    """Code-level lookup. Returns (matched_name, map_url) or None."""
    loc = location.lower()
    words = [w for w in loc.split() if len(w) >= 3]
    for dest_obj in _all_destinations():
        name = dest_obj.get("name", "")
        dest = name.lower()
        map_url = dest_obj.get("map_url")
        tags = [t.lower() for t in dest_obj.get("tags", [])]
        if any(tag in loc for tag in tags):
            return name, map_url
        for word in words:
            if word in dest:
                return name, map_url
    return None


def _llm_resolve_location(user_location: str) -> str | None:
    """Ask LLM to fuzzy-match user query to the closest destination name."""
    dest_list = "\n".join(f"- {d['name']}" for d in _all_destinations())
    try:
        response = _CLIENT.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"รายชื่อสถานที่ในกำหนดการทริป:\n{dest_list}\n\n"
                        "ผู้ใช้ถามหาแผนที่ของสถานที่ใด? "
                        "ตอบเฉพาะชื่อสถานที่จากรายการข้างต้นเท่านั้น "
                        "ถ้าไม่มีที่ตรงให้ตอบว่า NONE"
                    ),
                },
                {"role": "user", "content": user_location},
            ],
            temperature=0,
            max_completion_tokens=30,
        )
        result = response.choices[0].message.content.strip()
        return None if result.upper() == "NONE" else result
    except Exception:
        return None


def ask(user_text: str) -> str:
    # Code-level map lookup — bypass LLM entirely
    stripped = user_text.strip()
    if stripped.lower().startswith("map "):
        location = stripped[4:].strip()
        result = _find_map_url(location)
        if not result:
            matched = _llm_resolve_location(location)
            if matched:
                result = _find_map_url(matched)
        if result:
            name, url = result
            return f"แผนที่ {name}:\n{url}"
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
