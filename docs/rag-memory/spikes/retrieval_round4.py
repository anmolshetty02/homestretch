"""Retrieval round 4 (Assignment 3): query expansion with plain-word -> label-word mapping. Setup and rule: design.md,
Section A ("round 4"). Reuses rounds 2-3 (name check, filter, hybrid, reranker, chunk-level scoring). Run from the repo root:
    .venv/bin/python docs/rag-memory/spikes/retrieval_round4.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import retrieval_check as rc  # noqa: E402
from query_expansion import expand  # noqa: E402

SEEN = {"dev", "heldout", "heldout2", "heldout3"}


def main():
    from fastembed import TextEmbedding
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    cache_dir = str(Path.home() / ".cache" / "fastembed")
    embed = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=cache_dir)
    reranker = TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2", cache_dir=cache_dir)
    questions = [q for q in json.loads((HERE / "retrieval_questions.json").read_text())
                 if q["split"] in SEEN | {"heldout4"}]
    chunks = rc.chunk_by_section(rc.load_labels())
    vecs = np.array(list(embed.embed([c["text"] for c in chunks])))
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    bm25 = rc.BM25([c["text"] for c in chunks])

    def qvec(text):
        v = np.array(list(embed.query_embed([text])))[0]
        return v / np.linalg.norm(v)

    setups = {"R2 hybrid": (False, False), "R2 + expansion": (True, False),
              "R3c hybrid + reranker": (False, True), "R3c + expansion": (True, True)}
    results = {}
    for setup, (qe, rerank) in setups.items():
        per_q = {}
        for q in questions:
            text = expand(q["question"]) if qe else q["question"]
            ranked, _ = rc.run_setup(chunks, bm25, vecs, qvec(text), text, "Hybrid (RRF)", rnd=2)
            if rerank:
                pool = ranked[:20]
                scores = list(reranker.rerank(q["question"], [chunks[i]["text"] for i in pool]))
                ranked = [pool[j] for j in sorted(range(len(pool)), key=lambda j: -scores[j])]
            per_q[q["id"]] = [(chunks[i]["drug"], chunks[i]["section"], rc.has_evidence(q, chunks[i])) for i in ranked[:3]]
        results[setup] = per_q

    def hits(setup, splits):
        rows = [q for q in questions if q["split"] in splits and q["accept"]]
        acc = [{tuple(a) for a in q["accept"]} for q in rows]
        return (sum(rc.hit_at(1, results[setup][q["id"]], a) for q, a in zip(rows, acc)),
                sum(rc.hit_at(3, results[setup][q["id"]], a) for q, a in zip(rows, acc)), len(rows))

    print("| Setup | Selection hit@1 | Selection hit@3 | heldout4 hit@1 | heldout4 hit@3 |\n|---|---|---|---|---|")
    for s in setups:
        a1, a3, n = hits(s, SEEN)
        b1, b3, m = hits(s, {"heldout4"})
        print(f"| {s} | {a1}/{n} | {a3}/{n} | {b1}/{m} | {b3}/{m} |")
    best = max(setups, key=lambda s: (hits(s, SEEN)[1], hits(s, SEEN)[0]))
    print(f"\nChosen on the selection set: {best}")
    print("\nheldout4 per question (hit@3 for each setup, in table order):")
    for q in [q for q in questions if q["split"] == "heldout4" and q["accept"]]:
        marks = [rc.hit_at(3, results[s][q["id"]], {tuple(a) for a in q["accept"]}) for s in setups]
        print(f"  {q['id']} {marks} {q['question']}  | expanded: {expand(q['question'])[len(q['question']):].strip() or '-'}")


if __name__ == "__main__":
    main()
