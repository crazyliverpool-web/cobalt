#!/bin/zsh
# Claude → Codex job runner. Each job gets its own folder under outputs/.
# Usage: codex-cli/run.sh [--web|--net] [--role image|checker|extractor|reviewer|editor] <job-name> "<task>" [ref-image ...]
#   (default)  offline: no web search, shell commands have no network
#   --web      Codex's web_search tool only; shell commands still offline
#   --net      web_search + network for shell commands (curl/downloads) — grant only when the job needs it
#   prints the job folder path, then Codex's final report (STATUS/FILES/SOURCES/NOTES),
#   then a NET-AUDIT block listing risky shell commands Codex ran (uploads, POSTs, remote copies).
set -euo pipefail

HERE="${0:A:h}"
mode=offline
role=""
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --web) mode=web; shift ;;
    --net) mode=net; shift ;;
    --role) role="${2:?role name required}"; shift 2 ;;
    *) echo "STATUS: failed"; echo "NOTES: unknown option $1"; exit 1 ;;
  esac
done
[[ -z $role || -f "$HERE/roles/$role.md" ]] || { echo "STATUS: failed"; echo "NOTES: unknown role $role"; exit 1; }
job="${1:?job name required}"; task="${2:?task required}"; shift 2

codex login status >/dev/null 2>&1 || { echo "STATUS: failed"; echo "NOTES: codex not logged in — run: codex login"; exit 1; }

dir="$HERE/outputs/$(date +%Y%m%d-%H%M)-$job"
mkdir -p "$dir"

img_args=()
for ref in "$@"; do img_args+=(-i "${ref:A}"); done

top_args=(); net_args=()
[[ $mode != offline ]] && top_args=(--search)
[[ $mode == net ]] && net_args=(-c sandbox_workspace_write.network_access=true)

# Codex reads the mode from the task header so AGENTS.md rules for that mode apply.
# stdin must be closed: `codex exec` otherwise waits forever on "Reading additional input from stdin".
# Role and network rules are added only when the job needs them, to keep every job's context small.
full_task="NETWORK MODE: $mode"
[[ $mode != offline ]] && full_task+="

$(<"$HERE/rules/network.md")"
[[ -n $role ]] && full_task+="

$(<"$HERE/roles/$role.md")"
full_task+="

$task"
print -r -- "$full_task" > "$dir/task.txt"
echo "JOB: $dir  (network: $mode, role: ${role:-none})"
codex "${top_args[@]}" exec -s workspace-write "${net_args[@]}" -C "$dir" "${img_args[@]}" \
  -o "$dir/report.txt" "$full_task" </dev/null > "$dir/codex.log" 2>&1 || true

echo "$(date '+%F %T')  $job  [$mode${role:+/$role}]  $dir" >> "$HERE/outputs/jobs.log"
cat "$dir/report.txt" 2>/dev/null || { echo "STATUS: failed"; echo "NOTES: no report — see $dir/codex.log"; tail -20 "$dir/codex.log"; }

if [[ $mode == net ]]; then
  echo; echo "NET-AUDIT:"
  grep -E '^/bin/(zsh|bash|sh) -lc' "$dir/codex.log" \
    | grep -E -i 'curl.*(-X ?(POST|PUT)|-d |--data|-F |--form|-T |--upload)|wget.*--post|scp |rsync .*:|sftp|ftp |nc |ncat|ssh |\| *(sh|bash|zsh|python)|gh |git push' \
    || echo "(no risky network commands found)"
fi
