#!/usr/bin/env python3
"""Collect timestamped A-share snapshots; never sends orders."""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


def clean(value):
    if value is None:
        return None
    try:
        if value != value:
            return None
    except TypeError:
        pass
    if hasattr(value, "item"):
        value = value.item()
    return value


def normalize_records(source_rows, captured):
    fields = {
        "代码": "ticker", "名称": "name", "最新价": "last_price",
        "涨跌幅": "pct_change", "成交量": "volume_lot", "成交额": "turnover_value",
        "今开": "open", "昨收": "previous_close", "最高": "high", "最低": "low",
        "量比": "volume_ratio", "换手率": "turnover_rate",
        "总市值": "total_market_cap", "流通市值": "float_market_cap",
    }
    records = []
    for source in source_rows:
        row = {target: clean(source.get(label)) for label, target in fields.items()}
        ticker = str(row.get("ticker") or "").zfill(6)
        if not ticker or ticker.startswith(("4", "8", "9")):
            continue
        row["ticker"] = ticker
        row["captured_at_cst"] = captured
        records.append(row)
    return records


def eastmoney_snapshot():
    field_map = {
        "f12": "代码", "f14": "名称", "f2": "最新价", "f3": "涨跌幅",
        "f5": "成交量", "f6": "成交额", "f17": "今开", "f18": "昨收",
        "f15": "最高", "f16": "最低", "f10": "量比", "f8": "换手率",
        "f20": "总市值", "f21": "流通市值",
    }
    params = {
        "pn": 1, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
        "fid": "f3", "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        "fields": ",".join(field_map),
    }
    query = urllib.parse.urlencode(params)
    hosts = ("push2.eastmoney.com", "82.push2.eastmoney.com", "33.push2.eastmoney.com")
    errors = []
    diff = []
    used_host = None
    for attempt in range(3):
        for host in hosts:
            url = f"https://{host}/api/qt/clist/get?{query}"
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
            )
            try:
                with urllib.request.urlopen(request, timeout=12) as response:
                    payload = json.load(response)
                diff = ((payload.get("data") or {}).get("diff") or [])
                if diff:
                    used_host = host
                    break
                errors.append(f"{host}: empty response")
            except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                errors.append(f"{host}: {type(exc).__name__}: {exc}")
        if diff:
            break
        if attempt < 2:
            time.sleep(attempt + 1)
    if not diff:
        raise RuntimeError("Eastmoney candidate scan failed: " + " | ".join(errors[-9:]))
    captured = datetime.now(CST).isoformat(timespec="seconds")
    rows = [{field_map[key]: value for key, value in source.items() if key in field_map} for source in diff]
    return captured, normalize_records(rows, captured), f"Eastmoney.top_gainers_single_request:{used_host}"


def akshare_snapshot():
    try:
        return eastmoney_snapshot()
    except Exception as direct_error:
        import akshare as ak
        frame = ak.stock_zh_a_spot_em()
        source_rows = frame.to_dict("records")
        captured = datetime.now(CST).isoformat(timespec="seconds")
        records = normalize_records(source_rows, captured)
        if not records:
            raise RuntimeError(f"direct={direct_error!r}; AKShare returned no records")
        return captured, records, "AKShare.stock_zh_a_spot_em"


def write_failure(output, mode, exc):
    captured = datetime.now(CST).isoformat(timespec="seconds")
    payload = {
        "schema_version": "1.0", "run_type": mode, "captured_at_cst": captured,
        "status": "failure", "error_type": type(exc).__name__, "error": str(exc),
        "record_count": 0, "records": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tushare_metadata(trade_date):
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        return {"enabled": False, "reason": "TUSHARE_TOKEN_missing"}, {}
    import tushare as ts

    pro = ts.pro_api(token)
    limits = pro.stk_limit(trade_date=trade_date, fields="ts_code,trade_date,up_limit,down_limit")
    result = {}
    for row in limits.to_dict("records"):
        result[str(row["ts_code"]).split(".")[0]] = {
            "up_limit": clean(row.get("up_limit")),
            "down_limit": clean(row.get("down_limit")),
        }
    return {"enabled": True, "records": len(result)}, result


def collect_once(output, mode):
    captured, rows, source = akshare_snapshot()
    trade_date = captured[:10].replace("-", "")
    ts_status, limits = tushare_metadata(trade_date)
    for row in rows:
        row.update(limits.get(row["ticker"], {}))
    cutoff_pct = rows[-1].get("pct_change") if rows else None
    payload = {
        "schema_version": "1.0",
        "run_type": mode,
        "captured_at_cst": captured,
        "status": "success",
        "source": source,
        "source_native_timestamp_available": False,
        "tushare": ts_status,
        "record_count": len(rows),
        "candidate_cutoff_pct": cutoff_pct,
        "candidate_scan_truncated": cutoff_pct is not None and float(cutoff_pct) >= 8.0,
        "records": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=("opening", "afternoon"), required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--interval-seconds", type=int, default=30)
    args = parser.parse_args()
    manifest = []
    for index in range(max(1, args.count)):
        target = args.output
        if args.count > 1:
            target = args.output.parent / f"snapshot-{datetime.now(CST):%H-%M-%S}.json"
        try:
            payload = collect_once(target, args.mode)
        except Exception as exc:
            write_failure(target, args.mode, exc)
            raise
        manifest.append({"path": str(target), "captured_at_cst": payload["captured_at_cst"], "record_count": payload["record_count"]})
        if index + 1 < args.count:
            time.sleep(max(1, args.interval_seconds))
    if args.count > 1:
        args.output.write_text(json.dumps({"schema_version": "1.0", "run_type": args.mode, "snapshots": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
