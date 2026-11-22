"""Records the desktop pitch clips: web UI, Discord bot and Chrome extension, each with its own case.

Needs the web dev server on :5173 (proxying the API on :8000) and a built extension
(`pnpm build` in channels/chrome_extension).

    uv run --with playwright python docs/design/demo/pitch/record_desktop.py <out_dir>

Writes web.mp4, discord.mp4 and extension.mp4 (1440x900).
"""

import json
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright

from screencast import ScreencastRecorder

API_URL = "http://localhost:5173"
PITCH_DIR = Path(__file__).parent.resolve()
REPO_DIR = PITCH_DIR.parents[3]
DISCORD_BOT_DIR = REPO_DIR / "channels" / "discord_bot"
EXTENSION_DIST = REPO_DIR / "channels" / "chrome_extension" / "dist"
OUT_DIR = Path(sys.argv[1])
VIEWPORT = {"width": 1440, "height": 900}
SIZE = (VIEWPORT["width"], VIEWPORT["height"])
WEB_CLAIM = (
    "Inflacja w Polsce spadła do 4,3 proc. w kwietniu 2025 r. z poziomu ponad 18 proc., "
    "który utrzymywał się jeszcze w momencie zaprzysiężenia rządu Donalda Tuska."
)
DISCORD_CLAIM = (
    "Rząd przyjął projekt zamrożenia cen gazu na 2027 rok. "
    "Maksymalna cena dla gospodarstw domowych ma wynieść 197,29 zł/MWh."
)
EXTENSION_CLAIM = "W Gdyni otwarto podmorski tunel samochodowy do Szwecji."
CURSOR_JS = """
document.addEventListener('DOMContentLoaded', () => {
  const cursor = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  cursor.setAttribute('viewBox', '0 0 22 30');
  cursor.style.cssText = 'position:fixed;z-index:99999;width:22px;height:30px;pointer-events:none;left:-40px;top:-40px';
  cursor.innerHTML = '<path d="M2 2v22l6-6 4 9 4-2-4-9h8z" fill="#fff" stroke="#202124" stroke-width="1.6" stroke-linejoin="round"/>';
  document.body.appendChild(cursor);
  document.addEventListener('mousemove', e => { cursor.style.left = e.clientX + 'px'; cursor.style.top = e.clientY + 'px'; });
});
"""


def get_check_result(channel: str, text: str) -> dict:
    """Warms the API's result cache, so each recorded check answers at once."""
    body = json.dumps(
        {"channel": channel, "session_id": "demo-recording-0001", "input": {"type": "text", "text": text}}
    ).encode()
    request = urllib.request.Request(
        f"{API_URL}/v1/checks", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        result = json.load(response)
    print(f"{channel}: {result['status']} {[claim['verdict'] for claim in result['claims']]}")
    return result


def get_discord_embeds(result: dict) -> list:
    """Renders the result with the bot's own renderer, so the clip shows exactly what the bot posts."""
    import subprocess

    script = (
        "import json, sys\n"
        "from prawdowid_discord.render import get_result_embeds\n"
        "result = json.load(sys.stdin)\n"
        "messages = get_result_embeds(result, 'https://prawdowid.example')\n"
        "print(json.dumps([[embed.to_dict() for embed in message] for message in messages]))\n"
    )
    completed = subprocess.run(
        ["uv", "run", "--project", str(DISCORD_BOT_DIR), "python", "-c", script],
        input=json.dumps(result), capture_output=True, text=True, check=True, cwd=DISCORD_BOT_DIR,
    )
    return json.loads(completed.stdout)


def move_and_click(page: Page, selector: str) -> None:
    target = page.locator(selector).first
    box = target.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=20)
        page.wait_for_timeout(200)
    target.click()


def smooth_scroll(page: Page, distance: int, steps: int = 30) -> None:
    for _ in range(steps):
        page.mouse.wheel(0, distance / steps)
        page.wait_for_timeout(16)


