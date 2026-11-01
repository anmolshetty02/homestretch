"""Assignment 3, Task D-tech: retrieval experiment on real FDA labels (no LLM calls).

Question: when the caregiver asks "can she take Advil with her water pill?", which way of chunking and searching
the drug labels brings back the right label section, and when should HomeStretch say "I don't have that"?

2 chunkings (by label section; fixed 800 chars / 100 overlap) x 3 searches (BM25; vector bge-small; hybrid RRF)
= 6 setups, all behind the same metadata filter (Rosa's plan + cabinet drugs, plus any drug the question names).
Scores hit@1 / hit@3 on the answerable questions in retrieval_questions.json, then prints the top vector cosine
score per question for the best setup and picks the "I don't know" threshold with the rule in compliance.md.

Run (offline after the labels are saved):  .venv/bin/python docs/rag-memory/spikes/retrieval_check.py
Re-fetch the labels from openFDA (network): .venv/bin/python docs/rag-memory/spikes/retrieval_check.py --fetch
Needs: fastembed (installed in .venv). The first run downloads BAAI/bge-small-en-v1.5.
"""
import json
import math
import re
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LABELS = HERE / "labels"
QUESTIONS = HERE / "retrieval_questions.json"
PATIENT = REPO / "fixtures" / "p001.json"

# Drug -> openFDA generic_name used for the search (salt names where openFDA lists the drug only that way).
CORPUS = {
    "furosemide": "furosemide",
    "metoprolol succinate": "metoprolol succinate",
    "metoprolol tartrate": "metoprolol tartrate",
    "lisinopril": "lisinopril",
    "ibuprofen": "ibuprofen",
    "naproxen": "naproxen",
    "amlodipine": "amlodipine besylate",
    "atorvastatin": "atorvastatin calcium",
}
# Common brand names not in Rosa's plan (the plan's own "brands" are read from p001.json).
EXTRA_BRANDS = {"advil": "ibuprofen", "motrin": "ibuprofen", "aleve": "naproxen", "naprosyn": "naproxen",
                "norvasc": "amlodipine", "lipitor": "atorvastatin"}

# Label fields that are not clinical text sections.
SKIP = {"openfda", "_fetch", "set_id", "id", "effective_time", "version", "spl_product_data_elements",
        "package_label_principal_display_panel", "spl_unclassified_section"}

SECTION_MAX = 1500          # by-section: split longer sections at paragraph (or sentence) breaks
FIXED_SIZE, FIXED_OVERLAP = 800, 100
K1, B = 1.5, 0.75           # BM25
RRF_K = 60                  # hybrid: score = sum 1 / (60 + rank)
MODEL = "BAAI/bge-small-en-v1.5"


# ---------------------------------------------------------------- scoring pieces (tested by self_check)

def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    def __init__(self, docs):
        self.docs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(c.values()) for c in self.docs]
        self.avg = sum(self.lens) / len(self.lens)
        df = Counter(t for c in self.docs for t in c)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query, i):
        c, s = self.docs[i], 0.0
        for t in tokenize(query):
            f = c.get(t, 0)
            if f:
                s += self.idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * self.lens[i] / self.avg))
        return s


def rrf(*rankings):
    """Reciprocal Rank Fusion of ranked id lists (rank starts at 1)."""
    score = Counter()
    for ranking in rankings:
        for r, doc in enumerate(ranking, start=1):
            score[doc] += 1 / (RRF_K + r)
    return [d for d, _ in sorted(score.items(), key=lambda x: (-x[1], x[0]))]


def hit_at(k, ranked_keys, answers):
    """1 if any acceptable (drug, section) is in the top k results, else 0."""
    return int(any(key in answers for key in ranked_keys[:k]))


def self_check():
    docs = ["the cat sat on the mat", "furosemide is a water pill", "dogs like to run in the park"]
    bm = BM25(docs)
    scores = [bm.score("furosemide", i) for i in range(3)]
    assert max(range(3), key=lambda i: scores[i]) == 1, "BM25 must rank the doc with the query word first"
    assert rrf(["a", "b", "c"], ["a", "b", "c"]) == ["a", "b", "c"], "RRF of identical rankings keeps order"
    ans = {("furosemide", "drug_interactions")}
    ranked = [("x", "a"), ("y", "b"), ("furosemide", "drug_interactions"), ("z", "c")]
    assert hit_at(3, ranked, ans) == 1, "hit@3 is 1 when the answer is at rank 3"
    assert hit_at(3, [("x", "a"), ("y", "b"), ("z", "c"), ("furosemide", "drug_interactions")], ans) == 0, \
        "hit@3 is 0 when the answer is at rank 4"
    print("self-check passed")


# ---------------------------------------------------------------- corpus

