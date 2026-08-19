"""Vercel entrypoint for the application stored in the New/ subdirectory."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent / "New"
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app  # noqa: E402,F401
