#!/usr/bin/env python3
"""Archive an exchange-calendar check for a scheduled collection."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    now = datetime.now(CST)
    payload = {"schema_version": "1.0", "checked_at_cst": now.isoformat(timespec="seconds"),
               "trade_date": now.date().isoformat(), "source": "AKShare.tool_trade_date_hist_sina"}
    exit_code = 2
    try:
        import akshare as ak
        dates = {str(value)[:10] for value in ak.tool_trade_date_hist_sina()["trade_date"]}
        payload.update(status="success", is_trading_day=now.date().isoformat() in dates)
        exit_code = 0 if payload["is_trading_day"] else 1
    except Exception as exc:
        payload.update(status="failure", is_trading_day=None,
                       error_type=type(exc).__name__, error=str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
