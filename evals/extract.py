"""Prompt A, OCR route: label image -> Tesseract -> model with prompts/extract_vN.md -> {name, strength, directions}.

  python -m evals.render_labels                                   # once: synthetic label images + manifest
  python -m evals.extract --version v1                            # field-level scoring on every label image
  python -m evals.extract --version v1 --e2e dx-01 dx-02 dx-06    # plus end to end: extracted cabinet -> Prompt B -> flags

Each field is scored correct, unreadable (safe: the pipeline can ask the caregiver or the pharmacist), or wrong.
A wrong medicine name is the dangerous outcome and is counted separately.
"""
import argparse
import datetime as dt
import json
import re
import statistics
import subprocess
from pathlib import Path

import yaml

from evals.checks import overall, parse_reply, run_checks, score_flags
from evals.providers import cost_usd, get_entry, get_provider
from evals.run import ROOT, build_messages, cached_call, collect_ids, estimate_usd, load_env, log_spend, render

FIELDS = ("name", "strength", "directions")


def ocr(path):
    return subprocess.run(["tesseract", str(ROOT / path), "-", "--psm", "6"], capture_output=True, text=True, check=True).stdout


def norm(text):
    t = " ".join(str(text or "").lower().split()).rstrip(".")
    return re.sub(r"(\d)\s*(mg|g|mcg|ml)\b", r"\1 \2", t)


def field_status(got, truth):
    if norm(got) == "unreadable":
        return "unreadable"
    return "correct" if norm(got) == norm(truth) else "wrong"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="extract prompt version, e.g. v1 -> prompts/extract_v1.md")
    ap.add_argument("--model", default="deepseek-flash")
    ap.add_argument("--temperature", type=float, default=0.3)
    ap.add_argument("--e2e", nargs="*", default=[], help="cabinet case ids to run end to end through Prompt B")
    ap.add_argument("--e2e-style", default="blur", help="label style used for the end-to-end cabinets")
    ap.add_argument("--agent", default="v3", help="Prompt B version for the end-to-end check")
    ap.add_argument("--max-cost", type=float, default=0.50)
    args = ap.parse_args()

    load_env()
    entry, provider = get_entry(args.model), get_provider(args.model)
    system = (ROOT / "prompts" / f"extract_{args.version}.md").read_text()
    manifest = json.loads((ROOT / "fixtures" / "labels" / "manifest.json").read_text())
    cases = {c["id"]: c for c in yaml.safe_load((ROOT / "evals" / "cases" / "cabinet_diff.yaml").read_text())}
    fixture = json.loads((ROOT / "fixtures" / "p001.json").read_text())

    jobs = [(lab, [{"role": "system", "content": system}, {"role": "user", "content": ocr(lab["path"])}]) for lab in manifest["labels"]]
    # the e2e agent calls are estimated with the true cabinet as a stand-in for the extracted one
    agent_tpl = (ROOT / "prompts" / f"agent_{args.agent}.md").read_text()
    proxy = [build_messages(render(agent_tpl, fixture, cases[c]), cases[c], json.dumps(cases[c]["cabinet"])) for c in args.e2e]
    est, new_calls = estimate_usd(entry, [(m, 0) for _, m in jobs] + [(m, 0) for m in proxy], args.temperature, None)
    print(f"Estimate: {len(jobs) + len(proxy)} calls, {new_calls} not cached, ~${est:.3f} at peak prices")
    if est is not None and est > args.max_cost:
        raise SystemExit(f"Aborted: estimate ${est:.3f} is over --max-cost ${args.max_cost:.2f}.")

    run_dir = ROOT / "results" / f"extract_{args.version}_{args.model}_t{args.temperature}_{dt.datetime.now():%m%d-%H%M}"
    run_dir.mkdir(parents=True, exist_ok=True)
    records, extracted = [], {}
    for lab, messages in jobs:
        raw, latency, usage, cached = cached_call(provider, entry, messages, args.temperature, 0)
        reply, err = parse_reply(raw)
        fields = {f: field_status((reply or {}).get(f), lab["truth"][f]) for f in FIELDS}
        extracted[(lab["label"], lab["style"])] = {f: (reply or {}).get(f, "unreadable") for f in FIELDS}
        records.append({"kind": "extract", "label": lab["label"], "style": lab["style"], "ocr": messages[1]["content"],
                        "truth": lab["truth"], "reply": reply, "parse_error": err, "fields": fields,
                        "latency_s": round(latency, 3), "usage": usage, "cached": cached, "cost_usd": cost_usd(usage, entry.get("price"))})
        print("." if all(v == "correct" for v in fields.values()) else ("u" if "wrong" not in fields.values() else "W"), end="", flush=True)
    print()

    fixture_ids = collect_ids(fixture)
    for cid in args.e2e:
        case = cases[cid]
        cabinet = [{"id": cab, **extracted[(manifest["cabinets"][cid][cab], args.e2e_style)]} for cab in manifest["cabinets"][cid]]
        text = json.dumps(cabinet)
        messages = build_messages(render(agent_tpl, fixture, case), case, text)
        raw, latency, usage, cached = cached_call(provider, entry, messages, args.temperature, 0)
        reply, err = parse_reply(raw)
        checks = run_checks(reply, case, fixture_ids, text)
        records.append({"kind": "e2e", "case": cid, "style": args.e2e_style, "cabinet": cabinet, "reply": reply,
                        "parse_error": err, "checks": checks, "overall": overall(checks),
                        "flags": score_flags(reply, case["expect"]["flags"]) if reply else None,
                        "latency_s": round(latency, 3), "usage": usage, "cached": cached, "cost_usd": cost_usd(usage, entry.get("price"))})

    with open(run_dir / "records.jsonl", "w") as f:
        f.writelines(json.dumps(r, default=dict) + "\n" for r in records)
    meta = {**vars(args), "model_id": entry.get("model"), "extra_body": entry.get("extra_body")}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    row = log_spend(run_dir, args, entry, records, est)
    write_summary(run_dir, records, meta)
    print(f"Spent ${row['actual_usd']} -> results/spend.csv\nSummary: {run_dir / 'summary.md'}")


