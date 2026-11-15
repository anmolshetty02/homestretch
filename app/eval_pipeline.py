"""Score the WHOLE pipeline (app/graph.py) on the A2/A3 cases, end to end, with the A2 checks (evals/checks.py).
Records use the evals/run.py format, so evals/report.py summarizes them and --compare puts them next to the
single-call Prompt B v8 baseline from A3.

    .venv/bin/python -m app.eval_pipeline --model mock                     # plumbing only, never report
    .venv/bin/python -m app.eval_pipeline --model deepseek-flash --suite cases
    .venv/bin/python -m evals.report --compare results/v8_deepseek-flash_t0.3_1101-1727 results/pipeline_...
"""
import argparse
import datetime as dt
import json
import time

from app import llm
from app.graph import patient_context, run_turn
from evals import report
from evals.checks import overall, run_checks
from evals.providers import get_entry
from evals.run import ROOT, load_cases, log_spend, unstated_names

PER_TURN_USD = 0.004  # upper bound per turn from a deepseek-flash smoke run: tool choice + Prompt B (+ a retry)


def executed_tools(trace):
    """Tools that actually ran (not blocked, refused as duplicates, or unknown)."""
    out = []
    for t in trace:
        if t["step"] == "tools":
            for part in t["detail"].split("; "):
                name, _, status = part.partition(": ")
                if not any(w in status for w in ("blocked", "duplicate", "not available")):
                    out.append(name)
    return out


def tool_check(case, ran):
    """A4 cases may set expect.tools_called / expect.tools_not_called (tool names)."""
    exp = case.get("expect") or {}
    if "tools_called" not in exp and "tools_not_called" not in exp:
        return ("skip", "")
    missing = [t for t in exp.get("tools_called", []) if t not in ran]
    extra = [t for t in exp.get("tools_not_called", []) if t in ran]
    return ("fail", f"missing {missing}, should not run {extra}") if missing or extra else ("pass", ",".join(ran))


def as_reply(final):
    """The caregiver-facing result in Prompt B's JSON shape, so fixed-rule and fallback replies are scored the same way."""
    return {"mode": final["mode"], "analysis": "", "flags": final.get("flags") or [], "sources": final.get("sources") or [],
            "red_flag_tier": final.get("red_flag_tier"), "self_check": None, "reply": final.get("reply")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mock")
    ap.add_argument("--suite", default="cases", choices=["cases", "confirm", "a4_heldout", "a4_triage", "heldout"])
    ap.add_argument("--max-cost", type=float, default=0.75)
    ap.add_argument("--no-tools", action="store_true", help="ablation: same pipeline without the ReAct lookups")
    ap.add_argument("--gate", default="off", choices=["keep", "backstop", "off"], help="911 rule variant")
    args = ap.parse_args()
    jobs = []
    for case in load_cases(suite=args.suite):
        inputs = [("base", case.get("cabinet") or case.get("input"))]
        inputs += [(v["kind"], v.get("cabinet") or v["text"]) for v in case.get("variants", [])]
        jobs += [(case, kind, x) for kind, x in inputs]
    est = 0 if args.model == "mock" else len(jobs) * PER_TURN_USD
    print(f"{len(jobs)} turns, estimate ~${est:.2f} (upper bound, before cache)")
    if est > args.max_cost:
        raise SystemExit(f"Aborted: over --max-cost ${args.max_cost}")

    run_dir = ROOT / "results" / f"pipeline{'-notools' if args.no_tools else ''}-gate{args.gate}_{args.model}_{dt.datetime.now():%m%d-%H%M}{'_' + args.suite if args.suite != 'cases' else ''}"
    run_dir.mkdir(parents=True)
    meta = {"version": "pipeline (graph + v8, no tools)" if args.no_tools else "pipeline (graph + tools_v1 + v8)", "model": args.model, "model_key": args.model,
            "gate": args.gate, "use_tools": not args.no_tools,
            "provider": "mock" if args.model == "mock" else "deepseek", "temperature": 0.3, "repeats": 1, "suite": args.suite}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    with open(run_dir / "records.jsonl", "w") as out:
        for n, (case, kind, x) in enumerate(jobs):
            cabinet = x if isinstance(x, list) else None
            text = json.dumps(cabinet) if cabinet else x
            start = time.time()
            patient = case.get("fixture", "p001")  # Synthea held-out cases name their own patient
            ctx = patient_context(patient)
            res = run_turn(f"eval-{n}", "" if cabinet else x, cabinet=cabinet, model=args.model,
                           history=case.get("history") or [], save=False, use_tools=not args.no_tools, gate=args.gate,
                           patient=patient)
            reply = as_reply(res["final"])
            said = " ".join([text] + [h.get("content", "") for h in case.get("history") or [] if h.get("role") == "user"])
            checks = run_checks(reply, case, ctx["ids"] | set(res["ref_ids"]), text, unstated_names(ctx["fixture"], said))
            checks["tools"] = ("skip", "ablation") if args.no_tools else tool_check(case, executed_tools(res["trace"]))
            usage = {"total_tokens": sum((u.get("usage") or {}).get("total_tokens", 0) for u in res["usage"])}
            rec = {"case": case["id"], "patient": patient, "category": case["category"], "variant": kind, "repeat": 0,
                   "expect": case.get("expect", {}), "input": text, "parse_error": None, "reply": reply,
                   "checks": checks, "overall": overall(checks), "latency_s": round(time.time() - start, 3),
                   "usage": usage, "cached": all(u["cached"] for u in res["usage"]),
                   "cost_usd": sum(u["cost_usd"] for u in res["usage"]), "answered_by": res["final"]["by"],
                   "trace": res["trace"], "model_calls": len(res["usage"])}
            out.write(json.dumps(rec) + "\n")
            print("." if rec["overall"] == "pass" else "F", end="", flush=True)
    print()
    report.write_summary(run_dir)
    spent = sum(u["cost_usd"] for u in llm.USAGE if not u["cached"])
    if args.model != "mock":  # one row per run, like evals/run.py; calls = model calls, not turns
        log_spend(run_dir, args, get_entry(args.model), llm.USAGE, est)
    print(f"Spent ${spent:.4f} this run ({len(llm.USAGE)} model calls) -> results/spend.csv. Summary: {run_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
