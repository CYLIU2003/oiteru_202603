"""Production WSGI entry point for the OITERU parent service."""

from server import app, bootstrap_parent

# Gunicorn imports this module in its master process.  Running the common,
# idempotent bootstrap here guarantees schema readiness before workers accept
# device heartbeats.
bootstrap_parent(start_background=True)