def fetch_labels():
    import requests
    LABELS.mkdir(exist_ok=True)
    for drug, generic in CORPUS.items():
        url = ("https://api.fda.gov/drug/label.json?search="
               + urllib.parse.quote(f'openfda.generic_name:"{generic}"') + "&limit=10")
        results = requests.get(url, timeout=30).json()["results"]
        # First result (openFDA order) whose generic_name is exactly this drug, single ingredient.
        pick = next(r for r in results
                    if [g.strip().lower() for g in r.get("openfda", {}).get("generic_name", [])] == [generic])
        pick["_fetch"] = {"request_url": url, "fetched": time.strftime("%Y-%m-%d"),
                          "source": "openFDA drug label API", "picked_rank": results.index(pick) + 1}
        (LABELS / f"{drug.replace(' ', '_')}.json").write_text(json.dumps(pick, indent=1))
        print("saved", drug, pick["set_id"], pick["effective_time"])
        time.sleep(0.5)


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def label_sections(label):
    """(section, text) in label order. A section whose text repeats inside a bigger section (e.g. furosemide's
    'information_for_patients' inside 'precautions') is kept as its own, more specific section, and its text is
    removed from the bigger one, so no text is indexed twice."""
    secs = [(k, norm(" ".join(v))) for k, v in label.items()
            if k not in SKIP and not k.endswith("_table") and isinstance(v, list) and v and isinstance(v[0], str)]
    out = []
    for name, text in secs:
        for other, otext in secs:
            if other != name and len(otext) < len(text) and otext in text:
                text = text.replace(otext, " ")
        text = norm(text)
        if len(text) >= 40:
            out.append((name, text))
    return out


def split_long(text, limit):
    """Split at paragraph breaks; openFDA text has none, so fall back to sentence breaks; hard-cut a too-long unit."""
    units = [u for u in re.split(r"\n\s*\n", text) if u.strip()]
    if len(units) == 1:
        units = re.split(r"(?<=[.;:])\s+(?=[A-Z0-9•])", text)
    chunks, cur = [], ""
    for u in units:
        while len(u) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(u[:limit])
            u = u[limit:]
        if cur and len(cur) + 1 + len(u) > limit:
            chunks.append(cur)
            cur = u
        else:
            cur = f"{cur} {u}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def load_corpus():
    labels = {}
    for drug in CORPUS:
        p = LABELS / f"{drug.replace(' ', '_')}.json"
        if not p.exists():
            sys.exit(f"missing {p}; run with --fetch first")
        labels[drug] = json.loads(p.read_text())
    return labels


def chunk(labels, how):
    chunks = []
    for drug, lab in labels.items():
        meta = {"drug": drug, "set_id": lab["set_id"], "effective_time": lab["effective_time"], "source": "openFDA"}
        secs = label_sections(lab)
        if how == "section":
            for name, text in secs:
                for piece in split_long(text, SECTION_MAX):
                    chunks.append({**meta, "section": name, "text": piece})
        else:  # fixed size over the whole label; section = the section the chunk starts in
            doc, starts = "", []
            for name, text in secs:
                starts.append((len(doc), name))
                doc += text + " "
            step = FIXED_SIZE - FIXED_OVERLAP
            for i in range(0, max(1, len(doc) - FIXED_OVERLAP), step):
                section = [n for s, n in starts if s <= i][-1]
                chunks.append({**meta, "section": section, "text": doc[i:i + FIXED_SIZE]})
    return chunks


# ---------------------------------------------------------------- metadata filter

def name_map(patient):
    names = {d: d for d in CORPUS}
    names.update(EXTRA_BRANDS)
    for m in patient["care_plan"]["medications"] + patient["care_plan"]["stopped_medications"]:
        for b in m.get("brands", []):
            names[b.lower()] = m["name"]
    return names


def find_drugs(text, names):
    t = text.lower()
    found = {drug for name, drug in names.items() if re.search(rf"\b{re.escape(name)}\b", t)}
    if re.search(r"\bmetoprolol\b", t):  # bare "metoprolol" could be either salt
        found |= {"metoprolol succinate", "metoprolol tartrate"}
    return {d for d in found if d in CORPUS}


def patient_drugs(patient, names):
    plan = patient["care_plan"]
    drugs = {m["name"] for m in plan["medications"] + plan["stopped_medications"]}
    for flag in patient.get("cabinet_diff", []):  # bottles found in the cabinet
        drugs |= find_drugs(flag.get("found", ""), names)
    return {d for d in drugs if d in CORPUS}


# ---------------------------------------------------------------- experiment

