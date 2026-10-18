"""
One-off diagnostic: connects to your already-running debug Chrome, finds the
chatgpt.com (or claude.ai) tab, and prints what's actually on the page right
now — so we can see why the input/response selectors aren't matching.

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
                print(">>> Yeh AI tab hai, iska detail nikaal raha hoon:\n")

                print("--- Full body text (first 3000 chars) ---")
                try:
                    body_text = page.inner_text("body")
                    print(body_text[:3000])
                except Exception as exc:
                    print(f"Body text fetch failed: {exc}")

                print("\n--- Input selectors ---")
                for sel in ["textarea", 'div[contenteditable="true"]', "#prompt-textarea", "input"]:
                    try:
                        count = page.locator(sel).count()
                        print(f"Selector {sel!r}: {count} element(s) found")
                    except Exception as exc:
                        print(f"Selector {sel!r}: error {exc}")

                print("\n--- Playwright text-engine search for the reply ---")
                # Playwright's own text matcher is resilient to text split
                # across multiple nested <span> elements, unlike a plain
                # DOM textContent search.
                try:
                    found = page.get_by_text("4", exact=False).all()
                    print(f"Elements whose accessible text includes '4': {len(found)}")
                    for el in found[:5]:
                        try:
                            tag = el.evaluate("e => e.tagName")
                            cls = el.evaluate("e => e.className")
                            testid = el.evaluate("e => e.getAttribute('data-testid')")
                            print(f"  tag={tag} class={cls!r} data-testid={testid!r} text={el.inner_text()[:80]!r}")
                        except Exception as exc:
                            print(f"  (element inspect failed: {exc})")
                except Exception as exc:
                    print(f"get_by_text search failed: {exc}")
                print("\n--- Climbing up from the reply text to find its wrapper ---")
                try:
                    found = page.get_by_text("4", exact=False).all()
                    if found:
                        el = found[-1]
                        chain = el.evaluate(
                            """
                            (node) => {
                              let el = node;
                              const chain = [];
                              for (let i = 0; i < 8 && el; i++) {
                                chain.push({
                                  tag: el.tagName,
                                  id: el.id || null,
                                  cls: (el.className || '').toString().slice(0, 80),
                                  testid: el.getAttribute ? el.getAttribute('data-testid') : null,
                                  textLen: el.textContent ? el.textContent.length : 0
                                });
                                el = el.parentElement;
                              }
                              return chain;
                            }
                            """
                        )
                        for level, c in enumerate(chain):
                            print(f"  level {level}: {c}")
                except Exception as exc:
                    print(f"ancestor walk failed: {exc}")

                print("\n--- Climbing up from code text to find the code block wrapper ---")
                try:
                    found = page.get_by_text("reversed_text", exact=False).all()
                    print(f"Elements containing 'reversed_text': {len(found)}")
                    if found:
                        el = found[0]
                        chain = el.evaluate(
                            """
                            (node) => {
                              let el = node;
                              const chain = [];
                              for (let i = 0; i < 10 && el; i++) {
                                chain.push({
                                  tag: el.tagName,
                                  cls: (el.className || '').toString().slice(0, 80),
                                  testid: el.getAttribute ? el.getAttribute('data-testid') : null,
                                  textLen: el.textContent ? el.textContent.length : 0
                                });
                                el = el.parentElement;
                              }
                              return chain;
                            }
                            """
                        )
                        for level, c in enumerate(chain):
                            print(f"  level {level}: {c}")
                except Exception as exc:
                    print(f"code wrapper climb failed: {exc}")
                print("\n--- Elements near the bottom of the conversation area ---")
                try:
                    # Grab the last several DIVs that have some visible text,
                    # deepest-first, to see what structure actually holds replies.
                    candidates = page.evaluate(
                        """
                        () => {
                          const all = Array.from(document.querySelectorAll('div, p, span'));
                          const withText = all.filter(e => e.textContent && e.textContent.trim().length > 0 && e.children.length === 0);
                          return withText.slice(-15).map(e => ({
                            tag: e.tagName,
                            cls: (e.className || '').toString().slice(0, 50),
                            text: e.textContent.trim().slice(0, 60)
                          }));
                        }
                        """
                    )
                    for c in candidates:
                        print(c)
                except Exception as exc:
                    print(f"bottom-elements scan failed: {exc}")
            print()


if __name__ == "__main__":
    main()