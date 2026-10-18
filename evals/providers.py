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
    SELF_CHECK = {k: True for k in ("every_item_labeled", "labels_rechecked", "grounded",
                                    "no_diagnosis", "no_dose_advice", "tier_checked")}

    def complete(self, messages, model, temperature):
        raw = messages[-1]["content"]
        text = raw.lower()
        if messages[0]["content"].startswith("You review"):
            return json.dumps({"verdict": "ok", "problems": [], "revised": None}), 0.01, {}
        if raw.lstrip().startswith("["):  # a cabinet: flag only the old metoprolol, call everything else ok
            flags = [{"id": f"flag-{i}", "cabinet_ref": item.get("id"), "priority": i, "detail": "mock",
                      **({"label": "stopped_still_present", "plan_ref": "stopped-1"}
                         if any(k in item.get("name", "").lower() for k in ("tartrate", "lopressor"))
                         else {"label": "ok", "plan_ref": None})}
                     for i, item in enumerate(json.loads(raw), 1)]
            reply = {"mode": "diff", "analysis": "mock reply", "flags": flags, "red_flag_tier": None,
                     "sources": [], "self_check": self.SELF_CHECK, "reply": "Mock cabinet check."}
            return json.dumps(reply), random.uniform(0.2, 0.6), {}
        tier = 3 if any(k in text for k in self.TIER3) else None
        if tier is None and any(k in text for k in ("dizzy", "pounds", "pillows", "racing")):
            tier = 1
        reply = {
            "mode": "chat",
            "analysis": "mock reply",
            "flags": [],
            "red_flag_tier": tier,
            "sources": [],
            "self_check": self.SELF_CHECK,
            "reply": "Call 911 now." if tier == 3 else "This is a mock reply for testing the pipeline.",
        }
        return json.dumps(reply), random.uniform(0.2, 0.6), {}


def get_provider(name):
    if name == "mock":
        return MockProvider()
    if name in ENDPOINTS:
        return OpenAICompatible(name)
    raise SystemExit(f"Unknown provider '{name}'. Use mock, groq, or custom.")
