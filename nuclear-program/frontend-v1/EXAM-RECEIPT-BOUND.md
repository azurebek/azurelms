# Exam applied-receipt bound — admission 2026-09-26

ADMIT — launch-critical. Owner explicitly approved configurable protection
after PR140 review4110573482 identified unbounded successful-action receipts.
Outcome: repeated allowed actions cannot grow recovery rows without a bound;
KPI: at most the configured number per learner/exam after an applied command.

Canonical mutation service will retain the newest configured receipt count
(default1000, validated1–10000), independently of attempts. The existing
owner-only audited runtime settings surface will expose this one value with
reason, confirmation, audit and no-op behavior; no new control plane.

Under the existing user lock and action transaction, eviction rotates the
server-issued epoch before removing old technical receipts. Exact delayed
requests with an evicted identity carry an obsolete epoch and cannot write.
Retained receipts still deduplicate; an absent receipt from an old epoch is
explicitly uncertain, never falsely reported as applied or cancelled. The
browser closes its pending identity, keeps its draft and requires inspection
of current server state, without automatic resend.

Only technical recovery receipts are evicted; answers, files, grades, attempts
and audit events are not deleted. Reducing the cap applies on the next new
successful action for each learner/exam; no broad background cleanup. No new
time-based retention, request-rate policy or limit on answering/listening.

Feature OFF restores the legacy renderer; the epoch check and uncertainty
reconciliation remain fail-closed. Additive core migration precedes code.
No current DB/AWS mutation in this task. Required tests: bound/scoping, live
configuration/audit/no-op/permissions, evicted delayed request, retained retry,
unknown draft recovery, transactional rollback and real PostgreSQL race.

## Implementation and evidence

Runtime `842edb4`, additive `core0006`. Owner mutation path remains
`/backoffice/control/runtime-settings/`; Django admin is read-only.

- [x] ~~Configurable bound, atomic epoch rotation/eviction, honest recovery.~~
- [x] ~~Provider-free focused exam/settings85 OK skip6 (9.511s), Node110 PASS;
  migration drift0/diff PASS. New PG eviction race is included in the skips.~~
- [x] ~~Isolated IAB8069: lost ack in first tab, two later saves in second tab
  evict it; explicit recovery reports uncertainty, preserves stale draft,
  never resends. Owner changes cap2→3 with reason/confirmation and audit.~~
- [ ] Final full suite and fresh required CI/review/main acceptance.

Browser screenshot: `playground/frontend-v1-smoke/i8b-receipt-admin-desktop.png`.
Desktop actual1280, page overflow0 and owner console0. Viewport requests320
did not apply to this hidden admin tab (actual readback stayed1280); no new
mobile verification claim for this added panel. Prior I8b six-width evidence
remains historical, not a substitute for this panel's mobile release gate.
The initial student→owner URL attempt redirected repeatedly; explicitly
logging out of the synthetic student and signing in as synthetic owner worked.
No auth/access policy was weakened or bypassed.

Full-suite checkpoint: first run exited0 (summary output truncated); repeat
reported2236, failures3, skip52 in11103.767s. Do not claim final full green.
Windows Power-Troubleshooter event1 confirms the host slept during that run:
2026-09-26T10:41:17Z→13:42:48Z. A diagnostic rerun also crossed host sleep
13:45:15Z→16:26:07Z; failure names/isolated rerun and fresh cloud CI are pending.
No assertion was weakened and no speculative runtime fix was made for these
failures. Machine power settings were not changed. Merge remains held.
