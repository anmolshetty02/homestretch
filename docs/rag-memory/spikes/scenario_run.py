"""Section C scenarios (Assignment 3): baseline (Prompt B v4, no memory, no retrieval) vs HomeStretch (v6 + memory +
references), same question, same patient (fixtures/p001.json), deepseek-flash, temperature 0.3, thinking off.
Run from the repo root:
    PYTHONPATH=. .venv/bin/python docs/rag-memory/spikes/scenario_run.py                          # v6, 1 run
    PYTHONPATH=. .venv/bin/python docs/rag-memory/spikes/scenario_run.py --version v7 --repeats 3
Memory comes from the memory experiment's cached DeepSeek record (no new calls); references come from the retrieval
pipeline chosen in compliance.md (round 2). Replies are cached in .cache_scenario.json, so reruns are free.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from evals.providers import get_provider
from evals.run import ROOT, load_env, render

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import memory_check  # noqa: E402
import retrieval_check as rc  # noqa: E402

MODEL = "deepseek-flash"
CACHE = HERE / ".cache_scenario.json"
THRESHOLD = 0.582  # compliance.md, round 2

# retrieve: what the router (design.md Section A) decides for this message; the router itself is not implemented here
SCENARIOS = [
    {"name": "S1 multi-turn: what to ask the pharmacy (memory)", "session": "dev",
     "question": "OK, I'm about to call Brighton Pharmacy. What should I ask them?", "retrieve": False},
    {"name": "S2 side effect not in the plan (retrieval)", "session": None,
     "question": "Her ears are ringing. Could that be one of her pills?", "retrieve": True},
    # S3 was picked after the retrieval experiment showed this question retrieves well (dev q10); disclosed in design.md
    {"name": "S3 label fact not in the plan, retrieval working (selected)", "session": None,
     "question": "Does the water pill make her lose potassium?", "retrieve": True},
]


def build_prompt(template, fixture, **slots):
    """Fill the v6+ slots BEFORE render(): render() fills unfilled {{memory}}, {{references}}, {{follow_ups}} with empty
    defaults for the A2 suites, which once silently dropped scenario memory. The assert keeps that from recurring."""
    for key, val in slots.items():
        template = template.replace("{{" + key + "}}", val)
    prompt = render(template, fixture, {})
    for key, val in slots.items():
        assert "{{" + key + "}}" not in template and (val in prompt or "{{" + key not in template), key
    return prompt


def references(question):
    """Round-2 pipeline: name check, filter, hybrid search on by-section chunks, top 3, threshold."""
    rx = json.loads(rc.RXNAV_CACHE.read_text()) if rc.RXNAV_CACHE.exists() else {}
    if rc.unknown_names(question, rx):
        return "none"
    from fastembed import TextEmbedding
    model = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=str(Path.home() / ".cache" / "fastembed"))
    chunks = rc.chunk_by_section(rc.load_labels())
    vecs = np.array(list(model.embed([c["text"] for c in chunks])))
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    qv = np.array(list(model.query_embed([question])))[0]
    ranked, top_cos = rc.run_setup(chunks, rc.BM25([c["text"] for c in chunks]), vecs, qv / np.linalg.norm(qv),
                                   question, "Hybrid (RRF)", rnd=2)
    print(f"  retrieval top cosine {top_cos:.3f} (threshold {THRESHOLD})")
    if top_cos < THRESHOLD:
        return "none"
    refs = [chunks[i] for i in ranked[:3]]
    return "\n".join(f'<ref id="ref-{n}" drug="{c["drug"]}" source="openFDA label" section="{c["section"]}" '
                     f'set_id="{c["set_id"]}" date="{c["effective_time"][:4]}-{c["effective_time"][4:6]}-'
                     f'{c["effective_time"][6:]}">{c["text"]}</ref>' for n, c in enumerate(refs, 1))


def memory(session):
    if session is None:
        return "No session notes yet. No saved preferences."
    cache = json.loads(memory_check.CACHE.read_text())
    calls = []
    _, record = memory_check.build(MODEL, memory_check.DEV, cache, calls)
    assert not calls, "memory record must come from the cached reported run"
    recent = memory_check.DEV[-2:]
    return json.dumps({"session_record": record, "recent_turns": recent})


def follow_ups(session):
    """v9 slot, filled by the app from all memory: the session record's pending questions and open warning signs."""
    if session is None:
        return "None."
    cache = json.loads(memory_check.CACHE.read_text())
    _, record = memory_check.build(MODEL, memory_check.DEV, cache, [])
    return "; ".join(record.get("pending_questions", []) + record.get("red_flags", [])) or "None."


def ask(system, question, cache, calls, rep=0):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    key = hashlib.sha256(json.dumps(messages).encode()).hexdigest()[:16] + (f"|r{rep}" if rep else "")
    if key not in cache:
        text, _, usage = get_provider(MODEL).complete(messages, temperature=0.3)
        calls.append(usage)
        cache[key] = text
        CACHE.write_text(json.dumps(cache, indent=2))
    return json.JSONDecoder().raw_decode(cache[key].strip())[0]


def checks(scenario, question, reply):
    """Automatic hints for the hand read: names the caregiver never wrote, and (S1) which memory facts the reply uses."""
    name = "Rosa" in reply and "Rosa" not in question
    facts = [f for f, g in memory_check.DEV_FACTS.items() if f != "F4" and memory_check.survives(reply, g)] \
        if scenario["session"] == "dev" else []
    return name, facts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v6")
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    load_env()
    fixture = json.loads((ROOT / "fixtures" / "p001.json").read_text())
    v4 = (ROOT / "prompts" / "agent_v4.md").read_text()
    v6 = (ROOT / "prompts" / f"agent_{args.version}.md").read_text()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    calls, summary = [], []
    for s in SCENARIOS:
        print(f"\n=== {s['name']} ===\nCaregiver: {s['question']}")
        base = render(v4, fixture, {})
        refs = references(s["question"]) if s["retrieve"] else "none"
        mem = memory(s["session"])
        follow = follow_ups(s["session"])
        full = build_prompt(v6, fixture, memory=mem, references=f"<references>{refs}</references>", follow_ups=follow)
        assert mem in full and refs in full, "memory or references did not reach the prompt"
        print(f"\nMemory sent:\n{mem}\n\nReferences sent:\n{refs}")
        for label, system in [("BASELINE (v4, no memory, no retrieval)", base),
                              (f"HOMESTRETCH ({args.version} + memory + refs)", full)]:
            for rep in range(args.repeats):
                out = ask(system, s["question"], cache, calls, rep)
                name, facts = checks(s, s["question"], out.get("reply", ""))
                refs_cited = [x for x in out.get("sources", []) if str(x).startswith("ref-")]
                summary.append((s["name"][:2], label.split(" ")[0], rep + 1, out.get("red_flag_tier"), name, facts, refs_cited))
                print(f"\n--- {label}, run {rep + 1} ---\ntier: {out.get('red_flag_tier')}  sources: {out.get('sources')}\n"
                      f"self_check: {out.get('self_check')}\nreply: {out.get('reply')}")
    print("\n| Scenario | Prompt | Run | Tier | Unstated name used | S1 memory facts in reply (key words) | Refs cited |")
    print("|---|---|---|---|---|---|---|")
    for row in summary:
        print("| " + " | ".join(str(x) for x in row) + " |")
    if calls:
        print(f"\nSpent ${memory_check.log_spend(MODEL, calls)} ({len(calls)} calls) -> results/spend.csv")
    else:
        print("\nAll answers from cache; no API calls.")


if __name__ == "__main__":
    main()
