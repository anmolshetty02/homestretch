"""Long-term memory scenarios (Assignment 3): a new session with saved long-term memory vs the baseline without it.
day4 = first test (v7, no state fix; seen); day6 = new test for the memory fixes (design.md, "Memory fixes").
Run from the repo root:
    PYTHONPATH=. .venv/bin/python docs/rag-memory/spikes/longterm_scenario.py                                  # day4, v7
    PYTHONPATH=. .venv/bin/python docs/rag-memory/spikes/longterm_scenario.py --scenario day6 --version v8 --fix-state
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import memory_check as mc  # noqa: E402
import scenario_run as sr  # noqa: E402
from evals.run import ROOT, load_env, render  # noqa: E402

SCENARIOS = {  # synthetic; every memory entry confirmed by the caregiver, with source and date
    "day4": {"today": "Thursday, October 22, 2026", "question": "Morning! Anything I should keep in mind today?",
             "memory": {"long_term": {
                 "semantic": {"preferences": ["Use simple words; caregiver's English is not perfect (caregiver, Oct 19, confirmed)"]},
                 "episodic": ["Oct 19: flag-4 resolved, Zestril bottle put away (caregiver)",
                              "Oct 20: dizzy when standing up, warn-4, tier 1; Maria called the clinic, told to keep watching (caregiver)",
                              "Oct 21: morning weight 148.6 lb (caregiver)"],
                 "open_items": ["Pelvacor 20 mg bottle found Oct 19, not identified yet: ask the pharmacist (caregiver)"],
                 "resolved_flags": [{"id": "flag-4", "date": "Oct 19", "source": "caregiver"}]},
                 "session_record": "new session, nothing yet"},
             "hints": {"open item raised": r"pelvacor", "resolved flag called open": r"flag-4|zestril"}},
    "day6": {"today": "Saturday, October 24, 2026", "question": "Good morning, how are things looking?",
             "memory": {"long_term": {
                 "semantic": {"preferences": ["Short answers (caregiver, Oct 20, confirmed)"]},
                 "episodic": ["Oct 21: old Lopressor bottle returned to the pharmacy (caregiver)",
                              "Oct 23: weight 151.0 lb, up 2 lb from Oct 22; below the 3-lb warning sign; recheck Oct 24 morning (caregiver)"],
                 "open_items": ["Ask the pharmacist whether Tylenol is okay for her knee pain (caregiver, Oct 23)"],
                 "resolved_flags": [{"id": "flag-1", "date": "Oct 21", "source": "caregiver"}]},
                 "session_record": "new session, nothing yet"},
             "hints": {"Tylenol question raised": r"tylenol", "weight recheck raised": r"weigh|weight|scale",
                       "resolved flag called open": r"flag-1|tartrate|lopressor"}},
    "day8": {"today": "Monday, October 26, 2026", "question": "Hey, we're starting the week. Where do we stand?",
             "memory": {"long_term": {
                 "semantic": {"preferences": ["Short answers (caregiver, Oct 20, confirmed)"]},
                 "episodic": ["Oct 24: new metoprolol succinate picked up from the pharmacy (caregiver)",
                              "Oct 25: ankles a bit puffy in the evening, below the warning sign; check again Oct 26 morning (caregiver)"],
                 "open_items": ["Ask the clinic whether she can restart her evening walk (caregiver, Oct 25)"],
                 "follow_ups": ["Ask the clinic whether she can restart her evening walk (open since Oct 25)",
                                "Check her ankles this morning: a bit puffy on Oct 25 evening (recheck due Oct 26)"],
                 "resolved_flags": [{"id": "flag-3", "date": "Oct 24", "source": "caregiver"}]},
                 "session_record": "new session, nothing yet"},
             "hints": {"walk question raised": r"walk", "ankle check raised": r"ankle|swell|puffy",
                       "resolved flag called open": r"flag-3|not (been )?filled|not in the cabinet"}},
}
SCENARIOS["day10"] = {
    "today": "Wednesday, October 28, 2026", "question": "Hi there, what's the plan for today?",
    "memory": {"long_term": {
        "semantic": {"preferences": ["Short answers (caregiver, Oct 20, confirmed)"]},
        "episodic": ["Oct 27: new furosemide 40 mg picked up; old 20 mg bottle returned (caregiver)",
                     "Oct 27: needed an extra pillow to sleep; check breathing lying flat Oct 28 night (caregiver)"],
        "open_items": ["Ask the pharmacist whether she can use her old eye drops (caregiver, Oct 27)"],
        "follow_ups": ["Ask the pharmacist whether she can use her old eye drops (open since Oct 27)",
                       "Check her breathing when she lies flat tonight: needed an extra pillow Oct 27 (recheck due Oct 28)"],
        "resolved_flags": [{"id": "flag-2", "date": "Oct 27", "source": "caregiver"}]},
        "session_record": "new session, nothing yet"},
    "hints": {"eye drops question raised": r"eye drop", "breathing/pillow check raised": r"pillow|lie flat|lies flat|lying flat",
              "resolved flag called open": r"flag-2|20 ?mg"}}
SCENARIOS["day6"]["memory"]["long_term"]["follow_ups"] = [
    "Ask the pharmacist whether Tylenol is okay for her knee pain (open since Oct 23)",
    "Weigh her this morning: up 2 lb on Oct 23 (recheck due Oct 24)"]


def digest(memory):
    """Fix B2: follow-ups move to a top-level `raise_first` field, ahead of everything else in {{memory}}."""
    lt = copy.deepcopy(memory["long_term"])
    return {"raise_first": lt.pop("follow_ups", []), "long_term": lt, "session_record": memory["session_record"]}


def apply_resolutions(fixture, memory):
    """Fix A: memory's caregiver-confirmed resolutions update the cabinet check itself (one source of truth)."""
    fx = copy.deepcopy(fixture)
    done = {r["id"]: r for r in memory["long_term"].get("resolved_flags", [])}
    for flag in fx["cabinet_diff"]:
        if flag["id"] in done:
            flag["status"] = "resolved"
            flag["summary"] += f" Resolved {done[flag['id']]['date']} ({done[flag['id']]['source']})."
    return fx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="day4", choices=SCENARIOS)
    parser.add_argument("--version", default="v7")
    parser.add_argument("--fix-state", action="store_true", help="fix A: apply memory resolutions to the cabinet check")
    parser.add_argument("--digest", action="store_true", help="fix B2: put follow-ups in a top-level raise_first field")
    args = parser.parse_args()
    sc = SCENARIOS[args.scenario]
    load_env()
    fixture = json.loads((ROOT / "fixtures" / "p001.json").read_text())
    fixture["today"] = sc["today"]
    fixed = apply_resolutions(fixture, sc["memory"]) if args.fix_state else fixture
    memory = digest(sc["memory"]) if args.digest else {**sc["memory"], "long_term": {
        k: v for k, v in sc["memory"]["long_term"].items() if k != "follow_ups"}}
    v4 = render((ROOT / "prompts" / "agent_v4.md").read_text(), fixture, {})
    follow = "; ".join(sc["memory"]["long_term"].get("follow_ups", [])) or "None."
    new = sr.build_prompt((ROOT / "prompts" / f"agent_{args.version}.md").read_text(), fixed, follow_ups=follow,
                          memory=json.dumps(memory), references="<references>none</references>")
    assert json.dumps(memory) in new, "memory did not reach the prompt"
    cache = json.loads(sr.CACHE.read_text()) if sr.CACHE.exists() else {}
    calls, rows = [], []
    print(f"Scenario {args.scenario}, {sc['today']}; prompt {args.version}; state fix: {args.fix_state}; digest: {args.digest}\n"
          f"Caregiver: {sc['question']}\nMemory sent:\n{json.dumps(memory, indent=1)}")
    for label, system in [("BASELINE v4, no memory", v4), (f"{args.version} + long-term memory", new)]:
        for rep in range(3):
            out = sr.ask(system, sc["question"], cache, calls, rep)
            reply = out.get("reply", "")
            rows.append((label, rep + 1, {h: bool(re.search(rx, reply, re.I)) for h, rx in sc["hints"].items()}))
            print(f"\n--- {label}, run {rep + 1} --- tier {out.get('red_flag_tier')}\n{reply}")
    print("\nKey-word hints (read the replies to confirm):")
    for label, rep, h in rows:
        print(f"  {label}, run {rep}: {h}")
    print(f"\nSpent ${mc.log_spend(sr.MODEL, calls)} ({len(calls)} calls)" if calls else "\nAll cached.")


if __name__ == "__main__":
    main()
