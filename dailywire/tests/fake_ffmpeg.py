"""Stand-ins for ffmpeg and ffprobe, installed on PATH by the audio tests.

The convention that makes assertions exact: one byte of file is one millisecond
of audio. `anullsrc -t N` writes N*1000 bytes; a concat writes the sum of its
inputs' sizes; ffprobe reports size/1000 seconds. Chapter arithmetic in
audio.narrate can then be checked to the millisecond without real audio.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

FFMPEG = '''#!/usr/bin/env python3
import re, sys
from pathlib import Path

args = sys.argv[1:]
stderr = sys.stderr

def value_after(flag):
    return args[args.index(flag) + 1] if flag in args else None

# Measurement pass: print a loudnorm JSON block and write nothing.
if "null" in args and "-f" in args:
    idx = [i for i, a in enumerate(args) if a == "-f"]
    if any(args[i + 1] == "null" for i in idx):
        stderr.write("""[Parsed_loudnorm_0 @ 0x1]
{
\t"input_i" : "-21.28",
\t"input_tp" : "-4.51",
\t"input_lra" : "6.20",
\t"input_thresh" : "-31.51",
\t"target_offset" : "0.02"
}
""")
        sys.exit(0)

out = args[-1]
if out == "-":
    sys.exit(0)

source = value_after("-i")
size = 0
if source and "anullsrc" in source:
    duration = float(value_after("-t") or 1.0)
    size = int(round(duration * 1000))
elif source:
    listing = Path(source)
    if listing.exists():
        for line in listing.read_text().splitlines():
            m = re.match(r"file '(.*)'$", line.strip())
            if m:
                path = Path(m.group(1).replace(r"'\\''", "'"))
                if path.exists():
                    size += path.stat().st_size

# MP3 outputs get real MPEG-1 Layer III frame headers so that mutagen can
# parse and tag the file; the byte count still equals the intended duration.
if out.endswith(".mp3"):
    frame = bytes([0xFF, 0xFB, 0x90, 0x00]) + b"\\0" * 413
    payload = (frame * (size // len(frame) + 2))[:size]
else:
    payload = b"\\0" * size

Path(out).write_bytes(payload)
sys.exit(0)
'''

FFPROBE = '''#!/usr/bin/env python3
import sys
from pathlib import Path

path = Path(sys.argv[-1])
if not path.exists():
    sys.stderr.write("no such file\\n")
    sys.exit(1)
print(path.stat().st_size / 1000.0)
'''


def install(directory: Path) -> Path:
    """Write the fake binaries into `directory` and return it."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in (("ffmpeg", FFMPEG), ("ffprobe", FFPROBE)):
        path = directory / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return directory


def prepend_to_path(directory: Path, monkeypatch) -> None:
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
