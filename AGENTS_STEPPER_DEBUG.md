# Agent Instructions: ULN2003AN + 28BYJ-48 Stepper Debug

## Scope

Repository: `CYLIU2003/oiteru_202603`
Branch: `main_stepping_branch`
Target runtime: Raspberry Pi, `unit.py`
Target motor stack: `28BYJ-48` stepper motor driven through `ULN2003AN` driver board
Control method: Raspberry Pi GPIO direct control, not PCA9685, not Arduino

This branch is allowed to be stepper-specific. Do not preserve servo/PCA9685 UI behavior inside this branch unless it is needed for compatibility with archived code. Keep changes isolated to the stepper branch and avoid polluting servo-oriented branches.

## Current Problem

The NFC flow reaches `dispense_item()`, but the motor still does not physically rotate. Previous symptoms included:

```text
!! 未サポートのモーター設定です: STEPPER, RASPI_DIRECT
```

That unsupported-branch issue has been addressed at the runtime patch layer, but the remaining issue is likely one of the following:

1. The injected `STEPPER + RASPI_DIRECT` branch is still not actually present at runtime.
2. GPIO output is present, but the ULN2003 input order / 28BYJ-48 coil phase order is wrong.
3. GPIO uses BCM numbering, while the wiring was done using physical pin numbering.
4. The motor is underpowered or the Raspberry Pi and external 5V supply do not share GND.
5. Step timing is too fast, causing vibration or stall instead of rotation.
6. The active runtime file is not the latest pulled version.

## Hard Constraints

- Do not modify unrelated parent server logic unless needed for passing stepper settings.
- Do not remove NFC, inventory, Flask API, heartbeat, or sensor logic.
- Do not rely on PCA9685 for `STEPPER + RASPI_DIRECT`.
- Do not switch this branch back to servo-first behavior.
- Do not commit `config.json`, local secrets, logs, sqlite databases, or `.env` files.
- Keep `config.example.json` free from real passwords, real locations, private URLs, and secrets.
- Prefer small, inspectable changes.

## Important Files

- `unit.py`
  - Entry point.
  - Loads `archive/unit_client.py`.
  - Applies `stepping_patch.patch_unit_client_source()`.
  - Must ensure a real `elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':` branch exists after patching.

- `stepping_patch.py`
  - Branch-specific runtime patch.
  - Contains stepper CUI menu, diagnostics, and dispense branch injection.
  - This is the main file to modify for stepper behavior.

- `archive/unit_client.py`
  - Original archived common implementation.
  - Avoid direct heavy edits unless the runtime patch approach becomes unmaintainable.

- `config.example.json`
  - Example only.
  - Safe defaults should reflect ULN2003AN + 28BYJ-48.

- `.gitignore`
  - Must ignore local runtime configuration, especially `config.json`.

## Required First Checks

Before changing code, inspect the actual runtime path on the Raspberry Pi:

```bash
pwd
ls -la
git branch --show-current
git log --oneline -5
git status
python - <<'PY'
import pathlib
print(pathlib.Path('unit.py').resolve())
print(pathlib.Path('stepping_patch.py').exists())
print(pathlib.Path('archive/unit_client.py').exists())
PY
```

Confirm the branch is:

```text
main_stepping_branch
```

Then confirm that runtime patching inserts the real branch:

```bash
python - <<'PY'
from pathlib import Path
from stepping_patch import patch_unit_client_source
src = Path('archive/unit_client.py').read_text(encoding='utf-8')
patched = patch_unit_client_source(src)
marker = "elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':"
print('marker_present=', marker in patched)
print('unsupported_present=', "未サポートのモーター設定" in patched)
idx = patched.find(marker)
print('marker_index=', idx)
print(patched[idx-300:idx+500] if idx != -1 else 'NO MARKER')
PY
```

If `marker_present=False`, fix branch injection before touching motor timing.

## Hardware Assumptions

Default logical mapping:

```json
"STEPPER_PINS": [5, 6, 13, 19]
```

Interpretation:

| ULN2003AN input | Raspberry Pi BCM GPIO |
|---|---:|
| IN1 | GPIO5 |
| IN2 | GPIO6 |
| IN3 | GPIO13 |
| IN4 | GPIO19 |

Important: These are BCM GPIO numbers, not physical board pin numbers.

Recommended logical phase order to test first:

```json
"STEPPER_PHASE_ORDER": [0, 2, 1, 3]
```

This means the code receives pins as `IN1, IN2, IN3, IN4`, then drives them as `IN1, IN3, IN2, IN4`. This is a common practical correction for 28BYJ-48 examples where naive `IN1,IN2,IN3,IN4` ordering only vibrates.

## Power Check

If ULN2003 LEDs blink but the motor only vibrates or does not rotate:

- Use external 5V for the ULN2003/motor VCC if possible.
- Connect external supply GND to Raspberry Pi GND.
- Do not assume Raspberry Pi 5V rail can reliably drive the motor under load.
- Keep step delay slow while debugging.

