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

_PROJECT_OPEN_WORDS = ["kholo", "khol", "open", "select"]
_PROJECT_STRIP_WORDS = [
    r"\bproject\b", r"\bfolder\b", r"\bkholo\b", r"\bkhol\b", r"\bopen\b", r"\bselect\b", r"\bkaro\b",
]
_LIST_FILES_PHRASES = [
    ["files", "dikhao"], ["files", "batao"], ["list", "files"], ["file", "list"],
]

_CONFIRM_WORDS = [["haan", "confirm"], ["confirm", "karo"], ["yes", "confirm"]]
_CANCEL_WORDS = [["nahi", "cancel"], ["cancel", "karo"], ["no", "cancel"]]

_FILE_READ_WORDS = ["dikhao", "padho", "kholo", "show"]
_FILE_READ_STRIP_WORDS = [
    r"\bfile\b", r"\bdikhao\b", r"\bpadho\b", r"\bkholo\b", r"\bshow\b", r"\bkaro\b",
]


def _has_file_read_action(lowered):
    return "file" in lowered and any(re.search(r"\b" + w + r"\b", lowered) for w in _FILE_READ_WORDS)


def _build_file_name(original_text):
    name = original_text
    for pattern in _FILE_READ_STRIP_WORDS:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    return name.strip(" ,.:-")


def _has_project_open_action(lowered):
    return "project" in lowered and any(re.search(r"\b" + w + r"\b", lowered) for w in _PROJECT_OPEN_WORDS)


def _build_project_path(original_text):
    path = original_text
    for pattern in _PROJECT_STRIP_WORDS:
        path = re.sub(pattern, "", path, flags=re.IGNORECASE)
    return path.strip(" ,.:-")


def classify(text: str) -> Intent:
    lowered = text.lower().strip()
    if not lowered:
        return Intent(name="EMPTY", raw_text=text)

    for keyword_set in _CONFIRM_WORDS:
        if all(k in lowered for k in keyword_set):
            return Intent(name="EDIT_CONFIRM", raw_text=text)

    for keyword_set in _CANCEL_WORDS:
        if all(k in lowered for k in keyword_set):
            return Intent(name="EDIT_CANCEL", raw_text=text)

    if "::" in text:
        return Intent(name="EDIT_PROPOSE", raw_text=text, payload=text)

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

    if _has_project_open_action(lowered):
        path = _build_project_path(text)
        return Intent(name="PROJECT_OPEN", raw_text=text, payload=path)

    for keyword_set in _LIST_FILES_PHRASES:
        if all(k in lowered for k in keyword_set):
            return Intent(name="LIST_FILES", raw_text=text)

    if "files" not in lowered and _has_file_read_action(lowered):
        name = _build_file_name(text)
        return Intent(name="FILE_READ", raw_text=text, payload=name)

    for intent_name, keyword_sets in _INTENT_KEYWORD_SETS.items():
        for keyword_set in keyword_sets:
            if all(keyword in lowered for keyword in keyword_set):
                return Intent(name=intent_name, raw_text=text)

    return Intent(name="UNKNOWN", raw_text=text)