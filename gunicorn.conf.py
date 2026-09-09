import os

bind = f"0.0.0.0:{os.getenv('SERVER_PORT', '5000')}"
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
accesslog = "-"
errorlog = "-"
preload_app = True
