"""Vercel entrypoint: exposes the ChainSentinel FastAPI `app` (backend/app.py). Run locally with ./run.sh instead."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from app import app  # noqa: E402,F401  (FastAPI instance named `app`, as Vercel expects)
