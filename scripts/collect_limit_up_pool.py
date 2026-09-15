#!/usr/bin/env python3
"""Collect the current Eastmoney limit-up pool with seal microstructure fields."""
import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")


def collect():
    trade_date = datetime.now(CST).strftime("%Y%m%d")
    params = {"ut":"7eea3edcaed734bea9cbfc24409ed989","dpt":"wz.ztzt","Pageindex":"0","pagesize":"10000","sort":"fbt:asc","date":trade_date}
    request = urllib.request.Request("https://push2ex.eastmoney.com/getTopicZTPool?" + urllib.parse.urlencode(params), headers={"User-Agent":"Mozilla/5.0","Referer":"https://quote.eastmoney.com/ztb/detail"})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.load(response)
    captured = datetime.now(CST).isoformat(timespec="seconds")
    records = []
    for item in ((payload.get("data") or {}).get("pool") or []):
        stats = item.get("zttj") or {}
        records.append({"ticker":str(item.get("c") or "").zfill(6),"name":item.get("n"),"last_price":item.get("p") / 1000 if item.get("p") is not None else None,"pct_change":item.get("zdp"),"turnover_value":item.get("amount"),"float_market_cap":item.get("ltsz"),"total_market_cap":item.get("tshare"),"turnover_rate":item.get("hs"),"board_count":item.get("lbc"),"first_seal_time":str(item.get("fbt") or "").zfill(6),"last_seal_time":str(item.get("lbt") or "").zfill(6),"queue_value":item.get("fund"),"reopen_count":item.get("zbc"),"industry":item.get("hybk"),"limit_up_days":stats.get("days"),"limit_up_count":stats.get("ct"),"captured_at_cst":captured})
    return {"schema_version":"1.0","run_type":"limit_up_pool","status":"success","captured_at_cst":captured,"source":"Eastmoney.getTopicZTPool","source_native_timestamp_available":False,"pool_scan_complete":len(records)<10000,"record_count":len(records),"records":records}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True, type=Path); args = parser.parse_args()
    try:
        payload = collect()
    except Exception as exc:
        payload = {"schema_version":"1.0","run_type":"limit_up_pool","status":"failure","captured_at_cst":datetime.now(CST).isoformat(timespec="seconds"),"error_type":type(exc).__name__,"error":str(exc),"record_count":0,"records":[]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if payload["status"] != "success": raise SystemExit(1)


if __name__ == "__main__": main()
