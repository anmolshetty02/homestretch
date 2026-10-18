"""Run the test suite against one prompt version.

Examples:
  python -m evals.run --version v1 --model mock
  python -m evals.run --version v1 --model deepseek-flash
  python -m evals.run --version v1 --model deepseek-flash --repeats 3 --category cabinet_diff --max-cost 1.00
  python -m evals.run --version v1 --model ollama-qwen3-8b
Model keys live in evals/models.yaml.
"""
import argparse
import csv
import datetime as dt
import glob
import hashlib
import json
from pathlib import Path

import yaml

from evals import report
from evals.checks import overall, parse_reply, run_checks
from evals.providers import cost_usd, get_entry, get_provider, ollama_context

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / ".cache"
SPEND = ROOT / "results" / "spend.csv"
SPEND_FIELDS = ["utc_time", "run", "model_key", "model", "calls", "cached_calls", "input_hit", "input_miss",
                "output", "reasoning", "est_usd", "actual_usd"]


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def collect_ids(fixture):
    ids = set()
    plan = fixture["care_plan"]
    for section in plan.values():
        for item in section:
            ids.add(item["id"])
    ids.update(flag["id"] for flag in fixture["cabinet_diff"])
    return ids


NO_DIFF = "No cabinet check has been run yet."


def render(template, fixture, case):
    values = {
        "today": fixture["today"],
        "patient_profile": json.dumps(fixture["patient_profile"]),
        "care_plan": json.dumps(fixture["care_plan"]),
        # diff cases must not see the answer key
        "cabinet_diff": NO_DIFF if "cabinet" in case else json.dumps(fixture["cabinet_diff"]),
    }
    for key, val in values.items():
        template = template.replace("{{" + key + "}}", val)
    return template


def build_messages(system, case, user_text):
    messages = [{"role": "system", "content": system}]
    for turn in case.get("history", []) or []:
        if turn["role"] == "assistant":  # earlier agent turns are shown in the agent's own JSON format
            messages.append({"role": "assistant", "content": json.dumps({"reply": turn["reply"]})})
        else:
            messages.append({"role": "user", "content": turn["content"]})
    messages.append({"role": "user", "content": user_text})
    return messages


def cache_path(entry, messages, temperature, repeat):
    # the whole model setup is in the key, so thinking-on and thinking-off replies never mix
    setup = {k: entry.get(k) for k in ("provider", "model", "extra_body")}
    key = hashlib.sha256(json.dumps([setup, temperature, repeat, messages], sort_keys=True).encode()).hexdigest()[:24]
    return CACHE / f"{key}.json"


def cached_call(provider, entry, messages, temperature, repeat):
    path = cache_path(entry, messages, temperature, repeat)
    if path.exists() and entry["provider"] != "mock":
        hit = json.loads(path.read_text())
        return hit["text"], hit["latency"], hit.get("usage", {}), True
    text, latency, usage = provider.complete(messages, temperature)
    if entry["provider"] != "mock":
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"text": text, "latency": latency, "usage": usage}))
    return text, latency, usage, False


