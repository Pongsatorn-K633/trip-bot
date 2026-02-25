from app.engine.tokenizer import tokenize

# ---------------------------------------------------------------------------
# Intent → Thai keyword triggers
# Add more keywords here to improve recall without changing any other module.
# ---------------------------------------------------------------------------
INTENT_KEYWORDS: dict[str, list[str]] = {
    "Ask_Wakeup_Time": [
        "ตื่น", "ตื่นนอน", "เช้า", "เวลาตื่น", "ตื่นกี่โมง",
    ],
    "Ask_Today_Schedule": [
        "วันนี้", "กำหนดการ", "แผน", "ตาราง", "โปรแกรม", "plan", "schedule",
    ],
    "Ask_Next_Destination": [
        "ต่อไป", "ถัดไป", "ไปที่ไหน", "จุดหมาย", "ปลายทาง", "ไปไหน", "ไปต่อ",
    ],
    "Ask_Travel_Mode": [
        "ยังไง", "วิธีไป", "รถไฟ", "บัส", "รถ", "เดิน", "เที่ยวบิน",
        "เครื่องบิน", "พาหนะ", "นั่งอะไร",
    ],
    "Ask_Activity": [
        "ทำอะไร", "กิจกรรม", "เที่ยว", "ดู", "ไหว้", "ช้อปปิ้ง", "ซื้อ",
    ],
    "Ask_Departure_Time": [
        "กี่โมง", "เวลาออก", "ออกเดินทาง", "นัด", "เวลาเดินทาง",
    ],
}

FALLBACK_INTENT = "Unknown"


def classify_intent(text: str) -> str:
    """
    Phase 1 — Rule-based intent classification.

    Tokenizes the input Thai text, then checks each token against the
    INTENT_KEYWORDS dictionary.  Returns the first matched intent name,
    or FALLBACK_INTENT ('Unknown') when no keyword is found.
    """
    tokens = set(tokenize(text))

    for intent, keywords in INTENT_KEYWORDS.items():
        if tokens.intersection(set(keywords)):
            return intent

    return FALLBACK_INTENT
