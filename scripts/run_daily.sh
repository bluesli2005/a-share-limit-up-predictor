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
"$collector_python" "$skill_dir/scripts/collect_with_retries.py" \
  --python "$collector_python" --scripts-dir "$skill_dir/scripts" --raw-dir "$raw_dir" \
  --max-attempts 3 --retry-delay-seconds 5 || true
midday_dir="$day_dir/raw/midday"
"$collector_python" "$skill_dir/scripts/compare_intraday_snapshots.py" \
  --midday-market "$midday_dir/market-11-30.json" \
  --midday-pool "$midday_dir/limit-up-pool-11-30.json" \
  --afternoon-market "$raw_dir/manifest.json" \
  --afternoon-pool "$raw_dir/limit-up-pool-14-40.json" \
  --output "$day_dir/11-30-to-14-40-comparison.json" || true
codex_bin=${CODEX_BIN:-codex}
<<<<<<< Updated upstream
"$codex_bin" exec --ephemeral --skip-git-repo-check -s workspace-write -C "$skill_dir" -o "$day_dir/14-40-prediction.md" 'Use $a-share-limit-up-predictor to run the 14:40 China Standard Time scan. Read today raw/afternoon/collection-attempts.json, manifest.json, limit-up-pool-14-40.json, and 11-30-to-14-40-comparison.json first. Report how many collection attempts were required. Use the comparison only as point-in-time evidence: report price-change delta, afternoon new seals/openings, queue-value change, turnover and turnover-rate increments, volume-ratio change, sector-breadth change, and strengthened/weakened labels when available. Verify timestamps and the SSE/SZSE trading day. Save 14-40-predictions.json following references/scheduling.md. Output T+1 probability and buyability; do not output a separate 11:30 prediction or T+2. If no separately calibrated return model exists, show expected return as unavailable. Never connect to a broker or execute trades.' </dev/null
=======
"$codex_bin" exec --ephemeral --skip-git-repo-check -s workspace-write -C "$skill_dir" -o "$day_dir/14-40-prediction.md" 'Use $a-share-limit-up-predictor to run the 14:40 China Standard Time scan. Read today raw/afternoon/collection-attempts.json, manifest.json, limit-up-pool-14-40.json, and 11-30-to-14-40-comparison.json first. Generate a complete, formal, human-readable Markdown report in 14-40-prediction.md and save machine-readable 14-40-predictions.json only for archive, comparison, and backtesting. Report how many collection attempts were required and distinguish collection success from formal data usability. Use the comparison only as point-in-time evidence: report price-change delta, afternoon new seals/openings, queue-value change, turnover and turnover-rate increments, volume-ratio change, sector-breadth change, and strengthened/weakened labels when available. Verify timestamps and the SSE/SZSE trading day. Output T+1 probability and buyability; do not output a separate 11:30 prediction or T+2. If no separately calibrated return model exists, show expected return as unavailable. Never connect to a broker or execute trades.' </dev/null
final_status=completed
>>>>>>> Stashed changes
