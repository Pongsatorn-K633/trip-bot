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

def ask(user_text: str) -> str:
    """
    Send user message to Typhoon API and return Thai reply.
    """
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