def estimate_usd(entry, jobs, temperature, critic):
    """Upper-bound cost of the calls that are not cached yet. Input ~ chars/3 (pessimistic), output from the registry."""
    new = [m for m, rep in jobs if entry["provider"] == "mock" or not cache_path(entry, m, temperature, rep).exists()]
    if entry.get("price") == "free":
        return 0.0, len(new)
    usage = {"prompt_tokens": sum(len(json.dumps(m)) // 3 for m in new),
             "completion_tokens": len(new) * entry.get("est_output_tokens", 1000)}
    est = cost_usd(usage, entry.get("price"))
    return (est * (2 if critic else 1) if est is not None else None), len(new)


def log_spend(run_dir, args, entry, records, est):
    fresh = [r for r in records if not r["cached"]]
    u = [r.get("usage") or {} for r in fresh]
    hit = sum(x.get("prompt_cache_hit_tokens", 0) for x in u)
    row = {
        "utc_time": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "run": run_dir.name,
        "model_key": args.model, "model": entry.get("model", "mock"), "calls": len(records),
        "cached_calls": len(records) - len(fresh), "input_hit": hit,
        "input_miss": sum(x.get("prompt_tokens", 0) for x in u) - hit,
        "output": sum(x.get("completion_tokens", 0) for x in u),
        "reasoning": sum((x.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) for x in u),
        "est_usd": f"{est:.4f}" if est is not None else "", "actual_usd": f"{sum(r['cost_usd'] or 0 for r in fresh):.4f}",
    }
    new_file = not SPEND.exists()
    with open(SPEND, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SPEND_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(row)
    return row


def load_cases(category=None, case_ids=None):
    cases = []
    for f in sorted(glob.glob(str(ROOT / "evals" / "cases" / "*.yaml"))):
        cases.extend(yaml.safe_load(Path(f).read_text()) or [])
    if category:
        cases = [c for c in cases if c["category"] == category]
    if case_ids:
        cases = [c for c in cases if c["id"] in case_ids]
    return cases


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="prompt version, e.g. v1 -> prompts/agent_v1.md")
    ap.add_argument("--model", default="deepseek-flash", help="model key from evals/models.yaml (mock for dry runs)")
    ap.add_argument("--temperature", type=float, default=0.3)
    ap.add_argument("--repeats", type=int, default=1, help="calls per input; >1 measures stability")
    ap.add_argument("--category", help="only run one category, e.g. red_flag or cabinet_diff")
    ap.add_argument("--cases", nargs="*", help="only run these case ids")
    ap.add_argument("--no-variants", action="store_true", help="skip variants (base inputs only)")
    ap.add_argument("--critic", help="optional critic prompt, e.g. critic_v1")
    ap.add_argument("--fixture", default="p001")
    ap.add_argument("--tag", default="", help="label added to the run folder name")
    ap.add_argument("--max-cost", type=float, default=0.50, help="abort if the estimated USD cost is higher")
    args = ap.parse_args()

    load_env()
    entry = get_entry(args.model)
    provider = get_provider(args.model)
    template = (ROOT / "prompts" / f"agent_{args.version}.md").read_text()
    critic_template = (ROOT / "prompts" / f"{args.critic}.md").read_text() if args.critic else None
    fixture = json.loads((ROOT / "fixtures" / f"{args.fixture}.json").read_text())
    fixture_ids = collect_ids(fixture)
    cases = load_cases(args.category, args.cases)

    # Plan every call first, so the cost guard runs before anything is spent.
    jobs = []
    for case in cases:
        system = render(template, fixture, case)
        # diff cases send the cabinet (what the vision step would produce) as JSON
        inputs = [("base", json.dumps(case["cabinet"]) if "cabinet" in case else case["input"])]
        if not args.no_variants:
            inputs += [(v["kind"], json.dumps(v["cabinet"]) if "cabinet" in v else v["text"]) for v in case.get("variants", [])]
        for kind, text in inputs:
            for rep in range(args.repeats):
                jobs.append((case, kind, text, rep, build_messages(system, case, text)))
    est, new_calls = estimate_usd(entry, [(m, rep) for *_, rep, m in jobs], args.temperature, args.critic)
    print(f"Estimate: {len(jobs)} calls, {new_calls} not cached, "
          + ("free" if est == 0 else "price unknown" if est is None else f"~${est:.3f} at peak prices"))
    if est is not None and est > args.max_cost:
        raise SystemExit(f"Aborted: estimate ${est:.3f} is over --max-cost ${args.max_cost:.2f}. Raise it to run.")

    temp_label = "-" if entry.get("temperature_ignored") else args.temperature
    stamp = dt.datetime.now().strftime("%m%d-%H%M")
    name = f"{args.version}{'+' + args.critic if args.critic else ''}_{args.model}_t{temp_label}_{stamp}"
    run_dir = ROOT / "results" / (name + (f"_{args.tag}" if args.tag else ""))
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {**vars(args), "model_key": args.model, "provider": entry["provider"], "model_id": entry.get("model"),
            "extra_body": entry.get("extra_body"), "temperature_ignored": bool(entry.get("temperature_ignored")),
            "num_ctx": entry.get("num_ctx"), "server_context": None}

    print(f"Run {run_dir.name}: {len(cases)} cases, {len(jobs)} calls{' (x2 with critic)' if args.critic else ''}")
    records = []
    try:
        with open(run_dir / "records.jsonl", "w") as out:
            for case, kind, text, rep, messages in jobs:
                raw, latency, usage, from_cache = cached_call(provider, entry, messages, args.temperature, rep)
                if entry["provider"] == "ollama" and meta["server_context"] is None and not from_cache:
                    # Ollama silently truncates prompts longer than its context, so check what it actually loaded
                    meta["server_context"] = ollama_context(entry)
                    if (meta["server_context"] or 0) < entry["num_ctx"]:
                        raise SystemExit(f"Aborted: Ollama loaded {entry['model']} with context {meta['server_context']}, "
                                         f"registry needs {entry['num_ctx']}. Restart the server with OLLAMA_CONTEXT_LENGTH.")
                reply, err = parse_reply(raw)
                critic_info = None
                if critic_template and reply is not None:
                    c_msgs = [{"role": "system", "content": render(critic_template, fixture, case)},
                              {"role": "user", "content": json.dumps({"caller_said": text, "assistant_reply": reply})}]
                    c_raw, c_lat, _, _ = cached_call(provider, entry, c_msgs, 0.0, rep)
                    c_obj, _ = parse_reply(c_raw)
                    latency += c_lat
                    if c_obj and c_obj.get("verdict") == "revise" and isinstance(c_obj.get("revised"), dict):
                        critic_info = {"verdict": "revise", "problems": c_obj.get("problems", []), "original_reply": reply.get("reply")}
                        reply = c_obj["revised"]
                    else:
                        critic_info = {"verdict": (c_obj or {}).get("verdict", "unparsed")}
                checks = run_checks(reply, case, fixture_ids)
                record = {
                    "case": case["id"], "category": case["category"], "variant": kind, "repeat": rep,
                    "expect": case.get("expect", {}),
                    "input": text, "raw": raw if reply is None else None, "parse_error": err,
                    "reply": reply, "checks": checks, "overall": overall(checks),
                    "latency_s": round(latency, 3), "usage": usage, "cached": from_cache, "critic": critic_info,
                    "cost_usd": cost_usd(usage, entry.get("price")),  # what this call costs fresh, even if cached now
                }
                out.write(json.dumps(record) + "\n")
                records.append(record)
                print("." if record["overall"] == "pass" else "F", end="", flush=True)
    finally:
        print()
        (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        if entry["provider"] != "mock":
            row = log_spend(run_dir, args, entry, records, est)
            print(f"Spent ${row['actual_usd']} ({row['calls']} calls, {row['cached_calls']} cached) -> results/spend.csv")
    report.write_summary(run_dir)
    print(f"Summary: {run_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
