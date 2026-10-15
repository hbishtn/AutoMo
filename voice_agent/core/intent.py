"""
Turns raw transcribed text (Hindi / Hinglish / English, mixed freely) into
a normalized intent name. No LLM call needed, so this works with zero API
keys configured.
"""
import re
from dataclasses import dataclass

_INTENT_KEYWORD_SETS = {
    "STOP": [
        ["stop"], ["band", "karo"], ["band", "kar"], ["exit"], ["quit"], ["bye"],
    ],
    "PAUSE": [
        ["pause"], ["ruk", "jao"], ["ruko"], ["wait"],
    ],
    "RESUME": [
        ["resume"], ["shuru", "karo"], ["phir", "shuru"], ["continue"],
    ],
    "TIME": [
        ["time"], ["samay"],
    ],
    "OPEN_NOTEPAD": [
        ["notepad"],
    ],
    "OPEN_CALCULATOR": [
        ["calculator"], ["calc"],
    ],
    "STATUS": [
        ["status"], ["kya", "chal", "raha"], ["kya", "kar", "rahe"],
    ],
}


@dataclass
class Intent:
    name: str
    raw_text: str
    service: str = ""
    payload: str = ""


_SERVICE_PATTERNS = {
    "chatgpt": [r"\bchatgpt\b", r"\bchat gpt\b", r"\bgpt\b"],
    "claude": [r"\bclaude\b"],
}
_ASK_ACTION_WORDS = [
    "pucho", "poocho", "poochho", "puch", "puchna", "bolo", "ask", "keh do", "batao",
]
_STRIP_WORDS = [
    r"\bchat gpt\b", r"\bchatgpt\b", r"\bgpt\b", r"\bclaude\b",
    r"\bpoochho\b", r"\bpoocho\b", r"\bpuchna\b", r"\bpucho\b", r"\bpuch\b",
    r"\bbolo\b", r"\bask\b", r"\bse\b", r"\bko\b", r"\bkeh do\b",
]


def _detect_service(lowered):
    for service, patterns in _SERVICE_PATTERNS.items():
        if any(re.search(p, lowered) for p in patterns):
            return service
    return ""


def _has_ask_action(lowered):
    return any(re.search(r"\b" + re.escape(w) + r"\b", lowered) for w in _ASK_ACTION_WORDS)


def _build_prompt(original_text):
    prompt = original_text
    for pattern in _STRIP_WORDS:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", prompt).strip(" ,.:-")


_READ_RESPONSE_PHRASES = [
    ["response", "padho"], ["jawab", "padho"], ["read", "response"], ["response", "batao"],
]
_COPY_CODE_PHRASES = [["code", "copy"], ["code", "nikaal"], ["copy", "code"]]


def classify(text: str) -> Intent:
    lowered = text.lower().strip()
    if not lowered:
        return Intent(name="EMPTY", raw_text=text)

    service = _detect_service(lowered)
    if service and _has_ask_action(lowered):
        prompt = _build_prompt(text)
        return Intent(name="ASK_AI", raw_text=text, service=service, payload=prompt)

    for keyword_set in _READ_RESPONSE_PHRASES:
        if all(k in lowered for k in keyword_set):
            return Intent(name="READ_RESPONSE", raw_text=text)

    for keyword_set in _COPY_CODE_PHRASES:
        if all(k in lowered for k in keyword_set):
            return Intent(name="COPY_CODE", raw_text=text)

    for intent_name, keyword_sets in _INTENT_KEYWORD_SETS.items():
        for keyword_set in keyword_sets:
            if all(keyword in lowered for keyword in keyword_set):
                return Intent(name=intent_name, raw_text=text)

    return Intent(name="UNKNOWN", raw_text=text)