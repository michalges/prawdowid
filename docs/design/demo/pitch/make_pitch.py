"""Edits the recorded clips into a ~50 s horizontal, TikTok-style pitch (1920x1080).

    uv run --with playwright python docs/design/demo/pitch/make_pitch.py <clips_dir> <output.mp4>

<clips_dir> holds web.mp4, discord.mp4, extension.mp4 (record_desktop.py) and selection.mp4, share.mp4
(record_android.py). Captions, cards, backgrounds and the animated hook/outro are rendered from HTML, then
composed with ffmpeg: punch-in zoom on each result, slide-in captions, a segmented progress bar and slide cuts.
"""

import base64
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from screencast import ScreencastRecorder

CLIPS_DIR = Path(sys.argv[1])
OUTPUT = Path(sys.argv[2])
LOGO_PATH = Path(__file__).parents[2] / "logo" / "prawdowid-app-icon.svg"
LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()
WIDTH, HEIGHT, FPS = 1920, 1080, 30
TRANSITION = 0.35
CLIP_BOX = (600, 150, 1248, 780)
CORNER_RADIUS = 18
VERDICTS = {
    "potwierdzone": ("Potwierdzone", "✓", "#0b6e4f", "#e7f4ee"),
    "falszywe": ("Fałszywe", "✕", "#8a1538", "#fbe9ee"),
    "wprowadzajace_w_blad": ("Wprowadzające w błąd", "!", "#8a5300", "#fdf2d8"),
    "brak_wystarczajacych_dowodow": ("Brak wystarczających dowodów", "–", "#475467", "#eef0f3"),
}


@dataclass
class Zoom:
    start: float
    factor: float
    focus_x: float
    focus_y: float


@dataclass
class Scene:
    name: str
    kicker: str
    title: str
    note: str
    verdicts: list[str]
    duration: float
    clips: list[tuple[str, float]] = field(default_factory=list)
    zoom: Zoom | None = None


SCENES = [
    Scene(
        "web", "01 · Strona WWW", "Wklej tekst albo link.",
        "Rozbija wypowiedź na twierdzenia i pokazuje dosłowne cytaty ze źródeł.",
        ["wprowadzajace_w_blad"], 10.5, [("web.mp4", 1.45)], Zoom(4.6, 1.5, 0.5, 0.35),
    ),
    Scene(
        "discord", "02 · Bot na Discordzie", "/sprawdz tam, gdzie rozmawiasz.",
        "Ten sam wynik i te same źródła, prosto na kanale.",
        ["potwierdzone"], 8.4, [("discord.mp4", 1.35)], Zoom(4.4, 1.45, 0.75, 0.75),
    ),
    Scene(
        "extension", "03 · Rozszerzenie Chrome", "Zaznacz. Prawy klik. Wynik.",
        "Gdy źródła milczą, mówimy to wprost. Nie zgadujemy.",
        ["brak_wystarczajacych_dowodow"], 9.6, [("extension.mp4", 1.5)], Zoom(5.6, 1.75, 1.0, 0.45),
    ),
    Scene(
        "mobile", "04 · Aplikacja na Androida", "Udostępnij albo zaznacz tekst.",
        "Z każdej aplikacji: menu „Udostępnij” i menu zaznaczenia tekstu.",
        ["falszywe", "potwierdzone"], 12.8, [("selection.mp4", 1.6), ("share.mp4", 1.42)],
    ),
]
HOOK_DURATION = 3.2
OUTRO_DURATION = 4.0

BASE_CSS = """
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@500;600;700&display=block" rel="stylesheet">
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; font-family: 'IBM Plex Sans', sans-serif; }
  .bg { position: absolute; inset: 0; background:
    radial-gradient(55% 60% at 70% 50%, rgba(212, 33, 61, .20), transparent 70%),
    radial-gradient(40% 50% at 10% 90%, rgba(31, 95, 174, .18), transparent 70%), #16181d; }
</style>
"""


def get_verdict_chips(verdicts: list[str]) -> str:
    chips = []
    for verdict in verdicts:
        label, symbol, fg, bg = VERDICTS[verdict]
        chips.append(
            f'<div class="chip" style="color:{fg};background:{bg}">'
            f'<span class="dot" style="background:{fg}">{symbol}</span>{label}</div>'
        )
    return "".join(chips)


