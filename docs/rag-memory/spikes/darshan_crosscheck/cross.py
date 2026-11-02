"""Cross-check: his pipeline vs ours, chunk-level scoring. Paths are copies in scratch."""
import json, re, sys
from pathlib import Path
import numpy as np

X = Path(sys.argv[1])  # scratch/xrun
HIS = X / "repo/docs/rag-memory/spikes"
OURS = X / "ours"
sys.path.insert(0, str(HIS)); import retrieval_check as H; sys.path.pop(0); del sys.modules["retrieval_check"]
sys.path.insert(0, str(OURS)); import retrieval_check as O; from query_expansion import expand

from fastembed import TextEmbedding
emb = TextEmbedding("BAAI/bge-small-en-v1.5")
def qv(t):
    v = np.array(list(emb.query_embed([t])))[0]; return v / np.linalg.norm(v)
def pv(texts):
    v = np.array(list(emb.passage_embed(texts))); return v / np.linalg.norm(v, axis=1, keepdims=True)

# Evidence regexes for HIS questions (my judgment; q08 is loose)
EV = {"q01": {"ibuprofen": r"diuretic", "furosemide": r"indomethacin|non-?steroidal|NSAID"},
      "q02": {"furosemide": r"diuresis|diuretic effect|urinat|polyuria"},
      "q03": {"metoprolol succinate": r"dizz|hypotension"},
      "q04": {"metoprolol succinate": r"abrupt|cessation"},
      "q05": {"lisinopril": r"cough"},
      "q06": {"lisinopril": r"angioedema"},
      "q07": {"naproxen": r"diuretic|ACE|angiotensin", "lisinopril": r"non-?steroidal|NSAID",
              "furosemide": r"indomethacin|non-?steroidal|NSAID"},
      "q08": {"metoprolol succinate": r"extended[- ]release", "metoprolol tartrate": r"succinate|extended"},
      "q09": {"amlodipine": r"edema"},
      "q10": {"furosemide": r"overdos"}}
his_qs = [q for q in json.loads((HIS / "retrieval_questions.json").read_text())["questions"] if q["answers"]]
und = lambda d: d.replace(" ", "_")

def score(rows, k):  # rows: list of (keys) with keys=(sec_ok, ev_ok)
    return (sum(any(a and b for a, b in r[:k]) for r in rows), sum(any(b for _, b in r[:k]) for r in rows))

# ---- A: his pipeline on his questions, section-level vs chunk-level
patient = json.loads((X / "repo/fixtures/p001.json").read_text())
labels = H.load_corpus(); names = H.name_map(patient); base = H.patient_drugs(patient, names)
print("A) HIS pipeline on HIS 10 questions: hit@1/hit@3  section-level | chunk-level (section AND evidence) | evidence-only")
his_chunks = {}
for how in ("section", "fixed"):
    ch = H.chunk(labels, how); his_chunks[how] = ch
    bm = H.BM25([c["text"] for c in ch]); cv = pv([c["text"] for c in ch])
    for search in ("bm25", "vector", "hybrid"):
        sec_rows, rows = [], []
        for q in his_qs:
            allowed = base | H.find_drugs(q["question"], names)
            idx = [i for i, c in enumerate(ch) if c["drug"] in allowed]
            cos = cv[idx] @ qv(q["question"])
            rv = [idx[j] for j in np.argsort(-cos, kind="stable")]
            rb = sorted(idx, key=lambda i: (-bm.score(q["question"], i), i))
            r = {"bm25": rb, "vector": rv, "hybrid": H.rrf(rb, rv)}[search][:3]
            ans = {tuple(a) for a in q["answers"]}
            rows.append([((ch[i]["drug"], ch[i]["section"]) in ans,
                          bool(re.search(EV[q["id"]].get(ch[i]["drug"], r"(?!)"), ch[i]["text"], re.I))) for i in r])
        s1 = sum(r[0][0] for r in rows); s3 = sum(any(a for a, _ in r) for r in rows)
        c1, e1 = score(rows, 1); c3, e3 = score(rows, 3)
        print(f"  {how:7s} {search:6s}  {s1}/10 {s3}/10 | {c1}/10 {c3}/10 | {e1}/10 {e3}/10")

# ---- B: our R2+expansion (by-section hybrid, round-2 filter) on his questions, our labels
ol = O.load_labels(); och = O.chunk_by_section(ol); obm = O.BM25([c["text"] for c in och]); ov = pv([c["text"] for c in och])
print("B) OUR pipeline on HIS 10 questions (section AND evidence | evidence-only):")
for name, exp in (("R2 hybrid", False), ("R2 + expansion", True)):
    rows = []
    for q in his_qs:
        t = expand(q["question"]) if exp else q["question"]
        ranked, _ = O.run_setup(och, obm, ov, qv(t), t, "Hybrid (RRF)", rnd=2)
        ans = {(und(d), s) for d, s in q["answers"]}
        ev = {und(d): r for d, r in EV[q["id"]].items()}
        rows.append([((och[i]["drug"], och[i]["section"]) in ans,
                      bool(re.search(ev.get(och[i]["drug"], r"(?!)"), och[i]["text"], re.I))) for i in ranked[:3]])
    c1, e1 = score(rows, 1); c3, e3 = score(rows, 3)
    print(f"  {name:15s} {c1}/10 {c3}/10 | {e1}/10 {e3}/10")

# ---- C: his pipeline on OUR 45 answerable questions, our evidence regexes, his labels
oq = [q for q in json.loads((OURS / "retrieval_questions.json").read_text()) if q["accept"]]
print(f"C) HIS pipeline on OUR {len(oq)} answerable questions (section AND evidence | evidence-only), his labels:")
for how, search in (("fixed", "vector"), ("section", "hybrid"), ("section", "vector")):
    ch = his_chunks[how]; bm = H.BM25([c["text"] for c in ch]); cv = pv([c["text"] for c in ch])
    rows = []
    for q in oq:
        allowed = base | H.find_drugs(q["question"], names)
        idx = [i for i, c in enumerate(ch) if c["drug"] in allowed]
        cos = cv[idx] @ qv(q["question"])
        rv = [idx[j] for j in np.argsort(-cos, kind="stable")]
        rb = sorted(idx, key=lambda i: (-bm.score(q["question"], i), i))
        r = {"vector": rv, "hybrid": H.rrf(rb, rv)}[search][:3]
        acc = {tuple(a) for a in q["accept"]}
        def ev_ok(c):
            rx = q["evidence"].get(und(c["drug"]))
            return rx == "(hand-set)" or bool(rx and re.search(rx, c["text"], re.I))
        rows.append([((und(ch[i]["drug"]), ch[i]["section"]) in acc, ev_ok(ch[i])) for i in r])
    c1, e1 = score(rows, 1); c3, e3 = score(rows, 3); n = len(oq)
    print(f"  {how} {search}: {c1}/{n} {c3}/{n} | {e1}/{n} {e3}/{n}")
