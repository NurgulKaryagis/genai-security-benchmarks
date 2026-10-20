"""Minimal OpenAI Responses API client (stdlib only) with usage and cost
accounting. The API key is read from the environment or a .env file and
is never printed or logged.

The Responses API is used because gpt-6 models do not allow function
tools together with reasoning on /v1/chat/completions. It has no `seed`
and these models accept no `temperature` other than the default, so
runs are not reproducible call by call; variance is measured instead.
"""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://api.openai.com/v1/responses"

# USD per 1M tokens: (input, cached input, output). Source: OpenAI pricing
# page, first price group, as recorded in the experiment design on 2026-10-19.
PRICES = {
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
}


def load_api_key(env_file: Path | None = None) -> str:
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    if env_file and env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENAI_API_KEY not set (environment or .env)")


def call_cost(model: str, usage: dict) -> float:
    p_in, p_cached, p_out = PRICES[model]
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    uncached = usage.get("input_tokens", 0) - cached
    out = usage.get("output_tokens", 0)  # includes reasoning tokens
    return (uncached * p_in + cached * p_cached + out * p_out) / 1_000_000


def output_text(resp: dict) -> str:
    """Concatenate the text of all message items in a response."""
    return "".join(
        part.get("text", "")
        for item in resp.get("output", []) if item.get("type") == "message"
        for part in item.get("content", []) if part.get("type") == "output_text"
    )


class APIError(RuntimeError):
    pass


class OpenAIClient:
    def __init__(self, api_key: str, max_retries: int = 4):
        self._key = api_key
        self.max_retries = max_retries

    def create(self, body: dict) -> tuple[dict, dict]:
        """POST to /v1/responses. Returns (response, call_record).
        Retries on rate limits and server errors; raises APIError otherwise."""
        data = json.dumps(body).encode()
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(API_URL, data=data, method="POST", headers={
                "Authorization": "Bearer " + self._key,
                "Content-Type": "application/json",
            })
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    resp = json.load(r)
                break
            except urllib.error.HTTPError as e:
                msg = (json.loads(e.read() or b"{}").get("error") or {}).get("message", "")
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(f"HTTP {e.code}: {msg}") from None
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(f"network error: {e}") from None
        if resp.get("status") not in (None, "completed"):
            raise APIError(f"response status {resp.get('status')}: {resp.get('incomplete_details')}")
        usage = resp.get("usage") or {}
        record = {
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "requested_model": body["model"],
            "returned_model": resp.get("model"),
            "reasoning": resp.get("reasoning"),
            "latency_s": round(time.perf_counter() - t0, 3),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0),
            "cached_tokens": (usage.get("input_tokens_details") or {}).get("cached_tokens", 0),
            "cost_usd": call_cost(body["model"], usage),
            "retries": attempt,
        }
        return resp, record
