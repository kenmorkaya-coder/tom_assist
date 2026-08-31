#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
tom_master_dir=${TOM_MASTER_DIR:-"$(dirname "$repo_dir")/tom_master"}
app_support=${TOM_ASSIST_APP_SUPPORT:-"$HOME/Library/Application Support/TomAssist"}
gateway_python="$repo_dir/.venv-gateway/bin/python"
check_only=false

if [ "${1:-}" = "--check" ]; then check_only=true; fi

for command in cargo npm python3 curl; do
  command -v "$command" >/dev/null 2>&1 || { echo "missing command: $command" >&2; exit 1; }
done
[ -x "$gateway_python" ] || { echo "missing .venv-gateway; follow docs/DEV_RUNBOOK.md" >&2; exit 1; }
[ -d "$tom_master_dir/.git" ] || { echo "tom_master not found at $tom_master_dir; set TOM_MASTER_DIR" >&2; exit 1; }

actual_sha=$(git -C "$tom_master_dir" rev-parse HEAD)
case "$actual_sha" in
  e9fdef81c*) ;;
  *) echo "warning: tom_master is $actual_sha, expected e9fdef81c" >&2 ;;
esac

if $check_only; then
  echo "dev prerequisites ready"
  echo "tom_master=$actual_sha"
  echo "app_support=$app_support"
  exit 0
fi

mkdir -p "$app_support/logs" "$app_support/projects"
gateway_socket="$app_support/tom_gateway.sock"
assistd_socket="$app_support/tom-assistd.sock"
database="$app_support/tom-assist.sqlite3"

cd "$repo_dir"
cargo build -p tom-assistd -p tom-assist-desktop -p tom-assist-native-host

gateway_pid=""; assistd_pid=""; vite_pid=""
cleanup() {
  [ -z "$vite_pid" ] || kill "$vite_pid" 2>/dev/null || true
  [ -z "$assistd_pid" ] || kill "$assistd_pid" 2>/dev/null || true
  [ -z "$gateway_pid" ] || kill "$gateway_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

PYTHONPATH="$tom_master_dir:$repo_dir" "$gateway_python" -m gateway.tom_gateway --socket "$gateway_socket" --data-dir "$app_support" --tom-master "$tom_master_dir" >"$app_support/logs/gateway.log" 2>&1 &
gateway_pid=$!
"$repo_dir/target/debug/tom-assistd" "$assistd_socket" "$database" >"$app_support/logs/assistd.log" 2>&1 &
assistd_pid=$!
npm run dev -w @tom-assist/desktop-ui >"$app_support/logs/desktop-ui.log" 2>&1 &
vite_pid=$!

attempt=0
until curl --silent --fail http://127.0.0.1:1420/ >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 40 ] || { echo "desktop UI did not start; see $app_support/logs/desktop-ui.log" >&2; exit 1; }
  sleep 0.25
done

echo "gateway socket: $gateway_socket"
echo "assistd socket: $assistd_socket"
echo "desktop logs: $app_support/logs"
TOM_ASSIST_APP_SUPPORT="$app_support" TOM_ASSIST_GATEWAY_SOCKET="$gateway_socket" TOM_ASSISTD_SOCKET="$assistd_socket" cargo run -p tom-assist-desktop