def render_caption(page: Page, scene: Scene, path: Path) -> None:
    page.set_content(f"""{BASE_CSS}
<style>
  html, body {{ width: 470px; height: 760px; background: transparent; }}
  .kicker {{ display: inline-block; font-weight: 700; font-size: 26px; color: #fff; background: #d4213d;
    padding: 6px 16px; border-radius: 8px; letter-spacing: .02em; }}
  h1 {{ font-size: 64px; line-height: 72px; color: #fff; margin: 28px 0 22px; font-weight: 700; }}
  p {{ font-size: 28px; line-height: 40px; color: #c7cad1; margin: 0 0 30px; font-weight: 500; }}
  .chip {{ display: inline-flex; align-items: center; gap: 12px; font-weight: 700; font-size: 25px;
    padding: 8px 20px 8px 8px; border-radius: 999px; margin: 0 10px 12px 0; }}
  .dot {{ width: 34px; height: 34px; border-radius: 50%; color: #fff; display: grid; place-items: center; font-size: 20px; }}
</style>
<div class="kicker">{scene.kicker}</div><h1>{scene.title}</h1><p>{scene.note}</p>{get_verdict_chips(scene.verdicts)}""")
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(path), omit_background=True, clip={"x": 0, "y": 0, "width": 470, "height": 760})


def render_background(page: Page, path: Path, with_clip_shadow: bool) -> None:
    x, y, width, height = CLIP_BOX
    shadow = (
        f'<div style="position:absolute;left:{x}px;top:{y}px;width:{width}px;height:{height}px;'
        f'border-radius:{CORNER_RADIUS}px;box-shadow:0 30px 80px rgba(0,0,0,.55),0 0 0 2px rgba(255,255,255,.08)"></div>'
        if with_clip_shadow
        else ""
    )
    page.set_content(f'{BASE_CSS}<div class="bg"></div>{shadow}')
    page.screenshot(path=str(path))


def render_mask(page: Page, path: Path) -> None:
    _, _, width, height = CLIP_BOX
    page.set_content(
        f'<body style="margin:0;background:#000;width:{width}px;height:{height}px">'
        f'<div style="width:{width}px;height:{height}px;border-radius:{CORNER_RADIUS}px;background:#fff"></div></body>'
    )
    page.screenshot(path=str(path), clip={"x": 0, "y": 0, "width": width, "height": height})


HOOK_HTML = f"""{BASE_CSS}
<style>
  .center {{ position: absolute; inset: 0; display: grid; place-items: center; text-align: center; }}
  .line {{ font-size: 110px; font-weight: 700; color: #fff; opacity: 0; transform: scale(.6);
    animation: pop .32s cubic-bezier(.2,1.6,.4,1) forwards; }}
  .l1 {{ animation-delay: .15s; }} .l2 {{ animation-delay: .75s; }}
  .hl {{ background: #d4213d; padding: 0 22px; border-radius: 14px; }}
  .brand {{ position: absolute; inset: 0; display: grid; place-items: center; background: #16181d; opacity: 0;
    animation: show .25s ease 1.9s forwards; }}
  .brand div {{ display: flex; align-items: center; gap: 34px; font-size: 120px; font-weight: 700; color: #fff;
    transform: scale(.8); animation: pop .4s cubic-bezier(.2,1.6,.4,1) 1.95s forwards; }}
  .brand img {{ width: 150px; height: 150px; }}
  .brand p {{ position: absolute; top: 700px; font-size: 40px; color: #c7cad1; font-weight: 500; margin: 0;
    opacity: 0; animation: show .3s ease 2.3s forwards; }}
  @keyframes pop {{ to {{ opacity: 1; transform: scale(1); }} }}
  @keyframes show {{ to {{ opacity: 1; }} }}
</style>
<div class="bg"></div>
<div class="center"><div><div class="line l1">Widzisz newsa w sieci.</div>
<div class="line l2">Prawda czy <span class="hl">fejk?</span></div></div></div>
<div class="brand"><div><img src="{LOGO_URI}" alt="">Prawdowid</div>
<p>Sprawdza informacje w oficjalnych źródłach. Z cytatami.</p></div>
"""

