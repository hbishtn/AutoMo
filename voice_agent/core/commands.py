"""
Phase 1 safe commands + Phase 2 browser-backed commands + Phase 3 file ops.
"""
import datetime
import logging
import subprocess
import re
from pathlib import Path

logger = logging.getLogger("voice_agent.commands")


class AgentState:
    def __init__(self):
        self.paused = False
        self.running = True
        self.last_ai_service = "claude"
        self.project_root = None
        self.pending_edit = None
        self.last_command = None  # Phase 4: the last terminal command string that was run
        self.last_command_output = None  # Phase 4: its output (for error-fixing)
        self.files_sent_to_ai = set()  # Phase 4: filenames whose full content we've already sent in this chat

    def status_text(self):
        if not self.running:
            return "Agent is stopped."
        if self.paused:
            return "Agent is paused. Say resume to continue."
        return "Agent is running and listening."


def handle_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    return f"Abhi time hai {now}"


def handle_open_notepad():
    try:
        subprocess.Popen(["notepad.exe"])
        return "Notepad khol diya."
    except FileNotFoundError:
        logger.error("notepad.exe not found on PATH")
        return "Mujhe Notepad nahi mila. Yeh Windows par hi chalega."


def handle_open_calculator():
    try:
        subprocess.Popen(["calc.exe"])
        return "Calculator khol diya."
    except FileNotFoundError:
        logger.error("calc.exe not found on PATH")
        return "Mujhe Calculator nahi mila. Yeh Windows par hi chalega."


def handle_pause(state):
    state.paused = True
    return "Theek hai, main ruk gaya. Resume bolne par wapas sununga."


def handle_resume(state):
    state.paused = False
    return "Main wapas sun raha hoon."


def handle_stop(state):
    state.running = False
    return "Agent band ho raha hai. Alvida!"


def handle_status(state):
    return state.status_text()


def handle_unknown(raw_text):
    from core import chat

    logger.info("No specific command matched, trying normal chat: %s", raw_text)
    return chat.get_reply(raw_text)

def handle_empty():
    return ""


def handle_ask_ai(browser, state, service, prompt_text):
    if not prompt_text:
        return "Kya poochna hai, yeh bhi bolo. Jaise: Claude se pucho, python me list kaise banate hain"
    try:
        browser.send_prompt(service, prompt_text)
        state.last_ai_service = service
        return f"{service.capitalize()} ko bhej diya. Jawab aane par 'response padho' bolo."
    except Exception as exc:
        logger.error("ask_ai failed: %s", exc)
        return str(exc)


def handle_read_response(browser, state):
    try:
        import pyperclip

        text = browser.read_latest_response(state.last_ai_service)
        pyperclip.copy(text)
        preview = text[:200] + ("..." if len(text) > 200 else "")
        logger.info("Full response copied to clipboard (%d chars)", len(text))
        return f"Jawab clipboard me copy ho gaya. Shuru: {preview}"
    except Exception as exc:
        logger.error("read_response failed: %s", exc)
        return str(exc)


def handle_copy_code(browser, state):
    try:
        import pyperclip

        blocks = browser.read_latest_code_blocks(state.last_ai_service)
        if not blocks:
            return "Is jawab me mujhe koi code block nahi mila."
        pyperclip.copy("\n\n".join(blocks))
        return f"{len(blocks)} code block clipboard me copy kar diye."
    except Exception as exc:
        logger.error("copy_code failed: %s", exc)
        return str(exc)


def handle_project_open(state, raw_path):
    from core import fileops

    if not raw_path:
        return "Kaunsa folder kholna hai, poora path bhi bolo."
    return fileops.set_project(state, raw_path)


def handle_list_files(state):
    from core import fileops

    return fileops.list_files(state)

def handle_file_read(state, raw_name):
    from core import fileops

    return fileops.read_file(state, raw_name)

def handle_edit_propose(state, raw_command):
    from core import fileops

    return fileops.propose_edit(state, raw_command)


