"""
Entry point — Phase 1 (voice + safe local commands) + Phase 2 (Chrome/AI commands).

Two input modes:
  - voice (default): mic -> speech-to-text -> command
  - text: type the command instead (no mic needed at all)

Switch modes:
  python main.py            # voice (or whatever INPUT_MODE says in .env)
  python main.py --text     # force text mode for this run
  python main.py --voice    # force voice mode for this run
"""
import logging
import sys

import config
from core import browser as browser_module
from core import commands, intent, tts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOGS_DIR / "session.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("voice_agent.main")

_SIMPLE_DISPATCH = {
    "TIME": lambda state: commands.handle_time(),
    "OPEN_NOTEPAD": lambda state: commands.handle_open_notepad(),
    "OPEN_CALCULATOR": lambda state: commands.handle_open_calculator(),
    "PAUSE": lambda state: commands.handle_pause(state),
    "RESUME": lambda state: commands.handle_resume(state),
    "STOP": lambda state: commands.handle_stop(state),
    "STATUS": lambda state: commands.handle_status(state),
    "LIST_FILES": lambda state: commands.handle_list_files(state),
}
_BROWSER_INTENTS = {"ASK_AI", "READ_RESPONSE", "COPY_CODE"}


def _resolve_input_mode():
    if "--text" in sys.argv:
        return "text"
    if "--voice" in sys.argv:
        return "voice"
    return config.INPUT_MODE


def _get_listen_function(mode):
    if mode == "text":
        from core import text_input
        return text_input.get_text_command
    from core import stt
    return stt.listen_and_transcribe


class _BrowserHolder:
    def __init__(self):
        self.controller = None

    def get_connected(self):
        if self.controller is None:
            self.controller = browser_module.BrowserController()
            self.controller.connect()
        return self.controller

    def close(self):
        if self.controller is not None:
            self.controller.close()


def _handle_browser_intent(parsed, state, holder):
    try:
        browser = holder.get_connected()
    except browser_module.BrowserAutomationError as exc:
        return str(exc)

    if parsed.name == "ASK_AI":
        return commands.handle_ask_ai(browser, state, parsed.service, parsed.payload)
    if parsed.name == "READ_RESPONSE":
        return commands.handle_read_response(browser, state)
    if parsed.name == "COPY_CODE":
        return commands.handle_copy_code(browser, state)
    return commands.handle_unknown(parsed.raw_text)


def _dispatch(parsed, state, holder):
    if parsed.name == "UNKNOWN":
        return commands.handle_unknown(parsed.raw_text)
    if parsed.name == "EMPTY":
        return commands.handle_empty()
    if parsed.name == "PROJECT_OPEN":
        return commands.handle_project_open(state, parsed.payload)
    if parsed.name in _BROWSER_INTENTS:
        return _handle_browser_intent(parsed, state, holder)
    if parsed.name in _SIMPLE_DISPATCH:
        return _SIMPLE_DISPATCH[parsed.name](state)
    return commands.handle_unknown(parsed.raw_text)


def run():
    mode = _resolve_input_mode()
    listen = _get_listen_function(mode)

    state = commands.AgentState()
    holder = _BrowserHolder()
    backend = config.stt_backend()
    logger.info("Starting agent. Input mode: %s. STT backend: %s", mode, backend)

    greeting = "Voice agent shuru ho gaya hai. Main sun raha hoon." if mode == "voice" \
        else "Text agent shuru ho gaya hai. Command type karo."
    print(f"Agent: {greeting}")
    tts.speak(greeting)
    if mode == "voice" and backend == "free_fallback":
        logger.info("No GROQ_API_KEY set — using free Google Web Speech fallback.")

    while state.running:
        if state.paused:
            text = listen()
            parsed = intent.classify(text)
            if parsed.name in ("RESUME", "STOP"):
                reply = _dispatch(parsed, state, holder)
                print(f"Agent: {reply}")
                tts.speak(reply)
            continue

        text = listen()
        parsed = intent.classify(text)
        reply = _dispatch(parsed, state, holder)

        if reply:
            print(f"Agent: {reply}")
            tts.speak(reply)

    holder.close()
    logger.info("Agent stopped cleanly.")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nInterrupted — shutting down.")