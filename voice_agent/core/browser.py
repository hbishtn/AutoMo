"""
Phase 2: Chrome browser automation.

Connects to YOUR already-running Chrome via CDP. Never sees or stores your
password. Selectors for ChatGPT/Claude are fragile by nature — every method
here fails LOUDLY with a clear message instead of guessing.
"""
import logging
import re
import time

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
        "response_selector": 'div[class*="MarkdownRoot"]',
    },
}


class BrowserAutomationError(Exception):
    """Raised whenever a browser step can't be completed reliably."""


class BrowserController:
    def __init__(self):
        self._playwright = None
        self._browser = None

    def connect(self):
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            raise BrowserAutomationError(
                "Chrome se connect nahi ho paya. Pehle Chrome ko remote-debugging mode me "
                "khol, phir dobara try karo."
            ) from exc

    def _ensure_connected(self):
        if self._browser is None or not self._browser.is_connected():
            logger.info("Browser connection lost — reconnecting...")
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
            self.connect()

    def _get_or_open_tab(self, service):
        self._ensure_connected()
        cfg = _SITE_CONFIG[service]
        context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        for page in context.pages:
            if cfg["domain"] in page.url:
                return page
        page = context.new_page()
        page.goto(cfg["url"], wait_until="domcontentloaded")
        return page

    def start_new_chat(self, service):
        """Not called automatically — available if ever needed."""
        cfg = _SITE_CONFIG[service]
        page = self._get_or_open_tab(service)
        page.goto(cfg["url"], wait_until="domcontentloaded")

    def send_prompt(self, service, prompt_text):
        if service not in _SITE_CONFIG:
            raise BrowserAutomationError(f"'{service}' supported nahi hai (sirf claude/chatgpt).")
        cfg = _SITE_CONFIG[service]
        page = self._get_or_open_tab(service)

        input_box = None
        for sel in cfg["input_selectors"]:
            visible_sel = f"{sel}:visible"
            try:
                page.wait_for_selector(visible_sel, timeout=15000)
                # Real chat input is always the LAST visible match — a code
                # editor in a previous reply is ALSO contenteditable and
                # sits earlier in the page than the actual input box.
                input_box = page.locator(visible_sel).last
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

    def _get_last_response_locator(self, service, wait_seconds):
        cfg = _SITE_CONFIG[service]
        page = self._get_or_open_tab(service)

        try:
            page.wait_for_selector(cfg["response_selector"], timeout=wait_seconds * 1000, state="visible")
        except PWTimeout:
            raise BrowserAutomationError(
                f"{service} se {wait_seconds} second me koi response nahi mila — "
                "ho sakta hai abhi bhi type ho raha ho, ya layout badal gaya ho."
            )

        responses = page.locator(cfg["response_selector"])
        count = responses.count()
        if count == 0:
            raise BrowserAutomationError(f"{service} par koi response text nahi mila.")
        last = responses.nth(count - 1)

        # Streams word-by-word. Poll until text stops changing for 3 checks
        # in a row, for up to wait_seconds total — logging progress so it's
        # clear something IS happening, not stuck.
        previous = None
        stable_count = 0
        start = time.time()
        last_log = start
        while time.time() - start < wait_seconds:
            current = last.inner_text()
            if current == previous:
                stable_count += 1
                if stable_count >= 3:
                    break
            else:
                stable_count = 0
            previous = current
            if time.time() - last_log > 5:
                logger.info("Waiting for %s response to finish streaming... (%ds elapsed)",
                            service, int(time.time() - start))
                last_log = time.time()
            time.sleep(1)

        return last

    def read_latest_response(self, service, wait_seconds=60):
        if service not in _SITE_CONFIG:
            raise BrowserAutomationError(f"'{service}' supported nahi hai (sirf claude/chatgpt).")
        last = self._get_last_response_locator(service, wait_seconds)
        return last.inner_text().strip()

    def read_latest_code_blocks(self, service, wait_seconds=60):
        if service not in _SITE_CONFIG:
            raise BrowserAutomationError(f"'{service}' supported nahi hai (sirf claude/chatgpt).")
        last_response = self._get_last_response_locator(service, wait_seconds)
        page = self._get_or_open_tab(service)

        global_code = page.locator(".cm-content")
        if global_code.count() > 0:
            blocks = [global_code.last.inner_text().strip()]
        else:
            code_elements = last_response.locator("pre")
            blocks = [code_elements.nth(i).inner_text().strip() for i in range(code_elements.count())]
            if not blocks:
                blocks = extract_code_blocks(last_response.inner_text())

        return [b for b in blocks if b]

    def close(self):
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
            self._browser = None


def extract_code_blocks(text: str) -> list:
    return [block.strip() for block in re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)]