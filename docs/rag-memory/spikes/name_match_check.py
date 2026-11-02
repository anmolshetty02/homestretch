"""Name matching experiment (Assignment 3, Task S-tech; Anmol's backup). Setup and decision rule: design.md, Section A
("Name matching experiment"). Run from the repo root:
    .venv/bin/python docs/rag-memory/spikes/name_match_check.py
A: RxNav exact lookup; B: RxNav approximate lookup with a score cutoff; C: local difflib against a known list.
RxNav answers are cached in .cache_rxnav_names.json (one request at a time, 0.2 s apart), so reruns send nothing.
"""
import csv
import re
import difflib
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / ".cache_rxnav_names.json"
API = "https://rxnav.nlm.nih.gov/REST/"
B_CUTOFFS = [0, 4, 6, 8]  # approximateTerm scores; fixed before running
C_CUTOFFS = [0.6, 0.7, 0.8]
BRANDS = {"lasix": "furosemide", "zestril": "lisinopril", "prinivil": "lisinopril", "aleve": "naproxen",
          "advil": "ibuprofen", "motrin": "ibuprofen", "lipitor": "atorvastatin", "norvasc": "amlodipine",
          "coreg": "carvedilol", "cozaar": "losartan", "plavix": "clopidogrel", "entresto": "sacubitril / valsartan",
          "toprol xl": "metoprolol", "glucophage xr": "metformin", "microzide": "hydrochlorothiazide",
          "zocor": "simvastatin", "tylenol": "acetaminophen", "vitamin d3": "cholecalciferol", "lanoxin": "digoxin",
          "coumadin": "warfarin"}


ALIASES = {"vitamin d3": "cholecalciferol"}  # same substance, two RxNorm names; key fix after the first run


def score(pred, true):
    """pred: an ingredient name or "no_match"; true: an ingredient name or NONE."""
    pred = ALIASES.get(pred, pred)
    if pred == "no_match":
        return "correct" if true == "NONE" else "no_match"
    return "correct" if pred == true else "wrong_drug"


def get(path, cache):
    if path not in cache:
        cache[path] = json.load(urllib.request.urlopen(API + path, timeout=30))
        CACHE.write_text(json.dumps(cache))
        time.sleep(0.2)
    return cache[path]


def ingredients(rxcui, cache):
    groups = get(f"rxcui/{rxcui}/related.json?tty=IN", cache)["relatedGroup"].get("conceptGroup", [])
    names = sorted({p["name"].lower() for g in groups for p in g.get("conceptProperties", [])})
    return " / ".join(names) or "no_match"


def exact(name, cache):
    ids = get(f"rxcui.json?name={urllib.parse.quote(name)}", cache)["idGroup"].get("rxnormId")
    return ingredients(ids[0], cache) if ids else "no_match"


def approximate(name, cache):
    """Top candidate's ingredient and score; (no_match, 0) when RxNav returns no candidate."""
    cands = get(f"approximateTerm.json?term={urllib.parse.quote(name)}&maxEntries=1", cache)[
        "approximateGroup"].get("candidate", [])
    return (ingredients(cands[0]["rxcui"], cache), float(cands[0]["score"])) if cands else ("no_match", 0.0)


def local(name, vocab, cutoff):
    hit = difflib.get_close_matches(name.lower(), list(vocab), n=1, cutoff=cutoff)
    return vocab[hit[0]] if hit else "no_match"


def self_check():
    assert score("furosemide", "lisinopril") == "wrong_drug"
    assert score("no_match", "NONE") == "correct"
    assert score("no_match", "lisinopril") == "no_match"
    assert score("furosemide", "NONE") == "wrong_drug"
    assert score("vitamin d3", "cholecalciferol") == "correct"
    assert variants("Motrin IB (ibuprofen)") == ["Motrin IB (ibuprofen)", "ibuprofen", "Motrin IB"]
    vocab = {"furosemide": "furosemide", "lasix": "furosemide"}
    assert local("FUROSEMLDE", vocab, 0.7) == "furosemide" and local("Zorvexa", vocab, 0.6) == "no_match"


