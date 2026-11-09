"""Run development processes and shut down both on exit."""

import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    python = ROOT / "backend" / ".venv" / "bin" / "python"
    if not python.exists():
        print("Run make setup first.", file=sys.stderr)
        return 1
    processes: list[subprocess.Popen] = []

    def stop(_signal=None, _frame=None):
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        processes.append(subprocess.Popen(
            [str(python), "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT / "backend",
        ))
        processes.append(subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1"], cwd=ROOT / "frontend",
        ))
        print("PaperMind: http://localhost:5173", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.25)
        return next((process.returncode for process in processes if process.returncode), 0)
    finally:
        stop()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
