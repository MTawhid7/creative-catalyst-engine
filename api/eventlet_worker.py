# api/eventlet_worker.py

"""
This is the official entry point for the Celery worker.
It ensures eventlet's monkey-patching is the very first thing that happens.
"""
import eventlet

eventlet.monkey_patch()

# Now that the environment is patched, we can safely import the Celery app.
from .worker import celery_app
