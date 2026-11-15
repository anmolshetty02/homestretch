"""Part 2 self-check: every branch of the graph, with the model calls replaced (no network, no cost).
    .venv/bin/python -m app.test_graph
"""
import json

from app import graph, llm

GOOD = {"mode": "chat", "analysis": "", "flags": [], "red_flag_tier": None, "sources": ["med-1"],
        "self_check": {}, "reply": "The water pill is taken twice a day [med-1]."}
BAD = dict(GOOD, reply="You should take an extra 40 mg dose now.", sources=["med-1"])


def fake_answers(*replies):
    it = iter(replies)
    llm.complete_json = lambda *a, **k: next(it) if k.get("purpose") == "answer" else {}


def fake_tools(*rounds):
    it = iter(rounds)

    def choose(msgs, tools, model, temperature=0.0):
        calls = next(it, [])
        return {"content": None if calls else "done", "tool_calls": [
            {"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
            for i, (n, a) in enumerate(calls)]}
    llm.choose_tools = choose


def steps(out):
    return [t["step"] for t in out["trace"]]


# tier 3 never reaches a model
out = graph.run_turn("t", "Her chest is tight and she can't breathe", save=False, gate="keep")
assert out["final"]["red_flag_tier"] == 3 and steps(out) == ["route", "emergency_reply"], steps(out)
assert not graph.EMERGENCY.search("She is a little dizzy when she stands up")  # tier 1, left to Prompt B

# failed output check -> one retry -> pass
fake_tools([]); fake_answers(BAD, GOOD)
out = graph.run_turn("t", "When does she take the water pill?", save=False)
assert out["final"]["reply"] == GOOD["reply"] and "answer attempt 2" in steps(out), steps(out)

# two failures -> fallback, never the unsafe reply
fake_tools([]); fake_answers(BAD, BAD)
out = graph.run_turn("t", "When does she take the water pill?", save=False)
assert out["final"]["by"] == "fallback" and "extra" not in out["final"]["reply"]

# dose question: label search is blocked even when the model asks for it; duplicates are refused; loop is capped
q = ("search_drug_label", {"question": "missed dose of furosemide"})
fake_tools([q], [q], [q], [q]); fake_answers(GOOD)
out = graph.run_turn("t", "She missed her water pill dose, what now?", save=False)
details = " ".join(t["detail"] for t in out["trace"] if t["step"] == "tools")
assert "blocked" in details and steps(out).count("agent round 1") == 1
assert sum(s.startswith("agent round") for s in steps(out)) == graph.MAX_ROUNDS, steps(out)

# hallucinated tool -> error back to the model, run continues
fake_tools([("delete_patient", {})]); fake_answers(GOOD)
out = graph.run_turn("t", "What is the heart pill for?", save=False)
assert "not available" in [t for t in out["trace"] if t["step"] == "tools"][0]["detail"]
print("graph self-check ok")

# ablation switch: no agent/tools steps, same answer path
fake_tools([("search_drug_label", {"question": "x"})]); fake_answers(GOOD)
out = graph.run_turn("t", "What is the heart pill for?", save=False, use_tools=False)
assert not any(s.startswith(("agent", "tools")) for s in steps(out)) and "answer attempt 1" in steps(out), steps(out)
print("ablation self-check ok")

# 911 rule variants
EM = "No chest pain at all, but her ankles are more swollen"   # a trap the word rule matches
fake_tools([]); fake_answers(GOOD)
assert graph.run_turn("t", EM, save=False, gate="keep")["final"]["by"] == "fixed rule"
fake_tools([]); fake_answers(GOOD)
out = graph.run_turn("t", EM, save=False, gate="off")
assert out["final"]["reply"] == GOOD["reply"], out["final"]
fake_tools([]); fake_answers(GOOD)
out = graph.run_turn("t", EM, save=False, gate="backstop")
assert out["final"]["reply"].startswith(GOOD["reply"]) and "call 911" in out["final"]["reply"] and "warn-6" in out["final"]["sources"]
fake_tools([]); fake_answers(dict(GOOD, reply="Call 911 now [warn-6].", red_flag_tier=3))
out = graph.run_turn("t", "her chest hurts", save=False, gate="backstop")
assert out["final"]["reply"] == "Call 911 now [warn-6]."   # reply already has 911: untouched
fake_tools([]); fake_answers(GOOD)
assert graph.run_turn("t", "When is the water pill?", save=False, gate="backstop")["final"]["reply"] == GOOD["reply"]
print("gate variants self-check ok")

# review fixes: no lookups on a possible emergency; fallback on an emergency still says 911; round cap is visible
fake_tools([("search_drug_label", {"question": "x"})]); fake_answers(GOOD)
out = graph.run_turn("t", "Her chest hurts, is it the new pill?", save=False)
assert not any(s.startswith(("agent", "tools")) for s in steps(out)), steps(out)
fake_tools([]); fake_answers(BAD, BAD)
out = graph.run_turn("t", "Her chest hurts and she is sweating", save=False)
assert out["final"]["reply"].startswith("Call 911 now") and out["final"]["red_flag_tier"] == 3, out["final"]
q2 = ("get_care_plan", {"item_id": "med-1"}); q3 = ("get_care_plan", {"item_id": "med-2"})
fake_tools([("get_care_plan", {})], [q2], [q3]); fake_answers(GOOD)
out = graph.run_turn("t", "What is the heart pill for?", save=False)
assert "not run (round cap" in out["trace"][-4]["detail"] or any("not run (round cap" in t["detail"] for t in out["trace"])
assert sum(t["step"] == "tools" for t in out["trace"]) == graph.MAX_ROUNDS - 1
assert not graph.DOSE.search("she needed extra pillows to breathe") and graph.DOSE.search("can she take an extra pill")
print("review-fix self-check ok")

# other patients: the patient's own plan reaches Prompt B and the tool prompt, and the orchestrator (not the model)
# picks whose plan a lookup reads
seen = {}
def capture(msgs, model, purpose="", **k):
    seen.setdefault(purpose, msgs)
    return GOOD if purpose == "answer" else {}
llm.complete_json = capture
fake_tools([("get_care_plan", {"item_id": "med-1", "patient": "p001"})])
calls, real_call = [], graph.tc.call_tool
graph.tc.call_tool = lambda name, args, model="mock": (calls.append((name, args)), real_call(name, args, model))[1]
out = graph.run_turn("t", "What is the blood thinner for?", save=False, patient="synthea/s02")
graph.tc.call_tool = real_call
assert ("get_care_plan", {"item_id": "med-1", "patient": "synthea/s02"}) in calls, calls  # model asked for p001
assert "clopidogrel" in seen["answer"][0]["content"] and "Rosa" not in seen["answer"][0]["content"]
assert "clopidogrel" in graph.patient_context("synthea/s02")["tools_prompt"]
assert any(t["step"] == "tools" and "get_care_plan: ok" in t["detail"] for t in out["trace"]), out["trace"]
from app import tools as _t
assert _t.get_care_plan("med-1", "synthea/s02") != _t.get_care_plan("med-1")  # different plans, so the check means something
try:
    graph.run_turn("t", "hi", save=False, patient="../p001")
    raise AssertionError("bad patient accepted")
except ValueError:
    pass
print("multi-patient self-check ok")
