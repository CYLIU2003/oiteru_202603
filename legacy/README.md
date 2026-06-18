"""
Legacy modules preserved for backward compatibility.

When the project is fully migrated to MySQL, the contents of this directory
can be removed.

Contents expected:
- db_adapter.py (SQLite + MySQL thin adapter)
- Unit client archive (archive/unit_client.py)
- Legacy Flask entry points (app.py, etc.)

Status (2026-06-18):
- db_adapter.py still in use at project root (supports both SQLite & MySQL)
- Migration target: pure MySQL via SQLAlchemy or equivalent ORM
- server.py still contains dual SQLite/MySQL code paths
"""
