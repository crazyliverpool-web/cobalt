#!/bin/zsh
# Claude → agy (Google Antigravity CLI) job runner. Each job gets its own folder under outputs/.
# Usage: agy-cli/run.sh [--role image|checker|extractor|reviewer|editor] [--model <id>] [--add-dir <dir>]... <job-name> "<task>" [ref-file ...]
#   --add-dir  give agy a folder to read (e.g. source/<TICKER>/); say "read only" in the task — writes there are
#              not in settings.json's allow list, but the sandbox treats added dirs as workspace, so check git diff after.
#   Always offline: agy runs with its terminal sandbox (no network) and the allow/deny rules in
#   ~/.gemini/antigravity-cli/settings.json (writes only under agy-cli/outputs/). No permission bypass.
#   Reference files are copied into the job folder and named in the task.
#   Prints the job folder path, then agy's final report (STATUS/FILES/SOURCES/NOTES).
set -euo pipefail

HERE="${0:A:h}"
role=""; model=""; add_dirs=()
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --role) role="${2:?role name required}"; shift 2 ;;
    --model) model="${2:?model id required}"; shift 2 ;;
    --add-dir) add_dirs+=(--add-dir "${${2:?dir required}:A}"); shift 2 ;;
    *) echo "STATUS: failed"; echo "NOTES: unknown option $1 (agy runner is offline-only)"; exit 1 ;;
  esac
done
[[ -z $role || -f "$HERE/roles/$role.md" ]] || { echo "STATUS: failed"; echo "NOTES: unknown role $role"; exit 1; }
job="${1:?job name required}"; task="${2:?task required}"; shift 2
command -v agy >/dev/null || { echo "STATUS: failed"; echo "NOTES: agy not installed — brew install --cask antigravity-cli"; exit 1; }

dir="$HERE/outputs/$(date +%Y%m%d-%H%M)-$job"
mkdir -p "$dir/refs"

refs=""
for ref in "$@"; do cp "${ref:A}" "$dir/refs/"; refs+="
- $dir/refs/${ref:t}"; done

full_task="NETWORK MODE: offline
JOB DIR: $dir

$(<"$HERE/AGENTS.md")"
[[ -n $role ]] && full_task+="

$(<"$HERE/roles/$role.md")"
[[ -n $refs ]] && full_task+="

รูป/ไฟล์อ้างอิง:$refs"
full_task+="

## งาน
$task"
print -r -- "$full_task" > "$dir/task.txt"
echo "JOB: $dir  (role: ${role:-none})"

model_args=(); [[ -n $model ]] && model_args=(--model "$model")
# stdin closed so print mode never waits for input. Permissions that settings.json doesn't
# allow are soft-denied (run continues), so check FILES on disk, not just the report.
( cd "$dir" && agy -p "$full_task" --sandbox --mode accept-edits "${model_args[@]}" "${add_dirs[@]}" \
    --print-timeout 900s </dev/null > "$dir/report.txt" 2> "$dir/agy.log" ) || true

echo "$(date '+%F %T')  $job  [${role:-none}]  $dir" >> "$HERE/outputs/jobs.log"
if [[ -s "$dir/report.txt" ]]; then cat "$dir/report.txt"
else echo "STATUS: failed"; echo "NOTES: no report — see $dir/agy.log"; tail -20 "$dir/agy.log"; fi
grep -i 'denied' "$dir/agy.log" 2>/dev/null | sed 's/^/DENIED: /' || true
