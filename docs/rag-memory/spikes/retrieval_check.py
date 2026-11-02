"""Retrieval experiment (Assignment 3, Task D-tech). Setup and decision rule: docs/rag-memory/design.md, section A.

2 chunkings x 3 searches on 8 openFDA labels, with a metadata filter; hit@1 and hit@3 on dev, then the chosen setup and
threshold on held-out. Round 1 = the pre-registered pipeline; round 2 adds an RxNav name check before retrieval and
searches stopped drugs only when named, judged on the fresh heldout2 set. No LLM calls. Run from the repo root:
    .venv/bin/python docs/rag-memory/spikes/retrieval_check.py
The first run downloads BAAI/bge-small-en-v1.5 into ~/.cache/fastembed and asks RxNav about a few names (cached in
.cache_rxnav_retrieval.json); later runs are offline.
"""
import json
import time
import urllib.parse
import urllib.request
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
SKIP = {"spl_product_data_elements", "package_label_principal_display_panel", "description", "clinical_studies",
        "how_supplied", "inactive_ingredient", "active_ingredient", "storage_and_handling",
        "keep_out_of_reach_of_children", "purpose", "questions", "spl_unclassified_section"}
PLAN_ACTIVE = ["furosemide", "metoprolol_succinate", "lisinopril"]  # fixtures/p001.json
PLAN_AND_CABINET = PLAN_ACTIVE + ["metoprolol_tartrate"]  # stopped-1, bottle still in the cabinet
NAMES = {"advil": "ibuprofen", "motrin": "ibuprofen", "ibuprofen": "ibuprofen", "aleve": "naproxen",
         "naproxen": "naproxen", "lipitor": "atorvastatin", "atorvastatin": "atorvastatin", "norvasc": "amlodipine",
         "amlodipine": "amlodipine", "lopressor": "metoprolol_tartrate", "tartrate": "metoprolol_tartrate"}
NOT_DRUGS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January", "February",
             "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}
RXNAV_CACHE = HERE / ".cache_rxnav_retrieval.json"
RRF_K = 60


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [Counter(tokens(d)) for d in docs]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / len(self.lens)
        df = Counter(w for d in self.docs for w in d)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query):
        q = tokens(query)
        return [sum(self.idf.get(w, 0) * d[w] * (self.k1 + 1) / (d[w] + self.k1 * (1 - self.b + self.b * n / self.avg))
                    for w in q if w in d) for d, n in zip(self.docs, self.lens)]


def rrf(*rankings):
    """Reciprocal Rank Fusion: each ranking is a list of doc indices, best first."""
    score = Counter()
    for ranking in rankings:
        for rank, i in enumerate(ranking, 1):
            score[i] += 1 / (RRF_K + rank)
    return sorted(score, key=lambda i: -score[i])


def hit_at(k, ranked_keys, accept):
    """A key is (drug, section) or (drug, section, chunk_has_evidence); a split section only counts if the chunk
    returned actually contains the evidence, not just some other part of the same section."""
    return int(any(key[:2] in accept and (len(key) < 3 or key[2]) for key in ranked_keys[:k]))


def has_evidence(q, chunk):
    rx = q["evidence"].get(chunk["drug"])
    return rx == "(hand-set)" or bool(rx and re.search(rx, chunk["text"], re.I))


def load_labels():
    labels = {}
    for f in sorted((HERE / "labels").glob("*.json")):
        if f.name == "manifest.json":
            continue
        x = json.loads(f.read_text())
        sections = [(k, " ".join(map(str, v))) for k, v in x.items()
                    if isinstance(v, list) and k != "openfda" and k not in SKIP and not k.endswith("_table")]
        labels[f.stem] = {"set_id": x["set_id"], "effective_time": x["effective_time"],
                          "sections": [(k, t) for k, t in sections if t.strip()]}
    return labels


def pack_sentences(text, limit):
    """Split text over `limit` characters at sentence ends (openFDA text has no paragraph breaks)."""
    out, cur = [], ""
    for s in re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + len(s) + 1 > limit:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    return out + ([cur] if cur else [])


def chunk_by_section(labels):
    return [{"drug": d, "section": sec, "text": part, "set_id": L["set_id"], "effective_time": L["effective_time"]}
            for d, L in labels.items() for sec, text in L["sections"] for part in pack_sentences(text, 1500)]


def chunk_fixed(labels, size=800, overlap=100):
    chunks = []
    for d, L in labels.items():
        full, starts = "", []
        for sec, text in L["sections"]:
            starts.append((len(full), sec))
            full += text + "\n"
        for pos in range(0, len(full), size - overlap):
            sec = [s for p, s in starts if p <= pos][-1]  # the section the chunk starts in
            chunks.append({"drug": d, "section": sec, "text": full[pos:pos + size], "set_id": L["set_id"],
                           "effective_time": L["effective_time"]})
    return chunks


