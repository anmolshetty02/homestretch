"""Plain words -> label words for query expansion (Assignment 3, retrieval round 4). Written from general consumer vs
clinical vocabulary BEFORE the heldout4 questions were written (design.md, "round 4"); do not edit after seeing results.
"""
import re

LAY_TO_LABEL = {
    r"pee|peeing|urinat|bathroom a lot": "urination diuresis nocturia",
    r"thirst|dry mouth": "thirst dry mouth dehydration",
    r"dizz|lighthead|woozy": "dizziness orthostatic hypotension",
    r"tired|worn out|sleepy|no energy": "fatigue tiredness",
    r"short of breath|winded|out of breath|breath": "dyspnea shortness of breath bronchospasm",
    r"swell|swollen|puffy": "edema swelling angioedema",
    r"ringing|ears": "tinnitus hearing ototoxicity",
    r"low blood sugar|sugar drop": "hypoglycemia",
    r"high potassium|potassium.*high": "hyperkalemia potassium",
    r"potassium": "potassium hypokalemia",
    r"cramp|weak": "muscle cramps weakness",
    r"sun|sunburn": "photosensitivity sunlight",
    r"stomach|belly|heartburn": "gastrointestinal stomach bleeding ulcer",
    r"cough": "cough",
    r"slow (pulse|heart)|pulse.*slow|heart rate.*low|pulse.*low": "bradycardia",
    r"fast heart|racing": "tachycardia palpitations",
    r"cold (hands|feet)|hands.*cold|feet.*cold": "cold extremities",
    r"rash|itch": "rash pruritus skin reactions",
    r"taste": "taste disturbance dysgeusia",
    r"gout|toe": "gout hyperuricemia uric acid",
    r"dream|nightmare|sleep": "sleep disturbances nightmares insomnia",
    r"sad|depress|down": "depression mental",
    r"blood pressure.*(up|high)|raise.*blood pressure": "hypertension blood pressure increase",
    r"bleed|bruis": "bleeding",
    r"kidney": "renal kidney function",
    r"with food|empty stomach|eat": "food meal",
    r"alcohol|wine|beer|drink": "alcohol",
    r"stop|quit": "abrupt cessation withdrawal",
}


def expand(question):
    """The question plus label words for every plain-word pattern it contains."""
    extra = [words for pat, words in LAY_TO_LABEL.items() if re.search(pat, question, re.I)]
    return question + (" " + " ".join(extra) if extra else "")


if __name__ == "__main__":
    assert expand("Can the heart rate pill make her hands and feet cold?").endswith("cold extremities")
    assert expand("What should I cook?") == "What should I cook?"
    print("query_expansion self-test ok")
