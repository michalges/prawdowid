"""Turns record.py output into demo.mp4, playing each model-wait segment 20x faster.

    python3 docs/design/demo/make_video.py <record_out_dir> <output.mp4>
"""

import json
import subprocess
import sys
from pathlib import Path

WAIT_SPEEDUP = 20

record_dir, output = Path(sys.argv[1]), sys.argv[2]
webm = next(record_dir.glob("*.webm"))
segments = json.loads((record_dir / "marks.json").read_text())

parts: list[str] = []
cursor = 0.0
for index, (start, end) in enumerate(segments):
    parts.append(f"[0:v]trim={cursor}:{start},setpts=PTS-STARTPTS[n{index}]")
    parts.append(f"[0:v]trim={start}:{end},setpts=(PTS-STARTPTS)/{WAIT_SPEEDUP}[w{index}]")
    cursor = end
parts.append(f"[0:v]trim=start={cursor},setpts=PTS-STARTPTS[tail]")
labels = "".join(f"[n{i}][w{i}]" for i in range(len(segments))) + "[tail]"
count = 2 * len(segments) + 1
parts.append(f"{labels}concat=n={count}:v=1:a=0,fps=30,format=yuv420p[v]")

subprocess.run(
    [
        "ffmpeg", "-y", "-v", "error", "-i", str(webm),
        "-filter_complex", ";".join(parts), "-map", "[v]",
        "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-movflags", "+faststart", output,
    ],
    check=True,
)
