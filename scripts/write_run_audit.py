#!/usr/bin/env python3
"""Append runner events so scheduled, late and manual runs are distinguishable."""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")
JST = ZoneInfo("Asia/Tokyo")


def append_event(output, run_type, scheduled_time, event, exit_code=None, detail=None, now=None):
    now = (now or datetime.now(CST)).astimezone(CST)
    hour, minute = (int(part) for part in scheduled_time.split(":", 1))
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    delay_seconds = int((now - scheduled).total_seconds())
    if delay_seconds < -60:
        trigger_timing = "early"
    elif delay_seconds <= 120:
        trigger_timing = "on_time"
    else:
        trigger_timing = "late"
    try:
        payload = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {
            "schema_version": "1.0",
            "run_type": run_type,
            "scheduled_time_cst": scheduled_time,
            "events": [],
        }
    payload["events"].append({
        "event": event,
        "recorded_at_cst": now.isoformat(timespec="seconds"),
        "recorded_at_jst": now.astimezone(JST).isoformat(timespec="seconds"),
        "scheduled_at_cst": scheduled.isoformat(timespec="seconds"),
        "delay_seconds": delay_seconds,
        "trigger_timing": trigger_timing,
        "pid": os.getppid(),
        "exit_code": exit_code,
        "detail": detail,
    })
    payload["latest_event"] = event
    payload["latest_recorded_at_cst"] = now.isoformat(timespec="seconds")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-type", required=True)
    parser.add_argument("--scheduled-time", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--exit-code", type=int)
    parser.add_argument("--detail")
    args = parser.parse_args()
    append_event(
        args.output, args.run_type, args.scheduled_time, args.event,
        exit_code=args.exit_code, detail=args.detail,
    )


if __name__ == "__main__":
    main()
