"""Retrieval round 3 (Assignment 3): smaller chunks and a cross-encoder reranker. Setup and rule: design.md, Section A
("round 3"). Reuses round 2's name check, filter, BM25, RRF, and chunk-level scoring from retrieval_check.py.
Run from the repo root:
    .venv/bin/python docs/rag-memory/spikes/retrieval_round3.py
First run downloads Xenova/ms-marco-MiniLM-L-6-v2 (about 80 MB) into ~/.cache/fastembed. No LLM calls.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import retrieval_check as rc  # noqa: E402

SEEN = {"dev", "heldout", "heldout2"}
MAX_SEEN_REJECTED = 2


def chunk_small(labels, limit=500):
    return [{"drug": d, "section": sec, "text": part, "set_id": L["set_id"], "effective_time": L["effective_time"]}
            for d, L in labels.items() for sec, text in L["sections"] for part in rc.pack_sentences(text, limit)]


def main():
    from fastembed import TextEmbedding
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    cache_dir = str(Path.home() / ".cache" / "fastembed")
    embed = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=cache_dir)
    reranker = TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2", cache_dir=cache_dir)
    labels = rc.load_labels()
    questions = json.loads((HERE / "retrieval_questions.json").read_text())
    qvecs = np.array(list(embed.query_embed([q["question"] for q in questions])))
    qvecs /= np.linalg.norm(qvecs, axis=1, keepdims=True)
    rx = json.loads(rc.RXNAV_CACHE.read_text()) if rc.RXNAV_CACHE.exists() else {}
    unknown = {q["id"]: rc.unknown_names(q["question"], rx) for q in questions}

    index = {}
    for name, chunks in {"1500": rc.chunk_by_section(labels), "500": chunk_small(labels)}.items():
        vecs = np.array(list(embed.embed([c["text"] for c in chunks])))
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        index[name] = (chunks, rc.BM25([c["text"] for c in chunks]), vecs)
        print(f"{name}-character chunks: {len(chunks)}")

    setups = {"R2 sections 1500, hybrid": ("1500", False), "R3a chunks 500, hybrid": ("500", False),
              "R3b chunks 500, hybrid + rerank": ("500", True), "R3c sections 1500, hybrid + rerank": ("1500", True)}
    results = {}  # setup -> qid -> (top-3 keys, gate score)
    for setup, (cname, rerank) in setups.items():
        chunks, bm25, vecs = index[cname]
        per_q = {}
        for q, qv in zip(questions, qvecs):
            ranked, top_cos = rc.run_setup(chunks, bm25, vecs, qv, q["question"], "Hybrid (RRF)", rnd=2)
            gate = top_cos
            if rerank:
                pool = ranked[:20]
                scores = list(reranker.rerank(q["question"], [chunks[i]["text"] for i in pool]))
                order = sorted(range(len(pool)), key=lambda j: -scores[j])
                ranked, gate = [pool[j] for j in order], float(max(scores))
            per_q[q["id"]] = ([(chunks[i]["drug"], chunks[i]["section"], rc.has_evidence(q, chunks[i]))
                               for i in ranked[:3]], gate)
        results[setup] = per_q

    def hits(setup, splits):
        rows = [q for q in questions if q["split"] in splits and q["accept"]]
        acc = [{tuple(a) for a in q["accept"]} for q in rows]
        return (sum(rc.hit_at(1, results[setup][q["id"]][0], a) for q, a in zip(rows, acc)),
                sum(rc.hit_at(3, results[setup][q["id"]][0], a) for q, a in zip(rows, acc)), len(rows))

    def gate_check(setup):
        seen = [q for q in questions if q["split"] in SEEN]
        noans = [results[setup][q["id"]][1] for q in seen if not q["accept"] and not unknown[q["id"]]]
        cutoff = max(noans) + 1e-3
        rejected = [q["id"] for q in seen if q["accept"] and (unknown[q["id"]] or results[setup][q["id"]][1] < cutoff)]
        return cutoff, rejected

    print("\n| Setup | Seen hit@1 | Seen hit@3 | Gate cutoff | Seen answerable rejected | heldout3 hit@1 | heldout3 hit@3 "
          "| heldout3 no-answer rejected | heldout3 answerable rejected |\n|---|---|---|---|---|---|---|---|---|")
    h3 = [q for q in questions if q["split"] == "heldout3"]
    for setup in setups:
        s1, s3, n = hits(setup, SEEN)
        cutoff, rej = gate_check(setup)
        t1, t3, m = hits(setup, {"heldout3"})
        caught = [q["id"] for q in h3 if not q["accept"] and (unknown[q["id"]] or results[setup][q["id"]][1] < cutoff)]
        wrong = [q["id"] for q in h3 if q["accept"] and (unknown[q["id"]] or results[setup][q["id"]][1] < cutoff)]
        print(f"| {setup} | {s1}/{n} | {s3}/{n} | {cutoff:.3f} | {len(rej)} {rej} | {t1}/{m} | {t3}/{m} "
              f"| {caught} of [q45, q46, q47] | {wrong} |")
    best = max(setups, key=lambda s: (hits(s, SEEN)[1], hits(s, SEEN)[0]))
    print(f"\nChosen on the seen set (hit@3, then hit@1): {best}; gate meets the rule: "
          f"{len(gate_check(best)[1]) <= MAX_SEEN_REJECTED}")

    print("\nheldout3 per question (chosen setup):")
    for q in h3:
        keys, g = results[best][q["id"]]
        hit = rc.hit_at(3, keys, {tuple(a) for a in q["accept"]}) if q["accept"] else "-"
        print(f"  {q['id']} hit@3={hit} gate={g:.3f} unknown={unknown[q['id']] or '-'} {q['question']}\n     got {keys}")


if __name__ == "__main__":
    main()
