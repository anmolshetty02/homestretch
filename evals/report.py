"""Summaries for one run, and comparisons between runs.

  python -m evals.report results/<run>                      # rebuild summary.md
  python -m evals.report --compare results/<A> results/<B>  # side-by-side table for slides
"""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def load(run_dir):
    with open(Path(run_dir) / "records.jsonl") as f:
        return [json.loads(line) for line in f if line.strip()]


def pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "n/a"


def tier_of(rec):
    return (rec.get("reply") or {}).get("red_flag_tier")


def metrics(records):
    m = {"records": len(records)}
    m["pass_rate"] = sum(r["overall"] == "pass" for r in records) / max(len(records), 1)

    t3 = [r for r in records if r["expect"].get("red_flag_tier") == 3]
    m["tier3_recall"] = sum(tier_of(r) == 3 for r in t3) / len(t3) if t3 else None
    m["under_triage"] = sum(r["checks"].get("tier", ["skip"])[0] == "fail" for r in records)
    m["over_triage"] = sum(r["checks"].get("tier", ["skip"])[0] == "warn" for r in records)
    m["identity_leaks"] = sum(r["checks"].get("identity_gate", ["skip"])[0] == "fail" for r in records)
    m["json_failures"] = sum(r["checks"].get("json_valid", ["fail"])[0] == "fail" for r in records)
    m["self_check_overconfident"] = sum(r["checks"].get("self_check_honest", ["skip"])[0] == "warn" for r in records)

    # Sensitivity: on the first repeat, do all variants of a case get the same tier and the same verdict?
    by_case = defaultdict(list)
    for r in records:
        if r["repeat"] == 0:
            by_case[r["case"]].append(r)
    multi = {c: rs for c, rs in by_case.items() if len(rs) > 1}
    unstable_cases = [c for c, rs in multi.items()
                      if len({tier_of(r) for r in rs}) > 1 or len({r["overall"] for r in rs}) > 1]
    m["sensitivity_consistent"] = 1 - len(unstable_cases) / len(multi) if multi else None
    m["sensitivity_inconsistent_cases"] = sorted(unstable_cases)

    # Stability: same input repeated. Do tier, state, and intent stay the same?
    by_input = defaultdict(list)
    for r in records:
        by_input[(r["case"], r["variant"])].append(r)
    repeated = {k: rs for k, rs in by_input.items() if len(rs) > 1}

    def sig(r):
        rep = r.get("reply") or {}
        return (rep.get("red_flag_tier"), rep.get("state"), rep.get("intent"), r["overall"])

    m["stability"] = (sum(len({sig(r) for r in rs}) == 1 for rs in repeated.values()) / len(repeated)) if repeated else None

    lat = sorted(r["latency_s"] for r in records if r.get("latency_s") is not None)
    m["latency_p50"] = statistics.median(lat) if lat else None
    m["latency_p95"] = lat[int(0.95 * (len(lat) - 1))] if lat else None
    m["tokens"] = sum((r.get("usage") or {}).get("total_tokens", 0) for r in records)
    return m


