"""Router test (Assignment 3): should a caregiver message trigger label retrieval? Setup and success rule: design.md,
Section A ("Router test"). Messages are the 74 A2 chat inputs; labels are fixed below by case id. Run from the repo root:
    .venv/bin/python docs/rag-memory/spikes/router_check.py
"""
import glob
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
# hand labels by case id (all variants of a case share the label); every other chat case = no retrieval
RETRIEVE = {"mq-01", "mq-02"} | {f"s0{i}-{k}" for i in range(1, 7) for k in ("nsaid", "purpose")}
SAFETY = re.compile(r"^(rf-01|rf-04|s0\d-chest|mq-03|mq-04|s0\d-missed|sc-02)$")  # emergencies and dose questions

TIER3 = re.compile(r"chest|can'?t breathe|cant breathe|gasping|barely talk|faint|passed out|confus|can'?t think|cant think"
                   r"|911|struggling to breathe", re.I)
DOSE = re.compile(r"\bdose|missed|forgot|skip|double|two\b|\b2\b|catch up|how much|maximum|most .* in a day|stop (taking|it)"
                  r"|\bstop\b|\bstart\b|split|extra", re.I)
MED = re.compile(r"pill|medicine|medication|\bmed\b|tablet|furosemide|lasix|metoprolol|toprol|lisinopril|zestril"
                 r"|hydrochlorothiazide|clopidogrel|simvastatin|amlodipine|advil|ibuprofen|aleve|naproxen|motrin|tylenol",
                 re.I)
ASK = re.compile(r"\bfor\b|why|side effect|cause|make (her|him)|can (she|he) (take|have)|okay to (give|take)|safe|with (her|his)"
                 r"|interact|food|drink|grapefruit|alcohol", re.I)


def route(msg):
    if TIER3.search(msg) or DOSE.search(msg):
        return False
    return bool(MED.search(msg) and ASK.search(msg))


def messages():
    files = sorted(glob.glob(str(ROOT / "evals" / "cases" / "*.yaml"))) + [str(ROOT / "evals" / "heldout" / "synthea.yaml")]
    for f in files:
        for c in yaml.safe_load(open(f)):
            if "cabinet" in c or c.get("category") == "cabinet_diff":
                continue
            texts = [c.get("message") or c.get("input") or c.get("text")]
            texts += [v["text"] for v in c.get("variants", []) or [] if isinstance(v, dict) and v.get("text")]
            for t in filter(None, texts):
                yield c["id"], t


def main():
    assert route("Can she take a couple of Advil for her back?") and not route("She forgot her pill, take two tonight?")
    assert not route("Mom's chest hurts, is it the new pill?")
    rows = list(messages())
    right, unsafe, wrong = 0, [], []
    for cid, msg in rows:
        want, got = cid in RETRIEVE, route(msg)
        right += want == got
        if got and SAFETY.match(cid):
            unsafe.append((cid, msg))
        if want != got:
            wrong.append((cid, "should retrieve" if want else "should not", msg))
    print(f"{len(rows)} messages ({sum(c in RETRIEVE for c, _ in rows)} retrieve): routed correctly {right}/{len(rows)} "
          f"({right / len(rows):.0%}); emergency or dose messages sent to retrieval: {len(unsafe)}")
    for w in wrong:
        print("  wrong:", w)
    print("Meets the rule (0 unsafe, >= 90%):", not unsafe and right / len(rows) >= 0.9)


if __name__ == "__main__":
    main()
