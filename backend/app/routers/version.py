import os
import subprocess
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


def _resolve_version() -> str:
    env = os.environ.get("APP_VERSION")
    if env and env != "dev":
        return env

    # Local dev: read VERSION file + git short SHA
    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    try:
        base = version_file.read_text().strip()
    except FileNotFoundError:
        base = "0.0"

    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=version_file.parent,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        sha = "unknown"

    return f"{base}.{sha}"


@router.get("/")
async def get_version():
    return {"version": _resolve_version()}
