#!/usr/bin/env python3
"""Compare 11:30 and 14:40 snapshots without producing predictions."""
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def records_by_ticker(payload):
    if not payload or payload.get("status") != "success":
        return {}
    return {str(row.get("ticker") or "").zfill(6): row for row in payload.get("records", [])}


def delta(after, before):
    return None if after is None or before is None else round(float(after) - float(before), 4)


def delta_pct(after, before):
    if after is None or before in (None, 0):
        return None
    return round((float(after) / float(before) - 1) * 100, 2)


def seal_event(midday_sealed, afternoon_sealed, afternoon, midday_pool=None, afternoon_pool=None):
    if midday_sealed and afternoon_sealed:
        before = (midday_pool or {}).get("reopen_count")
        after = (afternoon_pool or {}).get("reopen_count")
        if before is not None and after is not None and float(after) > float(before):
            return "afternoon_resealed"
        return "still_sealed"
    if not midday_sealed and afternoon_sealed:
        return "afternoon_new_seal"
    if midday_sealed and not afternoon_sealed:
        return "afternoon_opened"
    if float(afternoon.get("pct_change") or 0) >= 8:
        return "strong_unsealed"
    return "not_sealed"


def strength_label(row):
    if row["seal_event"] == "afternoon_new_seal":
        return "strengthened"
    if row["seal_event"] == "afternoon_opened":
        return "weakened"
    if row["seal_event"] in ("still_sealed", "afternoon_resealed"):
        queue_delta = row.get("queue_value_change_pct")
        if queue_delta is not None and queue_delta <= -30:
            return "weakened"
        if queue_delta is not None and queue_delta >= 30:
            return "strengthened"
        return "stable"
    pct_delta = row.get("pct_change_delta_pct_points")
    if pct_delta is None:
        return "unavailable"
    return "strengthened" if pct_delta >= 1 else "weakened" if pct_delta <= -1 else "stable"


def sector_breadth(rows):
    return Counter(row.get("industry") or "unknown" for row in rows.values()
                   if float(row.get("pct_change") or 0) >= 8)


def compare(midday_market, midday_pool, afternoon_market, afternoon_pool):
    mm, mp = records_by_ticker(midday_market), records_by_ticker(midday_pool)
    am, ap = records_by_ticker(afternoon_market), records_by_ticker(afternoon_pool)
    rows = []
    for ticker in sorted(set(mm) | set(mp) | set(am) | set(ap)):
        morning = mm.get(ticker) or mp.get(ticker) or {}
        afternoon = am.get(ticker) or ap.get(ticker) or {}
        if not (ticker in mp or ticker in ap or float(morning.get("pct_change") or 0) >= 8
                or float(afternoon.get("pct_change") or 0) >= 8):
            continue
        morning_pool, afternoon_pool_row = mp.get(ticker) or {}, ap.get(ticker) or {}
        row = {
            "ticker": ticker, "name": afternoon.get("name") or morning.get("name"),
            "industry": afternoon.get("industry") or morning.get("industry"),
            "midday_pct_change": morning.get("pct_change"),
            "afternoon_pct_change": afternoon.get("pct_change"),
            "pct_change_delta_pct_points": delta(afternoon.get("pct_change"), morning.get("pct_change")),
            "midday_at_limit_up": ticker in mp, "afternoon_at_limit_up": ticker in ap,
            "seal_event": seal_event(ticker in mp, ticker in ap, afternoon, morning_pool, afternoon_pool_row),
            "midday_queue_value": morning_pool.get("queue_value"),
            "afternoon_queue_value": afternoon_pool_row.get("queue_value"),
            "queue_value_change_pct": delta_pct(afternoon_pool_row.get("queue_value"), morning_pool.get("queue_value")),
            "midday_reopen_count": morning_pool.get("reopen_count"),
            "afternoon_reopen_count": afternoon_pool_row.get("reopen_count"),
            "turnover_value_delta": delta(afternoon.get("turnover_value"), morning.get("turnover_value")),
            "turnover_rate_delta_pct_points": delta(afternoon.get("turnover_rate"), morning.get("turnover_rate")),
            "volume_ratio_delta": delta(afternoon.get("volume_ratio"), morning.get("volume_ratio")),
            "total_market_cap": afternoon.get("total_market_cap") or morning.get("total_market_cap"),
            "float_market_cap": afternoon.get("float_market_cap") or morning.get("float_market_cap"),
        }
        row["afternoon_strength"] = strength_label(row)
        rows.append(row)
    before, after = sector_breadth(mm), sector_breadth(am)
    industries = sorted(set(before) | set(after))
    return {
        "schema_version": "1.0", "run_type": "11-30_to_14-40_comparison",
        "generated_at_cst": datetime.now(CST).isoformat(timespec="seconds"),
        "status": "success" if mm and am else "partial",
        "data_quality": {"midday_market_available": bool(mm), "midday_limit_up_pool_available": bool(mp),
                         "afternoon_market_available": bool(am), "afternoon_limit_up_pool_available": bool(ap),
                         "comparison_is_prediction": False},
        "sector_breadth_change": [{"industry": industry, "midday_strong_count": before[industry],
                                   "afternoon_strong_count": after[industry],
                                   "change": after[industry] - before[industry]} for industry in industries],
        "record_count": len(rows), "records": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--midday-market", required=True, type=Path)
    parser.add_argument("--midday-pool", required=True, type=Path)
    parser.add_argument("--afternoon-market", required=True, type=Path)
    parser.add_argument("--afternoon-pool", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = compare(*(load(path) for path in (args.midday_market, args.midday_pool,
                                                args.afternoon_market, args.afternoon_pool)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
