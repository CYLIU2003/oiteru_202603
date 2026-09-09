# OITERU developer onboarding

Start with the [documentation index](README.md) and complete the supported
[quick start](quick_start.md). The normal stack is Flask, MySQL 8 (InnoDB),
and Raspberry Pi child devices; SQLite and launcher-based flows are legacy.

## Working rules

- Work in `app/api/`, `app/services/`, `app/repositories/`, `app/models/`,
  `app/auth/`, and `unit/` according to their stated responsibilities.
- Keep SQL out of routes and templates; use a repository and service instead.
- Keep public user routes public, but keep `/admin/*` and
  `/api/v1/admin/*` authenticated. See [user_flow.md](user_flow.md).
- Do not store a child secret in JSON or a parent secret in source control.
- Add or adjust tests for behavior changes and update the relevant canonical
  document in this directory.

## Before proposing a change

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
git diff --check
```

Use focused tests while iterating, then run the full suite before integration.
Hardware code must remain behind an interface so tests can run with mocks.

## Where to look

| Need | Location |
| --- | --- |
| System entry and constraints | [../README.md](../README.md) |
| Deployment and child provisioning | [quick_start.md](quick_start.md) |
| Operational domain and failures | [operations.md](operations.md) |
| Parent and child configuration | [../config_templates/README.md](../config_templates/README.md) |
| Tests | `../tests/` |
