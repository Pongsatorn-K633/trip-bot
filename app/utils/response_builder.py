import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Load itinerary once at module level — stateless, read-only.
# Using the LINE event timestamp (UTC ms) to derive the current JST date
# avoids any server-side session state.
# ---------------------------------------------------------------------------
_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "tokyo-matsumoto.json"

with open(_DATA_PATH, encoding="utf-8") as _f:
    ITINERARY: dict[str, list[dict]] = json.load(_f)

JST = timezone(timedelta(hours=9))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_from_timestamp(timestamp_ms: int) -> str:
    """Convert LINE event timestamp (ms, UTC) → JST date string YYYY-MM-DD."""
    dt_utc = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return dt_utc.astimezone(JST).strftime("%Y-%m-%d")


def _events_for_day(timestamp_ms: int) -> tuple[str, list[dict]]:
    """Return (date_str, list_of_events) for the day of the given timestamp."""
    date_str = _date_from_timestamp(timestamp_ms)
    return date_str, ITINERARY.get(date_str, [])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_response(intent: str, timestamp_ms: int) -> str:
    """
    Map a classified intent + timestamp to a Thai reply string.
    All itinerary lookups are keyed on the JST date derived from timestamp_ms.
    """
    today, events = _events_for_day(timestamp_ms)

    if not events:
        return (
            f"ไม่พบกำหนดการสำหรับวันที่ {today} ในแผนการเดินทางนะคะ 🗓️\n"
            "วันท่องเที่ยวอยู่ระหว่าง 29 พ.ค. – 8 มิ.ย. 2569 ค่ะ"
        )

    if intent == "Ask_Wakeup_Time":
        first = events[0]
        return (
            f"วันที่ {today} ตื่นนอนหรือเริ่มต้นวันเวลา {first['time']} น. ค่ะ\n"
            f"กิจกรรมแรก: {first['activity']}"
        )

    elif intent == "Ask_Today_Schedule":
        lines = [f"📅 กำหนดการวันที่ {today}:"]
        for e in events:
            mode = f" ({e['travel_mode']})" if e["travel_mode"] != "none" else ""
            lines.append(f"  {e['time']} น. — {e['activity']}{mode}")
        return "\n".join(lines)

    elif intent == "Ask_Next_Destination":
        last = events[-1]
        return (
            f"จุดหมายสุดท้ายของวันนี้คือ {last['destination']} ค่ะ\n"
            f"({last['activity']})"
        )

    elif intent == "Ask_Travel_Mode":
        modes = sorted({e["travel_mode"] for e in events if e["travel_mode"] != "none"})
        return f"วันนี้เดินทางด้วย: {', '.join(modes)} ค่ะ"

    elif intent == "Ask_Activity":
        lines = ["กิจกรรมวันนี้:"]
        for e in events:
            lines.append(f"• {e['time']} น. {e['activity']}")
        return "\n".join(lines)

    elif intent == "Ask_Departure_Time":
        first = events[0]
        return (
            f"ออกเดินทางครั้งแรกวันนี้เวลา {first['time']} น. ค่ะ\n"
            f"จาก {first['origin']} → {first['destination']}"
        )

    else:  # Unknown / fallback
        return (
            "ขอโทษนะคะ ไม่เข้าใจคำถามค่ะ 😊 ลองถามเกี่ยวกับ:\n"
            "• กำหนดการวันนี้\n"
            "• จุดหมายถัดไป\n"
            "• เวลาตื่นนอน\n"
            "• วิธีการเดินทาง\n"
            "• กิจกรรมวันนี้\n"
            "• เวลาออกเดินทาง"
        )
