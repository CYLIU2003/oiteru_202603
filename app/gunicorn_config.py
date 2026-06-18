"""Gunicorn configuration for OITERU production deployment.

Usage:
    gunicorn -c app/gunicorn_config.py "server:app"

Or with db_server (MySQL):
    gunicorn -c app/gunicorn_config.py "db_server:app"
"""

import multiprocessing
import os

# Bind
bind = f"0.0.0.0:{os.getenv('SERVER_PORT', '5000')}"

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", min(4, multiprocessing.cpu_count() * 2 + 1)))
threads = int(os.getenv("GUNICORN_THREADS", 2))

# Worker class
worker_class = "sync"

# Timeout
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Process naming
proc_name = "oiteru-parent"

# Server hooks
def on_starting(server):
    server.log.info("OITERU parent server starting with gunicorn")

def when_ready(server):
    server.log.info("OITERU parent server is ready to accept connections")

def on_exit(server):
    server.log.info("OITERU parent server shutting down")
