# Library same-timestamp ABA guard — 2026-09-26

## Admission (before runtime changes)

ADMIT — launch-critical. Owner explicitly approved this narrow independent
fix while PR140 was held. Measured failure: existing LibraryV1Tests ABA
assertion failed in full2225; isolated rerun passed, controlled same-clock
test failed. No library runtime/test diff against baseline b8c1604.

Canonical resource metadata saves must invalidate an already-open V1 form
even when A→B→A saves share exactly one timestamp. Add non-editable bigint
`edit_revision` default0 (library0002), separate from file `version`.
LibraryResource.save increments the current persisted counter under a row
lock/transaction, including partial and no-op saves. Empty update_fields
remains a true no-op. V1 HMAC includes this counter; existing locked POST
comparison and bound draft409 remain unchanged. Legacy/admin saves also
invalidate V1 tokens. File bytes/storage, pricing, grading and permissions
are not changed; no delete or data backfill.

This is not a new operator setting or time/quota value. Existing OFF renderer
rollback remains available; additive migration stays and is required before
new code starts. Already-open pre-migration V1 forms safely get stale409.
Raw SQL/QuerySet.update/bulk writes and tag-only cycles without resource.save
are not claimed to have global monotonic revision coverage in this narrow fix;
normal editor tag saves already call resource.save in the same transaction.

## Verification gates

- [x] ~~Original ABA assertion made deterministic with a frozen timestamp.~~
- [x] ~~Stale409 keeps draft, file/version preserved, partial save, stale model
  instance counters and transactional rollback tests.~~
- [x] ~~Library/courses, full suite, Node and schema/check gates.~~
- [ ] Required CI and review, then manual PR merge; no AWS in this task.

Runtime `453b6dd`. Provider-free
`venv/Scripts/python.exe manage.py test library courses.test_exam_attempt_v1 --noinput`:
112 OK skip6 (10.349s), check0/drift0. Six skips = five existing exam races
plus the new real-PostgreSQL concurrent resource-save test; required PG CI
executes them. Original controlled same-clock repro now passes (0.060s),
without relaxing/removing its assertion. No browser design changes.

Final provider-free `venv/Scripts/python.exe manage.py test --noinput`:
**2229 OK skip51 (145.501s)**. `node --test tests/frontend_v1/*.test.mjs`:
**109 PASS** (unchanged JS since that run). Courses265 OK skip6 (26.850s).
The previous full2225 failure is now covered by the permanent frozen-clock
regression and the new stale-form/parallel-save tests; no assertion was removed.
