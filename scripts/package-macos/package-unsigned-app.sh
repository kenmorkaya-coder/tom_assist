#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
output_dir="$repo_dir/dist"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir) output_dir=$2; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
cd "$repo_dir"
npm run desktop:build
cargo build --release -p tom-assist-desktop --features custom-protocol

binary="$repo_dir/target/release/tom-assist-desktop"
[ -x "$binary" ] || { echo "desktop binary missing: $binary" >&2; exit 1; }
mkdir -p "$output_dir"
stage=$(mktemp -d "${TMPDIR:-/tmp}/tom-assist-app.XXXXXX")
trap 'rm -rf "$stage"' EXIT INT TERM
app="$stage/Tom Assist.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
install -m 0755 "$binary" "$app/Contents/MacOS/Tom Assist"
install -m 0644 "$repo_dir/apps/desktop/src-tauri/icons/icon.png" "$app/Contents/Resources/icon.png"
python3 - "$app/Contents/Info.plist" <<'PY'
import plistlib, pathlib, sys
payload = {
    "CFBundleDevelopmentRegion": "en",
    "CFBundleDisplayName": "Tom Assist",
    "CFBundleExecutable": "Tom Assist",
    "CFBundleIdentifier": "local.tom.assist",
    "CFBundleInfoDictionaryVersion": "6.0",
    "CFBundleName": "Tom Assist",
    "CFBundlePackageType": "APPL",
    "CFBundleShortVersionString": "0.1.0",
    "CFBundleVersion": "1",
    "LSMinimumSystemVersion": "11.0",
    "NSHighResolutionCapable": True,
}
pathlib.Path(sys.argv[1]).write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True))
PY
printf 'APPL????' >"$app/Contents/PkgInfo"

destination="$output_dir/Tom Assist.app"
if [ -e "$destination" ]; then
  previous="$output_dir/Tom Assist.previous.app"
  [ ! -e "$previous" ] || { echo "refusing to overwrite both current and previous app artifacts" >&2; exit 1; }
  mv "$destination" "$previous"
  echo "preserved prior artifact: $previous"
fi
mv "$app" "$destination"
echo "unsigned app: $destination"
echo "bundle id: $(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$destination/Contents/Info.plist")"
echo "signature: unsigned development artifact (signing/notarization is out of scope)"
