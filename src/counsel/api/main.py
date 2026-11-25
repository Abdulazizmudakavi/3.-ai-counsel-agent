from __future__ import annotations

from fastapi import FastAPI

from counsel.api.stub_routes import router as stub_router
from counsel.config import get_settings
from counsel.policy.sender import SEND_ENABLED

app = FastAPI(
    title="AI Corporate Counsel Agent (prototype)",
    description="Stub flow: try POST /stub/samples/{name}, then the review queue. "
    "Nothing is ever sent.",
)
app.include_router(stub_router)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "env": get_settings().env, "send_enabled": SEND_ENABLED}