def write_summary(run_dir, records, meta):
    ex = [r for r in records if r["kind"] == "extract"]
    styles = sorted({r["style"] for r in ex}, key=["clean", "blur", "tilt"].index)
    lines = [f"# Extract run {run_dir.name}", "",
             f"Prompt A `extract_{meta['version']}`, model `{meta['model']}`, temperature {meta['temperature']}. "
             f"OCR: Tesseract (--psm 6). {len(ex)} label images.", "",
             "## Field accuracy by style", "",
             "| Style | Labels | All 3 fields correct | Name correct | Strength correct | Directions correct | Unreadable fields | **Wrong names** |",
             "|---|---|---|---|---|---|---|---|"]
    for s in styles + ["all"]:
        rs = [r for r in ex if s == "all" or r["style"] == s]
        def n(field, status):
            return sum(r["fields"][field] == status for r in rs)
        lines.append(f"| {s} | {len(rs)} | {sum(all(v == 'correct' for v in r['fields'].values()) for r in rs)} | "
                     f"{n('name', 'correct')} | {n('strength', 'correct')} | {n('directions', 'correct')} | "
                     f"{sum(list(r['fields'].values()).count('unreadable') for r in rs)} | {n('name', 'wrong')} |")
    costs = [r["cost_usd"] for r in ex if r["cost_usd"] is not None]
    lat = [r["latency_s"] for r in ex]
    lines += ["", f"Cost per label: ${statistics.mean(costs):.5f} (all {len(ex)} labels: ${sum(costs):.4f}). "
                  f"Latency p50: {statistics.median(lat):.2f}s. Invalid JSON: {sum(r['reply'] is None for r in ex)}.", ""]
    wrong = [r for r in ex if "wrong" in r["fields"].values()]
    lines += ["## Wrong fields (first 30)", ""]
    for r in wrong[:30]:
        bad = {f: (r["reply"] or {}).get(f) for f, v in r["fields"].items() if v == "wrong"}
        lines.append(f"- **{r['label']} / {r['style']}**: got {bad}; truth {{" + ", ".join(f"'{f}': '{r['truth'][f]}'" for f in bad) + "}")
    e2e = [r for r in records if r["kind"] == "e2e"]
    if e2e:
        lines += ["", f"## End to end ({e2e[0]['style']} labels → extract → Prompt B {meta['agent']} → flag scoring)", "",
                  "| Case | Overall | Flags | Critical | Caught | Missed | False alarms |", "|---|---|---|---|---|---|---|"]
        for r in e2e:
            fl = r["flags"] or {}
            lines.append(f"| {r['case']} | {r['overall']} | {r['checks'].get('flags', ['?'])[0]} | {r['checks'].get('critical', ['?'])[0]} | "
                         f"{sum((fl.get('caught') or {}).values())} | {sum((fl.get('missed') or {}).values())} | {sum((fl.get('false_alarms') or {}).values())} |")
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