def main():
    self_check()
    if "--fetch" in sys.argv:
        fetch_labels()

    import numpy as np
    from fastembed import TextEmbedding

    labels = load_corpus()
    patient = json.loads(PATIENT.read_text())
    qs = json.loads(QUESTIONS.read_text())["questions"]
    names = name_map(patient)
    base = patient_drugs(patient, names)
    print(f"metadata filter base (Rosa's plan + cabinet): {sorted(base)}")
    print("labels:", ", ".join(f"{d} ({l['effective_time']})" for d, l in labels.items()))

    model = TextEmbedding(MODEL)
    q_vecs = np.array(list(model.query_embed([q["question"] for q in qs])))
    q_vecs /= np.linalg.norm(q_vecs, axis=1, keepdims=True)

    answerable = [q for q in qs if q["answers"]]
    setups, per_q, top_vec = {}, {}, {}
    for how in ("section", "fixed"):
        chunks = chunk(labels, how)
        sizes = [len(c["text"]) for c in chunks]
        print(f"\nchunking={how}: {len(chunks)} chunks, mean {sum(sizes) / len(sizes):.0f} chars, max {max(sizes)}")
        bm = BM25([c["text"] for c in chunks])
        c_vecs = np.array(list(model.passage_embed([c["text"] for c in chunks])))
        c_vecs /= np.linalg.norm(c_vecs, axis=1, keepdims=True)
        for qi, q in enumerate(qs):
            allowed = base | find_drugs(q["question"], names)
            idx = [i for i, c in enumerate(chunks) if c["drug"] in allowed]
            cos = c_vecs[idx] @ q_vecs[qi]
            rank_vec = [idx[j] for j in np.argsort(-cos, kind="stable")]
            bms = {i: bm.score(q["question"], i) for i in idx}
            rank_bm = sorted(idx, key=lambda i: (-bms[i], i))
            rank_hyb = rrf(rank_bm, rank_vec)
            top_vec[(how, q["id"])] = (float(cos.max()), chunks[rank_vec[0]]["drug"], chunks[rank_vec[0]]["section"])
            answers = {tuple(a) for a in q["answers"]}
            for search, ranking in (("bm25", rank_bm), ("vector", rank_vec), ("hybrid", rank_hyb)):
                keys = [(chunks[i]["drug"], chunks[i]["section"]) for i in ranking]
                per_q[(how, search, q["id"])] = keys[:3]
                if answers:
                    s = setups.setdefault((how, search), [0, 0])
                    s[0] += hit_at(1, keys, answers)
                    s[1] += hit_at(3, keys, answers)

    n = len(answerable)
    label = {"section": "By section", "fixed": f"Fixed {FIXED_SIZE}/{FIXED_OVERLAP}",
             "bm25": "Keyword (BM25)", "vector": "Vector (bge-small)", "hybrid": "Hybrid (RRF)"}
    print(f"\n## Six setups (answerable questions: {n})\n")
    print("| Chunking | Search | hit@1 | hit@3 |\n|---|---|---|---|")
    for (how, search), (h1, h3) in setups.items():
        print(f"| {label[how]} | {label[search]} | {h1}/{n} | {h3}/{n} |")

    # Decision rule: best hit@3, then hit@1; ties -> simpler (section before fixed; bm25, vector, hybrid).
    order = [(h, s) for h in ("section", "fixed") for s in ("bm25", "vector", "hybrid")]
    best = max(order, key=lambda k: (setups[k][1], setups[k][0], -order.index(k)))
    print(f"\nbest setup by the rule: {label[best[0]]} + {label[best[1]]}")

    print("\n## Per-question results (rank of first acceptable answer in top 3; '-' = miss)\n")
    print("| q | " + " | ".join(f"{label[h][:10]} {s}" for h, s in order) + " |")
    print("|---|" + "---|" * len(order))
    for q in answerable:
        answers = {tuple(a) for a in q["answers"]}
        cells = []
        for h, s in order:
            keys = per_q[(h, s, q["id"])]
            r = next((i + 1 for i, k in enumerate(keys) if k in answers), None)
            cells.append(str(r) if r else "-")
        print(f"| {q['id']} | " + " | ".join(cells) + " |")

    print(f"\n## Top-3 results of the best setup\n")
    for q in qs:
        keys = per_q[(best[0], best[1], q["id"])]
        print(f"{q['id']}: " + "; ".join(f"{d}/{s}" for d, s in keys))

    print(f"\n## Top vector cosine score per question (chunking: {label[best[0]]})\n")
    print("| q | answerable | top cosine | top chunk |\n|---|---|---|---|")
    for q in qs:
        sc, d, s = top_vec[(best[0], q["id"])]
        print(f"| {q['id']} | {'yes' if q['answers'] else 'NO'} | {sc:.4f} | {d}/{s} |")

    no_ans = [top_vec[(best[0], q["id"])][0] for q in qs if not q["answers"]]
    ans = [top_vec[(best[0], q["id"])][0] for q in answerable]
    cutoff = math.floor(max(no_ans) * 1000 + 1) / 1000  # lowest 3-decimal cutoff that rejects every no-answer
    rejected = [q["id"] for q in answerable if top_vec[(best[0], q["id"])][0] < cutoff]
    ok = len(rejected) <= 1
    print(f"\nhighest no-answer score {max(no_ans):.4f}; lowest answerable score {min(ans):.4f}")
    print(f"threshold: answer only if top cosine >= {cutoff:.3f}; rejects both no-answer questions and "
          f"{len(rejected)} answerable {rejected} -> rule {'PASSES' if ok else 'FAILS (more than one answerable rejected)'}")


if __name__ == "__main__":
    main()
