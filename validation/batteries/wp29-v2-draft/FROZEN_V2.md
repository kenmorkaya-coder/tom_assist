# WP-29 owner freeze — `wp29-prereg-frozen/2`

Frozen 1 September 2026 (Australia/Sydney) under
`ORCHESTRATOR_REVIEW_11.md`. This overlay freezes the accepted v2 draft without
editing it. The source pre-registration remains byte-for-byte at SHA-256
`c0add32c150fcee48e0f582ce3246c46982da3bf7567b866122266451317061d`.

## Frozen owner decisions

1. The sole criterion change from v1 is `typed-action-oracle/2`: the
   `cited_state_ids` and `historical_state_ids` fields use order-insensitive,
   duplicate-sensitive multiset comparison. All other answer fields remain
   exact as documented.
2. H1/H0/H2/H3 meanings, all margins, the 33-case selection, five-arm rotation,
   165-generation size, bootstrap seed 1729, floor-only injection rule,
   self-report-off setting, one-capture/no-retry discipline and stop rules are
   unchanged.
3. The corrected executable source is pinned by file hashes in `manifest.json`;
   its code commit is `9c3c5d3` (`fix(wp-29): add substrate engagement
   telemetry`). Substrate engagement must lead the report and remains execution
   telemetry, not efficacy evidence.
4. Pilot v3 is separately owner-authorized under
   `TOM_ASSIST_WP29_V3_LIVE=1` for exactly 165 logical generations. A stop is
   permanent for this run identity: preserve partial artifacts, never resume or
   resend, and require a new identity plus renewed authorization.
5. This freeze and pilot can resolve only the frozen pilot hypotheses. Neither
   may issue or imply a specification G-gate verdict.

The machine manifest records the canonical freeze payload and its SHA-256.
