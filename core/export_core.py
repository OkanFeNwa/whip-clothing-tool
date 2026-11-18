#!/usr/bin/env python3
"""Optional CLI bridge that runs the real Blender export worker.

The Tauri app launches Blender directly, but this script keeps a dependency-free
entry point for debugging the core from a terminal. It does not import GTA
libraries; Blender provides szio, PyMateria and Sollumz.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PREFIX = "WCT_JSON:"


def emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def log(level: str, message: str) -> None:
    emit({"kind": "log", "level": level, "message": message})


def find_blender() -> str | None:
    override = os.environ.get("WCT_BLENDER") or os.environ.get("BLENDER_EXE")
    if override and Path(override).is_file():
        return override

    found = shutil.which("blender")
    if found:
        return found

    roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    for root in roots:
        if not root:
            continue
        base = Path(root) / "Blender Foundation"
        if not base.is_dir():
            continue
        for child in base.iterdir():
            exe = child / "blender.exe"
            if exe.is_file():
                return str(exe)
    return None


def main() -> int:
    try:
        job = json.loads(sys.stdin.read() or "{}")
    except Exception as exc:  # noqa: BLE001
        log("error", f"Invalid job JSON: {exc}")
        emit({"kind": "done", "ok": False, "message": "Invalid job"})
        return 1

    blender = find_blender()
    if not blender:
        log("error", "Blender was not found. Install Blender/Sollumz or set WCT_BLENDER.")
        emit({"kind": "done", "ok": False, "message": "Blender not found"})
        return 1

    here = Path(__file__).resolve().parent
    worker = here / "blender_export.py"
    if not worker.is_file():
        log("error", f"Worker script not found: {worker}")
        emit({"kind": "done", "ok": False, "message": "Worker script not found"})
        return 1

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(job, handle, ensure_ascii=False)
        job_file = Path(handle.name)

    ok = False
    message = "Core finished"
    try:
        process = subprocess.Popen(
            [blender, "--background", "--python", str(worker), "--", str(job_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(PREFIX):
                payload = line[len(PREFIX):]
                try:
                    event = json.loads(payload)
                except Exception:
                    log("info", payload)
                    continue
                if event.get("kind") == "done":
                    ok = bool(event.get("ok"))
                    message = str(event.get("message", message))
                else:
                    emit(event)
            else:
                log("info", line)
        process.wait()
        if process.returncode != 0 and ok:
            ok = False
            message = f"Blender exited with status {process.returncode}"
    except Exception as exc:  # noqa: BLE001
        log("error", f"{type(exc).__name__}: {exc}")
        message = str(exc)
    finally:
        try:
            job_file.unlink(missing_ok=True)
        except Exception:
            pass

    emit({"kind": "done", "ok": ok, "message": message})
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
