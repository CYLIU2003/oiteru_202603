# OITERU quick start

This is the single setup and launch guide for the supported MySQL deployment.
The parent service runs on Linux with MySQL 8 and tmux; Windows is supported
for local development and the RC-S380 reader guide, not as the standard
production host.

## 1. Parent service on Linux

Prerequisites: Git, Python 3.10+, MySQL 8, and tmux.

```bash
git clone <repository-url> oiteru_202603
cd oiteru_202603
cp .env.example .env
chmod +x venv-start.sh scripts/*.sh
```

Edit `.env` before continuing. At minimum, replace `FLASK_SECRET_KEY`,
`OITERU_ADMIN_PASSWORD`, `CARD_UID_HMAC_KEY`, `MYSQL_PASSWORD`, and
`MYSQL_ROOT_PASSWORD`. For local-only HTTP development, set
`SESSION_COOKIE_SECURE=false`; restore `true` for every TLS-backed deployment.
Do not enable a non-local plaintext parent URL when strict security is enabled.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
scripts/setup_local_mysql.sh --install
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh status parent
```

Open `http://localhost:5000/` for the public user flow. Use
`http://localhost:5000/admin` to sign in as an administrator. The initial
parent start applies the application's migrations; do not run ad-hoc DDL.

Useful tmux commands:

```bash
scripts/tmux_oiteru.sh attach parent
scripts/tmux_oiteru.sh logs parent
scripts/tmux_oiteru.sh restart parent
```

## 2. Raspberry Pi child device

Run this on the intended Raspberry Pi. GPIO, NFC, and motor tests cannot be
validated from a development PC.

```bash
cd ~/oiteru_202603
chmod +x scripts/setup_unit_environment.sh scripts/provision_unit.sh
./scripts/setup_unit_environment.sh
sudo scripts/provision_unit.sh
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh status unit
```

`provision_unit.sh` creates `/etc/oiteru/unit-secret` with mode `0600` and
writes only its path to `config.json`. It also verifies that the parent is
reachable. The child remains pending until an administrator approves it.

For a direct stepper connection, keep `MOTOR_TYPE=STEPPER` and
`CONTROL_METHOD=RASPI_DIRECT`, and verify the BCM pins in `config.json` do
not overlap with LEDs or a sensor. See
[../config_templates/README.md](../config_templates/README.md).

## 3. Windows local development

Install Python 3.10+, create `.venv`, copy and complete `.env`, then start a
local MySQL instance appropriate for development. Start the parent service:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv-start.ps1 parent-mysql
```

For the RC-S380, follow [card_reader_windows.md](card_reader_windows.md).

## 4. Verify before operating

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
git diff --check
```

Use the Windows Python path when applicable. For production operation and
recovery procedures, continue to [operations.md](operations.md).
