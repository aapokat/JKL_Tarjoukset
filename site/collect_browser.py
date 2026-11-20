#!/usr/bin/env python3
"""Collect K-Ruoka offers with a real browser (Playwright) into data/k-ruoka-snapshot.json.

K-Ruoka sits behind Cloudflare, so a plain script is refused. This opens k-ruoka.fi in Chromium
and runs collectors/k-ruoka.js inside the page, exactly as if you pasted it into the console.

    pip install playwright && python -m playwright install chromium
    python site/collect_browser.py            # headless
    python site/collect_browser.py --show     # visible window (helps if Cloudflare asks to verify)
    python site/collect_browser.py --show --edge   # the Edge already on Windows, no Chromium download needed

Works best from a home connection. In GitHub Actions it is tried too, but Cloudflare may block
datacenter addresses; then the previous snapshot is kept and the page shows its date.
"""
import json, sys, time
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "data" / "k-ruoka-snapshot.json"


def main(show=False, edge=False):
    from playwright.sync_api import sync_playwright
    stores = json.loads((HERE / "data" / "stores.json").read_text(encoding="utf-8"))["kruoka"]
    script = (HERE / "collectors" / "k-ruoka.js").read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not show, channel="msedge" if edge else None)
        page = browser.new_page(locale="fi-FI", user_agent=None)
        page.goto("https://www.k-ruoka.fi/kauppa/tarjoushaku", wait_until="domcontentloaded", timeout=90000)
        page.wait_for_function("[...document.scripts].some(s => /\\/assets\\/b-\\d+\\//.test(s.src))", timeout=90000)
        page.evaluate("s => { window.K_STORES = s; window.K_NO_DOWNLOAD = true; }", stores)
        page.add_script_tag(content=script)
        started = time.time()
        while time.time() - started < 75 * 60:
            state = page.evaluate("({done: !!window.K_RESULT, error: window.K_ERROR || '', progress: window.K_PROGRESS || null})")
            if state["error"]:
                raise SystemExit("K-Ruoka collector failed: " + state["error"])
            if state["done"]:
                break
            print("progress:", state["progress"], flush=True)
            time.sleep(15)
        else:
            raise SystemExit("K-Ruoka collector timed out")
        result = page.evaluate("window.K_RESULT")
        browser.close()
    if not result["offers"]:
        raise SystemExit("K-Ruoka returned no offers, keeping the previous snapshot")
    if result.get("failed"):   # keep the previous rows of stores that failed this time
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))["offers"]
            result["offers"] += [r for r in old if r[0] in set(result["failed"])]
            print("kept previous offers for", result["failed"])
        except Exception:
            pass
    OUT.write_text(json.dumps({"collected": result["collected"], "counts": result["counts"], "offers": result["offers"]},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(result["counts"])


if __name__ == "__main__":
    main("--show" in sys.argv, "--edge" in sys.argv)
