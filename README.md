---
title: trip-bot
emoji: 🗾
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# trip-bot — LINE Itinerary Chatbot (Tokyo & Matsumoto)

A stateless Thai-language chatbot for the LINE Messaging API.
Users ask questions in Thai about a fixed travel itinerary and receive answers powered by the Typhoon LLM.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10+ | Install from [python.org](https://python.org) — pip + venv included |
| LINE Developers Account | — | Free at [developers.line.biz](https://developers.line.biz) |
| Typhoon API Key | — | Free at [playground.opentyphoon.ai](https://playground.opentyphoon.ai) |
| ngrok | 3.20.0+ | For local webhook testing |

---

## Project Structure

```
trip-bot/
├── main.py                   # App entry point
├── requirements.txt          # pip dependencies
├── .env                      # Your credentials (create this — never commit)
├── .env.example              # Template
├── data/
│   └── tokyo-matsumoto.json  # Itinerary data (single source of truth)
├── app/
│   ├── routes/webhook.py     # LINE webhook endpoint
│   └── utils/
│       └── llm_client.py     # Typhoon API client + system prompt
└── dev_tools/
    ├── learning_roadmap.md   # NLP → LLM learning path
    └── test_thainerwangchan.py  # Phase 2 NER experiments
```

---

## Setup

### Step 1 — Clone or open the project

Open the `trip-bot/` folder in VS Code (or any terminal).

### Step 2 — Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows
```

> Requires Python 3.10+. Check with `python --version`.

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `fastapi` + `uvicorn` — web framework and server
- `line-bot-sdk` — LINE Messaging API v3
- `openai` — Typhoon API client (OpenAI-compatible)
- `python-dotenv` — reads `.env` file
- `httpx` — required internally by line-bot-sdk

### Step 4 — Create your `.env` file

Copy the template and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` and set:

```env
LINE_CHANNEL_SECRET=your_channel_secret_here
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here
TYPHOON_API_KEY=your_typhoon_api_key_here
```

> How to get LINE credentials: see **LINE Developer Console Setup** below.
> How to get Typhoon API key: sign up at [playground.opentyphoon.ai](https://playground.opentyphoon.ai) → Settings → API Keys.

---

## LINE Developer Console Setup

> Skip this section if you already have a LINE Messaging API channel configured.

1. Go to [developers.line.biz](https://developers.line.biz) and log in
2. Create a **Provider** (your name or team name)
3. Create a new **Messaging API** channel inside that provider
4. In the channel settings:
   - Under **Basic settings** → copy **Channel secret** → paste to `.env` as `LINE_CHANNEL_SECRET`
   - Under **Messaging API** → issue a **Channel access token (long-lived)** → paste to `.env` as `LINE_CHANNEL_ACCESS_TOKEN`
5. Under **Messaging API** → turn **OFF** "Auto-reply messages" and "Greeting messages"
6. Leave the **Webhook URL** empty for now — you'll set it after starting the server

---

## Running the App

### Development (local)

```bash
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows
uvicorn main:app --reload --port 8000
```

The app starts at `http://localhost:8000`.

Verify it's running:
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Expose to LINE with ngrok

LINE requires a **public HTTPS URL** for the webhook. Use ngrok to tunnel your local server:

```bash
# In a separate terminal
ngrok http 8000
```

Copy the `https://` forwarding URL from ngrok output, for example:
```
https://a1b2c3d4.ngrok-free.app
```

Set the webhook URL in LINE Developers Console:

1. Go to your channel → **Messaging API** tab
2. Set **Webhook URL** to: `https://a1b2c3d4.ngrok-free.app/webhook`
3. Toggle **Use webhook** to **ON**
4. Click **Verify** — you should see "Success"

---

## Talking to the Bot

Add your LINE Official Account as a friend using the QR code in the LINE Developers Console (Messaging API tab).

The bot understands **free-form Thai** — no keywords required. Just ask naturally:

```
วันที่ 29 ทำอะไรบ้าง
วันแรกไปที่ไหน
คืนวันที่ 31 พักที่ไหน
จากมัตสึโมโตไปคามิโคจิยังไง
มีกิจกรรมอะไรวันที่ 2 มิถุนายน
```

> The itinerary covers **29 May – 8 June 2026**. Questions about dates outside this range will get a "no information" reply.

---

## Updating the Itinerary

Edit [data/tokyo-matsumoto.json](data/tokyo-matsumoto.json) directly. No code changes needed.

Each date entry follows this structure:

```json
"2026-06-01": [
  {
    "time": "07:00",
    "origin": "Hotel",
    "destination": "Hakuba",
    "activity": "ตื่นนอน เดินทางไป Hakuba",
    "travel_mode": "train"
  }
]
```

The full JSON is injected into the LLM system prompt on every request — changes take effect on the next server restart.

---

## Deploying to Production

### Option A — VPS / Cloud VM (pip + venv)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Use `systemd` or `supervisor` to keep the process running.

### Option B — Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t trip-bot .
docker run -p 8000:8000 --env-file .env trip-bot
```

### Option C — Managed Platforms (Railway, Render, Fly.io)

Push your code, set the three environment variables in the platform dashboard, and set the start command to:

```
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Import "fastapi" could not be resolved` in VS Code | Press `Ctrl+Shift+P` → Python: Select Interpreter → choose the `venv` interpreter |
| LINE Verify webhook returns error | Check that ngrok is running and the URL ends with `/webhook` |
| `InvalidSignatureError` | `LINE_CHANNEL_SECRET` in `.env` does not match the console value |
| `401` from LINE Reply API | `LINE_CHANNEL_ACCESS_TOKEN` is wrong or expired — reissue in console |
| Bot replies with error message | Check that `TYPHOON_API_KEY` is set in `.env` and the server was restarted after adding it |
| ngrok ERR_NGROK_334 | Old ngrok session still running — run `taskkill /IM ngrok.exe /F` then retry |
| ngrok version too old | Download latest from ngrok.com and run from the download folder |

---

## For Developers

See [developer_guide.md](developer_guide.md) for:
- Full architecture diagram
- Complete app flow walkthrough
- LLM system prompt details
- Phase 2 NER experiments and notes
- How to update the itinerary and extend the bot
