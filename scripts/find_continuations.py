#!/usr/bin/env python3
"""Compare a live snapshot with recent daily closes to find provisional continuations."""
import argparse
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def limit_threshold(ticker):
    return 19.8 if ticker.startswith(("300", "301", "688")) else 9.8


def daily_rows(ticker, count=12):
    market = "1" if ticker.startswith("6") else "0"
    params = {
        "secid": f"{market}.{ticker}", "klt": 101, "fqt": 1,
        "lmt": count, "end": "20500101", "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    query = urllib.parse.urlencode(params)
    errors = []
    for host in ("push2his.eastmoney.com", "61.push2his.eastmoney.com"):
        try:
            request = urllib.request.Request(
                f"https://{host}/api/qt/stock/kline/get?{query}",
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = json.load(response)
            lines = ((payload.get("data") or {}).get("klines") or [])
            if lines:
                return [line.split(",") for line in lines], host
        except Exception as exc:
            errors.append(f"{host}: {type(exc).__name__}: {exc}")
    raise RuntimeError(" | ".join(errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.input.read_text(encoding="utf-8"))
    results, failures = [], []
    candidates = []
    for row in snapshot.get("records", []):
        ticker, name = row["ticker"], row.get("name", "")
        threshold = limit_threshold(ticker)
        if "ST" in name.upper() or float(row.get("pct_change") or -999) < threshold:
            continue
        candidates.append((row, threshold))

    def compare(item):
        row, threshold = item
        ticker, name = row["ticker"], row.get("name", "")
        history, source_host = daily_rows(ticker)
        previous = history[-2] if len(history) >= 2 else None
        if not previous or float(previous[8]) < threshold:
            return None
        streak = 1
        for daily in reversed(history[:-1]):
            if float(daily[8]) >= threshold:
                streak += 1
            else:
                break
        return {
            "ticker": ticker, "name": name, "board_count_provisional": streak,
            "live_price": row.get("last_price"), "live_pct_change": row.get("pct_change"),
            "previous_trade_date": previous[0], "previous_close": float(previous[2]),
            "previous_pct_change": float(previous[8]), "threshold_pct": threshold,
            "total_market_cap": row.get("total_market_cap"),
            "float_market_cap": row.get("float_market_cap"),
            "daily_source": source_host,
            "passes_market_cap": (row.get("total_market_cap") or 0) >= 10_000_000_000 and (row.get("float_market_cap") or 0) >= 5_000_000_000,
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_rows = {executor.submit(compare, item): item[0]["ticker"] for item in candidates}
        for future in as_completed(future_rows):
            ticker = future_rows[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as exc:
                failures.append({"ticker": ticker, "error": str(exc)})
    output = {
        "schema_version": "1.0", "comparison_type": "provisional_intraday_continuation",
        "snapshot": str(args.input), "captured_at_cst": snapshot.get("captured_at_cst"),
        "records": sorted(results, key=lambda x: (-x["board_count_provisional"], -x["live_pct_change"])),
        "failures": failures,
        "limitations": ["intraday result, not a closing confirmation", "simple board-based threshold; IPO and exceptional price-limit status require separate verification"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
