"""
Phase 3: automatic Git backup before any file edit is applied.

Before writing a confirmed edit to disk, we commit the file's CURRENT
(pre-edit) state to Git first — so there's always a restore point. If the
project folder isn't a Git repo, or there's nothing to commit, we say so
but never block the edit because of it.
"""
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("voice_agent.gitbackup")


def backup_file(project_root: Path, file_path: Path) -> str:
    rel_path = file_path.relative_to(project_root)

    def run(args):
        return subprocess.run(
            ["git", "-C", str(project_root)] + args,
            capture_output=True, text=True,
        )

    check = run(["rev-parse", "--is-inside-work-tree"])
    if check.returncode != 0:
        return "(Git repo nahi mila, backup skip kiya)"

    add_result = run(["add", str(rel_path)])
    if add_result.returncode != 0:
        logger.error("git add failed: %s", add_result.stderr)
        return f"(Backup me dikkat: {add_result.stderr.strip()})"

    commit_result = run(["commit", "-m", f"Auto-backup before edit: {rel_path}"])
    if commit_result.returncode != 0:
        combined = (commit_result.stdout + commit_result.stderr).lower()
        if "nothing to commit" in combined or "no changes added to commit" in combined:
            return "(Pehle se hi committed hai, naya backup ki zarurat nahi)"
        logger.error(
            "git commit failed (code=%s) stdout=%r stderr=%r",
            commit_result.returncode, commit_result.stdout, commit_result.stderr,
        )
        return f"(Backup commit nahi hua — stdout: {commit_result.stdout.strip()!r} stderr: {commit_result.stderr.strip()!r})"

    logger.info("Backed up %s before edit", rel_path)
    return "(Backup commit ho gaya)"