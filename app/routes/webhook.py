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

from app.utils.llm_client import ask

# ---------------------------------------------------------------------------
# LINE SDK setup
# ---------------------------------------------------------------------------
_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
_ACCESS_TOKEN   = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

handler        = WebhookHandler(_CHANNEL_SECRET)
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
    body = (await request.body()).decode("utf-8")
    try:
        handler.handle(body, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid LINE signature")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    user_text: str = event.message.text

    reply_text: str = ask(user_text)

    with ApiClient(_configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )
