"""Run tests with this interpreter, from the repo root, without IP sockets."""
from pathlib import Path
import subprocess
import sys

if __name__ == "__main__":
    raise SystemExit(subprocess.run(
        [sys.executable, "-m", "pytest", *(sys.argv[1:] or ["tests", "-q"]),
         "--disable-socket", "--allow-unix-socket"],
        cwd=Path(__file__).resolve().parents[1], check=False,
    ).returncode)
