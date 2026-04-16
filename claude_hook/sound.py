import subprocess
from pathlib import Path

VOLUME_FILE = Path.home() / ".claude" / ".volume"
DEFAULT_VOLUME = 3

SOUNDS = dict(
    pop="/System/Library/Sounds/Pop.aiff",
    done=str(Path.home() / ".claude" / "done.aiff"),
)


def volume() -> int:
    if VOLUME_FILE.exists():
        return int(VOLUME_FILE.read_text().strip())
    return DEFAULT_VOLUME


def play(name: str):
    v = volume()
    if v == 0:
        return
    path = SOUNDS.get(name, name)
    subprocess.Popen(
        ["afplay", "-v", str(v / 10), path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
