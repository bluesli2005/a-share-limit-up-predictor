#!/bin/zsh
set -eu
skill_dir=${0:A:h:h}
stamp=$(TZ=Asia/Shanghai date +%Y-%m-%d)
output_dir="$skill_dir/outputs"
day_dir="$output_dir/$stamp"
mkdir -p "$day_dir"
raw_dir="$day_dir/raw/afternoon"
mkdir -p "$raw_dir"
collector_python="$skill_dir/.venv/bin/python"
if [[ ! -x "$collector_python" ]]; then collector_python=python3; fi
"$collector_python" "$skill_dir/scripts/collect_market_data.py" --mode afternoon --output "$raw_dir/manifest.json" --count 1 --interval-seconds 30 --continue-on-error || true
"$collector_python" "$skill_dir/scripts/collect_limit_up_pool.py" --output "$raw_dir/limit-up-pool-14-40.json" || true
midday_dir="$day_dir/raw/midday"
"$collector_python" "$skill_dir/scripts/compare_intraday_snapshots.py" \
  --midday-market "$midday_dir/market-11-30.json" \
  --midday-pool "$midday_dir/limit-up-pool-11-30.json" \
  --afternoon-market "$raw_dir/manifest.json" \
  --afternoon-pool "$raw_dir/limit-up-pool-14-40.json" \
  --output "$day_dir/11-30-to-14-40-comparison.json" || true
codex_bin=${CODEX_BIN:-codex}
"$codex_bin" exec --ephemeral --skip-git-repo-check -s workspace-write -C "$skill_dir" -o "$day_dir/14-40-prediction.md" 'Use $a-share-limit-up-predictor to run the 14:40 China Standard Time scan. Read today raw/afternoon/manifest.json, limit-up-pool-14-40.json, and 11-30-to-14-40-comparison.json first. Use the comparison only as point-in-time evidence: report price-change delta, afternoon new seals/openings, queue-value change, turnover and turnover-rate increments, volume-ratio change, sector-breadth change, and strengthened/weakened labels when available. Verify timestamps and the SSE/SZSE trading day. Save 14-40-predictions.json following references/scheduling.md. Output T+1 probability and buyability; do not output a separate 11:30 prediction or T+2. If no separately calibrated return model exists, show expected return as unavailable. Never connect to a broker or execute trades.' </dev/null