def main():
    self_check()
    truth = list(csv.DictReader(open(HERE / "name_truth_anmol.csv")))
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    vocab = {g: g for g in {r["true_generic"] for r in truth} if g not in ("NONE", "UNREADABLE")} | BRANDS
    preds = {"A": {}, "B": {}}
    for r in truth:
        preds["A"][r["name"]] = exact(r["name"], cache)
        preds["B"][r["name"]] = approximate(r["name"], cache)

    rows = [r for r in truth if r["true_generic"] != "UNREADABLE"]
    setups = [("A. Exact RxNav", "n/a", lambda n: preds["A"][n])]
    setups += [("B. Approximate RxNav", f"score >= {c}", lambda n, c=c: preds["B"][n][0] if preds["B"][n][1] >= c
                else "no_match") for c in B_CUTOFFS]
    setups += [("C. Local fuzzy (difflib)", f"{c}", lambda n, c=c: local(n, vocab, c)) for c in C_CUTOFFS]
    # post-hoc (after the first run): the known list first, then exact RxNav for real drugs not on the list
    setups += [("C then A (post-hoc)", "0.7", lambda n: local(n, vocab, 0.7) if local(n, vocab, 0.7) != "no_match"
                else preds["A"][n])]

    print(f"{len(rows)} names scored ({sum(r['true_generic'] == 'UNREADABLE' for r in truth)} UNREADABLE reported apart)\n")
    print("| Approach | Cutoff | Correct | Wrong drug | No match (real drug) | Zorvexa = no match? |\n|---|---|---|---|---|---|")
    wrong = {}
    for label, cut, f in setups:
        res = {r["name"]: score(f(r["name"]), r["true_generic"]) for r in rows}
        c = Counter(res.values())
        zor = "yes" if f("Zorvexa") == "no_match" else f"no ({f('Zorvexa')})"
        print(f"| {label} | {cut} | {c['correct']} | {c['wrong_drug']} | {c['no_match']} | {zor} |")
        wrong[(label, cut)] = [(r["name"], f(r["name"]), r["true_generic"]) for r in rows if res[r["name"]] == "wrong_drug"]

    best = min(wrong, key=lambda s: (len(wrong[s]), -sum(
        score(dict(((l, c), f) for l, c, f in setups)[s](r["name"]), r["true_generic"]) == "correct" for r in rows)))
    print(f"\nChosen by the rule (fewest wrong_drug, then most correct): {best[0]}, cutoff {best[1]}")
    print("\nWrong-drug cases per setup:")
    for s, cases in wrong.items():
        if cases:
            print(f"  {s[0]} ({s[1]}): " + "; ".join(f"{n} -> {p} (true {t})" for n, p, t in cases))
    per_patient({r["name"]: r["true_generic"] for r in truth}, preds, cache)
    fresh_check(cache)
    print("\nB scores, for reference (name: top ingredient, score):")
    print("  " + "; ".join(f"{n}: {p} {s:.2f}" for n, (p, s) in sorted(preds["B"].items(), key=lambda x: x[1][1])))