def handle_edit_confirm(state):
    from core import gitbackup

    if state.pending_edit is None:
        return "Koi pending edit nahi hai confirm karne ke liye."
    path = state.pending_edit["path"]
    new_content = state.pending_edit["new_content"]
    is_new_file = state.pending_edit.get("is_new_file", False)

    if is_new_file:
        # Nothing to back up yet — write first, THEN commit the new file.
        try:
            path.write_text(new_content, encoding="utf-8")
        except Exception as exc:
            logger.error("edit_confirm failed: %s", exc)
            return f"File save karte waqt error aaya: {exc}"
        backup_note = gitbackup.backup_file(state.project_root, path)
        state.pending_edit = None
        return f"{path.name} nayi file ban gayi. {backup_note}"

    backup_note = gitbackup.backup_file(state.project_root, path)
    try:
        path.write_text(new_content, encoding="utf-8")
    except Exception as exc:
        logger.error("edit_confirm failed: %s", exc)
        return f"File save karte waqt error aaya: {exc}"
    state.pending_edit = None
    return f"{path.name} save ho gayi. {backup_note}"


def handle_edit_cancel(state):
    if state.pending_edit is None:
        return "Koi pending edit nahi hai cancel karne ke liye."
    state.pending_edit = None
    return "Edit cancel kar diya, kuch save nahi hua."

def handle_run_command(state, raw_command):
    from core import terminal

    result = terminal.run_command(state, raw_command)
    state.last_command = raw_command
    state.last_command_output = result
    return result

def handle_fix_error(browser, state):
    if state.last_command_output is None:
        return "Abhi tak koi command run nahi hui, pehle 'command chalao' try karo."
    if "FAILED" not in state.last_command_output and "failed" not in state.last_command_output.lower():
        return "Pichla command successful tha, koi error nahi hai fix karne ko."

    file_content_note = ""
    # Find EVERY .py file mentioned in the traceback (via File "path", line N),
    # not just the one named on the command line — an ImportError points at
    # a DIFFERENT file than the one we ran, and AI needs that context too.
    traceback_files = re.findall(r'File "([^"]+\.py)"', state.last_command_output or "")
    command_match = re.search(r"(\S+\.py)", state.last_command or "")
    if command_match:
        traceback_files.append(command_match.group(1))

    seen_filenames = []
    for raw_path in traceback_files:
        try:
            fp = Path(raw_path).resolve()
        except Exception:  # noqa: BLE001
            continue
        if state.project_root is None:
            continue
        try:
            rel = fp.relative_to(state.project_root)
        except ValueError:
            continue  # outside project (e.g. a stdlib file) — skip
        rel_str = str(rel)
        if rel_str in seen_filenames or rel_str in state.files_sent_to_ai:
            continue
        if not fp.exists():
            continue
        seen_filenames.append(rel_str)
        content = fp.read_text(encoding="utf-8", errors="replace")
        file_content_note += f"\n\n--- {rel_str} ---\n```python\n{content}\n```"
        state.files_sent_to_ai.add(rel_str)

    if file_content_note:
        prompt = (
            f"Is error ko fix karo. Command tha: {state.last_command}\n\n"
            f"Error/output:\n{state.last_command_output}"
            f"{file_content_note}\n\n"
            "IMPORTANT FORMAT: jawab ka SABSE PEHLA word bilkul yeh hona chahiye: "
            "FILE: <exact filename.py> — us file ka naam jisme badlav karna hai "
            "(upar di gayi files me se). Uske turant baad, usi file ka poora "
            "corrected code do. Format example:\nFILE: helper.py\n```python\n...\n```"
        )
    else:
        prompt = (
            f"Yeh naya error aaya hai (files ka content tumhe pehle se pata hai is chat me): "
            f"{state.last_command_output}\n\n"
            "IMPORTANT FORMAT: jawab ka SABSE PEHLA word bilkul yeh hona chahiye: "
            "FILE: <exact filename.py>. Uske turant baad, usi file ka poora corrected "
            "code do."
        )
    try:
        browser.send_prompt("chatgpt", prompt)
        state.last_ai_service = "chatgpt"
        return "Error ChatGPT ko bhej diya fix karne ke liye. Jawab aane par 'response padho' ya 'code copy karo' bolo."
    except Exception as exc:  # noqa: BLE001
        logger.error("fix_error failed: %s", exc)
        return str(exc)


def handle_apply_fix(browser, state):
    from core import fileops

    return fileops.propose_apply_fix(browser, state)


