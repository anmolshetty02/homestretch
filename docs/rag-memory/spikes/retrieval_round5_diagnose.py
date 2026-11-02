"""Read-only diagnosis of every retrieval miss of the chosen setup (R2 + expansion), bucketed coverage/ranking/gate/filter."""
import json, re, sys
from pathlib import Path
import numpy as np
SP = Path(__file__).parent
sys.path.insert(0, str(SP))
import retrieval_check as rc
from query_expansion import expand
from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
cd = str(Path.home() / ".cache" / "fastembed")
embed = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=cd)
rer = TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2", cache_dir=cd)
chunks = rc.chunk_by_section(rc.load_labels())
vecs = np.array(list(embed.embed([c["text"] for c in chunks]))); vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
bm25 = rc.BM25([c["text"] for c in chunks])
def qvec(t):
    v = np.array(list(embed.query_embed([t])))[0]; return v / np.linalg.norm(v)
SEEN = {"dev", "heldout", "heldout2", "heldout3"}
ours = [q for q in json.loads((SP / "retrieval_questions.json").read_text()) if q["split"] in SEEN | {"heldout4"}]
from darshan_questions import DARSHAN as his  # noqa: E402


def good(q, i, strict=True):
    c = chunks[i]
    sec_ok = [c["drug"], c["section"]] in q["accept"] or (c["drug"], c["section"]) in {tuple(a) for a in q["accept"]}
    return rc.has_evidence(q, c) and (sec_ok or not strict)

def run(q):
    t = expand(q["question"])
    ranked, _ = rc.run_setup(chunks, bm25, vecs, qvec(t), t, "Hybrid (RRF)", rnd=2)
    pool = ranked[:20]
    g = float(max(rer.rerank(q["question"], [chunks[i]["text"] for i in pool])))
    return t, ranked, g

# gate cutoff exactly as round 3: just above the best no-answer score among seen non-unknown questions
cache = json.loads(rc.RXNAV_CACHE.read_text()) if rc.RXNAV_CACHE.exists() else {}
noans = [run(q)[2] for q in ours if q["split"] in SEEN and not q["accept"] and not rc.unknown_names(q["question"], cache)]
cutoff = max(noans) + 1e-3
print(f"Gate cutoff (round-3 rule, R2+expansion pool): {cutoff:.3f}\n")
tot = {}
for label, qs, strict in (("SELECTION (dev..heldout3, 37)", [q for q in ours if q["split"] in SEEN and q["accept"]], True),
                          ("HELDOUT4 (8)", [q for q in ours if q["split"] == "heldout4" and q["accept"]], True),
                          ("DARSHAN (10), strict = his sections + evidence", his, True)):
    print(f"######## {label}")
    n_hit = 0
    for q in qs:
        t, ranked, g = run(q)
        hit3 = any(good(q, i, strict) for i in ranked[:3])
        gated = g < cutoff
        if hit3 and not gated: n_hit += 1; continue
        anywhere = [i for i in range(len(chunks)) if good(q, i, strict)]
        allowed = set(rc.drugs_for(t, 2))
        in_allowed = [i for i in anywhere if chunks[i]["drug"] in allowed]
        rank = min((ranked.index(i) + 1 for i in in_allowed if i in ranked), default=None)
        loose = [i for i in range(len(chunks)) if good(q, i, False) and chunks[i]["drug"] in allowed]
        lrank = min((ranked.index(i) + 1 for i in loose if i in ranked), default=None)
        if hit3 and gated: b = "c GATE"
        elif not anywhere: b = "a COVERAGE"
        elif not in_allowed: b = "d FILTER"
        else: b = "b RANKING"
        tot.setdefault(label, {}).setdefault(b, []).append(q["id"])
        print(f"\n{q['id']} [{b}] gate={g:.3f} best-correct-rank={rank} evidence-only-rank={lrank}\n  Q: {q['question']}\n  expanded: {t[len(q['question']):].strip() or '-'}\n  expect: {q['accept']}  evidence: {q['evidence']}")
        if b == "a COVERAGE":
            ev_any = [(chunks[i]['drug'], chunks[i]['section']) for i in range(len(chunks)) if rc.has_evidence(q, chunks[i])]
            print(f"  evidence text found in (any section): {sorted(set(ev_any))[:8]}")
        for r, i in enumerate(ranked[:10], 1):
            c = chunks[i]
            print(f"   {r:2d}. {c['drug']}/{c['section']} {'<== correct' if good(q,i) else ('(evidence, other section)' if good(q,i,False) else '')}")
    print(f"\n{label}: {n_hit}/{len(qs)} hit@3 and not gated\n")
print("BUCKETS:", json.dumps(tot, indent=1))
