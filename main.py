from dotenv import load_dotenv

load_dotenv()  # Must run before any module reads os.getenv()

from fastapi import FastAPI
from app.routes.webhook import router as webhook_router

app = FastAPI(
    title="LINE Itinerary Bot",
    description="Stateless Thai-language chatbot for the Tokyo–Matsumoto trip itinerary.",
    version="1.0.0",
)

app.include_router(webhook_router)


@app.get("/health")
async def health_check() -> dict:
    """Simple liveness probe for deployment platforms."""
    return {"status": "ok"}
