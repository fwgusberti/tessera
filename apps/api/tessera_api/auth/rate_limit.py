"""Redis-backed rate limiter using INCR + EXPIRE."""

from __future__ import annotations

import hashlib

from redis.asyncio import Redis


def _safe_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def check_rate_limit(
    redis: Redis,
    key: str,
    max_count: int,
    window_seconds: int,
) -> bool:
    """Return True if request is within limit, False if it exceeds it.

    The key is hashed before storage to avoid persisting raw identifiers (e.g. IPs).
    """
    safe = f"tessera:rate:{_safe_key(key)}"
    count = await redis.incr(safe)
    if count == 1:
        await redis.expire(safe, window_seconds)
    return count <= max_count
