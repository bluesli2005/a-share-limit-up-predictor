#!/usr/bin/env python3
"""Collect the 14:40 market snapshot and limit-up pool with bounded retries."""
import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


def usable(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("status") == "success" and int(payload.get("record_count") or 0) > 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--scripts-dir", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=float, default=5)
    args = parser.parse_args()
    maximum = min(3, max(1, args.max_attempts))
    attempts_dir = args.raw_dir / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    attempts = []
    final_market = args.raw_dir / "manifest.json"
    final_pool = args.raw_dir / "limit-up-pool-14-40.json"

    for number in range(1, maximum + 1):
        market = attempts_dir / f"market-attempt-{number}.json"
        pool = attempts_dir / f"limit-up-pool-attempt-{number}.json"
        started = datetime.now(CST).isoformat(timespec="seconds")
        market_run = subprocess.run([
            args.python, str(args.scripts_dir / "collect_market_data.py"),
            "--mode", "afternoon", "--output", str(market), "--count", "1",
            "--interval-seconds", "1", "--continue-on-error",
        ], check=False)
        pool_run = subprocess.run([
            args.python, str(args.scripts_dir / "collect_limit_up_pool.py"), "--output", str(pool)
        ], check=False)
        market_ok, pool_ok = usable(market), usable(pool)
        attempts.append({
            "attempt": number, "started_at_cst": started,
            "market_exit_code": market_run.returncode, "market_usable": market_ok,
            "limit_up_pool_exit_code": pool_run.returncode, "limit_up_pool_usable": pool_ok,
        })
        if market.exists():
            shutil.copy2(market, final_market)
        if pool.exists():
            shutil.copy2(pool, final_pool)
        if market_ok and pool_ok:
            break
        if number < maximum:
            time.sleep(max(0, args.retry_delay_seconds))

    success = bool(attempts and attempts[-1]["market_usable"] and attempts[-1]["limit_up_pool_usable"])
    summary = {
        "schema_version": "1.0", "run_type": "afternoon_collection_attempts",
        "generated_at_cst": datetime.now(CST).isoformat(timespec="seconds"),
        "status": "success" if success else "failure", "max_attempts": maximum,
        "attempt_count": len(attempts), "attempts": attempts,
    }
    (args.raw_dir / "collection-attempts.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
