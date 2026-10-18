"""Model providers. Every provider returns (text, latency_seconds, usage_dict)."""
import json
import os
import random
import time

import requests

ENDPOINTS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "custom": (os.environ.get("CUSTOM_BASE_URL", ""), "CUSTOM_API_KEY"),
}


class OpenAICompatible:
    """Chat Completions over plain HTTP. Works for Groq and other OpenAI-compatible APIs."""

    def __init__(self, name):
        base_url, key_env = ENDPOINTS[name]
        if name == "custom":
            base_url = os.environ.get("CUSTOM_BASE_URL", "")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.key = os.environ.get(key_env)
        if not self.key or not base_url:
            raise SystemExit(f"Missing {key_env} (or base URL). Copy .env.example to .env and fill it in.")

    def complete(self, messages, model, temperature):
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(6):
            start = time.time()
            resp = requests.post(self.url, headers=headers, json=body, timeout=60)
            latency = time.time() - start
            if resp.status_code == 429:  # rate limited: wait and retry
                wait = float(resp.headers.get("retry-after", 2 ** attempt))
                print(f"  rate limited, waiting {wait:.0f}s")
                time.sleep(wait)
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"{resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            return data["choices"][0]["message"]["content"], latency, data.get("usage", {})
        raise RuntimeError("Gave up after repeated rate limits. Try later or use a smaller model.")


class MockProvider:
    """Offline stand-in for plumbing tests. Keyword rules, not a real model. Never report its scores."""

    TIER3 = ("chest", "gasping", "can't breathe", "cant breathe", "barely talk")

    def complete(self, messages, model, temperature):
        text = messages[-1]["content"].lower()
        if messages[0]["content"].startswith("You review"):
            return json.dumps({"verdict": "ok", "problems": [], "revised": None}), 0.01, {}
        tier = 3 if any(k in text for k in self.TIER3) else None
        if tier is None and any(k in text for k in ("dizzy", "pounds", "pillows", "racing")):
            tier = 1
        reply = {
            "state": "safety" if tier == 3 else "answer",
            "intent": "symptom" if tier is not None else "med_question",
            "analysis": "mock reply",
            "red_flag_tier": tier,
            "sources": [],
            "draft": "Mock draft.",
            "self_check": {k: True for k in ("grounded", "no_diagnosis", "no_dose_advice",
                                             "identity_ok", "tier_checked", "fits_voice")},
            "say": "Please call 911 now." if tier == 3 else "This is a mock reply for testing the pipeline.",
            "actions": [],
        }
        return json.dumps(reply), random.uniform(0.2, 0.6), {}


def get_provider(name):
    if name == "mock":
        return MockProvider()
    if name in ENDPOINTS:
        return OpenAICompatible(name)
    raise SystemExit(f"Unknown provider '{name}'. Use mock, groq, or custom.")
