# Tom Assist Extension

Manifest V3 + Preact extension. The MV3 service worker validates protocol
envelopes, persists held transactions in `chrome.storage.session`, and talks to
the exact allowlisted native host.

The committed manifest key fixes the unpacked extension ID at
`mollhhfpcdpgbnlinhhghkndeniglfba`. Its private key lives only in the ignored
`apps/extension/.keys/extension-private.pem`. Regenerating it intentionally
changes the ID, so update `manifest.json`, the native-host manifest, Rust's
`EXTENSION_ID`, and installed host manifests together.
