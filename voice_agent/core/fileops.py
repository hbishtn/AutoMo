"""
Phase 3, step 1: selecting a project folder and listing its files.

Nothing in this file writes, edits, or deletes anything — it only reads.
"""
import logging
import re
from pathlib import Path
import difflib

logger = logging.getLogger("voice_agent.fileops")

_IGNORE_DIR_NAMES = {".git", ".git_backup", "node_modules", "venv", "__pycache__", ".venv", "dist", "build"}


def set_project(state, raw_path: str) -> str:
    path = Path(raw_path.strip().strip('"').strip("'")).expanduser()
    if not path.exists():
        return f"Yeh path nahi mila: {path}"
    if not path.is_dir():
        return f"Yeh ek folder nahi hai: {path}"
    state.project_root = path.resolve()
    logger.info("Project folder set: %s", state.project_root)
    return f"Project folder set ho gaya: {state.project_root}"


def list_files(state, max_files: int = 40) -> str:
    if state.project_root is None:
        return "Pehle project folder select karo. Jaise: project kholo C:\\Users\\dell\\Desktop\\mera-project"

    root = state.project_root
    files = []
    for p in sorted(root.rglob("*")):
        if any(part in _IGNORE_DIR_NAMES for part in p.parts):
            continue
        if p.is_file():
            files.append(p.relative_to(root))
        if len(files) >= max_files:
            break

    if not files:
        return f"{root} me koi file nahi mili."

    listing = "\n".join(f"  - {f}" for f in files)
    more_note = " (sirf pehli 40 dikha raha hoon)" if len(files) >= max_files else ""
    return f"{root} ki files{more_note}:\n{listing}"

def read_file(state, raw_name: str) -> str:
    if state.project_root is None:
        return "Pehle project folder select karo."
    if not raw_name:
        return "Kaunsi file padhni hai, naam bhi bolo."

    target = (state.project_root / raw_name.strip()).resolve()

    # Safety: never read anything outside the selected project folder.
    try:
        target.relative_to(state.project_root)
    except ValueError:
        return "Yeh file project folder se bahar hai, main usse nahi padh sakta."

    if not target.exists():
        return f"Yeh file nahi mili: {raw_name}"
    if not target.is_file():
        return f"Yeh ek file nahi hai: {raw_name}"

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        logger.error("read_file failed: %s", exc)
        return f"File padhne me error aaya: {exc}"

    lines = content.count("\n") + 1
    logger.info("Read file %s (%d lines)", target, lines)
    preview = content[:800] + ("\n...(aur bhi hai)..." if len(content) > 800 else "")
    return f"{raw_name} ({lines} lines):\n{preview}"


def propose_edit(state, raw_command: str) -> str:
    if state.project_root is None:
        return "Pehle project folder select karo."

    parts = raw_command.split("::")
    if len(parts) != 3:
        return "Format sahi nahi hai. Aise bolo: filename.py :: purana text :: naya text"

    filename, old_text, new_text = (p.strip() for p in parts)
    target = (state.project_root / filename).resolve()

    try:
        target.relative_to(state.project_root)
    except ValueError:
        return "Yeh file project folder se bahar hai, main usse edit nahi kar sakta."

    if not target.exists() or not target.is_file():
        return f"Yeh file nahi mili: {filename}"

    content = target.read_text(encoding="utf-8", errors="replace")
    match_count = content.count(old_text)
    if match_count == 0:
        return f"Yeh text file me nahi mila:\n{old_text}"
    if match_count > 1:
        return (
            f"Yeh text file me {match_count} jagah match ho raha hai — "
            "zyada specific text do taaki sirf ek jagah match ho (jaise poori line copy karo)."
        )
    new_content = content.replace(old_text, new_text, 1)

    diff = "\n".join(difflib.unified_diff(
        content.splitlines(), new_content.splitlines(),
        fromfile=filename, tofile=filename, lineterm="",
    ))

    state.pending_edit = {"path": target, "new_content": new_content}
    return f"Yeh change hoga:\n{diff}\n\nConfirm karne ke liye 'haan confirm karo' bolo, cancel ke liye 'nahi cancel karo'."

def propose_apply_fix(browser, state) -> str:
    if state.project_root is None:
        return "Pehle project folder select karo."
    if not state.last_command:
        return "Pehle koi command run karo jiska error fix karna hai."

    blocks = browser.read_latest_code_blocks(state.last_ai_service)
    if not blocks:
        return "AI ke jawab me mujhe koi code block nahi mila."

    # Check if the AI told us WHICH file this code is for ("FILE: xyz.py").
    # Case-insensitive, and tolerant of markdown formatting (**FILE:** `x.py`).
    response_text = browser.read_latest_response(state.last_ai_service)
    file_marker = re.search(r"(?i)file:?\**\s*`?(\S+?\.py)`?", response_text)
    if file_marker:
        filename = file_marker.group(1)
    else:
        # No explicit marker — DON'T guess which file, that risks overwriting
        # the wrong one (as happened before). Ask the user instead.
        sent_files = ", ".join(sorted(state.files_sent_to_ai)) or "(koi nahi)"
        return (
            "AI ne yeh nahi bataya kaunsi file ke liye yeh code hai, isliye main "
            "guess nahi karunga (galat file overwrite ho sakti thi). Ab tak AI ko "
            f"yeh files pata hain: {sent_files}. 'response padho' karke khud check "
            "karo, phir specific bolo."
        )

    target = (state.project_root / filename).resolve()
    try:
        target.relative_to(state.project_root)
    except ValueError:
        return "Yeh file project folder se bahar hai."
    if not target.exists():
        return f"Yeh file nahi mili: {filename}"

    new_content = blocks[0]

    old_content = target.read_text(encoding="utf-8", errors="replace")

    diff = "\n".join(difflib.unified_diff(
        old_content.splitlines(), new_content.splitlines(),
        fromfile=filename, tofile=filename, lineterm="",
    ))

    state.pending_edit = {"path": target, "new_content": new_content}
    return f"Yeh fix apply hoga:\n{diff}\n\nConfirm karne ke liye 'haan confirm karo' bolo."

def propose_new_file(browser, state) -> str:
    if state.project_root is None:
        return "Pehle project folder select karo."

    response_text = browser.read_latest_response(state.last_ai_service)
    file_marker = re.search(r"(?i)file:?\**\s*`?(\S+?\.py)`?", response_text)
    if not file_marker:
        return "AI ne file ka naam nahi bataya. 'response padho' karke khud check karo."
    filename = file_marker.group(1)

    blocks = browser.read_latest_code_blocks(state.last_ai_service)
    if not blocks:
        return "AI ke jawab me mujhe koi code block nahi mila."
    new_content = blocks[0]

    target = (state.project_root / filename).resolve()
    try:
        target.relative_to(state.project_root)
    except ValueError:
        return "Yeh file project folder se bahar hai."

    if target.exists():
        old_content = target.read_text(encoding="utf-8", errors="replace")
        diff = "\n".join(difflib.unified_diff(
            old_content.splitlines(), new_content.splitlines(),
            fromfile=filename, tofile=filename, lineterm="",
        ))
        preview = f"Yeh file already exist karti hai, yeh change hoga:\n{diff}"
    else:
        preview = f"Yeh NAYI file banegi: {filename}\n\n{new_content[:500]}"

    state.pending_edit = {"path": target, "new_content": new_content, "is_new_file": not target.exists()}
    return f"{preview}\n\nConfirm karne ke liye 'haan confirm karo' bolo."