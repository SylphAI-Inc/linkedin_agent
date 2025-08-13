import re
from typing import Dict


def score_candidate(profile: Dict) -> float:
    text = " ".join(str(profile.get(k, "") or "") for k in ["headline", "experience", "about"]).lower()
    score = 0.0
    if re.search(r"react|node|typescript|javascript|full\s*stack", text):
        score += 0.4
    if re.search(r"(202[2-5])", text):
        score += 0.2
    if re.search(r"(bay area|san francisco|oakland|san jose)", text):
        score += 0.2
    if re.search(r"(open source|oss|maintainer|github)", text):
        score += 0.2
    return min(score, 1.0)
