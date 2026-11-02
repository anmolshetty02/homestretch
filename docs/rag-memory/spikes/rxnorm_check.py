"""Task S-tech: drug-name matching experiment (Assignment 3, Sriya).

Question: how should HomeStretch turn a messy bottle name (OCR misread, brand name, or a made-up drug) into a real
active ingredient, and say "no match" when there isn't one?

Approaches, all on the same 151 names in name_truth.csv (answer key, hand-checked):
  A. Exact RxNav lookup        rxcui.json?name=<name>
  B. Approximate RxNav lookup  approximateTerm.json?term=<name>&maxEntries=1, swept over score cutoffs
  C. Local fuzzy match         difflib.get_close_matches against a small list of ingredients + brand names (no API)
For A and B the RxCUI is turned into its ingredient(s) with RxNav: properties.json (if it is already an ingredient,
TTY=IN) or related.json?tty=IN (brand, salt form, multi-ingredient, etc.).

Decision rule and cutoffs are written in docs/rag-memory/sources.md ("Name matching experiment") before running.

Be polite to the free API: one request at a time, >= 0.2 s apart, every answer cached in .cache_rxnav.json, so a
second run sends no requests. Drug names only are sent; no patient data.

Run from the repo root:  .venv/bin/python docs/rag-memory/spikes/rxnorm_check.py
Uses requests and the standard library only.
"""

import csv
import difflib
import json
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

HERE = Path(__file__).resolve().parent
TRUTH_CSV = HERE / "name_truth.csv"
CACHE_PATH = HERE / ".cache_rxnav.json"
BASE = "https://rxnav.nlm.nih.gov/REST/"
PAUSE_S = 0.2

NO_MATCH = "no_match"
CORRECT, WRONG, MISS = "correct", "wrong_drug", "no_match"

# C: brand names we expect on bottles in this test set, mapped to their ingredient (lowercase).
BRANDS = {
    "lasix": "furosemide",
    "toprol xl": "metoprolol",
    "zestril": "lisinopril",
    "coreg": "carvedilol",
    "plavix": "clopidogrel",
    "lipitor": "atorvastatin",
    "zocor": "simvastatin",
    "norvasc": "amlodipine",
    "cozaar": "losartan",
    "microzide": "hydrochlorothiazide",
    "glucophage xr": "metformin",
    "entresto": "sacubitril / valsartan",
    "advil": "ibuprofen",
    "aleve": "naproxen",
    "tylenol": "acetaminophen",
}
C_CUTOFFS = [0.6, 0.7, 0.8, 0.9]


# ----------------------------------------------------------------------------------------------- scoring

def norm(ingredients):
    """Lowercase; several ingredients sorted and joined with ' / '. Accepts a string or a list."""
    if ingredients == NO_MATCH or ingredients is None:
        return NO_MATCH
    if isinstance(ingredients, str):
        ingredients = ingredients.split("/")
    parts = sorted({p.strip().lower() for p in ingredients if p.strip()})
    return " / ".join(parts) if parts else NO_MATCH


def score(predicted, true_generic):
    """One name -> correct / wrong_drug / no_match (UNREADABLE rows are reported separately by the caller)."""
    p = norm(predicted)
    if true_generic == "NONE":
        return CORRECT if p == NO_MATCH else WRONG
    if p == NO_MATCH:
        return MISS
    return CORRECT if p == norm(true_generic) else WRONG


def fuzzy_match(name, vocab, cutoff):
    """C: best vocabulary key at or above cutoff -> its ingredient, else no_match."""
    hit = difflib.get_close_matches(name.lower(), list(vocab), n=1, cutoff=cutoff)
    return vocab[hit[0]] if hit else NO_MATCH


def self_check():
    # Required by the README.
    assert score("furosemide", "lisinopril") == WRONG
    assert score(NO_MATCH, "NONE") == CORRECT
    assert score(NO_MATCH, "lisinopril") == MISS
    # Extra: a made-up drug matched to anything is dangerous; combos compare order-free; case is ignored.
    assert score("lisinopril", "NONE") == WRONG
    assert score(["valsartan", "sacubitril"], "sacubitril / valsartan") == CORRECT
    assert score("Furosemide", "furosemide") == CORRECT
    # Extra: fuzzy matcher finds a misread, rejects junk.
    toy = {"lisinopril": "lisinopril", "lasix": "furosemide"}
    assert fuzzy_match("LISIN0PRIL", toy, 0.8) == "lisinopril"
    assert fuzzy_match("Zorvexa", toy, 0.6) == NO_MATCH
    # Extra: history parser reads ingredients of a retired RxCUI, and finds a remapped RxCUI.
    toy_hist = {"rxcuiStatusHistory": {"derivedConcepts": {
        "ingredientConcept": [{"ingredientRxcui": "6809", "ingredientName": "metformin"}],
        "remappedConcept": [{"remappedRxCui": "861004"}]}}}
    assert parse_history(toy_hist) == ["metformin"]
    assert remapped_rxcuis(toy_hist) == ["861004"]
    assert parse_history({}) == []
    print("self-check: OK")


