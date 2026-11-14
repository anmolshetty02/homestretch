"""HomeStretch tools (Assignment 4, Part 1). Each tool is a plain function plus a JSON schema in SPECS.
The same functions are served by app/mcp_server.py (MCP) and called in-process by the evals (app/tool_client.py).
Tools never raise to the model: bad input or a failed service returns {"error": "..."} the model can act on.

Reuses Assignment 3 code from docs/rag-memory/spikes/ (RxNorm lookup, retrieval round 5, session record).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPIKES = ROOT / "docs" / "rag-memory" / "spikes"
sys.path.insert(0, str(SPIKES))
sys.path.insert(0, str(ROOT))

import rxnorm_check  # noqa: E402
import retrieval_check as rc  # noqa: E402
from query_expansion import expand  # noqa: E402
from memory_check import EMPTY_RECORD, INSTRUCTIONS, RECORD_TASK  # noqa: E402

FIXTURE = json.loads((ROOT / "fixtures" / "p001.json").read_text())
SESSIONS = ROOT / "app" / "sessions"
RXNAV_CACHE = ROOT / "app" / ".cache_rxnav.json"
TOP_K = 5  # design.md §E round 5: hybrid + expansion, reranked, top 5, bge-base, no gate
MED_ID = re.compile(r"^(med|stopped)-\d+$")
SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
RELEASE = re.compile(r"\s+\b(XL|ER|SR|CR|XR|LA|DR|24 ?HR?)\b\.?$", re.I)
_rx = None
_index = None


def _err(msg):
    return {"error": msg}


# ----------------------------------------------------------------------------------------------- read-only tools

def check_medicine_name(name):
    """RxNorm: is this a real medicine, and what are its ingredients? No match means pharmacist_check, never a guess."""
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        return _err("name must be a non-empty string of at most 100 characters, e.g. 'Lasix'.")
    global _rx
    _rx = _rx or rxnorm_check.RxNav(RXNAV_CACHE)
    clean = name.strip()
    base = RELEASE.sub("", clean).strip()  # "Toprol XL" -> "Toprol": RxNav knows the name but its id is retired
    try:
        found, how, score = _rx.exact(clean), "exact", None
        if found == rxnorm_check.NO_MATCH and base != clean:
            found, how = _rx.exact(base), "exact, release suffix removed"
        if found == rxnorm_check.NO_MATCH:
            found, score = _rx.approximate(clean)
            how = f"approximate (score {score})"
    except rxnorm_check.NetworkDown as e:
        return _err(f"RxNorm service unavailable ({e}). Treat the name as unchecked: pharmacist_check.")
    if found != rxnorm_check.NO_MATCH:
        return {"name": name, "status": "matched", "how": how, "ingredients": [i.lower() for i in found]}
    if score is not None and score >= 8:  # ponytail: one cutoff from A3 name_match_check's B_CUTOFFS
        return {"name": name, "status": "matched", "how": how, "ingredients": [],
                "note": "RxNorm knows this name but its ingredients could not be resolved"}
    return {"name": name, "status": "no_match", "action": "pharmacist_check: do not guess what this medicine is"}


def get_care_plan(item_id=None):
    """The discharge care plan, or one item of it (med-1, stopped-1, ...)."""
    plan = FIXTURE["care_plan"]
    if item_id in (None, ""):
        return plan
    if not isinstance(item_id, str) or not MED_ID.match(item_id):
        return _err("item_id must look like med-1 or stopped-1, or be omitted for the whole plan.")
    items = plan["medications"] + plan.get("stopped_medications", [])
    hit = next((m for m in items if m.get("id") == item_id), None)
    return hit or _err(f"No plan item {item_id}. Known: {[m['id'] for m in items]}")


def _load_index():
    global _index
    if _index is None:
        import numpy as np
        from fastembed import TextEmbedding
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        cd = str(Path.home() / ".cache" / "fastembed")
        embed = TextEmbedding("BAAI/bge-base-en-v1.5", cache_dir=cd)
        chunks = rc.chunk_by_section(rc.load_labels())
        cache = ROOT / "app" / f".cache_label_vecs_{len(chunks)}.npy"  # embedding all chunks takes ~2 min
        if cache.exists():
            vecs = np.load(cache)
        else:
            vecs = np.array(list(embed.embed([c["text"] for c in chunks])))
            np.save(cache, vecs)
        _index = {"np": np, "embed": embed, "chunks": chunks, "bm25": rc.BM25([c["text"] for c in chunks]),
                  "vecs": vecs / np.linalg.norm(vecs, axis=1, keepdims=True),
                  "rerank": TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2", cache_dir=cd)}
    return _index


def search_drug_label(question):
    """FDA drug-label passages for a medicine question (side effects, food, interactions). Not for doses or emergencies."""
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        return _err("question must be a non-empty string of at most 500 characters.")
    rx = json.loads(rc.RXNAV_CACHE.read_text()) if rc.RXNAV_CACHE.exists() else {}
    try:
        unknown = rc.unknown_names(question, rx)
    except OSError as e:
        return _err(f"name check unavailable ({e}); no references returned.")
    if unknown:
        return {"references": [], "note": f"unknown medicine names {unknown}: no label exists, pharmacist_check"}
    ix = _load_index()
    np = ix["np"]
    t = expand(question)
    qv = np.array(list(ix["embed"].query_embed([t])))[0]
    ranked, _ = rc.run_setup(ix["chunks"], ix["bm25"], ix["vecs"], qv / np.linalg.norm(qv), t, "Hybrid (RRF)", rnd=2)
    pool = ranked[:20]
    scores = list(ix["rerank"].rerank(t, [ix["chunks"][i]["text"] for i in pool]))
    top = [pool[j] for j in sorted(range(len(pool)), key=lambda j: -scores[j])][:TOP_K]
    refs = []
    for n, i in enumerate(top, 1):
        c = ix["chunks"][i]
        d = c["effective_time"]
        refs.append({"id": f"ref-{n}", "drug": c["drug"], "section": c["section"], "source": "openFDA label",
                     "set_id": c["set_id"], "date": f"{d[:4]}-{d[4:6]}-{d[6:]}", "text": c["text"]})
    return {"references": refs}


def read_label_photo(path, model="mock"):
    """Prompt A, OCR route: a label image -> {name, strength, directions}. Unreadable fields stay 'unreadable'."""
    p = (ROOT / str(path)).resolve()
    allowed = [(ROOT / "fixtures" / "labels").resolve(), SESSIONS.resolve()]
    if not any(p.is_relative_to(a) for a in allowed) or p.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        return _err("path must be a .png/.jpg under fixtures/labels/ or an uploaded photo.")
    if not p.exists():
        return _err(f"no file at {path}")
    text = subprocess.run(["tesseract", str(p), "-", "--psm", "6"], capture_output=True, text=True).stdout
    if not text.strip():
        return {"name": "unreadable", "strength": "unreadable", "directions": "unreadable", "ocr": ""}
    from app.llm import complete_json
    system = (ROOT / "prompts" / "extract_v2.md").read_text()
    out = complete_json([{"role": "system", "content": system}, {"role": "user", "content": text}], model, purpose="extract")
    if "error" in out:
        return out
    return {k: out.get(k, "unreadable") for k in ("name", "strength", "directions")} | {"ocr": text}


def get_session_memory(session_id):
    """The session record (open flags, pending questions, reports, red flags, preferences) and the last cabinet check."""
    if not isinstance(session_id, str) or not SESSION_ID.match(session_id):
        return _err("session_id must be 1-64 letters, digits, - or _.")
    f = SESSIONS / f"{session_id}.json"
    return json.loads(f.read_text()) if f.exists() else {"record": EMPTY_RECORD, "cabinet_diff": None, "turns": []}


# ----------------------------------------------------------------------------------------------- write tools

def update_session_memory(session_id, message, reply=None, cabinet_diff=None, model="mock"):
    """WRITE. Folds the newest turn into the session record (A3 memory design: structured record, one call per turn)."""
    mem = get_session_memory(session_id)
    if "error" in mem:
        return mem
    if not isinstance(message, str) or len(message) > 4000:
        return _err("message must be a string of at most 4000 characters.")
    if cabinet_diff is not None:
        mem["cabinet_diff"] = cabinet_diff
    from app.llm import complete_json
    context = json.dumps({"care_plan": FIXTURE["care_plan"], "cabinet_diff": mem["cabinet_diff"] or FIXTURE["cabinet_diff"]})
    record = complete_json([
        {"role": "system", "content": INSTRUCTIONS + RECORD_TASK},
        {"role": "user", "content": f"<context>{context}</context>\n<memory>{json.dumps(mem['record'])}</memory>\n"
                                    f"<newest_message>Turn {len(mem['turns']) + 1}: {message}</newest_message>"}],
        model, purpose="memory")
    if "error" not in record and set(EMPTY_RECORD) <= set(record):
        mem["record"] = {k: record[k] for k in EMPTY_RECORD}
    mem["turns"] = (mem["turns"] + [{"user": message, "assistant": reply}])[-6:]
    SESSIONS.mkdir(parents=True, exist_ok=True)
    (SESSIONS / f"{session_id}.json").write_text(json.dumps(mem, indent=1))
    return {"saved": True, "record": mem["record"]}


# ----------------------------------------------------------------------------------------------- registry

def _spec(name, description, props, required=(), write=False):
    return {"name": name, "description": description, "write": write,
            "parameters": {"type": "object", "properties": props, "required": list(required)}}


SPECS = [
    _spec("check_medicine_name", "Look a medicine name up in RxNorm (NIH). Use for any medicine name the care plan does "
          "not contain, including brand names and misspellings. status no_match means the medicine is unknown: tell the "
          "caregiver to check with the pharmacist, never guess.", {"name": {"type": "string"}}, ["name"]),
    _spec("search_drug_label", "Search FDA drug labels for the medicines in the care plan. Use for questions about side "
          "effects, food or drink, interactions, or what a medicine does, when the care plan does not answer it. "
          "Never use for dose, missed-dose, or emergency questions.", {"question": {"type": "string"}}, ["question"]),
    _spec("get_care_plan", "Get the discharge care plan, or one item by id (med-1, stopped-1).",
          {"item_id": {"type": "string", "description": "optional, e.g. med-2"}}),
    _spec("read_label_photo", "Read a medicine bottle label photo into name, strength, and directions.",
          {"path": {"type": "string"}}, ["path"]),
    _spec("get_session_memory", "Get this caregiver's session record and last cabinet check.",
          {"session_id": {"type": "string"}}, ["session_id"]),
    _spec("update_session_memory", "Save the newest turn into the session record.",
          {"session_id": {"type": "string"}, "message": {"type": "string"}, "reply": {"type": "string"},
           "cabinet_diff": {"type": "array", "items": {"type": "object"},
                            "description": "flags from a cabinet check, saved for follow-up questions"}},
          ["session_id", "message"], write=True),
]
FUNCTIONS = {"check_medicine_name": check_medicine_name, "search_drug_label": search_drug_label,
             "get_care_plan": get_care_plan, "read_label_photo": read_label_photo,
             "get_session_memory": get_session_memory, "update_session_memory": update_session_memory}
assert set(FUNCTIONS) == {s["name"] for s in SPECS}
