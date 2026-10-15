"""
One-off diagnostic: connects to your already-running debug Chrome, finds the
chatgpt.com (or claude.ai) tab, and prints what's actually on the page right
now — so we can see why the input box selector isn't matching.

Run with:  python diagnose.py
"""
from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:9222"


def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            print(f"Chrome se connect NAHI ho paya: {exc}")
            return

        context = browser.contexts[0] if browser.contexts else None
        if context is None or not context.pages:
            print("Koi bhi tab khuli nahi mili is Chrome me.")
            return

        print(f"Total tabs open: {len(context.pages)}\n")
        for i, page in enumerate(context.pages):
            print(f"--- Tab {i} ---")
            print(f"URL: {page.url}")
            try:
                print(f"Title: {page.title()}")
            except Exception as exc:
                print(f"Title fetch failed: {exc}")

            if "chatgpt.com" in page.url or "claude.ai" in page.url:
                print(">>> Yeh AI tab hai, iska detail nikaal raha hoon:")
                try:
                    body_text = page.inner_text("body")
                    print("Body text (first 500 chars):")
                    print(body_text[:500])
                except Exception as exc:
                    print(f"Body text fetch failed: {exc}")

                # Check common input element types present on the page.
                for sel in ["textarea", 'div[contenteditable="true"]', "#prompt-textarea", "input"]:
                    try:
                        count = page.locator(sel).count()
                        print(f"Selector {sel!r}: {count} element(s) found")
                    except Exception as exc:
                        print(f"Selector {sel!r}: error {exc}")

                print("\n--- Response selector check ---")
                for sel in [
                    '[data-message-author-role="assistant"]',
                    '[data-message-author-role]',
                    '.markdown',
                    'div[data-testid^="conversation-turn"]',
                    'article',
                ]:
                    try:
                        count = page.locator(sel).count()
                        print(f"Selector {sel!r}: {count} element(s) found")
                        if count > 0:
                            last_text = page.locator(sel).last.inner_text()[:200]
                            print(f"  -> last element text: {last_text!r}")
                    except Exception as exc:
                        print(f"Selector {sel!r}: error {exc}")
            print()


if __name__ == "__main__":
    main()