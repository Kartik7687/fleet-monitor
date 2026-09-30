"""Simulates N devices sending heartbeats.

Interactive commands while running:
  stop <device-id>    stop heartbeats for one device (it goes OFFLINE after 30s)
  start <device-id>   resume heartbeats
  quit
"""
import argparse
import random
import threading
from datetime import datetime, timezone

import requests


def run_device(base_url: str, device_id: str, interval: float, stop: threading.Event):
    while True:
        if not stop.is_set():
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "OK",
                "cpu_usage": random.randint(10, 90),
                "signal_strength": random.randint(-90, -50),
            }
            try:
                r = requests.post(f"{base_url}/devices/{device_id}/heartbeat", json=payload, timeout=5)
                print(f"{device_id} -> heartbeat {r.status_code}")
            except requests.RequestException as exc:
                print(f"{device_id} -> error: {exc}")
        threading.Event().wait(interval)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--devices", type=int, default=5)
    p.add_argument("--interval", type=float, default=5.0)
    args = p.parse_args()

    stops: dict[str, threading.Event] = {}
    for i in range(1, args.devices + 1):
        device_id = f"device-{i:02d}"
        r = requests.post(f"{args.url}/devices", json={"id": device_id, "name": f"Simulated Device {i:02d}"}, timeout=5)
        if r.status_code not in (201, 409):
            raise SystemExit(f"Could not register {device_id}: {r.status_code} {r.text}")
        stops[device_id] = threading.Event()
        threading.Thread(target=run_device, args=(args.url, device_id, args.interval, stops[device_id]), daemon=True).start()

    print(__doc__)
    while True:
        try:
            cmd = input().strip().split()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        if cmd[0] == "quit":
            break
        if len(cmd) == 2 and cmd[0] in ("stop", "start") and cmd[1] in stops:
            (stops[cmd[1]].set if cmd[0] == "stop" else stops[cmd[1]].clear)()
            print(f"{cmd[1]} {'stopped' if cmd[0] == 'stop' else 'started'}")
        else:
            print("unknown command")


if __name__ == "__main__":
    main()