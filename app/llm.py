"""Model calls for the app. JSON calls reuse evals/ (registry, cache, mock); tool-selection calls add the `tools`
parameter, which evals/providers.py does not send. Model "mock" makes no network calls."""
import json
import time

import requests

from evals.checks import parse_reply
from evals.providers import cost_usd, get_entry, get_provider
from evals.run import cached_call, load_env

load_env()
USAGE = []  # one row per real call: purpose, model, latency, cost (read by the UI and the pipeline eval)


def _log(purpose, model, latency, usage, cached):
    USAGE.append({"purpose": purpose, "model": model, "latency_s": round(latency, 2), "cached": cached, "usage": usage,
                  "cost_usd": cost_usd(usage, get_entry(model).get("price")) or 0.0})


def _mock_json(purpose):
    if purpose == "extract":
        return {"name": "unreadable", "strength": "unreadable", "directions": "unreadable"}
    if purpose == "memory":
        return {"open_flags": [], "resolved_flags": [], "pending_questions": [], "caregiver_reports": [],
                "red_flags": [], "preferences": [], "current_medicine": None}
    return None


def complete_json(messages, model, purpose, temperature=0.3, repeat=0):
    """One JSON-mode call. Returns the parsed object, or {"error": ...}."""
    if model == "mock" and _mock_json(purpose) is not None:
        return _mock_json(purpose)
    entry = get_entry(model)
    try:
        raw, latency, usage, cached = cached_call(get_provider(model), entry, messages, temperature, repeat)
    except (RuntimeError, requests.RequestException) as e:
        return {"error": f"model call failed: {e}"}
    _log(purpose, model, latency, usage, cached)
    reply, err = parse_reply(raw)
    return reply if isinstance(reply, dict) else {"error": f"unparseable reply: {err}", "raw": raw}


def _mock_tool_choice(messages, tools):
    """Keyword stand-in for the model's choice. Never report its scores."""
    if messages[-1]["role"] == "tool":
        return {"content": "done", "tool_calls": []}
    text = messages[-1]["content"].lower()
    names = {t["function"]["name"] for t in tools}
    calls = []
    if "search_drug_label" in names and any(k in text for k in ("side effect", "food", "grapefruit", "potassium",
                                                                 "interact", "ringing", "advil", "what is", "for?")):
        calls.append(("search_drug_label", {"question": messages[-1]["content"]}))
    return {"content": None, "tool_calls": [{"id": f"call-{i}", "type": "function",
                                             "function": {"name": n, "arguments": json.dumps(a)}}
                                            for i, (n, a) in enumerate(calls)]}


def choose_tools(messages, tools, model, temperature=0.0):
    """One tool-calling turn. Returns the assistant message: {"content", "tool_calls": [...]}, or {"error": ...}."""
    if model == "mock":
        return _mock_tool_choice(messages, tools)
    entry = get_entry(model)
    provider = get_provider(model)
    body = {"model": entry["model"], "messages": messages, "tools": tools, "temperature": temperature,
            **entry.get("extra_body", {})}
    start = time.time()
    try:
        r = requests.post(provider.url, json=body, timeout=provider.timeout,
                          headers={"Authorization": f"Bearer {provider.key}", "Content-Type": "application/json"})
        r.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"tool-selection call failed: {e}"}
    data = r.json()
    _log("tool_choice", model, time.time() - start, data.get("usage", {}), False)
    msg = data["choices"][0]["message"]
    return {"content": msg.get("content"), "tool_calls": msg.get("tool_calls") or []}
