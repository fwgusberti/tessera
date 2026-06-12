"""Performance validation for SC-009.

Targets:
  - POST /v1/search       p95 < 2 000 ms
  - POST /v1/assistant/answer  first-byte p95 < 5 000 ms

Usage (requires a running API):
    TEST_API_URL=http://localhost:8000 \
    TEST_API_TOKEN=<bearer-token> \
    pytest apps/api/tests/perf/test_performance.py -v

The tests are skipped when TEST_API_URL is not set so they never block the
unit-test suite in CI.
"""

from __future__ import annotations

import asyncio
import os
import statistics
import time
import uuid
from typing import Any

import httpx
import pytest

BASE_URL = os.getenv("TEST_API_URL", "")
TOKEN = os.getenv("TEST_API_TOKEN", "")
CONCURRENCY = int(os.getenv("TEST_PERF_CONCURRENCY", "10"))
ITERATIONS = int(os.getenv("TEST_PERF_ITERATIONS", "50"))

pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="Set TEST_API_URL to run performance tests against a live environment",
)


def _headers() -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


async def _timed_post(client: httpx.AsyncClient, path: str, payload: dict[str, Any]) -> float:
    """Return elapsed milliseconds for a POST request."""
    start = time.perf_counter()
    r = await client.post(path, json=payload, headers=_headers(), timeout=30.0)
    elapsed = (time.perf_counter() - start) * 1000
    assert r.status_code == 200, f"Unexpected {r.status_code}: {r.text[:200]}"
    return elapsed


async def _run_load(path: str, payload: dict[str, Any]) -> list[float]:
    """Run ITERATIONS requests with CONCURRENCY concurrency; return latency samples (ms)."""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    samples: list[float] = []

    async def one() -> None:
        async with semaphore:
            async with httpx.AsyncClient(base_url=BASE_URL) as client:
                ms = await _timed_post(client, path, payload)
                samples.append(ms)

    await asyncio.gather(*[one() for _ in range(ITERATIONS)])
    return samples


def _p95(samples: list[float]) -> float:
    sorted_s = sorted(samples)
    idx = int(len(sorted_s) * 0.95)
    return sorted_s[min(idx, len(sorted_s) - 1)]


def _report(label: str, samples: list[float], threshold_ms: float) -> None:
    p50 = statistics.median(samples)
    p95 = _p95(samples)
    mean = statistics.mean(samples)
    print(
        f"\n[{label}] n={len(samples)}  "
        f"p50={p50:.0f}ms  mean={mean:.0f}ms  p95={p95:.0f}ms  "
        f"threshold={threshold_ms:.0f}ms  {'PASS' if p95 <= threshold_ms else 'FAIL'}"
    )
    assert p95 <= threshold_ms, (
        f"{label} p95 latency {p95:.0f}ms exceeds SC-009 target {threshold_ms:.0f}ms"
    )


@pytest.mark.asyncio
async def test_search_p95_under_2s():
    """SC-009: POST /v1/search p95 < 2 000 ms."""
    payload = {"query": "how to deploy to production", "top_k": 10}
    samples = await _run_load("/v1/search", payload)
    _report("search", samples, threshold_ms=2_000)


@pytest.mark.asyncio
async def test_assistant_answer_p95_under_5s():
    """SC-009: POST /v1/assistant/answer first-byte p95 < 5 000 ms."""
    payload = {"query": "what is the onboarding process for new engineers?"}
    samples = await _run_load("/v1/assistant/answer", payload)
    _report("assistant/answer", samples, threshold_ms=5_000)
