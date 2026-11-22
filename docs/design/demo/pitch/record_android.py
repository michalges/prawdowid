"""Records phone-framed clips of the Prawdowid app (Expo web build) with animated Android share entry points.

Needs: web dev server on :5173 (proxying the API on :8000) and the Expo web build of mobile/ on :8081
started with EXPO_PUBLIC_API_URL=http://localhost:5173.

    uv run --with playwright python docs/design/demo/pitch/record_android.py <out_dir>

Writes <out_dir>/selection.mp4 (text-selection menu) and <out_dir>/share.mp4 (Share menu). Frames come from the Chrome
screencast at 1x: a device scale factor of 2 halves the iframe's innerWidth in Chromium.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import Frame, Page, sync_playwright

from screencast import ScreencastRecorder

API_URL = "http://localhost:5173"
APP_URL = "http://localhost:8081"
STAGE_PATH = Path(__file__).with_name("android_stage.html").resolve()
OUT_DIR = Path(sys.argv[1])
VIEWPORT = {"width": 600, "height": 1080}
SCALE = 1
SELECTION_CLAIM = "Wrocław był jedynym miastem w Polsce, w którym 65-latkowie jeździli komunikacją miejską za darmo."
SHARE_CLAIM = "Bułgaria przyjęła euro 1 stycznia 2026 r."
FONT_JS = """
document.addEventListener('DOMContentLoaded', () => {
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=block';
  document.head.appendChild(link);
});
"""


def warm_cache(text: str) -> None:
    """The API caches results per input, so the recorded check returns at once instead of after ~40 s."""
    body = json.dumps(
        {"channel": "mobile", "session_id": "demo-recording-0001", "input": {"type": "text", "text": text}}
    ).encode()
    request = urllib.request.Request(
        f"{API_URL}/v1/checks", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        result = json.load(response)
    print(f"warm: {result['status']} {[claim['verdict'] for claim in result['claims']]}")


def get_app_frame(page: Page) -> Frame:
    frame = page.frame_locator("#app-frame")
    frame.get_by_text("Sprawdź, co wyślemy").wait_for(timeout=60_000)
    app_frame = next(child for child in page.frames if child.url.startswith(APP_URL))
    app_frame.evaluate("document.fonts.ready")
    return app_frame


def tap_in_app(page: Page, app_frame: Frame, text: str) -> None:
    target = app_frame.get_by_role("button", name=text, exact=True).first
    box = target.bounding_box()
    if box:
        page.evaluate("([x, y]) => stage.tapAt(x, y)", [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
    target.click()
    page.evaluate("stage.hideTouch()")


def scroll_result(page: Page, app_frame: Frame) -> None:
    app_frame.get_by_text("Pokaż w przeglądarce").wait_for(state="attached", timeout=120_000)
    page.wait_for_timeout(2200)
    box = page.locator("#app-frame").bounding_box()
    if not box:
        return
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.6)
    for _ in range(3):
        for _ in range(30):
            page.mouse.wheel(0, 9)
            page.wait_for_timeout(16)
        page.wait_for_timeout(1700)


def record_flow(page: Page, name: str, layer: str, claim: str, flow: str) -> None:
    page.goto(STAGE_PATH.as_uri())
    page.evaluate("document.fonts.ready")
    page.evaluate(f"stage.showLayer('{layer}')")
    recorder = ScreencastRecorder(page, OUT_DIR / f"{name}-frames", (VIEWPORT["width"] * SCALE, VIEWPORT["height"] * SCALE))
    recorder.start()
    page.wait_for_timeout(500)
    query = urllib.parse.urlencode({"text": claim})
    page.evaluate(f"stage.loadApp('{APP_URL}/?{query}')")
    app_frame = get_app_frame(page)
    page.wait_for_timeout(500)
    recorder.mark_start()
    page.wait_for_timeout(1200)
    page.evaluate(f"stage.{flow}()")
    page.evaluate("stage.openApp()")
    page.wait_for_timeout(1800)
    tap_in_app(page, app_frame, "Sprawdź")
    try:
        scroll_result(page, app_frame)
    except Exception:
        page.screenshot(path=str(OUT_DIR / f"{name}-failure.png"))
        print(app_frame.evaluate("document.body.innerText")[:800])
        raise
    recorder.stop(page, OUT_DIR / f"{name}.mp4")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    warm_cache(SELECTION_CLAIM)
    warm_cache(SHARE_CLAIM)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE)
        context.add_init_script(FONT_JS)
        page = context.new_page()
        record_flow(page, "selection", "browser", SELECTION_CLAIM, "selectionFlow")
        record_flow(page, "share", "social", SHARE_CLAIM, "shareFlow")
        browser.close()


if __name__ == "__main__":
    main()
