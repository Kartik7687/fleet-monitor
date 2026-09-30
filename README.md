# Mini Device Fleet Monitor

A small FastAPI service that tracks heartbeats from a fleet of devices and reports each device as **ONLINE** or **OFFLINE**, plus a simulator to try it out.

## 1. What it does

- Register devices, receive heartbeats, list devices, get a single device, and get a fleet summary.
- A device is **ONLINE** if its last heartbeat arrived within the last 30 seconds, otherwise **OFFLINE**. The status returned by every API reflects this automatically.
- Includes a device simulator and an automated test suite.

## 2. Design / architecture

```
app/main.py     HTTP layer: routes, status codes, error mapping
app/models.py   Pydantic request/response models and input validation
app/store.py    Device registry: all business logic, thread-safe
simulator/      Script that simulates N devices sending heartbeats
tests/          pytest suite (API behaviour + concurrency)
```

Key decisions:

- **Status is computed at read time** from the time the last heartbeat was received. There is no background job or timer, so status can never be stale or drift.
- **Injectable clock.** `DeviceStore` accepts a clock function, so the 30-second rule is tested deterministically without sleeping.
- **Server receive time drives liveness**, not the device-reported timestamp. A device with a wrong clock therefore can't appear falsely online or offline. The device-reported timestamp is still stored and returned as `last_heartbeat`.
- **Thread safety.** The in-memory store is protected by a single `threading.Lock`. `/summary` and `/devices` read a single "now" so counts are consistent.
- **Thin API layer.** Routes only translate between HTTP and the store (`409` duplicate, `404` unknown device, `422` invalid input).

## 3. Prerequisites

- Python 3.10 or newer
- Git
- Commands below are for Windows PowerShell. On macOS/Linux, activate the virtual environment with `source .venv/bin/activate` instead.

## 4. Build / install

```powershell
git clone https://github.com/Kartik7687/fleet-monitor.git
cd fleet-monitor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

## 5. Run the application

```powershell
uvicorn app.main:app
```

- API: http://127.0.0.1:8000
- Interactive API docs (Swagger UI): http://127.0.0.1:8000/docs
- Optional: `$env:OFFLINE_TIMEOUT_SECONDS = "30"` changes the timeout (default 30).

## 6. Run the simulator

With the server running, open a second terminal, activate the virtual environment, and run:

```powershell
python simulator\simulate.py
```

By default it registers and simulates 5 devices (`device-01` to `device-05`), each sending a heartbeat every 5 seconds. Options: `--devices N`, `--interval SECONDS`, `--url URL`.

Interactive commands in the simulator terminal:

| Command | Effect |
|---|---|
| `stop device-03` | Device stops sending heartbeats; it becomes OFFLINE after 30 seconds |
| `start device-03` | Device resumes; it becomes ONLINE again with its next heartbeat |
| `quit` | Exit the simulator |

To watch the fleet, use a third terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/summary
```

## 7. Run the tests

```powershell
pytest -v
```

The suite (15 tests) covers registration, duplicate and invalid registration, heartbeat handling and validation, ONLINE/OFFLINE status, the 30-second rule (29s, exactly 30s, and 30.001s), recovery after a new heartbeat, list/filter/summary, and concurrent heartbeats.

## 8. Example API requests

```powershell
# Register a device
Invoke-RestMethod -Method Post http://127.0.0.1:8000/devices -ContentType "application/json" -Body '{"id":"device-01","name":"Lab Device 01"}'

# Send a heartbeat (cpu_usage and signal_strength are optional)
Invoke-RestMethod -Method Post http://127.0.0.1:8000/devices/device-01/heartbeat -ContentType "application/json" -Body '{"timestamp":"2026-09-21T10:30:00Z","status":"OK","cpu_usage":42,"signal_strength":-71}'

# List devices (optionally filter by status)
Invoke-RestMethod http://127.0.0.1:8000/devices
Invoke-RestMethod "http://127.0.0.1:8000/devices?status=OFFLINE"

# Get one device
Invoke-RestMethod http://127.0.0.1:8000/devices/device-01

# Fleet summary
Invoke-RestMethod http://127.0.0.1:8000/summary
```

Example `GET /devices/device-01` response:

```json
{
  "id": "device-01",
  "name": "Lab Device 01",
  "status": "ONLINE",
  "last_heartbeat": "2026-09-21T10:30:00Z",
  "reported_status": "OK",
  "cpu_usage": 42.0,
  "signal_strength": -71.0
}
```

Example `GET /summary` response:

```json
{ "total": 5, "online": 4, "offline": 1 }
```

Error responses: `409` device already exists, `404` unknown device, `422` invalid input.

## 9. Assumptions

- Exactly 30 seconds since the last heartbeat still counts as ONLINE; more than 30 seconds is OFFLINE.
- A registered device that has never sent a heartbeat is OFFLINE with `last_heartbeat: null`.
- Device IDs are 1 to 64 characters: letters, digits, `.`, `_`, `-`.
- Heartbeat timestamps must include a timezone (for example `Z`).
- `cpu_usage` must be between 0 and 100; `signal_strength` is unrestricted.
- Devices must be registered before sending heartbeats.

## 10. Known limitations

- Data is stored in memory only, so it is lost when the server restarts.
- Single process: the lock does not protect state across multiple worker processes.
- No authentication; any client can register devices or send heartbeats for any device.
- No pagination on `GET /devices`.
- A late or out-of-order heartbeat overwrites the latest one.
- Only the latest heartbeat per device is kept (no history).

## 11. What I would improve with one more day

- Persistent storage (SQLite or Postgres), with Redis if scaling to multiple workers.
- Per-device authentication tokens.
- Handle out-of-order heartbeats and keep a heartbeat history.
- Pagination, structured (JSON) logging, and graceful shutdown.
- A Dockerfile and a small web dashboard.

## AI Usage

- **Tools used:** Claude, for design discussion, scaffolding, test drafting, and README drafting.
- **Suggestion I changed or improved:** <<< I corrected a typo in simulate.py, made the necessary modifications to ensure the application runs smoothly on Windows, and executed multiple test cases to verify the functionality and expected behavior. >>>
- **Verified myself:** ran `pytest` (15 passed); ran the simulator, stopped `device-03`, and confirmed via `/summary` that the fleet showed 4 online / 1 offline, then returned to 5 online within one heartbeat interval after `start device-03`.