# ----------------------------------------------------------------------------------------------- RxNav

def _find(obj, key):
    """All values stored under `key` anywhere in a nested JSON object."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            out.extend(_find(v, key))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_find(v, key))
    return out


def parse_history(hist):
    """Ingredient names from a historystatus.json reply: derivedConcepts.ingredientConcept[].ingredientName,
    else definitionalFeatures.ingredientAndStrength[].baseName."""
    names = [n for n in _find(hist, "ingredientName") if n]
    if not names:
        names = [n for n in _find(hist, "baseName") if n]
    return sorted(set(names))


def remapped_rxcuis(hist):
    return [r for r in _find(hist, "remappedRxCui") if r]


class NetworkDown(Exception):
    pass


class RxNav:
    def __init__(self, cache_path):
        self.cache_path = cache_path
        self.cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        self.sent = 0
        self._last = 0.0

    def get(self, path):
        url = BASE + path
        if url in self.cache:
            return self.cache[url]
        wait = PAUSE_S - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        try:
            r = requests.get(url, timeout=30)
        except requests.exceptions.RequestException as e:
            raise NetworkDown(f"{url}: {e}") from e
        self._last = time.monotonic()
        self.sent += 1
        if r.status_code == 404:
            data = None
        elif r.ok:
            data = r.json()
        else:
            raise NetworkDown(f"{url}: HTTP {r.status_code}")
        self.cache[url] = data
        self.cache_path.write_text(json.dumps(self.cache, indent=1, sort_keys=True))
        return data

    def ingredients(self, rxcui, depth=0):
        """RxCUI -> list of ingredient names (TTY=IN), or [] if none found."""
        props = (self.get(f"rxcui/{rxcui}/properties.json") or {}).get("properties") or {}
        if not props:
            # Not an active concept: approximateTerm can return retired RxCUIs (seen in run 1 for Toprol XL,
            # Glucophage XR, Microzide, ...). Ask RxNav's history service what it became.
            return self.history_ingredients(rxcui, depth)
        if props.get("tty") == "IN":
            return [props["name"]]
        rel = self.get(f"rxcui/{rxcui}/related.json?tty=IN") or {}
        names = []
        for group in (rel.get("relatedGroup") or {}).get("conceptGroup") or []:
            for c in group.get("conceptProperties") or []:
                names.append(c["name"])
        return names

    def history_ingredients(self, rxcui, depth):
        """Retired RxCUI -> ingredient names via rxcui/{rxcui}/historystatus.json [VERIFY field names]."""
        hist = self.get(f"rxcui/{rxcui}/historystatus.json") or {}
        names = parse_history(hist)
        if names or depth >= 1:
            return names
        for new_rxcui in remapped_rxcuis(hist):  # remapped to a current concept: resolve that one instead
            names = self.ingredients(new_rxcui, depth + 1)
            if names:
                return names
        return []

    def exact(self, name):
        """A: exact name -> ingredient(s) or no_match."""
        data = self.get(f"rxcui.json?name={quote(name)}") or {}
        ids = (data.get("idGroup") or {}).get("rxnormId") or []
        if not ids:
            return NO_MATCH
        return self.ingredients(ids[0]) or NO_MATCH

    def approximate(self, name):
        """B: (ingredient(s) or no_match, score or None) for the top candidate, before any cutoff."""
        data = self.get(f"approximateTerm.json?term={quote(name)}&maxEntries=1") or {}
        cands = (data.get("approximateGroup") or {}).get("candidate") or []
        cands = [c for c in cands if c.get("rxcui")]
        if not cands:
            return NO_MATCH, None
        top = cands[0]
        return (self.ingredients(top["rxcui"]) or NO_MATCH), float(top["score"])


# ----------------------------------------------------------------------------------------------- run

def tally(rows, predictions):
    """rows: [(name, truth)], predictions: {name: pred} -> counts + wrong_drug list."""
    counts = {CORRECT: 0, WRONG: 0, MISS: 0, "unreadable_ok": 0, "unreadable_matched": 0}
    wrong = []
    for name, truth in rows:
        pred = predictions[name]
        if truth == "UNREADABLE":
            counts["unreadable_ok" if norm(pred) == NO_MATCH else "unreadable_matched"] += 1
            continue
        s = score(pred, truth)
        counts[s] += 1
        if s == WRONG:
            wrong.append((name, truth, norm(pred)))
    zorvexa = "yes" if all(norm(predictions[n]) == NO_MATCH for n, t in rows if n == "Zorvexa") else "NO"
    return counts, wrong, zorvexa


def main():
    self_check()

    with TRUTH_CSV.open(newline="") as f:
        rows = [(r["name"], r["true_generic"].strip()) for r in csv.DictReader(f)]
    n_unreadable = sum(t == "UNREADABLE" for _, t in rows)
    print(f"test set: {len(rows)} names ({sum(t == 'NONE' for _, t in rows)} NONE, {n_unreadable} UNREADABLE)")

    setups = []  # (approach, cutoff label, predictions)

    # C first: needs no network.
    vocab = {g.lower(): g.lower() for _, g in rows if g not in ("NONE", "UNREADABLE")}
    vocab.update(BRANDS)
    for c in C_CUTOFFS:
        setups.append(("C. Local fuzzy (difflib)", f"{c}", {n: fuzzy_match(n, vocab, c) for n, _ in rows}))

    api = RxNav(CACHE_PATH)
    network_ok = True
    try:
        a_pred, b_raw = {}, {}
        for i, (name, _) in enumerate(rows, 1):
            a_pred[name] = api.exact(name)
            b_raw[name] = api.approximate(name)
            if api.sent and i % 25 == 0:
                print(f"  ...{i}/{len(rows)} names looked up ({api.sent} requests so far)")
    except NetworkDown as e:
        network_ok = False
        print(f"\nRxNav not reachable, so A and B are skipped this run ({e}).")
        print("Answers fetched so far are cached; run again where rxnav.nlm.nih.gov is reachable.\n")

    if network_ok:
        setups.insert(0, ("A. Exact RxNav", "n/a", a_pred))
        scores = [s for _, s in b_raw.values() if s is not None]
        q1, q2, q3 = statistics.quantiles(scores, n=4)
        print(f"B top-candidate scores: min {min(scores):g}, 25th pct {q1:g}, median {q2:g}, "
              f"75th pct {q3:g}, max {max(scores):g} ({len(scores)} of {len(rows)} names had a candidate)")
        b_cuts = [("none", None), (f"{q1:g} (p25)", q1), (f"{q2:g} (p50)", q2), (f"{q3:g} (p75)", q3)]
        for k, (label, cut) in enumerate(b_cuts):
            preds = {n: (p if (cut is None or (s is not None and s >= cut)) else NO_MATCH)
                     for n, (p, s) in b_raw.items()}
            setups.insert(1 + k, ("B. Approximate RxNav", label, preds))

    print(f"\nHTTP requests sent this run: {api.sent} (cache: {len(api.cache)} answers in {CACHE_PATH.name})\n")

    print("| Approach | Cutoff | Correct | Wrong drug | No match (real drug) | Zorvexa = no match? |")
    print("|---|---|---|---|---|---|")
    results = []
    for approach, cut, preds in setups:
        counts, wrong, zorvexa = tally(rows, preds)
        results.append((approach, cut, counts, wrong, zorvexa))
        print(f"| {approach} | {cut} | {counts[CORRECT]} | {counts[WRONG]} | {counts[MISS]} | {zorvexa} |")
    if n_unreadable:
        print("\nUNREADABLE rows (should be no_match):")
        for approach, cut, counts, _, _ in results:
            print(f"  {approach} {cut}: {counts['unreadable_ok']} no_match, {counts['unreadable_matched']} matched")

    print("\nWrong-drug cases (name -> predicted, true):")
    for approach, cut, _, wrong, _ in results:
        print(f"  {approach}, cutoff {cut}: {len(wrong)}")
        for name, truth, pred in wrong:
            print(f"    {name!r} -> {pred} (true: {truth})")

    if network_ok:
        print("\nB top candidate per name (for checking the answer key; score before any cutoff):")
        for name, truth in rows:
            pred, s = b_raw[name]
            mark = "" if score(pred, truth) == CORRECT else "   <-- differs from answer key"
            print(f"  {name!r}: {norm(pred)} (score {s}){mark}")

    if not network_ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