def per_patient(truth_map, preds, cache):
    """Realistic C: each stress bottle is matched only against its own patient's plan (names + brands), then exact
    RxNav. Added after the first run, because C's list above was the answer key's own drugs (optimistic)."""
    import yaml
    root = HERE.parents[2]
    cases = yaml.safe_load(open(root / "evals" / "stress" / "stress.yaml"))
    pairs = set()
    for case in cases:
        if "cabinet" not in case:
            continue
        fx = json.loads((root / "fixtures" / f"{case['fixture']}.json").read_text())
        meds = fx["care_plan"]["medications"] + fx["care_plan"].get("stopped_medications", [])
        vocab = {}
        for m in meds:
            ing = exact(m["name"], cache)  # plan names are clean; RxNav gives the ingredient
            for n in [m["name"]] + m.get("brands", []):
                vocab[n.lower()] = ing
        for item in case["cabinet"]:
            pairs.add((case["fixture"], item["name"], json.dumps(vocab, sort_keys=True)))
    results = Counter()
    wrong, unmatched_real = [], Counter()
    for fixture, name, vocab_json in sorted(pairs):
        vocab = json.loads(vocab_json)
        pred = local(name, vocab, 0.7)
        if pred == "no_match":
            pred = preds["A"][name]
        res = score(pred, truth_map[name])
        results[res] += 1
        if res == "wrong_drug":
            wrong.append(f"{fixture}: {name} -> {pred} (true {truth_map[name]})")
        if res == "no_match":
            unmatched_real[truth_map[name]] += 1
    print(f"\nPer-patient (realistic) C 0.7 then A, on {len(pairs)} (patient, bottle name) pairs from the stress cabinets:")
    print(f"  correct {results['correct']}, wrong_drug {results['wrong_drug']}, no_match on a real drug {results['no_match']}")
    print(f"  wrong: {wrong or 'none'}")
    print(f"  no match (-> pharmacist_check), by true drug: {dict(unmatched_real.most_common())}")


# Fresh names for the bracket fix (written after the per-patient run showed "Tylenol (acetaminophen)" unmatched);
# truth confirmed with RxNav 2026-11-01. Matched against Rosa's plan (fixtures/p001.json).
FRESH = [("Tylenol Extra Strength (acetaminophen)", "acetaminophen"), ("Motrin IB (ibuprofen)", "ibuprofen"),
         ("Aleve (naproxen sodium) 220 mg", "naproxen"), ("Bayer Low Dose Aspirin", "aspirin"),
         ("Prilosec OTC (omeprazole)", "omeprazole"), ("Zyrtec (cetirizine)", "cetirizine"),
         ("Claritin (loratadine)", "loratadine"), ("Benadryl (diphenhydramine)", "diphenhydramine"),
         ("Pepcid AC (famotidine)", "famotidine"), ("Senna (sennosides)", "sennosides, usp"),
         ("Mucinex (guaifenesin)", "guaifenesin"), ("Imodium (loperamide)", "loperamide"),
         ("Lasix 40mg (furosemide)", "furosemide"), ("LISIN0PRIL 10 MG", "lisinopril"),
         ("Fluvexin", "NONE"), ("Dramorin (made-up)", "NONE")]


def variants(name):
    """The full name, the text inside brackets, and the text before them (labels often read "Brand (generic)")."""
    inner = re.findall(r"\(([^)]*)\)", name)
    outer = re.sub(r"\([^)]*\)", " ", name)
    return list(dict.fromkeys(v.strip() for v in [name, *inner, outer] if v.strip()))


def match(name, vocab, cache, brackets):
    names = variants(name) if brackets else [name]
    for n in names:  # the patient's own list first, then exact RxNav
        if (pred := local(n, vocab, 0.7)) != "no_match":
            return pred
    for n in names:
        if (pred := exact(n, cache)) != "no_match":
            return pred
    return "no_match"


def fresh_check(cache):
    root = HERE.parents[2]
    fx = json.loads((root / "fixtures" / "p001.json").read_text())["care_plan"]
    vocab = {}
    for m in fx["medications"] + fx["stopped_medications"]:
        for n in [m["name"]] + m.get("brands", []):
            vocab[n.lower()] = exact(m["name"], cache)
    print("\nFresh names (bracket fix), Rosa's list then exact RxNav:")
    for brackets in (False, True):
        res = Counter(score(match(n, vocab, cache, brackets), t) for n, t in FRESH)
        print(f"  {'with' if brackets else 'without'} bracket variants: correct {res['correct']}, "
              f"wrong_drug {res['wrong_drug']}, no_match {res['no_match']} (of {len(FRESH)})")
    print("  misses with brackets: " + "; ".join(f"{n} -> {match(n, vocab, cache, True)}" for n, t in FRESH
                                            if score(match(n, vocab, cache, True), t) != "correct"))


if __name__ == "__main__":
    main()