OUTRO_HTML = f"""{BASE_CSS}
<style>
  .center {{ position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center;
    justify-content: center; gap: 36px; text-align: center; }}
  .row {{ display: flex; gap: 22px; }}
  .pill {{ font-size: 36px; font-weight: 700; color: #fff; padding: 14px 30px; border-radius: 999px;
    border: 3px solid rgba(255,255,255,.25); opacity: 0; transform: translateY(30px);
    animation: up .35s cubic-bezier(.2,1.4,.4,1) forwards; }}
  .pill:nth-child(1) {{ animation-delay: .1s; }} .pill:nth-child(2) {{ animation-delay: .25s; }}
  .pill:nth-child(3) {{ animation-delay: .4s; }} .pill:nth-child(4) {{ animation-delay: .55s; }}
  h1 {{ font-size: 92px; color: #fff; margin: 0; opacity: 0; animation: up .4s ease .9s forwards; transform: translateY(30px); }}
  .brand {{ display: flex; align-items: center; gap: 24px; font-size: 64px; font-weight: 700; color: #fff;
    opacity: 0; animation: up .4s ease 1.6s forwards; transform: translateY(30px); }}
  .brand img {{ width: 84px; height: 84px; }}
  .cta {{ font-size: 40px; color: #fff; background: #d4213d; padding: 12px 30px; border-radius: 12px; font-weight: 700;
    opacity: 0; animation: up .4s ease 2.1s forwards; transform: translateY(30px); }}
  @keyframes up {{ to {{ opacity: 1; transform: none; }} }}
</style>
<div class="bg"></div>
<div class="center">
  <div class="row"><div class="pill">Strona WWW</div><div class="pill">Discord</div>
  <div class="pill">Chrome</div><div class="pill">Android</div></div>
  <h1>Jedno API. Cztery kanały.</h1>
  <div class="brand"><img src="{LOGO_URI}" alt="">Prawdowid</div>
  <div class="cta">Sprawdź, zanim udostępnisz.</div>
</div>
"""


def record_card(page: Page, html: str, duration: float, output: Path, work_dir: Path) -> None:
    page.set_content("<body style='margin:0;background:#16181d'></body>")
    recorder = ScreencastRecorder(page, work_dir / f"{output.stem}-frames", (WIDTH, HEIGHT))
    recorder.start()
    page.wait_for_timeout(300)
    page.set_content(html)
    page.evaluate("document.fonts.ready")
    recorder.mark_start()
    page.wait_for_timeout(int(duration * 1000))
    recorder.stop(page, output)


def run_ffmpeg(arguments: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *arguments], check=True)


def get_zoom_filter(zoom: Zoom | None) -> str:
    _, _, width, height = CLIP_BOX
    if zoom is None:
        return f"scale={width}:{height}"
    progress = f"clip((in/{FPS}-{zoom.start})/0.45,0,1)"
    eased = f"({progress}*{progress}*(3-2*{progress}))"
    return (
        f"fps={FPS},zoompan=z='1+{zoom.factor - 1}*{eased}':x='(iw-iw/zoom)*{zoom.focus_x}'"
        f":y='(ih-ih/zoom)*{zoom.focus_y}':d=1:s={width}x{height}:fps={FPS}"
    )


def get_progress_filter(scene_index: int, input_label: str, output_label: str) -> str:
    """Four segments at the top; the current one fills during the scene (TikTok-style story bar)."""
    parts = []
    segment_width, gap, top = 452, 16, 28
    label = input_label
    for index in range(len(SCENES)):
        x = 48 + index * (segment_width + gap)
        if index < scene_index:
            fill = f"{segment_width}"
        elif index == scene_index:
            fill = f"{segment_width}*min(t/{SCENES[scene_index].duration},1)"
        else:
            fill = "0"
        parts.append(f"{label}drawbox=x={x}:y={top}:w={segment_width}:h=6:color=white@0.25:t=fill[p{index}a]")
        parts.append(f"[p{index}a]drawbox=x={x}:y={top}:w='{fill}':h=6:color=white:t=fill[p{index}b]")
        label = f"[p{index}b]"
    parts[-1] = parts[-1].replace(f"[p{len(SCENES) - 1}b]", output_label)
    return ";".join(parts)


def render_desktop_scene(scene: Scene, index: int, assets: Path, output: Path) -> None:
    clip_name, speed = scene.clips[0]
    x, y, _, _ = CLIP_BOX
    filters = [
        f"[1:v]setpts=PTS/{speed},tpad=stop_mode=clone:stop_duration=10,trim=duration={scene.duration},"
        f"{get_zoom_filter(scene.zoom)},format=yuva420p[clip]",
        "[2:v]format=gray[mask]",
        "[clip][mask]alphamerge[rounded]",
        f"[0:v][rounded]overlay={x}:{y}[withclip]",
        f"[3:v]format=rgba,fade=in:st=0:d=0.3:alpha=1[caption]",
        "[withclip][caption]overlay=x='if(lt(t,0.35),70-60*(1-t/0.35),70)':y=170[captioned]",
        get_progress_filter(index, "[captioned]", "[v]"),
    ]
    run_ffmpeg([
        "-loop", "1", "-t", str(scene.duration), "-i", str(assets / "bg-clip.png"),
        "-i", str(CLIPS_DIR / clip_name),
        "-loop", "1", "-t", str(scene.duration), "-i", str(assets / "mask.png"),
        "-loop", "1", "-t", str(scene.duration), "-i", str(assets / f"caption-{scene.name}.png"),
        "-filter_complex", ";".join(filters), "-map", "[v]", "-r", str(FPS),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", str(output),
    ])


