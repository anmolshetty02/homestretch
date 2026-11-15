"""Usefulness judge: on every turn where the pipeline ran a lookup, is its reply more useful than v8 alone's?
The A2/A3 checks score safety; v8 alone passes them by deferring, so they cannot see this (prompts/judge_usefulness_v1.md).

    .venv/bin/python -m app.judge_usefulness --model mock            # plumbing only (fixed fake verdicts), never report
    .venv/bin/python -m app.judge_usefulness --model deepseek-flash

Each pair is judged twice with the order swapped; a side wins only if it wins both orders, else tie.
Writes results/usefulness_<model>_<time>/ (records.jsonl, summary.md, meta.json) and a spend.csv row.
"""
import argparse
import collections
import datetime as dt
import json
import random

from app import llm
from app.graph import patient_context
from evals.providers import get_entry
from evals.run import ROOT, log_spend

PROMPT = ROOT / "prompts" / "judge_usefulness_v1.md"
PER_CALL_USD = 0.0005  # upper bound per judge call (care plan + two replies, deepseek-flash, before cache)
# The final runs (docs/workflow/README.md §4): (v8 alone, full pipeline) per set.
PAIRS = [
    ("v8_deepseek-flash_t0.3_1101-1727", "pipeline-gateoff_deepseek-flash_1115-1321"),
    ("v8_deepseek-flash_t0.3_1101-1932_confirm_confirm", "pipeline-gateoff_deepseek-flash_1115-1323_confirm"),
    ("v8_deepseek-flash_t0.3_1114-1023_a4_heldout", "pipeline-gateoff_deepseek-flash_1115-1325_a4_heldout"),
    ("v8_deepseek-flash_t0.3_1114-1047_a4_triage", "pipeline-gateoff_deepseek-flash_1115-1327_a4_triage"),
    ("v8_deepseek-flash_t0.3_1115-1319_heldout", "pipeline-gateoff_deepseek-flash_1115-1319_heldout"),
]


def load(run):
    return [json.loads(line) for line in open(ROOT / "results" / run / "records.jsonl")]


def tools_ran(rec):
    return [part.split(":")[0] for t in rec["trace"] if t["step"] == "tools" for part in t["detail"].split("; ")]


def pairs():
    """Pipeline turns with a lookup, next to v8 alone's reply to the same input."""
    out = []
    for v8_run, pipe_run in PAIRS:
        v8 = {(r["case"], r["variant"]): r for r in load(v8_run)}
        for p in load(pipe_run):
            v = v8.get((p["case"], p["variant"]))
            if v and tools_ran(p):
                out.append({"set": pipe_run, "case": p["case"], "variant": p["variant"], "category": p["category"],
                            "patient": p.get("patient", "p001"), "input": p["input"], "tools": tools_ran(p),
                            "pipeline": p["reply"].get("reply") or "", "v8": v["reply"].get("reply") or ""})
    return out


def judge(pair, first, model):
    """first = "pipeline" or "v8": which reply is shown as A. Returns the winner as a side name, or "tie"."""
    a, b = (pair["pipeline"], pair["v8"]) if first == "pipeline" else (pair["v8"], pair["pipeline"])
    plan = json.dumps(patient_context(pair["patient"])["fixture"]["care_plan"])
    msgs = [{"role": "system", "content": PROMPT.read_text().replace("{{care_plan}}", plan)},
            {"role": "user", "content": f"Caregiver message:\n{pair['input']}\n\nReply A:\n{a}\n\nReply B:\n{b}"}]
    if model == "mock":
        out = {"winner": "A", "why": "mock"}  # fixed: always A, so the swapped pair must come out as a tie
    else:
        out = llm.complete_json(msgs, model, purpose="judge", temperature=0.0)
    w = out.get("winner")
    side = {"A": first, "B": "v8" if first == "pipeline" else "pipeline"}.get(w, "tie" if w == "tie" else "error")
    return side, out.get("why", out.get("error", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mock")
    ap.add_argument("--max-cost", type=float, default=0.25)
    args = ap.parse_args()
    todo = pairs()
    est = 0 if args.model == "mock" else 2 * len(todo) * PER_CALL_USD
    print(f"{len(todo)} pairs, {2 * len(todo)} judge calls, estimate ~${est:.2f} (upper bound)")
    if est > args.max_cost:
        raise SystemExit(f"Aborted: over --max-cost ${args.max_cost}")
    run_dir = ROOT / "results" / f"usefulness_{args.model}_{dt.datetime.now():%m%d-%H%M}"
    run_dir.mkdir(parents=True)
    (run_dir / "meta.json").write_text(json.dumps({"judge_prompt": PROMPT.name, "model": args.model, "temperature": 0.0,
                                                   "pairs_from": PAIRS, "rule": "win = wins both orders, else tie"}, indent=2))
    rows = []
    with open(run_dir / "records.jsonl", "w") as f:
        for pair in todo:
            s1, why1 = judge(pair, "pipeline", args.model)
            s2, why2 = judge(pair, "v8", args.model)
            verdict = s1 if s1 == s2 and s1 in ("pipeline", "v8") else "tie"
            row = {**pair, "order1": s1, "order2": s2, "verdict": verdict, "why": [why1, why2],
                   "cites_lookup": any(f"[{k}-" in pair["pipeline"] for k in ("ref", "name"))}
            rows.append(row)
            f.write(json.dumps(row) + "\n")
            print({"pipeline": "P", "v8": "V", "tie": "."}[verdict], end="", flush=True)
    print()
    tally = collections.Counter(r["verdict"] for r in rows)
    lines = [f"# Usefulness judge: pipeline vs v8 alone ({args.model})", "",
             f"{len(rows)} turns where the pipeline ran a lookup; each judged in both orders; win = wins both orders.", "",
             "| Group | Turns | Pipeline more useful | v8 alone more useful | Tie |", "|---|---|---|---|---|"]
    groups = {"All": rows, "Reply cites a lookup": [r for r in rows if r["cites_lookup"]],
              "Lookup ran, reply cites none": [r for r in rows if not r["cites_lookup"]]}
    for cat in sorted({r["category"] for r in rows}):
        groups[f"category {cat}"] = [r for r in rows if r["category"] == cat]
    for name, g in groups.items():
        c = collections.Counter(r["verdict"] for r in g)
        lines.append(f"| {name} | {len(g)} | {c['pipeline']} | {c['v8']} | {c['tie']} |")
    disagree = sum(r["order1"] != r["order2"] for r in rows)
    lines += ["", f"Order disagreements (counted as tie): {disagree} of {len(rows)}."]
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    if args.model != "mock":
        log_spend(run_dir, args, get_entry(args.model), llm.USAGE, est)
    print("\n".join(lines))
    print(f"Spent ${sum(u['cost_usd'] for u in llm.USAGE if not u['cached']):.4f} -> {run_dir / 'summary.md'}")
    assert args.model != "mock" or tally["tie"] == len(rows), "mock: a position-biased judge must come out all ties"


if __name__ == "__main__":
    main()
