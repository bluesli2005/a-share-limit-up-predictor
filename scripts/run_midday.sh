#!/bin/zsh
set -eu
skill_dir=${0:A:h:h}
stamp=$(TZ=Asia/Shanghai date +%Y-%m-%d)
raw_dir="$skill_dir/outputs/$stamp/raw/midday"
mkdir -p "$raw_dir"
collector_python="$skill_dir/.venv/bin/python"
if [[ ! -x "$collector_python" ]]; then collector_python=python3; fi
audit_file="$raw_dir/run-audit.json"
final_status=failed
finish_audit() {
  exit_code=$?
  "$collector_python" "$skill_dir/scripts/write_run_audit.py" \
    --output "$audit_file" --run-type midday --scheduled-time 11:30 \
    --event "$final_status" --exit-code "$exit_code" || true
  return "$exit_code"
}
trap finish_audit EXIT
"$collector_python" "$skill_dir/scripts/write_run_audit.py" \
  --output "$audit_file" --run-type midday --scheduled-time 11:30 --event started

set +e
"$collector_python" "$skill_dir/scripts/check_trading_day.py" --output "$raw_dir/trading-day-check.json"
calendar_status=$?
set -e
if [[ $calendar_status -ne 0 ]]; then
  final_status=skipped_non_trading_day
  exit 0
fi

# Allow the morning close's final quote to settle after the 11:30 CST trigger.
sleep 8
collection_status=0
"$collector_python" "$skill_dir/scripts/collect_with_retries.py" \
  --python "$collector_python" --scripts-dir "$skill_dir/scripts" --raw-dir "$raw_dir" \
  --mode midday --max-attempts 3 --retry-delay-seconds 5 || collection_status=$?
"$collector_python" "$skill_dir/scripts/write_run_audit.py" \
  --output "$audit_file" --run-type midday --scheduled-time 11:30 \
  --event collection_finished --exit-code "$collection_status"
if [[ $collection_status -ne 0 ]]; then
  final_status=data_quality_failure
  exit "$collection_status"
fi
final_status=completed
