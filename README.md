# OITERU

NFC card-based sanitary-product dispensing system for campus operation. The
standard deployment is a Flask parent service with MySQL 8 (InnoDB) and
Raspberry Pi child devices. The child device supports a servo or a directly
connected ULN2003AN/28BYJ-48 stepper motor.

## Start here

Choose the path that matches your role:

| Goal | Read next |
| --- | --- |
| Run the parent service or a child device | [Quick start](docs/quick_start.md) |
| Find an operational or recovery procedure | [Operations guide](docs/operations.md) |
| Understand public and administrator access | [User-flow and access boundary](docs/user_flow.md) |
| Join development | [Developer onboarding](docs/onboarding.md) |
| Set up the Windows RC-S380 reader | [Windows card reader guide](docs/card_reader_windows.md) |
| Find a configuration template | [Configuration templates](config_templates/README.md) |

## Architecture and security boundary

```text
Public user browser ── /, /register, /usage ──> Parent service ──> MySQL 8
                                              ^
Raspberry Pi child ── NFC / motor / heartbeat ┘

Administrator browser ── /admin/* and /api/v1/admin/* (authenticated only)
```

- Public users can register a card and check their own usage without an
  administrator login.
- Administrative screens and administrative APIs require an authenticated
  administrator session.
- The normal database is MySQL 8 (InnoDB). SQLite support is legacy-only and
  must not be used for a standard or production deployment.
- Store parent secrets in `.env`; store a child-device secret in its separate
  `UNIT_SECRET_FILE`. Never commit either file.

## Minimal Linux deployment

The full, verified sequence is in [docs/quick_start.md](docs/quick_start.md).
In outline:

```bash
cp .env.example .env
# Edit .env and replace every change-this value.
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
scripts/setup_local_mysql.sh --install
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh status parent
```

Open `http://localhost:5000/` for the public flow. Open
`http://localhost:5000/admin` only to sign in as an administrator.

## Development checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
git diff --check
```

On Linux, replace the Python path with `.venv/bin/python`. Hardware tests use
mocks; run real NFC, GPIO, and motor checks only on the intended Raspberry Pi.

## Repository map

| Path | Responsibility |
| --- | --- |
| `app/api/` | HTTP routes, validation, and response formatting |
| `app/services/` | Business rules |
| `app/repositories/` | Database access |
| `app/models/` | DTOs, schemas, and enums |
| `app/auth/` | Administrator and child-device authentication |
| `unit/` | Hardware abstractions and safe child configuration |
| `scripts/` | Explicit setup, tmux, provisioning, and recovery commands |
| `docs/` | Canonical user, operator, and developer documentation |
| `tests/` | Unit and integration-style regression tests |

## Important constraints

- Do not put SQL in route handlers or access the database from templates.
- Use migrations; do not apply handwritten DDL directly to production.
- Treat dispensing as a tracked state transition and preserve event history.
- Keep each change focused, update the relevant documentation, and run the
  affected tests before merging.

The documentation index in [docs/README.md](docs/README.md) is the canonical
map; older duplicate manuals and bundled installers have been removed.