def drugs_for(question, rnd=1):
    """Round 1: plan and cabinet drugs plus named ones. Round 2: stopped drugs only when the question names them."""
    q = question.lower()
    return set(PLAN_AND_CABINET if rnd == 1 else PLAN_ACTIVE) | {drug for name, drug in NAMES.items() if name in q}


def drug_like(question):
    """Capitalized words that don't start a sentence, minus days and months. ponytail: crude; in the app the model
    extracts drug mentions, and Sriya's RxNorm step handles misspellings."""
    return [w for sentence in re.split(r"(?<=[.!?])\s+", question)
            for w in re.findall(r"[A-Za-z]+", sentence)[1:] if w[0].isupper() and len(w) > 1 and w not in NOT_DRUGS]


def unknown_names(question, cache):
    """Drug-like words with no RxNorm match (exact or normalized name), looked up one at a time and cached."""
    out = []
    for w in drug_like(question):
        if w not in cache:
            url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={urllib.parse.quote(w)}&search=2"
            cache[w] = json.load(urllib.request.urlopen(url, timeout=20))["idGroup"].get("rxnormId")
            RXNAV_CACHE.write_text(json.dumps(cache, indent=1))
            time.sleep(0.2)
        if not cache[w]:
            out.append(w)
    return out


def run_setup(chunks, bm25, vecs, qvec, question, search, rnd=1):
    """Ranked chunk indices (after the metadata filter) and the top vector cosine score."""
    allowed = [i for i, c in enumerate(chunks) if c["drug"] in drugs_for(question, rnd)]
    cos = {i: float(vecs[i] @ qvec) for i in allowed}
    bm = bm25.scores(question)
    by_bm25 = sorted(allowed, key=lambda i: -bm[i])
    by_vec = sorted(allowed, key=lambda i: -cos[i])
    ranked = {"BM25": by_bm25, "Vector": by_vec, "Hybrid (RRF)": rrf(by_bm25, by_vec)}[search]
    return ranked, max(cos.values())


def self_check():
    toy = ["the cat sat", "dogs bark loudly", "furosemide removes fluid"]
    s = BM25(toy).scores("furosemide")
    assert max(range(3), key=lambda i: s[i]) == 2
    assert rrf([2, 0, 1], [2, 0, 1]) == [2, 0, 1]
    accept = {("a", "x")}
    assert hit_at(3, [("b", "y"), ("c", "z"), ("a", "x")], accept) == 1
    assert hit_at(3, [("b", "y"), ("c", "z"), ("d", "w"), ("a", "x")], accept) == 0
    assert hit_at(1, [("a", "x", False)], accept) == 0  # right section, but this chunk lacks the evidence
    assert drugs_for("Can she take Advil?") == set(PLAN_AND_CABINET) | {"ibuprofen"}
    assert drugs_for("Zorvexa side effects") == set(PLAN_AND_CABINET)
    assert "metoprolol_tartrate" not in drugs_for("Is the heart rate pill making her tired?", rnd=2)
    assert "metoprolol_tartrate" in drugs_for("She still has some Lopressor left.", rnd=2)
    assert drug_like("Can she go to church on Sunday?") == []
    assert drug_like("What should I cook for her?") == []  # the pronoun "I" is not a drug name
    assert drug_like("Is Bravacil safe with Advil?") == ["Bravacil", "Advil"]
    assert drug_like("Her ears are ringing. Could that be one of her pills?") == []  # sentence starts are not drugs
    assert drug_like("She still has some Lopressor left. What is that one for?") == ["Lopressor"]
    assert all(len(p) <= 1500 for p in pack_sentences("Short sentence. " * 300, 1500))


def main():
    self_check()
    from fastembed import TextEmbedding
    model = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=str(Path.home() / ".cache" / "fastembed"))
    labels = load_labels()
    questions = json.loads((HERE / "retrieval_questions.json").read_text())
    qvecs = np.array(list(model.query_embed([q["question"] for q in questions])))
    qvecs /= np.linalg.norm(qvecs, axis=1, keepdims=True)
    rx_cache = json.loads(RXNAV_CACHE.read_text()) if RXNAV_CACHE.exists() else {}
    unknown = {q["id"]: unknown_names(q["question"], rx_cache) for q in questions}

    index = {}
    for cname, chunks in {"By section": chunk_by_section(labels), "Fixed 800/100": chunk_fixed(labels)}.items():
        vecs = np.array(list(model.embed([c["text"] for c in chunks])))
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        index[cname] = (chunks, BM25([c["text"] for c in chunks]), vecs)
        print(f"{cname}: {len(chunks)} chunks")

    for rnd, dev, held in [(1, "dev", "heldout"), (2, "dev", "heldout2")]:
        print(f"\n\n======== Round {rnd} ({'pre-registered' if rnd == 1 else 'name check + stopped drugs only when named'}) ========")
        qs = [q for q in questions if q["split"] in (dev, held) or (rnd == 2 and q["split"] == "heldout")]
        results = {}  # (chunking, search) -> {qid: (top-3 (drug, section), top cosine)}
        for cname, (chunks, bm25, vecs) in index.items():
            for search in ["BM25", "Vector", "Hybrid (RRF)"]:
                per_q = {}
                for q in qs:
                    qv = qvecs[questions.index(q)]
                    ranked, top_cos = run_setup(chunks, bm25, vecs, qv, q["question"], search, rnd)
                    per_q[q["id"]] = ([(chunks[i]["drug"], chunks[i]["section"], has_evidence(q, chunks[i]))
                                       for i in ranked[:3]], top_cos)
                results[(cname, search)] = per_q
        name_rejected = (lambda q: bool(unknown[q["id"]])) if rnd == 2 else (lambda q: False)
        report(results, qs, dev, held, name_rejected, unknown, rnd)


