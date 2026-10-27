"""
Phase 4, step 1: run a shell command inside the selected project folder
and capture its output. Just runs + shows output for now — AI-based error
fixing comes in a later step.
"""
import logging
import subprocess

logger = logging.getLogger("voice_agent.terminal")


def run_command(state, command: str, timeout: int = 30) -> str:
    if state.project_root is None:
        return "Pehle project folder select karo."
    if not command:
        return "Kya command chalani hai, woh bhi bolo."

    try:
        result = subprocess.run(
            command,
            cwd=state.project_root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Command {timeout} second me complete nahi hui, rok diya."
    except Exception as exc:  # noqa: BLE001
        logger.error("run_command failed: %s", exc)
        return f"Command chalane me error aaya: {exc}"

    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip()
    status = "SUCCESS" if result.returncode == 0 else f"FAILED (exit code {result.returncode})"
    logger.info("Ran command %r -> %s", command, status)

    if not output:
        return f"Command {status.lower()}. Koi output nahi aaya."
    return f"Command {status.lower()}.\n{output[:2000]}"