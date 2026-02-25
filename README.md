# trip-bot — LINE Itinerary Chatbot (Tokyo & Matsumoto)

A stateless Thai-language chatbot for the LINE Messaging API.
Users ask questions in Thai about a fixed travel itinerary and receive answers instantly.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10+ | Install from [python.org](https://python.org) — pip + venv included |
| LINE Developers Account | — | Free at [developers.line.biz](https://developers.line.biz) |
| ngrok | any | For local webhook testing |

---

## Project Structure

```
trip-bot/
├── main.py                   # App entry point
├── requirements.txt          # pip dependencies
├── .env                      # Your LINE credentials (create this)
├── .env.example              # Template
├── data/
│   └── tokyo-matsumoto.json  # Itinerary data
└── app/
    ├── routes/webhook.py     # LINE webhook endpoint
    ├── engine/
    │   ├── tokenizer.py      # Thai tokenizer
    │   └── intent_engine.py  # Rule-based intent matching
    ├── models/
    │   └── ner_placeholder.py  # Phase 2 NER stub
    └── utils/
        └── response_builder.py  # Builds Thai replies
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
- `fastapi` — web framework
- `uvicorn` — ASGI server
- `line-bot-sdk` — LINE Messaging API v3
- `pythainlp` — Thai NLP tokenizer
- `python-dotenv` — reads `.env` file
- `httpx` — HTTP client (required by line-bot-sdk)

### Step 4 — Create your `.env` file

Copy the template and fill in your LINE credentials:

```bash
cp .env.example .env
```

Open `.env` and set:

```env
LINE_CHANNEL_SECRET=your_channel_secret_here
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here
```

> How to get these values: see **LINE Developer Console Setup** below.

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

The interactive API docs are available at `http://localhost:8000/docs`.

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

Then send any of these Thai messages:

| Thai Message | Intent Triggered | Example Reply |
|---|---|---|
| `วันนี้ทำอะไรบ้าง` | Ask_Activity | กิจกรรมวันนี้: • 06:00 น. ตื่นนอน... |
| `กำหนดการวันนี้` | Ask_Today_Schedule | 📅 กำหนดการวันที่ 2026-05-31:... |
| `ตื่นกี่โมง` | Ask_Wakeup_Time | วันที่ ... ตื่นนอนเวลา 06:00 น. ค่ะ |
| `ไปที่ไหนต่อ` | Ask_Next_Destination | จุดหมายสุดท้ายของวันนี้คือ... |
| `เดินทางยังไง` | Ask_Travel_Mode | วันนี้เดินทางด้วย: bus/train, train ค่ะ |
| `ออกเดินทางกี่โมง` | Ask_Departure_Time | ออกเดินทางครั้งแรกวันนี้เวลา... |

> The bot answers based on the **current JST date**. Itinerary dates run from **29 May – 8 June 2026**. Messages sent outside this range will receive a "no schedule found" reply.

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

---

## Deploying to Production

For production, **do not use conda**. Use pip with a clean Python environment or Docker.

### Option A — VPS / Cloud VM (pip + venv)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Use `systemd` or `supervisor` to keep the process running.

### Option B — Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t line-itinerary-bot .
docker run -p 8000:8000 --env-file .env line-itinerary-bot
```

### Option C — Managed Platforms (Railway, Render, Fly.io)

These platforms support pip natively. Push your code, set the two environment variables in the platform dashboard, and set the start command to:

```
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then update the LINE webhook URL to your platform's public URL.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Import "fastapi" could not be resolved` in VS Code | Press `Ctrl+Shift+P` → Python: Select Interpreter → choose the `venv` interpreter |
| LINE Verify webhook returns error | Check that ngrok is running and the URL ends with `/webhook` |
| Bot replies "ไม่พบกำหนดการ..." | The current JST date is outside `2026-05-29` to `2026-06-08` |
| `InvalidSignatureError` | `LINE_CHANNEL_SECRET` in `.env` does not match the console value |
| `401` from LINE Reply API | `LINE_CHANNEL_ACCESS_TOKEN` is wrong or expired — reissue in console |

---

## For Developers

See [developer_guide.md](developer_guide.md) for:
- Full architecture diagram
- Complete app flow walkthrough
- Intent system details
- How to add new intents
- Phase 2 ML NER upgrade plan
