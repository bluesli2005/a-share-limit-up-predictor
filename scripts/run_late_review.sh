#!/bin/zsh
set -eu
skill_dir=${0:A:h:h}
stamp=$(TZ=Asia/Shanghai date +%Y-%m-%d)
day_dir="$skill_dir/outputs/$stamp"
raw_dir="$day_dir/raw/afternoon"
mkdir -p "$raw_dir"
collector_python="$skill_dir/.venv/bin/python"
if [[ ! -x "$collector_python" ]]; then collector_python=python3; fi
"$collector_python" "$skill_dir/scripts/collect_limit_up_pool.py" --output "$raw_dir/limit-up-pool-14-50.json" || true
codex_bin=${CODEX_BIN:-codex}
"$codex_bin" exec --ephemeral --skip-git-repo-check -s workspace-write -C "$skill_dir" -o "$day_dir/14-50-late-review.md" 'Use $a-share-limit-up-predictor for a 14:50 CST late-seal T+1 update. Compare raw/afternoon/limit-up-pool-14-20.json with limit-up-pool-14-50.json and 14-20-predictions.json. Report stocks still sealed, newly opened, newly sealed, queue-value decay and reopen-count changes. Recalculate and display T+1 limit-up probability and buyability. Display expected next-day return or a return range only if a separately calibrated return model exists; otherwise show unavailable. Do not output any T+2 probability. Preserve the original 14:20 prediction and write 14-50-late-review.json separately. Never execute trades.' </dev/null
