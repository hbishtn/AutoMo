"""
Phase 2: Chrome browser automation.

IMPORTANT — how this stays safe:
This module connects to YOUR already-running Chrome over the Chrome
DevTools Protocol (CDP). It does NOT launch a separate/new browser and it
NEVER sees, asks for, or stores your Claude/ChatGPT password. You stay
logged in exactly as you already are in that Chrome window — Playwright
is just remote-controlling the tabs.

One-time setup each session: close all Chrome windows, then launch Chrome
with remote debugging enabled (exact command in README, "Phase 2 setup").
This agent then attaches to that running Chrome on localhost:9222.

If a selector below stops matching (site redesigned its UI), every method
here raises BrowserAutomationError with a clear message instead of
silently doing nothing or pretending it worked.
"""
import logging
import re

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

logger = logging.getLogger("voice_agent.browser")

CDP_URL = "http://localhost:9222"

_SITE_CONFIG = {
    "claude": {
        "url": "https://claude.ai/new",
        "domain": "claude.ai",
        "input_selectors": ['div[contenteditable="true"]', "textarea"],
        "submit_selectors": ['button[aria-label="Send Message"]', 'button[type="submit"]'],
        "response_selector": ".font-claude-message",
    },
    "chatgpt": {
        "url": "https://chatgpt.com/",
        "domain": "chatgpt.com",
        "input_selectors": ['div[contenteditable="true"]', "#prompt-textarea", "textarea"],
        "submit_selectors": ['button[data-testid="send-button"]', 'button[type="submit"]'],
        "response_selector": '[data-message-author-role="assistant"]',
    },
}


class BrowserAutomationError(Exception):
    """Raised whenever a browser step can't be completed reliably.
    Callers must speak/show this to the user — never swallow it."""


class BrowserController:
    def __init__(self):
        self._playwright = None
        self._browser = None

    def connect(self) -> None:
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            raise BrowserAutomationError(
                "Chrome se connect nahi ho paya. Pehle Chrome ko remote-debugging mode me "
                "khol (README ke 'Phase 2 setup' section me command hai), phir dobara try karo."
            ) from exc

    def _get_or_open_tab(self, service: str) -> Page:
        if self._browser is None:
            raise BrowserAutomationError("Browser connected nahi hai.")
        cfg = _SITE_CONFIG[service]
        context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        for page in context.pages:
            if cfg["domain"] in page.url:
                return page
        page = context.new_page()
        page.goto(cfg["url"], wait_until="domcontentloaded")
        return page

    def send_prompt(self, service: str, prompt_text: str) -> None:
        if service not in _SITE_CONFIG:
            raise BrowserAutomationError(f"'{service}' supported nahi hai (sirf claude/chatgpt).")
        cfg = _SITE_CONFIG[service]
        page = self._get_or_open_tab(service)

        input_box = None
        for sel in cfg["input_selectors"]:
            try:
                page.wait_for_selector(sel, timeout=3000)
                input_box = page.locator(sel).first
                break
            except PWTimeout:
                continue
        if input_box is None:
            raise BrowserAutomationError(
                f"{service} ka input box nahi mila — lagta hai website ka layout badal gaya hai. "
                "Main is wajah se ruk raha hoon, galat jagah type nahi karunga."
            )

        input_box.click()
        input_box.fill(prompt_text)

        submitted = False
        for sel in cfg["submit_selectors"]:
            try:
                page.locator(sel).first.click(timeout=2000)
                submitted = True
                break
            except Exception:
                continue
        if not submitted:
            input_box.press("Enter")

        logger.info("Prompt sent to %s: %s", service, prompt_text[:80])

    def read_latest_response(self, service: str, wait_seconds: int = 25) -> str:
        if service not in _SITE_CONFIG:
            raise BrowserAutomationError(f"'{service}' supported nahi hai (sirf claude/chatgpt).")
        cfg = _SITE_CONFIG[service]
        page = self._get_or_open_tab(service)

        try:
            page.wait_for_selector(cfg["response_selector"], timeout=wait_seconds * 1000)
        except PWTimeout:
            raise BrowserAutomationError(
                f"{service} se {wait_seconds} second me koi response nahi mila — "
                "ho sakta hai abhi bhi type ho raha ho, ya layout badal gaya ho."
            )

        responses = page.locator(cfg["response_selector"])
        count = responses.count()
        if count == 0:
            raise BrowserAutomationError(f"{service} par koi response text nahi mila.")
        return responses.nth(count - 1).inner_text().strip()

    def close(self) -> None:
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
            self._browser = None


def extract_code_blocks(text: str) -> list:
    return [block.strip() for block in re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)]