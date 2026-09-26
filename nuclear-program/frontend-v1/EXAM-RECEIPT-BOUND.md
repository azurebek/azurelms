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
- [x] ~~Final provider-free full suite2236 OK skip52 (168.837s).~~
- [ ] Fresh required CI/review/main acceptance.

Browser screenshot: `playground/frontend-v1-smoke/i8b-receipt-admin-desktop.png`.
Desktop actual1280, page overflow0 and owner console0. Viewport requests320
did not apply to this hidden admin tab (actual readback stayed1280); no new
mobile verification claim for this added panel. Prior I8b six-width evidence
remains historical, not a substitute for this panel's mobile release gate.
The initial student→owner URL attempt redirected repeatedly; explicitly
logging out of the synthetic student and signing in as synthetic owner worked.
No auth/access policy was weakened or bypassed.

Full-suite history: first run exited0 (summary output truncated); repeat
reported2236, failures3, skip52 in11103.767s.
Windows Power-Troubleshooter event1 confirms the host slept during that run:
2026-09-26T10:41:17Z→13:42:48Z. Another host sleep during the work session was
13:45:15Z→16:26:07Z; do not infer it overlapped the diagnostic rerun.
The final diagnostic full run completed2236 OK skip52 (168.837s), unchanged
runtime/assertions. The earlier3 failure names were lost in truncated tool
output, so sleep is a supported environmental concern, not a proven cause
of each assertion. Fresh cloud CI is independently required. Machine power
settings were not changed. Merge stays held until fresh CI/review acceptance.

## Outer audio rollback follow-up (before runtime edits)

ADMIT — same transaction-integrity scope, review4111999822. The nested audio
writer currently cannot see later receipt/pruning/snapshot/commit failures.
V1 will track only files created by this action and clean unreferenced files
after its complete atomic boundary exits. Never delete the previous recording,
or a new file still referenced by a committed answer (including on-commit
callback errors). If the database/storage cannot confirm safe cleanup, log the
failure and preserve the file; no false distributed-transaction guarantee.
Crash/power-loss between filesystem and DB remains a separate reconciliation
limit. No new product policy, migration, quota or UI is introduced.

Implemented `e39a263`. Provider-free `manage.py test courses.test_exam_attempt_v1
courses.test_exam_api_security --noinput`:73 OK skip7 (9.180s), diff PASS.
Receipt/eviction/snapshot failure removes only the new file and rolls back
answer/revision/receipt; referenced/unverifiable files are preserved. New PG
transaction test makes an on_commit callback fail after a successful audio
commit and verifies the recording and receipt still exist. Full/latest-head
CI/review pending; prior head86eaf08 CI36255695367 all3PASS (SQLite5m27s,
PostgreSQL4m42s, security2m12s) remains a historical checkpoint.
