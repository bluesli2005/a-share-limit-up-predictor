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
"$collector_python" "$skill_dir/scripts/collect_market_data.py" --mode afternoon --output "$raw_dir/manifest.json" --count 11 --interval-seconds 30 --continue-on-error --direct-only || true
"$collector_python" "$skill_dir/scripts/collect_limit_up_pool.py" --output "$raw_dir/limit-up-pool-14-20.json" || true
codex_bin=${CODEX_BIN:-codex}
"$codex_bin" exec --ephemeral --skip-git-repo-check -s workspace-write -C "$skill_dir" -o "$day_dir/14-20-prediction.md" 'Use $a-share-limit-up-predictor to run the 14:20 China Standard Time scan. Read today raw/afternoon/manifest.json, its snapshots, and limit-up-pool-14-20.json first. A failed snapshot does not invalidate successful neighboring snapshots, but disclose gaps. Verify timestamps and the SSE/SZSE trading day. Use last seal time, reopen count and queue value from the limit-up pool. Save 14-20-predictions.json following references/scheduling.md. Output T+1 probability and buyability; do not output T+2. If no separately calibrated return model exists, show expected return as unavailable. Never connect to a broker or execute trades.' </dev/null
