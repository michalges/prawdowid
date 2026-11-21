"""Records a scripted walkthrough of the local web UI (vite on :5173, API on :8000).

    uv run --with playwright python docs/design/demo/record.py <out_dir>

Writes a .webm plus marks.json with the model-wait segments, which make_video.sh speeds up.
"""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE_URL = "http://localhost:5173"
OUT_DIR = Path(sys.argv[1])
PL_CLAIM = "Czy Wrocław był jedynym miastem w Polsce, w którym 65-latkowie jeździli komunikacją miejską za darmo?"
EN_CLAIM = "Was a general strike held in Italy on 20 November 2026?"
CURSOR_JS = """
const dot = document.createElement('div');
dot.style.cssText = 'position:fixed;z-index:99999;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;background:rgba(212,33,61,.35);border:2px solid #d4213d;pointer-events:none;transition:transform .15s;left:-50px;top:-50px';
document.addEventListener('DOMContentLoaded', () => document.body.appendChild(dot));
document.addEventListener('mousemove', e => { dot.style.left = e.clientX + 'px'; dot.style.top = e.clientY + 'px'; });
document.addEventListener('mousedown', () => dot.style.transform = 'scale(.7)');
document.addEventListener('mouseup', () => dot.style.transform = 'scale(1)');
"""
SCROLL_TO_LAST_EXCHANGE = (
    "const items = document.querySelectorAll('main > div > ol[aria-label] > li');"
    "items[items.length - 1].scrollIntoView({ behavior: 'smooth', block: 'start' })"
)

wait_segments: list[list[float]] = []
started_at = 0.0


def move_and_click(page: Page, selector: str) -> None:
    target = page.locator(selector).first
    box = target.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=25)
        page.wait_for_timeout(250)
    target.click()


def smooth_scroll(page: Page, distance: int, steps: int = 30, pause_ms: int = 35) -> None:
    for _ in range(steps):
        page.mouse.wheel(0, distance / steps)
        page.wait_for_timeout(pause_ms)


def read_result(page: Page) -> None:
    page.evaluate(SCROLL_TO_LAST_EXCHANGE)
    page.wait_for_timeout(3500)
    for distance in (320, 320, 320, 320):
        smooth_scroll(page, distance, steps=35)
        page.wait_for_timeout(2200)


def run_check(page: Page, text: str) -> None:
    move_and_click(page, "textarea")
    page.keyboard.type(text, delay=28)
    page.wait_for_timeout(500)
    count = page.locator("article").count()
    move_and_click(page, "button[type=submit]")
    wait_start = time.monotonic() - started_at + 1.0
    page.wait_for_function(f"document.querySelectorAll('article').length > {count}", timeout=240_000)
    wait_end = time.monotonic() - started_at - 0.3
    if wait_end > wait_start:
        wait_segments.append([wait_start, wait_end])
    page.wait_for_timeout(1200)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    context = browser.new_context(
        viewport={"width": 1280, "height": 760},
        locale="pl-PL",
        record_video_dir=str(OUT_DIR),
        record_video_size={"width": 1280, "height": 760},
    )
    context.add_init_script(CURSOR_JS)
    page = context.new_page()
    started_at = time.monotonic()
    page.goto(BASE_URL)
    page.evaluate("localStorage.setItem('prawdowid.locale', 'pl')")
    page.reload()
    page.wait_for_timeout(2000)

    run_check(page, PL_CLAIM)
    read_result(page)

    move_and_click(page, "header button[aria-expanded]")
    page.wait_for_timeout(700)
    move_and_click(page, "header ul button[lang=en]")
    page.wait_for_timeout(1200)
    run_check(page, EN_CLAIM)
    read_result(page)

    move_and_click(page, "header a[href='/zrodla']")
    page.wait_for_selector("h1", timeout=30_000)
    page.wait_for_timeout(2500)
    smooth_scroll(page, 700, steps=40)
    page.wait_for_timeout(2000)
    move_and_click(page, "header a[href='/discord']")
    page.wait_for_timeout(3500)

    (OUT_DIR / "marks.json").write_text(json.dumps(wait_segments))
    context.close()
    browser.close()