def report(results, qs, dev, held, name_rejected, unknown, rnd):
    def scores(setup, split):
        rows = [q for q in qs if q["split"] == split and q["accept"]]
        return (sum(hit_at(1, results[setup][q["id"]][0], {tuple(a) for a in q["accept"]}) for q in rows),
                sum(hit_at(3, results[setup][q["id"]][0], {tuple(a) for a in q["accept"]}) for q in rows), len(rows))

    print(f"\n| Chunking | Search | Dev hit@1 | Dev hit@3 |\n|---|---|---|---|")
    for s in results:
        h1, h3, n = scores(s, dev)
        print(f"| {s[0]} | {s[1]} | {h1}/{n} | {h3}/{n} |")
    best = max(results, key=lambda s: (scores(s, dev)[1], scores(s, dev)[0]))
    ties = [s for s in results if scores(s, dev)[:2] == scores(best, dev)[:2]]
    print(f"\nChosen on dev (hit@3, then hit@1): {best[0]} + {best[1]}" + (f"  (tied: {ties})" if len(ties) > 1 else ""))

    print("\n| id | split | answerable | unknown name (RxNav) | top cosine | hit@3 | question |\n|---|---|---|---|---|---|---|")
    for q in qs:
        keys, cos = results[best][q["id"]]
        hit = hit_at(3, keys, {tuple(a) for a in q["accept"]}) if q["accept"] else "-"
        print(f"| {q['id']} | {q['split']} | {'yes' if q['accept'] else 'no'} | {', '.join(unknown[q['id']]) or '-'} "
              f"| {cos:.3f} | {hit} | {q['question']} |")

    def passes(split):
        return [q for q in qs if q["split"] == split and not name_rejected(q)]
    dev_noans = [results[best][q["id"]][1] for q in passes(dev) if not q["accept"]]
    cutoff = max(dev_noans) + 0.001  # just above the highest dev no-answer score that reaches retrieval
    rej = [q["id"] for q in qs if q["split"] == dev and q["accept"]
           and (name_rejected(q) or results[best][q["id"]][1] < cutoff)]  # either check wrongly rejecting counts
    print(f"\nThreshold (dev): {cutoff:.3f}; name check rejects {[q['id'] for q in qs if q['split'] == dev and name_rejected(q)]}; "
          f"the threshold rejects all other dev no-answer; answerable rejected by either: {len(rej)} {rej}: "
          f"{'meets' if len(rej) <= 1 else 'FAILS'} the rule (at most 1)")

    for split in [held] + (["heldout"] if rnd == 2 else []):
        rows = [q for q in qs if q["split"] == split]
        h1, h3, n = scores(best, split)
        caught = [q["id"] for q in rows if not q["accept"] and (name_rejected(q) or results[best][q["id"]][1] < cutoff)]
        wrong = [q["id"] for q in rows if q["accept"] and (name_rejected(q) or results[best][q["id"]][1] < cutoff)]
        tart = [q["id"] for q in rows if any(key[0] == "metoprolol_tartrate" for key in results[best][q["id"]][0])
                and not drug_like(q["question"]) and "tartrate" not in q["question"].lower()]
        tag = " (seen in round 1; reference only)" if rnd == 2 and split == "heldout" else ""
        print(f"\n{split}{tag}, chosen setup and threshold unchanged: hit@1 {h1}/{n}, hit@3 {h3}/{n}")
        print(f"  no-answer rejected: {caught} of {[q['id'] for q in rows if not q['accept']]}")
        print(f"  answerable wrongly rejected: {wrong}")
        print(f"  tartrate (stopped drug) in top 3 without being named: {tart}")
        print("  all six setups:", "; ".join(f"{s[0]} + {s[1]} {scores(s, split)[1]}/{n}" for s in results))

    print("\nMisses at 3 (chosen setup):")
    for q in qs:
        keys = results[best][q["id"]][0]
        if q["accept"] and not hit_at(3, keys, {tuple(a) for a in q["accept"]}):
            print(f"  {q['id']} ({q['split']}) {q['question']}\n     got {keys}")


if __name__ == "__main__":
    main()
