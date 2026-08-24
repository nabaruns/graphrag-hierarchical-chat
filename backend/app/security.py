"""Abuse protection: per-IP rate limiting and Cloudflare Turnstile verification.

Both are exposed as FastAPI dependencies and attached to the expensive
endpoints (POST /chat, POST /ingest). Reads and status polling stay unlimited.

The rate limiter is an in-memory sliding window. The backend runs as a single
instance, so this is sufficient; a multi-instance deployment would back it with
Redis instead.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

import httpx
from fastapi import HTTPException, Request

from .config import settings

_WINDOW_SECONDS = 60.0
_TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

_hits: Dict[str, Deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """Real client IP, honoring the proxy (Render/Vercel set X-Forwarded-For)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request) -> None:
    if not settings.rate_limit_enabled:
        return
    ip = client_ip(request)
    now = time.monotonic()
    with _lock:
        dq = _hits[ip]
        while dq and now - dq[0] > _WINDOW_SECONDS:
            dq.popleft()
        if len(dq) >= settings.rate_limit_per_minute:
            retry_after = int(_WINDOW_SECONDS - (now - dq[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded: {settings.rate_limit_per_minute} "
                    "requests per minute. Please wait and try again."
                ),
                headers={"Retry-After": str(retry_after)},
            )
        dq.append(now)
        if not dq:  # keep the dict from accumulating empty entries
            _hits.pop(ip, None)


async def verify_turnstile(request: Request) -> None:
    secret = settings.turnstile_secret_key
    if not secret:
        return  # Turnstile disabled until a secret is configured.

    token = request.headers.get("x-turnstile-token", "")
    if not token:
        raise HTTPException(status_code=403, detail="Missing Turnstile token")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _TURNSTILE_VERIFY_URL,
                data={
                    "secret": secret,
                    "response": token,
                    "remoteip": client_ip(request),
                },
            )
            result = resp.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=503, detail="Turnstile verification temporarily unavailable"
        )

    if not result.get("success"):
        raise HTTPException(status_code=403, detail="Turnstile verification failed")