def render_mobile_scene(scene: Scene, index: int, assets: Path, output: Path) -> None:
    """Two phones side by side: text-selection menu (left) and Share menu (right)."""
    (selection, selection_speed), (share, share_speed) = scene.clips
    phone_filter = "crop=480:960:60:60,scale=528:1056"
    filters = [
        f"[1:v]setpts=PTS/{selection_speed},tpad=stop_mode=clone:stop_duration=10,trim=duration={scene.duration},{phone_filter}[left]",
        f"[2:v]setpts=PTS/{share_speed},tpad=stop_mode=clone:stop_duration=10,trim=duration={scene.duration},{phone_filter}[right]",
        "[0:v][left]overlay=700:12[one]",
        "[one][right]overlay=1300:12[two]",
        f"[3:v]format=rgba,fade=in:st=0:d=0.3:alpha=1[caption]",
        "[two][caption]overlay=x='if(lt(t,0.35),70-60*(1-t/0.35),70)':y=170[captioned]",
        get_progress_filter(index, "[captioned]", "[v]"),
    ]
    run_ffmpeg([
        "-loop", "1", "-t", str(scene.duration), "-i", str(assets / "bg-plain.png"),
        "-i", str(CLIPS_DIR / selection), "-i", str(CLIPS_DIR / share),
        "-loop", "1", "-t", str(scene.duration), "-i", str(assets / f"caption-{scene.name}.png"),
        "-filter_complex", ";".join(filters), "-map", "[v]", "-r", str(FPS),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", str(output),
    ])


def join_with_transitions(parts: list[tuple[Path, float]], output: Path) -> None:
    inputs: list[str] = []
    for path, _ in parts:
        inputs += ["-i", str(path)]
    filters = [f"[{index}:v]fps={FPS},settb=AVTB,format=yuv420p[n{index}]" for index in range(len(parts))]
    label = "[n0]"
    elapsed = parts[0][1]
    for index in range(1, len(parts)):
        offset = elapsed - TRANSITION
        next_label = f"[x{index}]" if index < len(parts) - 1 else "[joined]"
        filters.append(
            f"{label}[n{index}]xfade=transition=smoothleft:duration={TRANSITION}:offset={offset:.3f}{next_label}"
        )
        label = next_label
        elapsed += parts[index][1] - TRANSITION
    filters.append("[joined]format=yuv420p[v]")
    run_ffmpeg([
        *inputs, "-filter_complex", ";".join(filters), "-map", "[v]", "-r", str(FPS),
        "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-movflags", "+faststart", str(output),
    ])
    print(f"wrote {output} ({elapsed:.1f} s)")


def main() -> None:
    work_dir = Path(tempfile.mkdtemp(prefix="pitch-work-", dir=OUTPUT.parent))
    assets = work_dir / "assets"
    assets.mkdir()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        render_background(page, assets / "bg-clip.png", with_clip_shadow=True)
        render_background(page, assets / "bg-plain.png", with_clip_shadow=False)
        render_mask(page, assets / "mask.png")
        for scene in SCENES:
            render_caption(page, scene, assets / f"caption-{scene.name}.png")
        record_card(page, HOOK_HTML, HOOK_DURATION, work_dir / "hook.mp4", work_dir)
        record_card(page, OUTRO_HTML, OUTRO_DURATION, work_dir / "outro.mp4", work_dir)
        browser.close()

    parts = [(work_dir / "hook.mp4", HOOK_DURATION)]
    for index, scene in enumerate(SCENES):
        output = work_dir / f"scene-{scene.name}.mp4"
        if scene.name == "mobile":
            render_mobile_scene(scene, index, assets, output)
        else:
            render_desktop_scene(scene, index, assets, output)
        parts.append((output, scene.duration))
    parts.append((work_dir / "outro.mp4", OUTRO_DURATION))
    join_with_transitions(parts, OUTPUT)


if __name__ == "__main__":
    main()
