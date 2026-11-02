"""Retrieval round 5 (Assignment 3): gate and ranking fixes. Setup and rule: design.md, Section E. Reuses rounds 2-4
(name check, filter, hybrid, expansion, chunk-level scoring). Run from the repo root:
    .venv/bin/python docs/rag-memory/spikes/retrieval_round5.py            # choose on the selection set
    .venv/bin/python docs/rag-memory/spikes/retrieval_round5.py --final    # also run heldout5 once (chosen vs current)
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import retrieval_check as rc  # noqa: E402
from query_expansion import expand  # noqa: E402
from darshan_questions import DARSHAN  # noqa: E402

SEEN = {"dev", "heldout", "heldout2", "heldout3"}
CHANGES = {"G0": 0, "G1": 1, "G2": 1, "G3": 1, "G1+G2": 2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args()
    from fastembed import TextEmbedding
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    cd = str(Path.home() / ".cache" / "fastembed")
    reranker = TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2", cache_dir=cd)
    models = {m: TextEmbedding(m, cache_dir=cd) for m in ("BAAI/bge-small-en-v1.5", "BAAI/bge-base-en-v1.5")}
    labels = rc.load_labels()
    base_chunks = rc.chunk_by_section(labels)
    rx_cache = json.loads(rc.RXNAV_CACHE.read_text()) if rc.RXNAV_CACHE.exists() else {}
    questions = json.loads((HERE / "retrieval_questions.json").read_text())
    seen = [q for q in questions if q["split"] in SEEN]
    old8 = [q for q in questions if q["split"] == "heldout4"]

    index = {}
    for prefix, model in itertools.product((False, True), models):
        chunks = [dict(c, text=f"{c['section'].replace('_', ' ')}: {c['text']}") if prefix else c for c in base_chunks]
        vecs = np.array(list(models[model].embed([c["text"] for c in chunks])))
        index[prefix, model] = (chunks, rc.BM25([c["text"] for c in chunks]), vecs / np.linalg.norm(vecs, axis=1, keepdims=True))

    score_cache = {}

    def rerank(query, texts):
        missing = [t for t in texts if (query, t) not in score_cache]
        for t, s in zip(missing, reranker.rerank(query, missing) if missing else []):
            score_cache[query, t] = float(s)
        return [score_cache[query, t] for t in texts]

    run_cache = {}

    def run(q, *r):
        if (q["id"], r) not in run_cache:
            run_cache[q["id"], r] = _run(q, *r)
        return run_cache[q["id"], r]

    def _run(q, r1, r2, r3, r4):
        """Passages sent (top k), their keys, and gate scores for the raw and the expanded question."""
        chunks, bm25, vecs = index[r2, "BAAI/bge-base-en-v1.5" if r4 else "BAAI/bge-small-en-v1.5"]
        t = expand(q["question"])
        qv = np.array(list(models["BAAI/bge-base-en-v1.5" if r4 else "BAAI/bge-small-en-v1.5"].query_embed([t])))[0]
        ranked, _ = rc.run_setup(chunks, bm25, vecs, qv / np.linalg.norm(qv), t, "Hybrid (RRF)", rnd=2)
        pool = ranked[:20]
        texts = [chunks[i]["text"] for i in pool]
        if r1:
            s = rerank(t, texts)
            ranked = [pool[j] for j in sorted(range(len(pool)), key=lambda j: -s[j])]
        sent = ranked[:5 if r3 else 3]
        keys = [(chunks[i]["drug"], chunks[i]["section"], rc.has_evidence(q, chunks[i])) for i in sent]
        return {"keys": keys, "g_raw": max(rerank(q["question"], texts)), "g_exp": max(rerank(t, texts)),
                "unknown": bool(rc.unknown_names(q["question"], rx_cache))}

    def evaluate(setup, qs, cutoffs):
        r, gate = setup
        out = {"e2e": 0, "hit1": 0, "hitk": 0, "blocked": 0, "wrong_drug": 0, "off_target": 0, "noans_blocked": 0, "noans": 0, "n": 0}
        for q in qs:
            x = run(q, *r)
            g = x["g_exp"] if gate in ("G1", "G1+G2") else x["g_raw"]
            passes = not x["unknown"] and (gate == "G3" or g >= cutoffs[gate])
            if not q["accept"]:
                out["noans"] += 1
                out["noans_blocked"] += not passes
                continue
            acc = {tuple(a) for a in q["accept"]}
            out["n"] += 1
            hit = rc.hit_at(len(x["keys"]), x["keys"], acc)
            out["hitk"] += hit
            out["hit1"] += rc.hit_at(1, x["keys"], acc) and passes
            out["e2e"] += hit and passes
            out["blocked"] += not passes
            out["off_target"] += passes and x["keys"][0][0] not in q["evidence"]
            # wrong drug as in rounds 1-2: a passage from the stopped look-alike drug the question did not name
            out["wrong_drug"] += passes and any(k[0] not in rc.drugs_for(q["question"], 2) for k in x["keys"])
        return out

    def cutoffs_for(r):
        """Round-3 rule (just above the best seen no-answer score) for G0/G1; G2 recalibrated: block at most 1 of 37."""
        xs = [(q, run(q, *r)) for q in seen]
        noans = [x for q, x in xs if not q["accept"] and not x["unknown"]]
        ans = [x for q, x in xs if q["accept"] and not x["unknown"]]
        return {"G0": max(x["g_raw"] for x in noans) + 1e-3, "G1": max(x["g_exp"] for x in noans) + 1e-3,
                "G2": sorted(x["g_raw"] for x in ans)[1], "G1+G2": sorted(x["g_exp"] for x in ans)[1], "G3": None}

    rankings = list(itertools.product((False, True), repeat=4))
    rows = []
    for r in rankings:
        cuts = cutoffs_for(r)
        for gate in CHANGES:
            rows.append(((r, gate), cuts, evaluate((r, gate), seen, cuts)))

    def name(setup):
        r, gate = setup
        return "+".join([n for n, on in zip(("R1", "R2", "R3", "R4"), r) if on] or ["base"]) + f" / {gate}"

    def changes(setup):
        return sum(setup[0]) + CHANGES[setup[1]]

    print("Selection set (37 answerable). e2e = right passage sent AND passes the gate.\n")
    print("| Setup | Changes | e2e | hit@1 sent | right passage in sent (no gate) | real blocked | wrong drug | rank-1 off-target (info) | no-answer blocked |")
    print("|---|---|---|---|---|---|---|---|---|")
    for setup, cuts, m in sorted(rows, key=lambda x: (-x[2]["e2e"], changes(x[0]))):
        print(f"| {name(setup)} | {changes(setup)} | {m['e2e']}/{m['n']} | {m['hit1']} | {m['hitk']} | {m['blocked']} | "
              f"{m['wrong_drug']} | {m['off_target']} | {m['noans_blocked']}/{m['noans']} |")
    ok = [x for x in rows if x[2]["wrong_drug"] == 0 and x[2]["blocked"] <= 1]
    best_setup, best_cuts, best_m = max(ok, key=lambda x: (x[2]["e2e"], -changes(x[0]), x[2]["hit1"], x[2]["noans_blocked"]))
    current = ((False, False, False, False), "G0")
    print(f"\nChosen by the rule: {name(best_setup)} (gate cutoff {best_cuts[best_setup[1]]})")
    made_up = [q["id"] for q in questions if not q["accept"] and rc.unknown_names(q["question"], rx_cache)]
    print(f"Made-up drugs stopped by the name check (unchanged): {made_up}")

    print("\nPost-hoc (not used to choose):")
    for label, qs in (("old heldout4 (8)", old8), ("Darshan's 10 (his sections + evidence)", DARSHAN)):
        for s in (current, best_setup):
            cuts = cutoffs_for(s[0])
            m = evaluate(s, qs, cuts)
            print(f"  {label}, {name(s)}: e2e {m['e2e']}/{m['n']}, right passage sent {m['hitk']}/{m['n']}, real blocked "
                  f"{m['blocked']}, wrong drug {m['wrong_drug']}, rank-1 off-target {m['off_target']}")
    if args.final:
        h5 = json.loads((HERE / "retrieval_heldout5.json").read_text())
        print("\nheldout5 (new, frozen, run once):")
        for s in (current, best_setup):
            m = evaluate(s, h5, cutoffs_for(s[0]))
            print(f"  {name(s)}: e2e {m['e2e']}/{m['n']}, hit@1 {m['hit1']}, right passage sent {m['hitk']}/{m['n']}, real "
                  f"blocked {m['blocked']}, wrong drug {m['wrong_drug']}, rank-1 off-target {m['off_target']}, no-answer blocked {m['noans_blocked']}/{m['noans']}")


if __name__ == "__main__":
    main()
