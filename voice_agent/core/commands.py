"""
Phase 1 safe commands + Phase 2 browser-backed commands. Browser errors are
caught here and turned into a spoken explanation — never swallowed, never
reported as success when they weren't.
"""
import datetime
import logging
import subprocess

logger = logging.getLogger("voice_agent.commands")


class AgentState:
    def __init__(self):
        self.paused = False
        self.running = True
        self.last_ai_service = "claude"

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
    logger.info("Unrecognized command: %s", raw_text)
    return "Maaf kijiye, main samjha nahi. Phir se boliye."


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


def handle_copy_code(browser, state: AgentState) -> str:
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