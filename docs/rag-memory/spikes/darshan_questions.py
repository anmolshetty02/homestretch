"""Darshan's 10 answerable retrieval questions (docs/rag-memory/originals/darshan/) in our format. The evidence regexes
come from the cross-check (spikes/darshan_crosscheck/); accept = his own (drug, section) answers."""
import json
from pathlib import Path

HERE = Path(__file__).parent
EV = {"q01": {"ibuprofen": r"diuretic", "furosemide": r"indomethacin|non-?steroidal|NSAID"},
      "q02": {"furosemide": r"diuresis|diuretic effect|urinat|polyuria"},
      "q03": {"metoprolol_succinate": r"dizz|hypotension"}, "q04": {"metoprolol_succinate": r"abrupt|cessation"},
      "q05": {"lisinopril": r"cough"}, "q06": {"lisinopril": r"angioedema"},
      "q07": {"naproxen": r"diuretic|ACE|angiotensin", "lisinopril": r"non-?steroidal|NSAID", "furosemide": r"indomethacin|non-?steroidal|NSAID"},
      "q08": {"metoprolol_succinate": r"extended[- ]release", "metoprolol_tartrate": r"succinate|extended"},
      "q09": {"amlodipine": r"edema"}, "q10": {"furosemide": r"overdos"}}
DARSHAN = json.loads((HERE.parent / "originals/darshan/retrieval_questions.json").read_text())["questions"]
DARSHAN = [{"id": "D-" + q["id"], "split": "darshan", "question": q["question"], "evidence": EV[q["id"]],
        "accept": [[d.replace(" ", "_"), s] for d, s in q["answers"]]} for q in DARSHAN if q["answers"]]
