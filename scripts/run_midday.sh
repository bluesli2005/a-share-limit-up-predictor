#!/bin/zsh
set -eu
skill_dir=${0:A:h:h}
stamp=$(TZ=Asia/Shanghai date +%Y-%m-%d)
raw_dir="$skill_dir/outputs/$stamp/raw/midday"
mkdir -p "$raw_dir"
collector_python="$skill_dir/.venv/bin/python"
if [[ ! -x "$collector_python" ]]; then collector_python=python3; fi

set +e
"$collector_python" "$skill_dir/scripts/check_trading_day.py" --output "$raw_dir/trading-day-check.json"
calendar_status=$?
set -e
if [[ $calendar_status -ne 0 ]]; then
  exit 0
fi

# Allow the morning close's final quote to settle after the 11:30 CST trigger.
sleep 8
"$collector_python" "$skill_dir/scripts/collect_market_data.py" --mode midday \
  --output "$raw_dir/market-11-30.json" --count 1 --interval-seconds 1 --continue-on-error || true
"$collector_python" "$skill_dir/scripts/collect_limit_up_pool.py" \
  --output "$raw_dir/limit-up-pool-11-30.json" || true
