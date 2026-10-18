"""Model providers, driven by evals/models.yaml. Every provider returns (text, latency_seconds, usage_dict)."""
import json
import os
import random
import time
from pathlib import Path

import requests
import yaml

REGISTRY = yaml.safe_load((Path(__file__).parent / "models.yaml").read_text())


def get_entry(key):
    """Registry entry for a model key, with its provider block under "provider_cfg"."""
    if key not in REGISTRY["models"]:
        raise SystemExit(f"Unknown model '{key}'. Known: {', '.join(REGISTRY['models'])}")
    entry = REGISTRY["models"][key]
    if entry.get("enabled", True) is False:
        raise SystemExit(f"Model '{key}' is disabled. Enable it in evals/models.yaml (see the comment there).")
    return {**entry, "provider_cfg": REGISTRY["providers"][entry["provider"]]}


def cost_usd(usage, price):
    """Cost of one call. None when the price is unknown."""
    if price == "free":
        return 0.0
    if not price or not usage:
        return None
    hit = usage.get("prompt_cache_hit_tokens", 0)
    miss = usage.get("prompt_cache_miss_tokens", usage.get("prompt_tokens", 0) - hit)
    out = usage.get("completion_tokens", 0)  # includes reasoning tokens
    return (hit * price["input_hit"] + miss * price["input_miss"] + out * price["output"]) / 1e6


class OpenAICompatible:
    """Chat Completions over plain HTTP. Works for DeepSeek, Ollama, Groq, and OpenRouter."""

    def __init__(self, entry):
        cfg = entry["provider_cfg"]
        key_env = cfg.get("key_env")
        self.key = os.environ.get(key_env) if key_env else None
        if key_env and not self.key:
            raise SystemExit(f"Missing {key_env}. Add it to .env (see .env.example).")
        self.url = cfg["base_url"].rstrip("/") + "/chat/completions"
        self.timeout = cfg.get("timeout", 60)
        self.model = entry["model"]
        self.extra = entry.get("extra_body", {})

    def complete(self, messages, temperature):
        body = {"model": self.model, "messages": messages, "temperature": temperature,
                "response_format": {"type": "json_object"}, **self.extra}
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        for attempt in range(6):
            start = time.time()
            resp = requests.post(self.url, headers=headers, json=body, timeout=self.timeout)
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


def ollama_context(entry):
    """Context length the Ollama server actually loaded the model with (None if not loaded)."""
    base = entry["provider_cfg"]["base_url"].rsplit("/v1", 1)[0]
    loaded = requests.get(base + "/api/ps", timeout=5).json().get("models", [])
    return next((m.get("context_length") for m in loaded if m["name"] == entry["model"]), None)


class MockProvider:
    """Offline stand-in for plumbing tests. Keyword rules, not a real model. Never report its scores."""

    TIER3 = ("chest", "gasping", "can't breathe", "cant breathe", "barely talk")
    SELF_CHECK = {k: True for k in ("every_item_labeled", "labels_rechecked", "grounded",
                                    "no_diagnosis", "no_dose_advice", "tier_checked")}

    def complete(self, messages, temperature):
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


def get_provider(key):
    entry = get_entry(key)
    return MockProvider() if entry["provider"] == "mock" else OpenAICompatible(entry)


if __name__ == "__main__":  # python -m evals.providers
    for key, m in REGISTRY["models"].items():
        assert m["provider"] in REGISTRY["providers"], key
        if m.get("enabled", True) and m["provider"] != "mock":
            assert "model" in m and "price" in m, key
        if m["provider"] == "ollama":
            assert m.get("num_ctx"), f"{key}: Ollama entries must record num_ctx"
    flash = REGISTRY["models"]["deepseek-flash"]["price"]
    # real usage from the first v1 test call: 3,968 input (all cache miss), 238 output
    usage = {"prompt_tokens": 3968, "completion_tokens": 238, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 3968}
    assert abs(cost_usd(usage, flash) - (3968 * 0.30 + 238 * 1.20) / 1e6) < 1e-12
    hit = {"prompt_tokens": 3968, "completion_tokens": 238, "prompt_cache_hit_tokens": 3000, "prompt_cache_miss_tokens": 968}
    assert cost_usd(hit, flash) < cost_usd(usage, flash)
    assert cost_usd({"prompt_tokens": 100, "completion_tokens": 10}, flash) == (100 * 0.30 + 10 * 1.20) / 1e6  # no cache fields
    assert cost_usd(usage, "free") == 0.0 and cost_usd(usage, None) is None
    for key in ("deepseek-flash", "deepseek-pro"):
        assert REGISTRY["models"][key]["extra_body"]["thinking"]["type"] == "disabled", key
    print(f"providers self-test ok; one v1 call on deepseek-flash = ${cost_usd(usage, flash):.5f}")
