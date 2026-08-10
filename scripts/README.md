# Developer scripts

- `dev-run.sh` validates the pinned runtime, starts the gateway, assistd, desktop Vite UI, and Tauri debug shell, and cleans up its child processes on exit.
- `install-native-host/install.sh` installs the native bridge and exact-extension manifest into Chrome's per-user macOS directory. `--target-root` supports non-mutating smoke tests.
- `package-macos/package-unsigned-app.sh` builds an unsigned local release `.app` with embedded frontend assets; an existing artifact is preserved once as `Tom Assist.previous.app`. Debug binaries are intentionally excluded because they require the Vite dev server.

See [`docs/DEV_RUNBOOK.md`](../docs/DEV_RUNBOOK.md) for the complete fresh-checkout sequence.