def write_summary(run_dir):
    run_dir = Path(run_dir)
    records = load(run_dir)
    m = metrics(records)
    meta = json.loads((run_dir / "meta.json").read_text()) if (run_dir / "meta.json").exists() else {}

    check_counts = defaultdict(lambda: defaultdict(int))
    for r in records:
        for name, (status, _) in r["checks"].items():
            check_counts[name][status] += 1
    by_cat = defaultdict(list)
    for r in records:
        by_cat[r["category"]].append(r["overall"] == "pass")

    def fmt(v, as_pct=True):
        if v is None:
            return "n/a"
        return f"{100 * v:.0f}%" if as_pct else f"{v:.2f}s"

    lines = [f"# Run {run_dir.name}", ""]
    if meta.get("provider") == "mock":
        lines += ["> MOCK RUN: plumbing test only. These numbers say nothing about the prompt.", ""]
    lines += [
        f"Prompt `{meta.get('version')}`{' + critic ' + meta['critic'] if meta.get('critic') else ''}, "
        f"model `{meta.get('model')}`, temperature {meta.get('temperature')}, repeats {meta.get('repeats')}", "",
        "## Headline", "",
        "| Metric | Value |", "|---|---|",
        f"| Replies scored | {m['records']} |",
        f"| Overall pass rate | {fmt(m['pass_rate'])} |",
        f"| Tier-3 (911) recall | {fmt(m['tier3_recall'])} |",
        f"| Under-triage (fail) | {m['under_triage']} |",
        f"| Over-triage (warn) | {m['over_triage']} |",
        f"| Identity leaks | {m['identity_leaks']} |",
        f"| Invalid JSON | {m['json_failures']} |",
        f"| Self-check said OK but a check failed | {m['self_check_overconfident']} |",
        f"| Sensitivity: cases consistent across variants | {fmt(m['sensitivity_consistent'])} |",
        f"| Stability: identical across repeats | {fmt(m['stability'])} |",
        f"| Latency p50 / p95 | {fmt(m['latency_p50'], False)} / {fmt(m['latency_p95'], False)} |",
        f"| Tokens used | {m['tokens']:,} |", "",
        "## By check", "", "| Check | Pass | Warn | Fail |", "|---|---|---|---|",
    ]
    for name, c in check_counts.items():
        if c["pass"] + c["warn"] + c["fail"]:
            lines.append(f"| {name} | {c['pass']} | {c['warn']} | {c['fail']} |")
    lines += ["", "## By category", "", "| Category | Pass rate | n |", "|---|---|---|"]
    for cat, vals in sorted(by_cat.items()):
        lines.append(f"| {cat} | {pct(sum(vals), len(vals))} | {len(vals)} |")
    if m["sensitivity_inconsistent_cases"]:
        lines += ["", "## Inconsistent across variants (sensitivity)", ""]
        lines += [f"- {c}" for c in m["sensitivity_inconsistent_cases"]]

    fails = [r for r in records if r["overall"] == "fail" or any(s == "warn" for s, _ in r["checks"].values())]
    lines += ["", "## Failures and warnings (first 40)", ""]
    for r in fails[:40]:
        bad = "; ".join(f"{k}: {s} {d}".strip() for k, (s, d) in r["checks"].items() if s in ("fail", "warn"))
        say = ((r.get("reply") or {}).get("say") or r.get("parse_error") or "")[:180]
        lines.append(f"- **{r['case']} / {r['variant']} / r{r['repeat']}** ({r['overall']}): {bad}  \n  Input: {r['input'][:120]}  \n  Said: {say}")
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    (run_dir / "summary.json").write_text(json.dumps({"meta": meta, "metrics": m}, indent=2))
    return m


def compare(dir_a, dir_b):
    ra, rb = load(dir_a), load(dir_b)
    ma, mb = metrics(ra), metrics(rb)
    rows = [("Overall pass rate", "pass_rate", True), ("Tier-3 recall", "tier3_recall", True),
            ("Under-triage", "under_triage", False), ("Over-triage", "over_triage", False),
            ("Identity leaks", "identity_leaks", False), ("Invalid JSON", "json_failures", False),
            ("Self-check overconfident", "self_check_overconfident", False),
            ("Sensitivity consistent", "sensitivity_consistent", True), ("Stability", "stability", True),
            ("Latency p50 (s)", "latency_p50", False)]

    def show(v, is_pct):
        if v is None:
            return "n/a"
        return f"{100 * v:.0f}%" if is_pct else (f"{v:.2f}" if isinstance(v, float) else str(v))

    print(f"| Metric | {Path(dir_a).name} | {Path(dir_b).name} |\n|---|---|---|")
    for label, key, is_pct in rows:
        print(f"| {label} | {show(ma[key], is_pct)} | {show(mb[key], is_pct)} |")

    va = {(r["case"], r["variant"], r["repeat"]): r["overall"] for r in ra}
    vb = {(r["case"], r["variant"], r["repeat"]): r["overall"] for r in rb}
    fixed = sorted(k for k in va if k in vb and va[k] == "fail" and vb[k] == "pass")
    broke = sorted(k for k in va if k in vb and va[k] == "pass" and vb[k] == "fail")
    print(f"\nFixed ({len(fixed)}): " + ", ".join(f"{c}/{v}" for c, v, _ in fixed))
    print(f"Broke ({len(broke)}): " + ", ".join(f"{c}/{v}" for c, v, _ in broke))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?", help="run folder to summarize")
    ap.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"))
    args = ap.parse_args()
    if args.compare:
        compare(*args.compare)
    elif args.run:
        write_summary(args.run)
        print(f"Wrote {Path(args.run) / 'summary.md'}")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
