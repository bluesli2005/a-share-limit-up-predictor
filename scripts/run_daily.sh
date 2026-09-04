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
"$collector_python" "$skill_dir/scripts/collect_market_data.py" --mode afternoon --output "$raw_dir/manifest.json" --count 11 --interval-seconds 30 || true
codex_bin=${CODEX_BIN:-codex}
"$codex_bin" exec --ephemeral --skip-git-repo-check -s workspace-write -C "$skill_dir" -o "$day_dir/14-30-prediction.md" 'Use $a-share-limit-up-predictor to run the 14:30 China Standard Time scan. Read today raw/afternoon/manifest.json and its snapshots first. Verify source timestamps and the SSE/SZSE trading day; retrieval time is not proof of provider freshness. Derive price path only from archived point-in-time snapshots. Save machine-readable predictions following references/scheduling.md. If checks fail, save failure records and do not rank stocks. Never connect to a broker or execute trades.'
