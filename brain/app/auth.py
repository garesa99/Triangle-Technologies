"""Bearer-token auth. Same token node->brain and node->node. No accounts, no cloud."""
from __future__ import annotations

from fastapi import Header, HTTPException, Query

from .config import settings


def require_token(authorization: str = Header(default="")) -> None:
    expected = f"Bearer {settings.token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")


def require_token_ws(token: str = Query(default="")) -> bool:
    """Websockets can't set headers in the browser — accept ?token= for the UI."""
    return token == settings.token
