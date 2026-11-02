"""Memory comparison (Assignment 3, Task A step 2). Setup and decision rule: docs/rag-memory/design.md, section B.

Which session memory still holds the facts the final reply needs? Run from the repo root:
    PYTHONPATH=. .venv/bin/python docs/rag-memory/spikes/memory_check.py                         # local, free
    PYTHONPATH=. .venv/bin/python docs/rag-memory/spikes/memory_check.py --model deepseek-flash --heldout  # reported
M3 and M4 are updated once per turn (2 x 10 calls per conversation); answers are cached per model and prompt in
.cache_memory.json, so reruns are free. The held-out conversation runs only with --heldout on a paid (reported) model.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

from evals.providers import cost_usd, get_entry, get_provider
from evals.run import ROOT, SPEND, SPEND_FIELDS, load_env

HERE = Path(__file__).parent
CACHE = HERE / ".cache_memory.json"

DEV = [  # turns 1-10; turn 11 is the test question ("OK, I'm about to call Brighton Pharmacy. What should I ask them?")
    "I found the old Lopressor bottle you flagged. I bagged it to take back to the pharmacy.",
    "Her heart doctor said to take the lisinopril at bedtime now, not the morning. Is that a problem?",
    "There's also a bottle that says Zorvexa 10 mg. I don't know what that is.",
    "Is her appointment with Dr. Patel still on Thursday?",
    "Weighed her this morning: 150.2 lb. Yesterday was 149.8.",
    "What's a low-salt snack she might like?",
    "The pharmacy says the new furosemide 40 isn't ready until tomorrow.",
    "Her ankles look a bit more swollen than yesterday.",
    "My brother is visiting this weekend, he can help with her pills.",
    "Thanks. Please keep answers short, I'm reading these at work.",
]

# Held-out: written after the dev build runs, frozen before any run, never run on the build model. Same fact kinds
# (F1..F7 mean the same thing), new wording and positions. Turn 11: "I'm making my list for tonight. What still needs
# follow-up?" Kelvanide is made up.
HELDOUT = [
    "The plan says her second water pill is at 2, but she'd rather take it at 4 so she isn't up at night. Is that okay?",
    "What time does the heart clinic open tomorrow?",
    "I put the Zestril bottle away, so we only use the lisinopril one now.",
    "There's a bottle of Kelvanide 5 mg in her drawer. No idea what it's for.",
    "She got dizzy when she stood up from the couch this afternoon.",
    "She wants to go to her granddaughter's recital on Saturday.",
    "Weight this morning was 148.6.",
    "Please use simple words, English is my second language.",
    "The new metoprolol won't be ready to pick up until Friday.",
    "Her neighbor brought soup, so dinner is covered tonight.",
]

# fact -> groups of key words; every group must have at least one word in the memory text
DEV_FACTS = {
    "F1": [["lopressor", "tartrate", "flag-1"], ["bag", "return", "drop"]],
    "F2": [["lisinopril", "zestril", "med-3"], ["bedtime", "night", "evening"]],
    "F3": [["zorvexa"]],
    "F4": [["150.2"]],
    "F5": [["furosemide", "lasix", "flag-2", "water pill"], ["tomorrow", "not ready", "pending", "delay"]],
    "F6": [["ankle", "swell", "warn-2"]],
    "F7": [["short", "brief", "concise"]],
}
HELDOUT_FACTS = {
    "F1": [["zestril", "flag-4", "duplicate"], ["away", "removed", "only use"]],
    "F2": [["furosemide", "lasix", "med-1", "water pill"], ["4"]],
    "F3": [["kelvanide"]],
    "F4": [["148.6"]],
    "F5": [["metoprolol", "succinate", "toprol", "flag-3"], ["friday", "not ready", "pending", "delay"]],
    "F6": [["dizz", "lightheaded", "warn-4"]],
    "F7": [["simple", "plain", "easy"]],
}
SETS = {"dev": (DEV, DEV_FACTS), "heldout": (HELDOUT, HELDOUT_FACTS)}
HAND = {"F2", "F3"}  # key words can't see distortions here (Zorvexa linked to a real drug, timing called a dose change)
SAFETY = ["F3", "F5", "F6"]
OTHER = ["F1", "F2", "F7"]  # F4 is reported but not scored

INSTRUCTIONS = ("You keep the session memory for HomeStretch, an assistant that helps a family caregiver in the 30 "
                "days after a parent's hospital discharge. You get the patient's care plan, the cabinet check, the "
                "current memory, and the caregiver's newest message. ")
SUMMARY_TASK = ("Update the summary with the newest message, in at most 80 words, keeping what the assistant will need "
                'later in this conversation. Reply with JSON only: {"summary": "..."}')
RECORD_TASK = ("Update the session record with the newest message. Use plan ids (med-1, flag-1, warn-1, ...) where "
               "they apply. Reply with JSON only, with exactly these keys: open_flags, resolved_flags, "
               "pending_questions, caregiver_reports, red_flags, preferences (lists of short strings), and "
               "current_medicine (a string or null).")
EMPTY_RECORD = {"open_flags": [], "resolved_flags": [], "pending_questions": [], "caregiver_reports": [],
                "red_flags": [], "preferences": [], "current_medicine": None}


def survives(text, groups):
    text = text.lower()
    return all(any(w in text for w in group) for group in groups)


def values_text(obj):
    """String values of a JSON record, without its keys (so a key like "pending_questions" can't match "pending")."""
    if isinstance(obj, dict):
        return " ".join(values_text(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(values_text(v) for v in obj)
    return "" if obj is None else str(obj)


def window(turns, k):
    return "\n".join(f"Turn {i}: {t}" for i, t in enumerate(turns, 1) if i > len(turns) - k)


def ask(model, task, memory, turns, turn, cache, calls):
    fx = json.loads((ROOT / "fixtures" / "p001.json").read_text())
    context = json.dumps({"care_plan": fx["care_plan"], "cabinet_diff": fx["cabinet_diff"]})
    messages = [{"role": "system", "content": INSTRUCTIONS + task},
                {"role": "user", "content": f"<context>{context}</context>\n<memory>{memory}</memory>\n"
                                            f"<newest_message>Turn {turn}: {turns[turn - 1]}</newest_message>"}]
    key = model + "|" + hashlib.sha256(json.dumps(messages).encode()).hexdigest()[:16]
    if key not in cache:
        text, _, usage = get_provider(model).complete(messages, temperature=0.0)
        calls.append(usage)
        cache[key] = text
        CACHE.write_text(json.dumps(cache, indent=2))
    return json.JSONDecoder().raw_decode(cache[key].strip())[0]  # first object; deepseek once added "</summary>"


def build(model, turns, cache, calls):
    """Per-turn updates, as the app would do them: each call sees only the previous memory and the newest message."""
    summary, record = "", EMPTY_RECORD
    for turn in range(1, len(turns) + 1):
        summary = ask(model, SUMMARY_TASK, summary, turns, turn, cache, calls)["summary"]
        record = ask(model, RECORD_TASK, json.dumps(record), turns, turn, cache, calls)
        print(f"  turn {turn} done", flush=True)
    return summary, record


def log_spend(model, calls):
    entry = get_entry(model)
    price = entry["price"]
    hit = sum(u.get("prompt_cache_hit_tokens", 0) for u in calls)
    row = {"utc_time": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "run": "rag-memory_memory_check",
           "model_key": model, "model": entry["model"], "calls": len(calls), "cached_calls": 0,
           "input_hit": hit, "input_miss": sum(u.get("prompt_tokens", 0) for u in calls) - hit,
           "output": sum(u.get("completion_tokens", 0) for u in calls), "reasoning": 0, "est_usd": "",
           "actual_usd": f"{sum(cost_usd(u, price) or 0 for u in calls):.4f}"}
    with open(SPEND, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=SPEND_FIELDS).writerow(row)
    return row["actual_usd"]


def self_check():
    assert survives("Maria bagged the old Lopressor", DEV_FACTS["F1"])
    assert not survives("Lopressor is still in the cabinet", DEV_FACTS["F1"])  # one group only: not enough
    assert survives("Lisinopril moved to BEDTIME", DEV_FACTS["F2"])
    assert not survives("lisinopril 10 mg", DEV_FACTS["F2"])
    assert survives("new furosemide delayed", DEV_FACTS["F5"])
    assert values_text({"pending_questions": [], "preferences": ["short replies"]}).strip() == "short replies"
    assert not survives(values_text({"pending_questions": ["furosemide"]}), DEV_FACTS["F5"])
    assert window(DEV, 3).startswith("Turn 8:") and window(DEV, 5).startswith("Turn 6:")
    # the 5-turn window must drop a safety fact in both sets, or the small-talk turns are not doing their job
    assert not survives(window(DEV, 5), DEV_FACTS["F3"])
    assert not survives(window(HELDOUT, 5), HELDOUT_FACTS["F6"])
    assert len(DEV) == len(HELDOUT) == 10


def main():
    self_check()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="ollama-qwen3-8b", help="model key from evals/models.yaml")
    parser.add_argument("--heldout", action="store_true", help="also run the held-out conversation (reported run)")
    args = parser.parse_args()
    model = args.model
    if args.heldout and get_entry(model)["price"] == "free":
        raise SystemExit("The held-out conversation is for the reported run only, not build models.")
    load_env()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    calls = []
    for name in ["dev", "heldout"] if args.heldout else ["dev"]:
        report(name, model, cache, calls)
    if calls and get_entry(model)["price"] != "free":
        print(f"\nSpent ${log_spend(model, calls)} ({len(calls)} calls) -> results/spend.csv")
    elif calls:
        print(f"\n{len(calls)} local calls (free).")
    else:
        print("\nAll answers from cache; no API calls.")


def report(set_name, model, cache, calls):
    turns, facts = SETS[set_name]
    print(f"\n=== {set_name} conversation ===")
    summary, record = build(model, turns, cache, calls)
    memories = {
        "M1 window, last 3": (window(turns, 3), window(turns, 3)),
        "M2 window, last 5": (window(turns, 5), window(turns, 5)),
        "M3 summary": (summary, summary),
        "M4 session record": (json.dumps(record, indent=1), values_text(record)),
    }

    print(f"\nModel: {model}, {set_name}. F2 and F3: key-word hint only ('?'), the score is the hand read.\n")
    print("| Approach | " + " | ".join(facts) + " | Safety F5, F6 (+F3 by hand) | Other F1, F7 (+F2 by hand) | Words |")
    print("|---|" + "---|" * (len(facts) + 3))
    for name, (shown, scored) in memories.items():
        hits = {f: survives(scored, g) for f, g in facts.items()}
        marks = " | ".join(("yes" if hits[f] else "no") + ("?" if f in HAND else "") for f in facts)
        print(f"| {name} | {marks} | {sum(hits[f] for f in SAFETY if f not in HAND)}/2 "
              f"| {sum(hits[f] for f in OTHER if f not in HAND)}/2 | {len(shown.split())} |")

    for name, (shown, _) in memories.items():
        print(f"\n--- {name} (read by hand for distortions) ---\n{shown}")


if __name__ == "__main__":
    main()
