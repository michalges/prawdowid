"""Chrome screencast → H.264 clip. Frames arrive only when the page changes, so each frame keeps its real duration."""

import base64
import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import Page

FPS = 30


class ScreencastRecorder:
    def __init__(self, page: Page, frames_dir: Path, size: tuple[int, int]) -> None:
        self.frames_dir = frames_dir
        self.size = size
        self.frames: list[tuple[Path, float]] = []
        self.first_frame = 0
        self.session = page.context.new_cdp_session(page)
        self.session.on("Page.screencastFrame", self._save_frame)

    def _save_frame(self, event: dict) -> None:
        path = self.frames_dir / f"{len(self.frames):06d}.jpg"
        path.write_bytes(base64.b64decode(event["data"]))
        self.frames.append((path, event["metadata"]["timestamp"]))
        self.session.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})

    def start(self) -> None:
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        width, height = self.size
        self.session.send(
            "Page.startScreencast",
            {"format": "jpeg", "quality": 95, "maxWidth": width, "maxHeight": height, "everyNthFrame": 1},
        )

    def mark_start(self) -> None:
        """Frames before this point (setup) are dropped from the clip."""
        self.first_frame = len(self.frames)

    def stop(self, page: Page, output: Path) -> None:
        page.wait_for_timeout(300)
        stopped_at = time.time()
        self.session.send("Page.stopScreencast")
        frames = self.frames[max(self.first_frame - 1, 0) :]
        end_time = max(stopped_at, frames[-1][1] + 0.1)
        lines = []
        for index, (path, timestamp) in enumerate(frames):
            next_time = frames[index + 1][1] if index + 1 < len(frames) else end_time
            lines += [f"file '{path.name}'", f"duration {max(next_time - timestamp, 0.001):.4f}"]
        lines.append(f"file '{frames[-1][0].name}'")
        concat = self.frames_dir / "frames.txt"
        concat.write_text("\n".join(lines) + "\n")
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
                "-vf", f"fps={FPS},scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-movflags", "+faststart", str(output),
            ],
            check=True,
        )
        shutil.rmtree(self.frames_dir)
        print(f"wrote {output}")
