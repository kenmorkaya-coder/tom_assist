# ORCHESTRATOR REVIEW 9 — WP-26 credential boundary, wire fix, pilot run v2

**Date:** 1 September 2026

## WP-26 — accepted; credential-boundary decision recorded

Tom Assist now owns its provider authorization: PKCE-S256 browser sign-in (browser-owned, never the webview), RS256 ID-token verification against the issuer's JWKS, tokens held solely in the product's macOS Keychain entry (`local.tom.assist.oauth`, zeroize-on-drop, revocation on Disconnect), an HTTP/1.0-only 0600 UDS broker with secret-free status, one concurrent generation, and no token/header/error leakage into IPC, logs, SQLite, archives, or the webview. The OAuth path no longer reads, calls, or depends on TomOwner in any way; tom_master remains a structural-preview dependency only.

**Ruling:** this supersedes WP-21's "no product token" restriction and refines spec SEC-001. SEC-001's intent — never hold the user's password, API key, or session cookie — is preserved; a user-authorized, scoped, revocable OAuth grant in the OS keychain is the correct desktop pattern and materially safer than depending on a running TomOwner process. This change was **owner-directed in advance** — the owner explicitly advised that Tom Assist have its own API authentication and instructed the change directly (attribution confirmed 1 Sep 2026); the owner also personally performed the browser sign-in. Audit verified: 8 broker tests in the workspace suite (58 passed), secret-free status confirmed against a real broker child, zero TomOwner references in the product OAuth path.

## Wire-protocol fix (`c23529c`) — accepted

`gateway/oauth_provider.py` pins HTTP/1.0 to match the broker's bounded protocol; fixture brokers now record and require HTTP/1.0 so the test gap that hid the divergence is closed. Gateway 50 passed under audit rerun.

## ESCALATE WP25-1 — resolved: run v2 authorized

`wp25-pilot-frozen-v1` is retained permanently as an operational stop record (1 pre-send claim, 0 generations, 0 captures — the frozen stop rule fired correctly on a transport defect; no hypothesis information exists in it). The correction was transport code only: no key, threshold, seed, comparator, selection, or exclusion changed, so the frozen pre-registration stands unversioned.

**New run identity `wp25-pilot-frozen-v2` is authorized** under the same frozen plan, pinned to the corrected code SHA. The owner's 165-generation quota authorization is renewed unchanged — the original authorization was for the pilot spend and zero was consumed. All stop rules remain binding; a v2 stop before completion requires the same process again (preserve, never resume, new identity).

No G-gate verdicts exist or are implied.
