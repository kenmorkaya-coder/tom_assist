# Tom Assist v1.2 developer runbook

This is a local-only alpha walkthrough for macOS. It does not run or assert any G-gate. Live provider selector validation, signing/notarization, SQLCipher/Keychain, cloud services, and Layer 2 routing are outside this build.

## 1. Prerequisites and checkout

Install Xcode Command Line Tools, Rust stable, Python 3.11+, and Node.js 20+. Keep the pinned read-only runtime beside this checkout:

```sh
git clone <tom-assist-repository> ToM_assist
git clone <approved-tom-master-repository> tom_master
cd ToM_assist
git -C ../tom_master rev-parse HEAD
```

The expected tom_master prefix is `8799ccbdd`. Do not run this project against `tom_master17D`; it is outside the authorized boundary.

## 2. Install build-only dependencies

```sh
npm ci
python3 -m venv .venv-gateway
.venv-gateway/bin/python -m pip install -r gateway/requirements-dev.txt
cargo build --workspace
npm run extension:build
```

No product path needs an LLM API, provider credential, cookie, telemetry endpoint, or other network service.

## 3. Build verification

```sh
cargo test --workspace
npm run schema:validate
npm run adapters:test
npm run extension:test
npm run desktop:test
PYTHONPATH="$(cd ../tom_master && pwd):$PWD" .venv-gateway/bin/python -m pytest -q gateway/tests
python3 -m unittest discover -s validation/tests -v
scripts/dev-run.sh --check
```

The gateway live UDS and Rust UDS tests require a normal macOS shell capable of binding a Unix socket. These are build-verification results only.

## 4. Start the local stack

```sh
scripts/dev-run.sh
```

The script starts user-only sockets and SQLite under `~/Library/Application Support/TomAssist`, writes local logs there, and keeps the Tauri window in the foreground. Stop it with Control-C. The desktop also maintains its Tauri app-data database and idempotently seeds the neutral 30-turn demo.

In the desktop window:

1. Confirm `Local Release Console` shows 16 state objects and state version 16.
2. Create and rename a project, quick-capture a decision, supersede it with a reason, and inspect the Audit view.
3. Review Interventions, mark a fixture finding accepted or false-positive when present, then inspect Settings and Diagnostics.
4. Export a project to an empty directory and import it; checksum verification occurs before import.

## 5. Install and load the Chromium extension

With the release native bridge built, install its per-user Chrome manifest:

```sh
cargo build --release -p tom-assist-native-host
scripts/install-native-host/install.sh --skip-build
```

The manifest is installed at `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/tom.assist.native.json` and allowlists only pinned extension ID `mollhhfpcdpgbnlinhhghkndeniglfba`.

Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select the absolute `apps/extension/dist` directory. Confirm the displayed ID exactly matches the pinned ID. The production manifest grants only `https://chatgpt.com/*`, native messaging, storage, and side-panel permissions.

On an explicitly supported fixture/provider page, open the side panel and attach a project ID. A user-initiated submit must show packet text, categories, warnings, and exclusions. Exercise **Send with Tom**, **Send once without Tom**, **Cancel**, and **Detach project**. Inserted state remains visible in the composer. When the service is unavailable, sending remains held until the user explicitly chooses the bypass.

Live `chatgpt.com` selector verification is intentionally not claimed by this shot; fixture regression and clean detach are the supported evidence.

## 6. Create an unsigned `.app`

```sh
scripts/package-macos/package-unsigned-app.sh
open "dist/Tom Assist.app"
```

This creates an unsigned development artifact with bundle ID `local.tom.assist`. macOS may require an explicit local security exception. Signing and notarization are out of scope.

## 7. Harness plumbing dry-run

```sh
python3 -m validation.harness \
  --input validation/fixtures/toy_cases.jsonl \
  --output-dir .tmp/harness-dry-run
```

Open `.tmp/harness-dry-run/report.md`. It must say `NOT-A-GATE`, list SUB-A through SUB-E, contain 15 Appendix-C-format observations, and report zero gate verdicts. The three toy cases are plumbing smoke fixtures, not a validation battery.

## 8. Shutdown and local data

Control-C stops the dev script's child processes. Databases, logs, exports, and checkpoints remain local. Remove or archive those user-owned files manually only when intended; none of the scripts erase project data.
