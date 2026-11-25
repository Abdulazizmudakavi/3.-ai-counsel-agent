from __future__ import annotations

from fastapi import FastAPI

from counsel.config import get_settings
from counsel.policy.sender import SEND_ENABLED

app = FastAPI(title="AI Corporate Counsel Agent (prototype)")


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "env": get_settings().env, "send_enabled": SEND_ENABLED}
