"""
Phase 3, step 1: selecting a project folder and listing its files.

Nothing in this file writes, edits, or deletes anything — it only reads.
"""
import logging
from pathlib import Path

logger = logging.getLogger("voice_agent.fileops")

_IGNORE_DIR_NAMES = {".git", "node_modules", "venv", "__pycache__", ".venv", "dist", "build"}


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