def record_web(context: BrowserContext) -> None:
    page = context.new_page()
    page.goto(API_URL)
    page.evaluate("localStorage.setItem('prawdowid.locale', 'pl')")
    page.reload()
    page.wait_for_selector("textarea")
    page.evaluate("document.fonts.ready")
    page.mouse.move(900, 700)
    recorder = ScreencastRecorder(page, OUT_DIR / "web-frames", SIZE)
    recorder.start()
    page.wait_for_timeout(800)
    recorder.mark_start()
    move_and_click(page, "textarea")
    page.keyboard.type(WEB_CLAIM, delay=10)
    page.wait_for_timeout(400)
    count = page.locator("article").count()
    move_and_click(page, "button[type=submit]")
    page.wait_for_function(f"document.querySelectorAll('article').length > {count}", timeout=240_000)
    page.wait_for_timeout(600)
    page.evaluate(
        "const items = document.querySelectorAll('main > div > ol[aria-label] > li');"
        "items[items.length - 1].scrollIntoView({ behavior: 'smooth', block: 'start' })"
    )
    page.wait_for_timeout(2600)
    for _ in range(3):
        smooth_scroll(page, 300)
        page.wait_for_timeout(1500)
    recorder.stop(page, OUT_DIR / "web.mp4")
    page.close()


def record_discord(context: BrowserContext, embeds: list) -> None:
    page = context.new_page()
    page.add_init_script(f"window.EMBEDS = {json.dumps(embeds)}")
    page.goto((PITCH_DIR / "discord_stage.html").as_uri())
    page.evaluate("document.fonts.ready")
    recorder = ScreencastRecorder(page, OUT_DIR / "discord-frames", SIZE)
    recorder.start()
    page.wait_for_timeout(600)
    recorder.mark_start()
    page.evaluate("claim => stage.run(claim)", DISCORD_CLAIM)
    page.wait_for_timeout(2800)
    page.evaluate("stage.scrollToBottom()")
    page.wait_for_timeout(2600)
    recorder.stop(page, OUT_DIR / "discord.mp4")
    page.close()


def record_extension(playwright) -> None:
    for name in ("extension_stage.html", "extension_stage.js"):
        shutil.copy(PITCH_DIR / name, EXTENSION_DIST / name)
    try:
        context = playwright.chromium.launch_persistent_context(
            tempfile.mkdtemp(), channel="chromium", headless=True, viewport=VIEWPORT,
            args=[f"--disable-extensions-except={EXTENSION_DIST}", f"--load-extension={EXTENSION_DIST}"],
        )
        worker = context.service_workers[0] if context.service_workers else context.wait_for_event("serviceworker")
        extension_id = worker.url.split("/")[2]
        page = context.new_page()
        page.goto(f"chrome-extension://{extension_id}/extension_stage.html")
        page.evaluate("document.fonts.ready")
        recorder = ScreencastRecorder(page, OUT_DIR / "extension-frames", SIZE)
        recorder.start()
        page.wait_for_timeout(600)
        recorder.mark_start()
        page.evaluate("claim => stage.run(claim)", EXTENSION_CLAIM)
        deadline = time.monotonic() + 120
        while not page.evaluate("stage.isResultShown()"):
            if time.monotonic() > deadline:
                raise TimeoutError("extension popup never showed a result")
            page.wait_for_timeout(200)
        page.wait_for_timeout(4200)
        recorder.stop(page, OUT_DIR / "extension.mp4")
        context.close()
    finally:
        for name in ("extension_stage.html", "extension_stage.js"):
            (EXTENSION_DIST / name).unlink(missing_ok=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    get_check_result("web", WEB_CLAIM)
    embeds = get_discord_embeds(get_check_result("discord", DISCORD_CLAIM))
    get_check_result("browser_extension", EXTENSION_CLAIM)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, locale="pl-PL")
        context.add_init_script(CURSOR_JS)
        record_web(context)
        record_discord(context, embeds)
        browser.close()
        record_extension(playwright)


if __name__ == "__main__":
    main()