def handle_auto_fix(browser, state):
    import time
    from core import fileops, terminal

    if not state.last_command:
        return "Pehle koi command run karo jiska error fix karna hai."

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        if "FAILED" not in (state.last_command_output or "") and "failed" not in (state.last_command_output or "").lower():
            return f"Command already successful hai, kuch fix karne ki zarurat nahi."

        logger.info("Auto-fix attempt %d/%d", attempt, max_attempts)

        file_content_note = ""
        traceback_files = re.findall(r'File "([^"]+\.py)"', state.last_command_output or "")
        command_match = re.search(r"(\S+\.py)", state.last_command or "")
        if command_match:
            traceback_files.append(command_match.group(1))

        seen_filenames = []
        for raw_path in traceback_files:
            try:
                fp = Path(raw_path).resolve()
            except Exception:  # noqa: BLE001
                continue
            if state.project_root is None:
                continue
            try:
                rel = fp.relative_to(state.project_root)
            except ValueError:
                continue
            rel_str = str(rel)
            if rel_str in seen_filenames or rel_str in state.files_sent_to_ai:
                continue
            if not fp.exists():
                continue
            seen_filenames.append(rel_str)
            content = fp.read_text(encoding="utf-8", errors="replace")
            file_content_note += f"\n\n--- {rel_str} ---\n```python\n{content}\n```"
            state.files_sent_to_ai.add(rel_str)

        if file_content_note:
            prompt = (
                f"Is error ko fix karo. Command tha: {state.last_command}\n\n"
                f"Error/output:\n{state.last_command_output}"
                f"{file_content_note}\n\n"
                "IMPORTANT FORMAT: jawab ka SABSE PEHLA word bilkul yeh hona chahiye: "
                "FILE: <exact filename.py> — us file ka naam jisme badlav karna hai "
                "(upar di gayi files me se). Uske turant baad, usi file ka poora "
                "corrected code do."
            )
        else:
            prompt = (
                f"Yeh naya error aaya hai (files ka content tumhe pehle se pata hai is chat me): "
                f"{state.last_command_output}\n\n"
                "IMPORTANT FORMAT: jawab ka SABSE PEHLA word bilkul yeh hona chahiye: "
                "FILE: <exact filename.py>. Uske turant baad, usi file ka poora corrected "
                "code do."
            )
        
        try:
            browser.send_prompt("chatgpt", prompt)
            state.last_ai_service = "chatgpt"
        except Exception as exc:  # noqa: BLE001
            return f"Attempt {attempt}: ChatGPT ko bhejne me error: {exc}"

        try:
            apply_result = fileops.propose_apply_fix(browser, state)
        except Exception as exc:  # noqa: BLE001
            logger.error("Attempt %d: propose_apply_fix failed: %s", attempt, exc)
            if attempt < max_attempts:
                continue
            return f"Attempt {attempt}: Chrome/AI se response nahi mila: {exc}"
        if "fix apply hoga" not in apply_result:
            return f"Attempt {attempt}: {apply_result}"

        if state.pending_edit is None:
            return f"Attempt {attempt}: edit propose nahi ho paya."
        path = state.pending_edit["path"]
        new_content = state.pending_edit["new_content"]
        from core import gitbackup
        gitbackup.backup_file(state.project_root, path)
        path.write_text(new_content, encoding="utf-8")
        state.pending_edit = None

        retest = terminal.run_command(state, state.last_command)
        state.last_command_output = retest
        logger.info("Attempt %d retest result: %s", attempt, "SUCCESS" if "success" in retest.lower() else "FAILED")

        if "success" in retest.lower():
            return f"Attempt {attempt} me fix ho gaya! {retest}"

    return f"{max_attempts} attempts ke baad bhi fix nahi hua. Aakhri error:\n{state.last_command_output}"

def handle_build_feature(browser, state, description):
    if state.project_root is None:
        return "Pehle project folder select karo."
    if not description:
        return "Kya banana hai, woh bhi bolo. Jaise: feature banao ek calculator jo do number add kare"

    prompt = (
        f"Mujhe yeh feature chahiye: {description}\n\n"
        "IMPORTANT FORMAT: jawab ka SABSE PEHLA word bilkul yeh hona chahiye: "
        "FILE: <filename.py> — naye file ka naam jo banana hai. Uske turant baad, "
        "us file ka poora Python code do. Sirf ek hi file banao, simple aur working rakho."
    )
    try:
        browser.send_prompt("chatgpt", prompt)
        state.last_ai_service = "chatgpt"
        return "ChatGPT ko feature-request bhej diya. Jawab aane par 'feature apply karo' bolo."
    except Exception as exc:  # noqa: BLE001
        logger.error("build_feature failed: %s", exc)
        return str(exc)

def handle_apply_feature(browser, state):
    from core import fileops

    try:
        return fileops.propose_new_file(browser, state)
    except Exception as exc:  # noqa: BLE001
        logger.error("apply_feature failed: %s", exc)
        return f"Feature apply karte waqt error aaya: {exc}"