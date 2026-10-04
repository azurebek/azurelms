# UX-04 — auth form clarity, Packet85

2026-10-04. Owner continuation, D31, local-only EXPERIMENT. UX-04 PARTIAL.
This records ignored Eleventh Trial work; not a real auth/AWS release.

## Scope and result

Four existing AUTH-01/02 forms: login, registration, reset request/confirm.
Each error appears once beside its field; summary says how many fields
need attention, not the same error again. Native required/email and existing
password equality are shown together. One first-invalid focus per submit;
Enter mismatch blocks before request/operation marker. Correction/sample
clear outdated messages, server fixture rejection shares the same slot.

Auth text links use existing44px control token. No shell, theme, palette,
breakpoint, menu or business rule change. Password strength/credential
validity stays server-owned; no new fake strength policy. Account password
center is unchanged and regression-tested. Next allowlist, secret exclusion,
stale/unknown/receipt/duplicate-submit guards unchanged.

Local files: `prototype/templates/patterns/auth_field.html`,
`prototype/static/css/auth.css`, `prototype/static/js/auth.js`, new
`auth_validation.js`; new `tests/auth_validation.test.mjs` and
`tests/test_auth_clarity.py`. Actual source is ignored, not force-added.

## Evidence

All commands in `playground/Eleventh Trial`; `AZURELMS_SKIP_ENV_FILE=1`,
`GEMINI_API_KEY=''`, `TELEGRAM_BOT_TOKEN=''`. No real env/DB/provider calls.

- `../../venv/Scripts/python.exe manage.py test tests --verbosity 0`:
  **881 PASS**,429.716s,exit0/check0.
- `../../venv/Scripts/python.exe manage.py test tests.test_auth
  tests.test_auth_clarity tests.test_library_settings --verbosity 0`:
  **40 PASS**,2.389s. Additional `tests.test_password_change
  tests.test_profile_entry`: **11 PASS**,0.777s.
- `$testFiles85 = @(Get-ChildItem tests/*.test.mjs | ForEach-Object FullName);
  node --test @testFiles85`: **246 PASS**,2395.6753ms. New helper10 tests;
  native event coalescing/focus, errors/correction/mismatch, no strength
  policy, server text-only rendering, unchanged values/pending notice.
- `node --check prototype/static/js/auth.js`, isolated `manage.py check`
  and `git diff --check` PASS.
- IAB localhost8088: **56responsive** (7routes×4widths×2themes) and
  **24state** cases (3forms×2widths×4faults), effective viewport asserted.
  Widths320/390/768/1280, light/dark; overflow0/duplicate IDs0, links≥44px.
- Browser blank4errors; email+mismatch together; correction→Enter focus;
  sample clears; duplicate-email rejection once; demo registration→onboarding;
  reset request→issued→mismatch→demo confirm→login. No real emails/accounts.
- Unknown login→reload→submit remains locked→GET reconcile; offline known
  rejection editable with generic notice. Show password→navigate→Back:
  secrets empty/typepassword, nonsecret name retained. Ack/reload verified.
- Console warn/error0. Full-page mobile light/desktop dark screenshots
  saved and inspected: local `evidence/packet-85-auth-{mobile,desktop}.jpg`.

## Recovery and limits

Verified local archive **678files**, every entry SHA256 checked:
`playground/Eleventh Trial/checkpoints/packet-85-20261004-145029.zip`.
ZIP SHA256 **`B4FF6010F29689BB134047AFF6571CA49FF7FAE325BDBCE7AD27A4F6643EE2B0`**.
Packet84 retained/hash matched. Only3existing implementation files differ
from84, plus new helper/tests. Archive source excludes checkpoints/caches/
CHECKPOINT.md. Same-disk recovery, not offsite backup; no upload.

Registry0.84.0 unchanged:139named+2aliases/77pages/118renderer-source+
2alias-source,1223states/213actions+3handlers. No new route/action.

OPEN: real V1 duplicate banner/errorlist and password-strength validation;
real footer/legal tap areas; AI onboarding CTA cannot be completed without
its actual availability/flow. Native keyboard, AT, other engines and owner
G2/G3 acceptance not tested. UX-01 iPhone Chrome remains OPEN. Runtime,
canonical services, DB, AWS untouched. Final UX/DATA/RULE/native/owner
acceptance → DESIGN-01; this packet does not close the entire UX-04 issue.
