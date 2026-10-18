"""Run the test suite against one prompt version.

Examples:
  python -m evals.run --version v1 --provider mock
  python -m evals.run --version v1 --provider custom --model deepseek-v4-flash
  python -m evals.run --version v1 --provider custom --repeats 3 --category cabinet_diff
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
from pathlib import Path

import yaml

from evals import report
from evals.checks import overall, parse_reply, run_checks
from evals.providers import get_provider

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / ".cache"


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


def cached_call(provider, provider_name, messages, model, temperature, repeat):
    key = hashlib.sha256(json.dumps([provider_name, model, temperature, repeat, messages]).encode()).hexdigest()[:24]
    path = CACHE / f"{key}.json"
    if path.exists() and provider_name != "mock":
        hit = json.loads(path.read_text())
        return hit["text"], hit["latency"], hit.get("usage", {}), True
    text, latency, usage = provider.complete(messages, model, temperature)
    if provider_name != "mock":
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"text": text, "latency": latency, "usage": usage}))
    return text, latency, usage, False


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
    ap.add_argument("--provider", default="mock", help="mock | groq | custom")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--temperature", type=float, default=0.3)
    ap.add_argument("--repeats", type=int, default=1, help="calls per input; >1 measures stability")
    ap.add_argument("--category", help="only run one category, e.g. red_flag or cabinet_diff")
    ap.add_argument("--cases", nargs="*", help="only run these case ids")
    ap.add_argument("--no-variants", action="store_true", help="skip variants (base inputs only)")
    ap.add_argument("--critic", help="optional critic prompt, e.g. critic_v1")
    ap.add_argument("--fixture", default="p001")
    ap.add_argument("--tag", default="", help="label added to the run folder name")
    args = ap.parse_args()

    load_env()
    provider = get_provider(args.provider)
    template = (ROOT / "prompts" / f"agent_{args.version}.md").read_text()
    critic_template = (ROOT / "prompts" / f"{args.critic}.md").read_text() if args.critic else None
    fixture = json.loads((ROOT / "fixtures" / f"{args.fixture}.json").read_text())
    fixture_ids = collect_ids(fixture)
    cases = load_cases(args.category, args.cases)

    model_short = args.model.split("/")[-1] if args.provider != "mock" else "mock"
    stamp = dt.datetime.now().strftime("%m%d-%H%M")
    name = f"{args.version}{'+' + args.critic if args.critic else ''}_{model_short}_t{args.temperature}_{stamp}"
    run_dir = ROOT / "results" / (name + (f"_{args.tag}" if args.tag else ""))
    run_dir.mkdir(parents=True, exist_ok=True)

    total = sum((1 + (0 if args.no_variants else len(c.get("variants", [])))) for c in cases) * args.repeats
    print(f"Run {run_dir.name}: {len(cases)} cases, {total} calls{' (x2 with critic)' if args.critic else ''}")
    calls = 0
    with open(run_dir / "records.jsonl", "w") as out:
        for case in cases:
            system = render(template, fixture, case)
            # diff cases send the cabinet (what the vision step would produce) as JSON
            inputs = [("base", json.dumps(case["cabinet"]) if "cabinet" in case else case["input"])]
            if not args.no_variants:
                inputs += [(v["kind"], json.dumps(v["cabinet"]) if "cabinet" in v else v["text"]) for v in case.get("variants", [])]
            for kind, text in inputs:
                for rep in range(args.repeats):
                    messages = build_messages(system, case, text)
                    raw, latency, usage, from_cache = cached_call(provider, args.provider, messages, args.model, args.temperature, rep)
                    reply, err = parse_reply(raw)
                    critic_info = None
                    if critic_template and reply is not None:
                        c_msgs = [{"role": "system", "content": render(critic_template, fixture, case)},
                                  {"role": "user", "content": json.dumps({"caller_said": text, "assistant_reply": reply})}]
                        c_raw, c_lat, _, _ = cached_call(provider, args.provider, c_msgs, args.model, 0.0, rep)
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
                    }
                    out.write(json.dumps(record) + "\n")
                    calls += 1
                    mark = "." if record["overall"] == "pass" else "F"
                    print(mark, end="", flush=True)
    print()
    meta = {k: v for k, v in vars(args).items()}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    report.write_summary(run_dir)
    print(f"Summary: {run_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
