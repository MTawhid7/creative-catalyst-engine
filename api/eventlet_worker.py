# api/eventlet_worker.py

"""
This is the official entry point for the Celery worker.
It ensures the environment is perfectly configured *before* any application
code is imported.
"""
# --- START OF DEFINITIVE FIX ---
# This MUST be the very first block of code to run.
import sys
from pathlib import Path

# 1. Add the project's root directory to the Python path.
# This ensures that all modules can be found correctly.
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 2. NOW, import and run eventlet's monkey-patching.
# This MUST happen before any other library (like requests or httpx) is imported.
import eventlet

eventlet.monkey_patch()
# --- END OF DEFINITIVE FIX ---

# 3. Now that the environment is fully patched and the path is set, we can
# safely import the Celery app.
from api.worker import celery_app