Recommended slow settings:

```json
"STEPPER_STEP_DELAY": 0.01,
"STEPPER_DRIVE_MODE": "full",
"STEPPER_TEST_STEPS": 256,
"STEPPER_STEPS_PER_REV": 2048
```

## Expected Runtime Log

When NFC triggers dispensing, the log should include a line similar to:

```text
INFO: STEPPER/RASPI_DIRECT start actual_pins(IN1-4)=[5, 6, 13, 19], phase_order=[0, 2, 1, 3], drive_pins=[5, 13, 6, 19], mode=full, steps=..., delay=0.0100s, reverse=False
```

If the log still shows:

```text
!! 未サポートのモーター設定です: STEPPER, RASPI_DIRECT
```

then the `dispense_item()` branch was not injected. Fix `unit.py` / `stepping_patch.py` injection, not motor timing.

## CUI Debug Flow

Run:

```bash
python unit.py
```

Open the settings menu. Use the stepper-specific items:

1. Confirm `STEPPER_PINS`.
2. Confirm `STEPPER_PHASE_ORDER`.
3. Set `STEP_DELAY` to `0.01` or slower.
4. Set `DRIVE_MODE` to `full` first.
5. Run positive direction test.
6. Run reverse direction test.
7. If vibration/no movement, run phase-order scan.
8. Save the working order.

The CUI must allow direct motor motion without NFC. The agent should improve this if it is not usable.

## Phase Order Exploration

Implement or verify a scan command that tries candidates like:

```python
candidate_orders = [
    [0, 2, 1, 3],
    [0, 1, 2, 3],
    [3, 1, 2, 0],
    [3, 2, 1, 0],
    [0, 2, 3, 1],
    [1, 3, 0, 2],
]
```

Each candidate should:

- Run slowly.
- Use the same physical `STEPPER_PINS`.
- Print the actual drive pins.
- Turn all coils off afterward.
- Let the operator choose the smoothest order.

## Minimal Standalone GPIO Test

If the integrated app is confusing, create a temporary local-only test file on the Raspberry Pi. Do not commit it unless it is generalized and safe.

Suggested local test script:

```python
import time
import RPi.GPIO as GPIO

pins_in1_to_in4 = [5, 6, 13, 19]
phase_order = [0, 2, 1, 3]
drive_pins = [pins_in1_to_in4[i] for i in phase_order]
step_delay = 0.01
steps = 512

sequence = [
    (1, 1, 0, 0),
    (0, 1, 1, 0),
    (0, 0, 1, 1),
    (1, 0, 0, 1),
]

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
for pin in pins_in1_to_in4:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

try:
    print('drive_pins=', drive_pins)
    for i in range(steps):
        phase = sequence[i % len(sequence)]
        for pin, value in zip(drive_pins, phase):
            GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
        time.sleep(step_delay)
finally:
    for pin in pins_in1_to_in4:
        GPIO.output(pin, GPIO.LOW)
    GPIO.cleanup()
```

If this does not rotate the motor but ULN2003 LEDs blink, investigate wiring/power/phase order. If LEDs do not blink, investigate GPIO numbering, permissions, and whether the code runs on the Raspberry Pi.

## Code Improvement Targets

The agent should make the following improvements if missing:

1. Ensure `STEPPER + RASPI_DIRECT` branch is injected using the exact `elif` marker, not by searching for a loose string such as `STEPPER/RASPI_DIRECT`.
2. Ensure all `STEPPER_PINS` are configured as `GPIO.OUT` before motion.
3. Ensure all coils are set LOW in `finally` after every test or dispense attempt.
4. Add clear logs showing:
   - `actual_pins`
   - `phase_order`
   - `drive_pins`
   - `drive_mode`
   - `step_delay`
   - `steps`
   - `reverse`
5. Make CUI direct motor tests independent of NFC.
6. Add a phase-order scan function.
7. Avoid PCA9685 imports/checks in `STEPPER + RASPI_DIRECT` mode.
8. Keep local config out of git.

## Acceptance Criteria

The task is complete only when all conditions are satisfied:

1. Running `python unit.py` on the Raspberry Pi does not fall into PC mode when `RPi.GPIO` is available.
2. CUI direct test causes ULN2003 LEDs to blink.
3. At least one CUI phase-order candidate physically rotates the 28BYJ-48.
4. The selected `STEPPER_PHASE_ORDER` is saved in `config.json` locally.
5. NFC card read triggers `dispense_item()` and logs `INFO: STEPPER/RASPI_DIRECT start ...`.
6. NFC card read physically rotates the motor.
7. No `config.json`, secrets, logs, or database files are committed.

## Suggested Commit Message

```text
Fix ULN2003 28BYJ-48 stepper drive and phase-order debug flow
```

## Report Back Format

When done, report:

```text
Branch:
Commit:
Files changed:
Runtime branch marker present: yes/no
CUI direct test result:
Best STEPPER_PHASE_ORDER:
NFC dispense result:
Remaining risks:
```
