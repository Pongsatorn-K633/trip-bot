# Developer Guide — trip-bot

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Directory Structure](#2-directory-structure)
3. [Architecture](#3-architecture)
4. [App Flow — Request Lifecycle](#4-app-flow--request-lifecycle)
5. [Module Responsibilities](#5-module-responsibilities)
6. [LLM System (Phase 3)](#6-llm-system-phase-3)
7. [Data Schema — tokyo-matsumoto.json](#7-data-schema--tokyo-matsumotojson)
8. [Stateless Design](#8-stateless-design)
9. [Phase 2 Reference (ML NER)](#9-phase-2-reference-ml-ner)
10. [Environment Variables](#10-environment-variables)
11. [Learning & Upgrade Roadmap](#11-learning--upgrade-roadmap)

---

## 1. Project Overview

A **stateless** Thai-language itinerary chatbot for the LINE Messaging API.
Users ask questions in Thai; the bot answers based on a fixed travel itinerary (Tokyo–Matsumoto).

| Property | Value |
|---|---|
| Language | Python 3.10+ |
| Framework | FastAPI |
| LLM | Typhoon API (`typhoon-v2.5-30b-a3b-instruct`) via OpenAI-compatible SDK |
| Integration | LINE Messaging API v3 Webhook |
| State | **None** — fully stateless |

---

## 2. Directory Structure

```
trip-bot/
├── main.py                         # FastAPI app entry point & router registration
├── requirements.txt                # pip dependencies
├── .env                            # Secrets — credentials (never commit)
├── .env.example                    # Template for .env
│
├── data/
│   └── tokyo-matsumoto.json        # Itinerary — single source of truth
│
├── app/
│   ├── routes/
│   │   └── webhook.py              # POST /webhook — LINE event receiver
│   └── utils/
│       └── llm_client.py           # Typhoon API client + system prompt
│
└── dev_tools/
    ├── learning_roadmap.md         # NLP → LLM learning path
    └── test_thainerwangchan.py     # Phase 2 NER experiments (WangchanBERTa)
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
│  • load_dotenv() — must run before any os.getenv()                     │
│  • Registers /webhook router                                            │
│  • Exposes GET /health                                                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  app/routes/webhook.py                                                  │
│  1. Verify HMAC-SHA256 signature  →  400 if invalid                    │
│  2. Parse LINE event (MessageEvent + TextMessageContent)                │
│  3. Pass raw user_text to llm_client.ask()                             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  user_text (raw Thai string)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  app/utils/llm_client.py                                                │
│  • Itinerary JSON loaded once at startup → injected into system prompt │
│  • OpenAI SDK with base_url = https://api.opentyphoon.ai/v1            │
│  • Model: typhoon-v2.5-30b-a3b-instruct                                │
│  • Returns Thai reply string                                            │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  POST /v1/chat/completions
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Typhoon API (cloud)                                                    │
│  • Receives: system prompt (itinerary JSON) + user message             │
│  • Generates: Thai reply grounded in itinerary data                    │
│  • Returns: choices[0].message.content                                 │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  reply_text
                                ▼
                  LINE Reply API — sends reply to user

             ┌──────────────────────────────────────────────────────────┐
             │  data/tokyo-matsumoto.json  (read-only at startup)       │
             │  Loaded once into memory — no DB, no file I/O per req   │
             └──────────────────────────────────────────────────────────┘
```

---

## 4. App Flow — Request Lifecycle

Below is the step-by-step flow for a single user message.

**Example:** User types `"วันที่ 29 ทำอะไรบ้าง"`

```
Step 1  ── LINE Platform
           User sends message → LINE generates webhook POST

Step 2  ── app/routes/webhook.py : async def webhook()
           • Reads raw request body
           • Verifies X-Line-Signature (HMAC-SHA256 with CHANNEL_SECRET)
           • Calls handler.handle(body, signature)
           • Returns {"status": "ok"} to LINE immediately

Step 3  ── app/routes/webhook.py : handle_text_message(event)
           • user_text = "วันที่ 29 ทำอะไรบ้าง"
           • Calls ask(user_text)

Step 4  ── app/utils/llm_client.py : ask(user_text)
           • Builds messages:
             - system: _SYSTEM_PROMPT  (Thai assistant rules + full itinerary JSON)
             - user:   "วันที่ 29 ทำอะไรบ้าง"
           • POST https://api.opentyphoon.ai/v1/chat/completions
             model: typhoon-v2.5-30b-a3b-instruct
             temperature: 0.6 / top_p: 0.6 / max_completion_tokens: 4096

Step 5  ── Typhoon API
           Reads full itinerary in context → identifies "วันที่ 29" = 2026-05-29
           Generates grounded Thai reply from itinerary data

Step 6  ── reply_text =
           "วันที่ 29 พฤษภาคม กิจกรรมมีดังนี้:
            • 06:00 น. ตื่นนอน เตรียมตัว
            • ..."

Step 7  ── LINE Reply API
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
- Extracts `user_text` from the event
- Calls `ask(user_text)` from `llm_client` and sends reply via LINE Reply API

### `app/utils/llm_client.py`
- Loads `data/tokyo-matsumoto.json` **once at startup** and serializes to string
- Builds the system prompt: Thai assistant persona + itinerary rules + full JSON
- Creates an `OpenAI` client pointed at `https://api.opentyphoon.ai/v1`
- `ask(user_text)` — sends system + user message, returns `choices[0].message.content`
- API key read from `TYPHOON_API_KEY` env var
- Model: `typhoon-v2.5-30b-a3b-instruct`

---

## 6. LLM System (Phase 3)

### System Prompt Structure

```python
_SYSTEM_PROMPT = f"""คุณเป็นผู้ช่วยท่องเที่ยวภาษาไทย ชื่อ "ทริปบอท"

ทริปนี้อยู่ในช่วงวันที่ 29 พฤษภาคม – 8 มิถุนายน 2569 (ค.ศ. 2026)

กฎ:
- ตอบตามข้อมูลกำหนดการด้านล่างเท่านั้น
- ห้ามแต่งหรือเพิ่มข้อมูลที่ไม่มีในกำหนดการ
- ตอบเป็นภาษาไทย กระชับและชัดเจน
- ถ้าไม่มีข้อมูลที่ถามให้บอกตรงๆ ว่าไม่มีข้อมูล

กำหนดการทริป:
{_ITINERARY_TEXT}"""   # ← full JSON injected here (~2600 tokens)
```

The LLM handles everything the old Phase 1 code did manually:

| Phase 1 needed | LLM does automatically |
|---|---|
| Regex for date extraction | Reads "วันที่ 29" in context → understands it |
| Gazetteer for place names | Matches places from the injected JSON |
| Intent classification | Infers what the user wants from phrasing |
| Typo handling | Predicts most likely meaning from context |

### Why Full Context Injection (not RAG)

The itinerary JSON is ~2600 tokens — well within the 128K context window.
No vector search or retrieval needed — the LLM reads all data every request.

RAG would only be needed if data grew beyond the context limit (100+ trips, external guides, etc.).

### Model Parameters

| Parameter | Value | Reason |
|---|---|---|
| `temperature` | 0.6 | Focused but not rigid |
| `top_p` | 0.6 | Reduces unlikely token sampling |
| `max_completion_tokens` | 4096 | Total budget: ~2635 prompt + ~1461 reply |

> Note: Typhoon's `max_completion_tokens` is the **total** limit (prompt + output), not output-only.

---

## 7. Data Schema — tokyo-matsumoto.json

> To change the bot's knowledge: edit this file and restart the server. No code changes needed.

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

## 8. Stateless Design

The bot holds **zero session state**. Every request is self-contained:

- No database, no session store, no cache
- The full itinerary JSON is re-injected into the system prompt on every call
- Date/time context is determined by the LLM reading the user's message
- Two users asking the same question at the same time get the same answer

---

## 9. Phase 2 Reference (ML NER)

> Phase 2 was a learning exercise — the production bot uses LLM (Phase 3).
> NER experiments are in `dev_tools/test_thainerwangchan.py`.

### Entity Extraction Strategy — Which Tool for What

Testing `Porameht/wangchanberta-thainer-corpus-v2-2` on itinerary queries revealed that
different entity types need different extraction tools:

| Entity | Example | Best Tool | Reason |
|---|---|---|---|
| Date with month | `"29 พ.ค."`, `"29 พฤษภาคม"` | **Regex** | Fixed pattern; NER returns `''` artifact |
| Date without month | `"วันที่ 29"` | **Regex** | `\d+` pattern is simpler and reliable |
| Time | `"15:00"`, `"บ่ายสาม"` | **Regex** | NER produces `''` and `'.'` subword artifacts |
| Known place names | `"มัตสึโมโต"`, `"ฮาคุบะ"` | **Gazetteer** | Itinerary is fixed; NER gives partial match at low score |
| Unknown place names | Any arbitrary city | **NER** | Can't enumerate; NER handles open vocabulary |

**Decision rule:**
```
Is the set of possible values finite and known in advance?
    YES → Gazetteer (exact match) or Regex (pattern match)
    NO  → NER (open vocabulary, but needs fine-tuning for domain-specific names)
```

**Recommended hybrid pipeline:**
```python
# 1. Date → Regex (existing response_builder.py logic — keep as-is)
date = _extract_date_from_text(user_text)

# 2. Known places → Gazetteer
KNOWN_PLACES = ["มัตสึโมโต", "คามิโคจิ", "ฮาคุบะ", "โตเกียว"]
location = next((p for p in KNOWN_PLACES if p in user_text), None)

# 3. Unknown places → NER (after fine-tuning, with artifact filtering)
if not location:
    location = extract_location_via_ner(user_text)  # filter empty/punctuation results
```

**NER artifact filtering** (always apply in production):
```python
for ent in ner_results:
    word = ent["word"].strip()
    if not word or word in {".", ",", ":", "-"}:
        continue  # skip empty string and punctuation artifacts
    if ent["score"] < 0.7:
        continue  # skip low-confidence predictions
```

NER's real value for this bot arrives **after fine-tuning** — when trips expand beyond the hard-coded place list.

### NER Output Artifacts — Are They Normal?

**Yes — `''` and `'.'` artifacts are a known post-processing issue, not a model defect.**

Root cause: `aggregation_strategy="simple"` reconstructs words by stripping the `▁` (SentencePiece word-start prefix). Two edge cases produce garbage:

| Artifact | Why it happens |
|---|---|
| `''` (empty string) | Token was only `▁` (a space piece with no word characters); stripping `▁` leaves nothing |
| `'.'` (punctuation) | Abbreviation like `น.` gets split into `น` + `.`; the `.` piece survives aggregation as a standalone entity |

The NER model itself classified correctly — the artifact is in the text reconstruction step only.

**Every production NER system applies post-processing filters.** Raw NER output is never used directly:

```
NER raw output  →  filter empty/punctuation  →  filter low score  →  merge with gazetteer  →  bot logic
```

**Is NER unsuitable for chatbots because of this?**

No. NER is widely used in production chatbots — but always as one layer in a pipeline:

| Problem observed | Root cause | Fix |
|---|---|---|
| `''` artifact | Subword space piece | Filter empty strings |
| `'.'` artifact | Punctuation in abbreviation | Filter punctuation tokens |
| Partial place name (`'มัตสึ'`) | Japanese names rare in training data | Fine-tune or use gazetteer |
| Date `"29"` not extracted | Model expects richer date context | Use regex instead |

The NER artifacts are predictable and filterable. The bigger limitation for this bot is the **domain mismatch** (Japanese place names in Thai training data) — which is solved by fine-tuning or a gazetteer.

### Pre-trained Model Cache (local)

All HuggingFace models are downloaded on first use and cached at:

```
C:\Users\WindowS 10\.cache\huggingface\hub\
```

> **Note:** This is a hidden folder. Enable "Show hidden items" in File Explorer to see it.

Models downloaded so far:

```
C:\Users\WindowS 10\.cache\huggingface\hub\
│
├── models--airesearch--wangchanberta-base-att-spm-uncased\
│   └── snapshots\
│       └── b81d38df6b4755dbedec0bfea863c9956cbb963e\
│           ├── config.json
│           ├── sentencepiece.bpe.model
│           └── tokenizer_config.json
│
└── models--Porameht--wangchanberta-thainer-corpus-v2-2\
    └── snapshots\
        └── <snapshot-hash>\
            ├── config.json          ← includes id2label (32 NER labels)
            ├── pytorch_model.bin    ← fine-tuned weights (~500 MB)
            └── tokenizer files
```

| Model | Purpose |
|---|---|
| `airesearch/wangchanberta-base-att-spm-uncased` | Base encoder — tokenizer experiments, Step 1 learning |
| `Porameht/wangchanberta-thainer-corpus-v2-2` | Fine-tuned NER — LOCATION, DATE, TIME, FACILITY extraction |

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

## 10. Environment Variables

| Variable | Description | Where to get it |
|---|---|---|
| `LINE_CHANNEL_SECRET` | Verifies webhook signatures (HMAC-SHA256) | LINE Developers Console → Basic settings → Channel secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | Calls the LINE Reply API | LINE Developers Console → Messaging API → Channel access token (long-lived) |
| `TYPHOON_API_KEY` | Authenticates requests to Typhoon LLM API | [playground.opentyphoon.ai](https://playground.opentyphoon.ai) → Settings → API Keys |

Store these in `.env` (never commit this file). See `.env.example` for the template.

---

## 11. Learning & Upgrade Roadmap

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

### Phase 3 — LLM-powered Chatbot (Current — Done)

The bot now uses full context injection: the entire itinerary JSON is pasted into the system prompt on every request. The LLM handles date parsing, place matching, intent inference, and Thai generation in one step.

See [Section 6](#6-llm-system-phase-3) for prompt structure and model parameters.

**Current stack:**
- Model: `typhoon-v2.5-30b-a3b-instruct` (Typhoon API, free tier)
- SDK: `openai` Python SDK with `base_url="https://api.opentyphoon.ai/v1"`
- No RAG, no NER, no entity extraction — LLM reads everything directly

**When RAG becomes necessary:**
- 10+ trips where full JSON no longer fits in context window
- Answering questions across external documents (hotel reviews, transport guides)
- For the current single-trip bot: **not needed**

---

### Architecture Evolution Summary

| Phase | Entity Extraction | Response Generation | Status |
|---|---|---|---|
| **1** | Keyword set intersection | Hardcoded templates | Replaced |
| **2** | WangchanBERTa NER | Hardcoded templates | Learning only (dev_tools) |
| **3** | LLM reads full JSON | Typhoon API (cloud) | **Current** |
