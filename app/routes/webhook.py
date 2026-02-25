import os

from fastapi import APIRouter, Header, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.engine.intent_engine import classify_intent
from app.utils.response_builder import build_response

# Phase 2 — uncomment when WangchanBERTa NER model is ready:
# from app.models.ner_placeholder import extract_entities

# ---------------------------------------------------------------------------
# LINE SDK setup (credentials loaded from .env via main.py → dotenv)
# ---------------------------------------------------------------------------
_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

handler = WebhookHandler(_CHANNEL_SECRET)
_configuration = Configuration(access_token=_ACCESS_TOKEN)

router = APIRouter()


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def webhook(
    request: Request,
    x_line_signature: str = Header(alias="X-Line-Signature"),
) -> dict:
    """
    Receives LINE platform webhook events.
    Verifies the HMAC-SHA256 signature before processing.
    """
    body = (await request.body()).decode("utf-8")

    try:
        handler.handle(body, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid LINE signature")

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Message event handler
# ---------------------------------------------------------------------------

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    """
    Main dispatch logic for incoming Thai text messages.

    timestamp_ms (int): UTC milliseconds from the LINE event.
                        Used to derive the current JST date for itinerary lookups,
                        keeping the bot fully stateless.
    """
    user_text: str = event.message.text
    timestamp_ms: int = event.timestamp  # UTC ms — drives all date lookups

    # ── Phase 1: Rule-Based Intent Engine ────────────────────────────────────
    intent = classify_intent(user_text)
    reply_text = build_response(intent=intent, timestamp_ms=timestamp_ms, user_text=user_text)

    # ── Phase 2 Placeholder: ML Named Entity Recognition ─────────────────────
    # Uncomment the block below once the WangchanBERTa NER model is trained.
    # It should SHORT-CIRCUIT Phase 1 when both entities are confidently found.
    #
    # try:
    #     entities = extract_entities(user_text)
    #     if entities["origin"] and entities["destination"]:
    #         reply_text = fetch_route(entities["origin"], entities["destination"])
    # except NotImplementedError:
    #     pass  # Fall through to Phase 1 result above

    # ── Send reply ───────────────────────────────────────────────────────────
    with ApiClient(_configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )
