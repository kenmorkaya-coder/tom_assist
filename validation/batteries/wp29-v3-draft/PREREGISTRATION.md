# DRAFT-PENDING-OWNER-FREEZE — WP-29 pre-registration v3 amendment

Version `wp29-prereg-draft/3`, 1 September 2026 (Australia/Sydney).

This is a versioned amendment to frozen pre-registration v2. The complete v2
registration remains at `validation/batteries/wp29-v2-draft/` and is inherited
by its recorded freeze SHA. Nothing in that retained artifact is copied,
reworded, or replaced. The scientific delta is exactly the following five
owner-approved clauses.

1. **Per-observation unknown-outcome disposition.** If an observation has an
   explicit-send record but no captured response because the provider call
   errors or reaches its deadline, record `unknown_outcome`, never resend that
   observation, and continue with the next independent observation. A case
   containing any unknown arm is excluded in full from paired analysis and is
   reported as excluded.
2. **Invalidity cap.** More than eight unknown outcomes permanently stops and
   invalidates the run. The ninth unknown outcome is preserved; no later
   observation is started.
3. **Primary validity bound.** H1 is interpretable only when at least 30 of the
   33 selected cases are complete across all five arms. Below 30 complete cases,
   H1 is `INVALID_INCOMPLETE`; incomplete data are not evidence for H0.
4. **Observation timing.** The per-observation timeout is 600 seconds. Wall time
   is recorded for every captured or unknown-outcome disposition.
5. **Inheritance lock.** Everything else is byte-inherited from frozen v2:
   margins, selection and arm order, 165-observation size, seed 1729, the
   duplicate-sensitive multiset citation comparator, self-report off, one
   capture/no retry/no best-of, integrity-event stop rules, floor-only no-rot
   rule, provider/quota boundaries, hypotheses, artifact retention, renderer,
   policy, runtime and implementation pins.

Version/freeze identifiers, file hashes, owner-review provenance, and the run
identity are administrative freeze mechanics, not additional scientific
changes. A live run remains forbidden until this amendment is frozen with
`owner_frozen:true` and separately authorized.

**DRAFT-PENDING-OWNER-FREEZE. No live run performed under this version.**
