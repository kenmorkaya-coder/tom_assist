#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
target_root=${HOME}
source_binary="$repo_dir/target/release/tom-assist-native-host"
skip_build=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target-root) target_root=$2; shift 2 ;;
    --binary) source_binary=$2; skip_build=true; shift 2 ;;
    --skip-build) skip_build=true; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if ! $skip_build; then (cd "$repo_dir" && cargo build --release -p tom-assist-native-host); fi
[ -x "$source_binary" ] || { echo "native host binary not executable: $source_binary" >&2; exit 1; }

app_support="$target_root/Library/Application Support/TomAssist"
bin_dir="$app_support/bin"
chrome_dir="$target_root/Library/Application Support/Google/Chrome/NativeMessagingHosts"
installed_binary="$bin_dir/tom-assist-native-host-bin"
launcher="$bin_dir/tom-assist-native-host"
manifest="$chrome_dir/tom.assist.native.json"
mkdir -p "$bin_dir" "$chrome_dir"
install -m 0755 "$source_binary" "$installed_binary"
printf '%s\n' '#!/bin/sh' "export TOM_ASSISTD_SOCKET='$app_support/tom-assistd.sock'" "exec '$installed_binary' \"\$@\"" >"$launcher"
chmod 0755 "$launcher"
python3 - "$manifest" "$launcher" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
payload = {
    "name": "tom.assist.native",
    "description": "Tom Assist local native messaging bridge",
    "path": sys.argv[2],
    "type": "stdio",
    "allowed_origins": ["chrome-extension://mollhhfpcdpgbnlinhhghkndeniglfba/"],
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
chmod 0644 "$manifest"
echo "installed native host: $installed_binary"
echo "installed Chrome manifest: $manifest"
echo "allowlisted extension: mollhhfpcdpgbnlinhhghkndeniglfba"
