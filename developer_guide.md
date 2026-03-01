# Developer Guide — trip-bot

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Directory Structure](#2-directory-structure)
3. [Architecture](#3-architecture)
4. [App Flow — Request Lifecycle](#4-app-flow--request-lifecycle)
5. [Module Responsibilities](#5-module-responsibilities)
6. [Intent System (Phase 1)](#6-intent-system-phase-1)
7. [Data Schema — tokyo-matsumoto.json](#7-data-schema--tokyo-matsumotojson)
8. [Stateless Design — How Dates Work](#8-stateless-design--how-dates-work)
9. [Phase 2 Upgrade Path (ML NER)](#9-phase-2-upgrade-path-ml-ner)
10. [Adding New Intents](#10-adding-new-intents)
11. [Environment Variables](#11-environment-variables)
12. [Learning & Upgrade Roadmap](#12-learning--upgrade-roadmap)

---

## 1. Project Overview

A **stateless** Thai-language itinerary chatbot for the LINE Messaging API.
Users ask questions in Thai; the bot answers based on a fixed travel itinerary (Tokyo–Matsumoto).

| Property | Value |
|---|---|
| Language | Python 3.10+ |
| Framework | FastAPI |
| NLP (Phase 1) | PyThaiNLP — rule-based keyword matching |
| NLP (Phase 2) | WangchanBERTa fine-tuned for NER *(planned)* |
| Integration | LINE Messaging API v3 Webhook |
| State | **None** — fully stateless, driven by LINE event timestamps |

---

## 2. Directory Structure

```
trip-bot/
├── main.py                         # FastAPI app entry point & router registration
├── requirements.txt                # Phase 1 dependencies (pip)
├── .env                            # Secrets — LINE credentials (never commit)
├── .env.example                    # Template for .env
│
├── data/
│   └── tokyo-matsumoto.json        # Mock itinerary — the single source of truth
│
└── app/
    ├── routes/
    │   └── webhook.py              # POST /webhook — LINE event receiver & dispatcher
    │
    ├── engine/
    │   ├── tokenizer.py            # PyThaiNLP wrapper (newmm engine)
    │   └── intent_engine.py        # Phase 1: keyword → intent classification
    │
    ├── models/
    │   └── ner_placeholder.py      # Phase 2: WangchanBERTa NER stub
    │
    └── utils/
        └── response_builder.py     # Maps intent + timestamp → Thai reply string
```

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          LINE Platform                                  │
│                    (sends webhook POST request)                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  POST /webhook
                                │  Header: X-Line-Signature (HMAC-SHA256)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  main.py  —  FastAPI Application                                        │
│  • Loads .env credentials                                               │
│  • Registers /webhook router                                            │
│  • Exposes GET /health                                                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  app/routes/webhook.py                                                  │
│  1. Verify HMAC-SHA256 signature  →  400 if invalid                    │
│  2. Parse LINE event (MessageEvent + TextMessageContent)                │
│  3. Extract: user_text (str), timestamp_ms (int)                       │
│  4. Dispatch to Phase 1 engine (Phase 2 stub commented out)            │
└────────────┬─────────────────────────────────┬──────────────────────────┘
             │                                 │
             ▼                                 ▼
┌────────────────────────┐       ┌─────────────────────────────────────────┐
│  app/engine/           │       │  app/utils/response_builder.py          │
│  tokenizer.py          │       │  1. timestamp_ms → JST date string      │
│  • newmm tokenization  │──────▶│  2. ITINERARY[date] → today's events   │
│                        │       │  3. intent → pick fields → Thai string  │
│  intent_engine.py      │       └──────────────────┬──────────────────────┘
│  • keyword set lookup  │                          │
│  • returns intent name │              reply_text  │
└────────────────────────┘                          ▼
                                ┌─────────────────────────────────────────┐
                                │  LINE Reply API                         │
                                │  MessagingApi.reply_message(...)        │
                                └─────────────────────────────────────────┘

             ┌──────────────────────────────────────────────────────────┐
             │  app/models/ner_placeholder.py  (PHASE 2 — STUB)         │
             │  WangchanBERTa fine-tuned on LST20                       │
             │  Extracts: {origin: str, destination: str}               │
             │  Would SHORT-CIRCUIT Phase 1 when entities are found     │
             └──────────────────────────────────────────────────────────┘

             ┌──────────────────────────────────────────────────────────┐
             │  data/tokyo-matsumoto.json  (read-only at startup)       │
             │  Loaded once into memory — no DB, no file I/O per req   │
             └──────────────────────────────────────────────────────────┘
```

---

## 4. App Flow — Request Lifecycle

Below is the step-by-step flow for a single user message.

**Example:** User types `"วันนี้ทำอะไรบ้าง"` on 31 May 2026

```
Step 1  ── LINE Platform
           User sends message → LINE generates webhook POST

Step 2  ── app/routes/webhook.py : async def webhook()
           • Reads raw request body
           • Verifies X-Line-Signature (HMAC-SHA256 with CHANNEL_SECRET)
           • Calls handler.handle(body, signature)
           • Returns {"status": "ok"} to LINE immediately

Step 3  ── app/routes/webhook.py : handle_text_message(event)
           • user_text    = "วันนี้ทำอะไรบ้าง"
           • timestamp_ms = 1748649600000  (31 May 2026 00:00 UTC)

Step 4  ── app/engine/tokenizer.py : tokenize(user_text)
           PyThaiNLP newmm engine splits text:
           ["วันนี้", "ทำอะไร", "บ้าง"]

Step 5  ── app/engine/intent_engine.py : classify_intent(user_text)
           token set  ∩  INTENT_KEYWORDS["Ask_Activity"]
           "ทำอะไร" matches → returns "Ask_Activity"

Step 6  ── app/utils/response_builder.py : build_response("Ask_Activity", timestamp_ms)
           • 1748649600000 ms → UTC → JST → "2026-05-31"
           • ITINERARY["2026-05-31"] → 2 events found
           • intent == "Ask_Activity" → formats bullet list

Step 7  ── reply_text =
           "กิจกรรมวันนี้:
            • 06:00 น. ตื่นนอน เตรียมตัวไปกำแพงหิมะ
            • 07:30 น. เที่ยว Alpine Route"

Step 8  ── LINE Reply API
           MessagingApi.reply_message_with_http_info(reply_token, TextMessage)
           User receives the reply in LINE chat
```

---

## 5. Module Responsibilities

### `main.py`
- Creates the FastAPI application instance
- Calls `load_dotenv()` **before** any other import reads `os.getenv()`
- Registers the webhook router
- Exposes `GET /health` for deployment liveness probes

### `app/routes/webhook.py`
- Owns the `POST /webhook` HTTP endpoint
- Verifies LINE's HMAC-SHA256 signature — rejects invalid requests with HTTP 400
- Extracts `user_text` and `timestamp_ms` from the event
- Orchestrates Phase 1 (calls intent engine + response builder)
- Contains the commented Phase 2 NER block ready to activate
- Sends the final reply back via LINE Reply API

### `app/engine/tokenizer.py`
- Thin wrapper around `pythainlp.word_tokenize`
- Engine: `newmm` (dictionary-based, best general-purpose Thai tokenizer)
- Strips whitespace tokens, returns `list[str]`
- Isolated here so the engine can be swapped without touching intent logic

### `app/engine/intent_engine.py`
- Holds `INTENT_KEYWORDS` dict — the only place to add/edit keyword triggers
- Converts text → token set → intersects with each intent's keyword set
- Returns the first matched intent name, or `"Unknown"` as fallback
- Order of `INTENT_KEYWORDS` dict determines priority when multiple intents match

### `app/utils/response_builder.py`
- Loads `data/tokyo-matsumoto.json` **once at module import** (not per request)
- Converts `timestamp_ms` (UTC ms) → JST date string for itinerary lookup
- Maps `(intent, events)` → formatted Thai reply string
- All itinerary field access is in one place — add new intents here too

### `app/models/ner_placeholder.py`
- Documents the Phase 2 plan inside the stub
- `extract_entities()` raises `NotImplementedError` until implemented
- `Entities` TypedDict defines the contract for the webhook dispatcher

---

## 6. Intent System (Phase 1)

### Supported Intents

| Intent | Trigger Keywords (Thai) | JSON Fields Used |
|---|---|---|
| `Ask_Wakeup_Time` | ตื่น, ตื่นนอน, เช้า, เวลาตื่น | `events[0].time`, `events[0].activity` |
| `Ask_Today_Schedule` | วันนี้, กำหนดการ, แผน, ตาราง, โปรแกรม | all `time`, `activity`, `travel_mode` |
| `Ask_Next_Destination` | ต่อไป, ถัดไป, ไปที่ไหน, จุดหมาย, ปลายทาง | `events[-1].destination`, `activity` |
| `Ask_Travel_Mode` | ยังไง, รถไฟ, บัส, เครื่องบิน, พาหนะ | all `travel_mode` |
| `Ask_Activity` | ทำอะไร, กิจกรรม, เที่ยว, ไหว้, ช้อปปิ้ง | all `time`, `activity` |
| `Ask_Departure_Time` | กี่โมง, เวลาออก, ออกเดินทาง | `events[0].time`, `origin`, `destination` |
| `Unknown` | *(fallback — no keyword matched)* | — help text returned |

### Classification Algorithm

```python
tokens = set(tokenize(user_text))          # e.g., {"วันนี้", "ทำอะไร", "บ้าง"}

for intent, keywords in INTENT_KEYWORDS:
    if tokens ∩ set(keywords):             # set intersection
        return intent                       # first match wins

return "Unknown"
```

> **Priority note:** Because a Python dict preserves insertion order (Python 3.7+),
> `Ask_Wakeup_Time` is checked before `Ask_Today_Schedule`, and so on.
> Place more specific intents higher in `INTENT_KEYWORDS` to avoid shadowing.

---

## 7. Data Schema — tokyo-matsumoto.json

```jsonc
{
  "YYYY-MM-DD": [           // JST date key — must match _date_from_timestamp() output
    {
      "time": "HH:MM",      // 24-hour local time (JST) — used for wakeup/departure intents
      "origin": "...",      // Departure location — used by Ask_Departure_Time & Phase 2 NER
      "destination": "...", // Arrival location   — used by Ask_Next_Destination & Phase 2 NER
      "activity": "...",    // Thai description   — used by Ask_Activity, Ask_Wakeup_Time
      "travel_mode": "..."  // "train" | "bus" | "flight" | "walk" | "hike" | "none" | combinations
    }
  ]
}
```

**Date range:** `2026-05-29` through `2026-06-08` (JST)

To add a new trip day, append a new date key with its events array.
No code changes are needed — `response_builder.py` picks it up automatically.

---

## 8. Stateless Design — How Dates Work

The bot holds **zero session state**. Every request is self-contained:

```
LINE event.timestamp (UTC milliseconds)
         │
         │  datetime.fromtimestamp(ts / 1000, tz=UTC)
         ▼
   UTC datetime object
         │
         │  .astimezone(JST)   ← JST = UTC+9
         ▼
   JST datetime object
         │
         │  .strftime("%Y-%m-%d")
         ▼
   "2026-05-31"  ← used as key into ITINERARY dict
```

This means:
- No database, no session store, no cache needed
- Two users messaging at the same moment always get the same day's itinerary
- Works correctly across midnight (UTC vs JST boundary handled by the conversion)

---

## 9. Phase 2 Upgrade Path (ML NER)

### Goal
Extract free-form location entities from Thai text to answer custom routing queries.

**Example:** `"จากฮาคุบะไปคามิโคจิยังไง"` → `{origin: "ฮาคุบะ", destination: "คามิโคจิ"}`

### Implementation Plan

| Step | Task |
|---|---|
| 1 | Fine-tune `airesearch/wangchanberta-base-att-spm-uncased` on LST20 with a BIO token-classification head |
| 2 | Save checkpoint to `app/models/checkpoints/wangchanberta-ner/` |
| 3 | Implement `extract_entities()` in `app/models/ner_placeholder.py` using `transformers.pipeline("ner", aggregation_strategy="simple")` |
| 4 | In `webhook.py`, uncomment the Phase 2 block — it SHORT-CIRCUITs Phase 1 when both entities are found |
| 5 | Call a Map API (Google Maps Directions) with the extracted entities |

### Activation in webhook.py

```python
# Uncomment this block in handle_text_message():
try:
    entities = extract_entities(user_text)
    if entities["origin"] and entities["destination"]:
        reply_text = fetch_route(entities["origin"], entities["destination"])
except NotImplementedError:
    pass  # Falls through to Phase 1 result
```

### Pre-trained Model Cache (local)

WangchanBERTa is downloaded from HuggingFace Hub on first use and cached locally:

```
C:\Users\WindowS 10\.cache\huggingface\hub\
└── models--airesearch--wangchanberta-base-att-spm-uncased\
    └── snapshots\
        └── b81d38df6b4755dbedec0bfea863c9956cbb963e\
            ├── config.json
            ├── sentencepiece.bpe.model
            └── tokenizer_config.json
```

After the first download, `from_pretrained()` loads from cache — no internet required.

### New dependencies (add to requirements.txt)

```
transformers>=4.40.0
torch>=2.2.0
sentencepiece>=0.1.99
protobuf>=4.0.0
tiktoken>=0.6.0
accelerate>=0.27.0   # fine-tuning only
```

---

## 10. Adding New Intents

To add a new intent (e.g., `Ask_Hotel_Info`):

**Step 1** — Add keywords to `app/engine/intent_engine.py`:
```python
"Ask_Hotel_Info": ["โรงแรม", "ที่พัก", "เช็คอิน", "เช็คเอาท์", "ห้อง"],
```

**Step 2** — Add a response handler to `app/utils/response_builder.py`:
```python
elif intent == "Ask_Hotel_Info":
    checkin = next((e for e in events if "เช็คอิน" in e["activity"]), None)
    if checkin:
        return f"เช็คอินเวลา {checkin['time']} น. ที่ {checkin['destination']} ค่ะ"
    return "ไม่มีข้อมูลโรงแรมสำหรับวันนี้ค่ะ"
```

No other files need to be changed.

---

## 11. Environment Variables

| Variable | Description | Where to get it |
|---|---|---|
| `LINE_CHANNEL_SECRET` | Used to verify webhook signatures (HMAC-SHA256) | LINE Developers Console → Messaging API → Channel secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | Used to call the LINE Reply API | LINE Developers Console → Messaging API → Channel access token (long-lived) |

Store these in `.env` (never commit this file). See `.env.example` for the template.

---

## 12. Learning & Upgrade Roadmap

This section documents the planned learning path from the current rule-based Phase 1 bot through ML-based NER (Phase 2) to a production LLM-powered chatbot (Phase 3).

---

### Phase 2 — ML-based NLP & Named Entity Recognition

The goal is to understand how transformers process Thai text and to fine-tune WangchanBERTa for NER.

| Step | Topic | What you learn |
|---|---|---|
| 1 | **Text preprocessing** | Why subword tokenization (SentencePiece/BPE) outperforms word-level tokenization for Thai; vocabulary size trade-offs |
| 2 | **Transformer architecture** | Attention mechanism, encoder-only vs. decoder-only models, how BERT/RoBERTa produce contextual embeddings |
| 3 | **NER & BIO tagging** | BIO scheme (B-LOC, I-LOC, O), token-classification head, how the model labels each subword |
| 4 | **Fine-tuning WangchanBERTa** | Load `airesearch/wangchanberta-base-att-spm-uncased`, attach a classification head, train on LST20 NER dataset |
| 5 | **Bot integration** | Implement `extract_entities()` in `app/models/ner_placeholder.py`; uncomment the Phase 2 block in `webhook.py` |

**Why WangchanBERTa instead of PyThaiNLP for Phase 2?**

PyThaiNLP uses dictionary-based word tokenization — fast but produces fixed vocabulary tokens.
WangchanBERTa uses SentencePiece subword tokenization trained on 78 GB of Thai text,
producing contextual embeddings that capture word meaning from surrounding context.
This is required for NER: the same word (e.g., "มัตสึโมโต") can be a location or a person name depending on context.

**Recommended study order:**

```
1. Read the WangchanBERTa paper (arxiv.org/abs/2101.09635)
2. Work through HuggingFace "Token Classification" tutorial
3. Explore the LST20 dataset structure to understand BIO labels
4. Run the fine-tuning notebook locally (requires accelerate — see requirements.txt)
5. Swap the stub in ner_placeholder.py with the trained pipeline
```

---

### Phase 3 — LLM-powered Chatbot (Production Standard)

The goal is to understand why Large Language Models replace intent engines entirely, and how to integrate one into the bot.

| Step | Topic | What you learn |
|---|---|---|
| 1 | **Why LLMs differ** | Decoder-only architecture, autoregressive generation, emergent instruction-following without task-specific fine-tuning |
| 2 | **Prompt engineering** | System prompts, few-shot examples, structured output (JSON mode), temperature/top-p control |
| 3 | **Context injection (RAG)** | Embed the itinerary JSON into the prompt; for larger documents, use vector search to retrieve only relevant chunks |
| 4 | **Replace the intent engine** | Remove `intent_engine.py` and `response_builder.py`; pass `user_text + itinerary context` directly to the LLM API |

**What a Phase 3 webhook handler looks like (conceptually):**

```python
system_prompt = f"""
คุณเป็นผู้ช่วยท่องเที่ยวภาษาไทย ตอบตามข้อมูลทริปต่อไปนี้เท่านั้น:
{json.dumps(ITINERARY, ensure_ascii=False)}
"""

reply_text = llm_client.chat(
    system=system_prompt,
    user=user_text,
)
```

The LLM handles date extraction, intent detection, and response formatting in one step — no rules required.

**RAG is needed when:**
- The itinerary is too large to fit in the context window
- You want to answer questions across multiple trips
- You need to retrieve from external knowledge bases

---

### Architecture Evolution Summary

| Phase | NLP Approach | Thai Tokenizer | Date Handling | Flexibility |
|---|---|---|---|---|
| **1 (current)** | Keyword set intersection | PyThaiNLP newmm | Regex + timestamp | Low — every case hand-coded |
| **2 (next)** | WangchanBERTa NER | SentencePiece BPE | Extracted entity | Medium — handles free-form locations |
| **3 (production)** | LLM + context injection | Model-internal | LLM infers | High — understands arbitrary Thai queries |
