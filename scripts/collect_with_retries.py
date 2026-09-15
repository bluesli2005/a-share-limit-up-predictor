#!/usr/bin/env python3
"""Collect a paired market snapshot and limit-up pool with bounded retries."""
import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


MARKET_REQUIRED_FIELDS = (
    "ticker", "name", "last_price", "pct_change", "previous_close",
    "total_market_cap", "float_market_cap", "industry", "up_limit",
)
POOL_REQUIRED_FIELDS = (
    "ticker", "name", "last_price", "pct_change", "board_count",
    "last_seal_time", "queue_value", "reopen_count",
    "total_market_cap", "float_market_cap", "industry",
)


def _parse_cst(value):
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CST)
    return parsed.astimezone(CST)


def assess_payload(path, kind, evaluated_at=None, max_age_seconds=60):
    issues = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "transport_usable": False,
            "quality_usable": False,
            "quality_issues": ["missing_or_invalid_json"],
            "record_count": 0,
        }
    records = payload.get("records")
    try:
        record_count = int(payload.get("record_count") or 0)
    except (TypeError, ValueError):
        record_count = 0
        issues.append("record_count_invalid")
    transport_usable = (
        payload.get("status") == "success"
        and record_count > 0
        and isinstance(records, list)
        and len(records) > 0
    )
    if not transport_usable:
        issues.append("non_success_or_empty_records")
    captured_at = _parse_cst(payload.get("captured_at_cst"))
    now = evaluated_at or datetime.now(CST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CST)
    now = now.astimezone(CST)
    if captured_at is None:
        issues.append("captured_at_missing_or_invalid")
    else:
        age_seconds = (now - captured_at).total_seconds()
        if age_seconds < -5 or age_seconds > max_age_seconds:
            issues.append("snapshot_outside_freshness_window")
    native_timestamp = payload.get("source_native_timestamp_available") is True
    provider_timestamp = (
        payload.get("provider_quote_time_available") is True
        and payload.get("provider_quote_date_available") is True
    )
    if not (native_timestamp or provider_timestamp):
        issues.append("provider_native_timestamp_unavailable")
    if kind == "market":
        if payload.get("candidate_scan_truncated") is True:
            issues.append("candidate_scan_truncated")
        if payload.get("candidate_scan_complete") is not True:
            issues.append("candidate_scan_completeness_unverified")
    elif payload.get("pool_scan_complete") is not True:
        issues.append("limit_up_pool_completeness_unverified")
    required = MARKET_REQUIRED_FIELDS if kind == "market" else POOL_REQUIRED_FIELDS
    relevant = records or []
    if kind == "market":
        candidates = []
        for row in relevant:
            try:
                if float(row.get("pct_change")) >= 8:
                    candidates.append(row)
            except (TypeError, ValueError):
                continue
        relevant = candidates
    missing_fields = sorted({
        field
        for row in relevant
        for field in required
        if row.get(field) is None or row.get(field) == ""
    })
    if missing_fields:
        issues.append("missing_required_fields:" + ",".join(missing_fields))
    return {
        "transport_usable": transport_usable,
        "quality_usable": transport_usable and not issues,
        "quality_issues": issues,
        "record_count": record_count,
    }


def usable(path, kind="market", evaluated_at=None, max_age_seconds=60):
    return assess_payload(path, kind, evaluated_at, max_age_seconds)["quality_usable"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--scripts-dir", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=("midday", "afternoon"), default="afternoon")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=float, default=5)
    parser.add_argument("--max-age-seconds", type=int, default=60)
    args = parser.parse_args()
    maximum = min(3, max(1, args.max_attempts))
    attempts_dir = args.raw_dir / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    attempts = []
    final_market = args.raw_dir / (
        "market-11-30.json" if args.mode == "midday" else "manifest.json"
    )
    final_pool = args.raw_dir / (
        "limit-up-pool-11-30.json" if args.mode == "midday" else "limit-up-pool-14-40.json"
    )

    for number in range(1, maximum + 1):
        market = attempts_dir / f"market-attempt-{number}.json"
        pool = attempts_dir / f"limit-up-pool-attempt-{number}.json"
        started = datetime.now(CST).isoformat(timespec="seconds")
        market_run = subprocess.run([
            args.python, str(args.scripts_dir / "collect_market_data.py"),
            "--mode", args.mode, "--output", str(market), "--count", "1",
            "--interval-seconds", "1", "--continue-on-error",
        ], check=False)
        pool_run = subprocess.run([
            args.python, str(args.scripts_dir / "collect_limit_up_pool.py"), "--output", str(pool)
        ], check=False)
        evaluated_at = datetime.now(CST)
        market_assessment = assess_payload(
            market, "market", evaluated_at, args.max_age_seconds
        )
        pool_assessment = assess_payload(
            pool, "limit_up_pool", evaluated_at, args.max_age_seconds
        )
        market_ok = market_assessment["quality_usable"]
        pool_ok = pool_assessment["quality_usable"]
        attempts.append({
            "attempt": number, "started_at_cst": started,
            "market_exit_code": market_run.returncode,
            "market_transport_usable": market_assessment["transport_usable"],
            "market_usable": market_ok,
            "market_quality_issues": market_assessment["quality_issues"],
            "limit_up_pool_exit_code": pool_run.returncode,
            "limit_up_pool_transport_usable": pool_assessment["transport_usable"],
            "limit_up_pool_usable": pool_ok,
            "limit_up_pool_quality_issues": pool_assessment["quality_issues"],
            "_market_path": market,
            "_pool_path": pool,
        })
        if market_ok and pool_ok:
            break
        if number < maximum:
            time.sleep(max(0, args.retry_delay_seconds))

    def attempt_rank(item):
        transport_count = int(item["market_transport_usable"]) + int(item["limit_up_pool_transport_usable"])
        issue_count = len(item["market_quality_issues"]) + len(item["limit_up_pool_quality_issues"])
        return (int(item["market_usable"] and item["limit_up_pool_usable"]), transport_count, -issue_count)

    selected = max(attempts, key=attempt_rank) if attempts else None
    if selected:
        if selected["_market_path"].exists():
            shutil.copy2(selected["_market_path"], final_market)
        if selected["_pool_path"].exists():
            shutil.copy2(selected["_pool_path"], final_pool)
    success = bool(selected and selected["market_usable"] and selected["limit_up_pool_usable"])
    transport_success = bool(
        selected
        and selected["market_transport_usable"]
        and selected["limit_up_pool_transport_usable"]
    )
    public_attempts = [
        {key: value for key, value in item.items() if not key.startswith("_")}
        for item in attempts
    ]
    summary = {
        "schema_version": "1.0", "run_type": f"{args.mode}_collection_attempts",
        "generated_at_cst": datetime.now(CST).isoformat(timespec="seconds"),
        "status": "success" if success else "data_quality_failure" if transport_success else "failure",
        "max_attempts": maximum,
        "attempt_count": len(attempts),
        "selected_attempt": selected["attempt"] if selected else None,
        "attempts": public_attempts,
    }
    (args.raw_dir / "collection-attempts.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
