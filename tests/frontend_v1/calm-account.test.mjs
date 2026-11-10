import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';

const read = path => readFileSync(new URL(`../../templates/frontend_v1/calm/${path}`, import.meta.url), 'utf8');
const css = readFileSync(new URL('../../static/frontend_v1/css/calm-account.css', import.meta.url), 'utf8');

test('account and commerce routes are complete CALM renderer groups', () => {
  assert.match(read('profile.html'), /data-calm-page="profile"/);
  assert.match(read('profile.html'), /profile_fields\.html/);
  assert.match(read('profile.html'), /method="post" action="\{% url 'logout' %\}"/);
  for (const path of ['settings_account.html', 'settings_privacy.html', 'settings_billing.html', 'settings_capabilities.html']) {
    assert.match(read(path), /extends "frontend_v1\/settings_/);
    assert.match(read(path), /d2-settings-body/);
    assert.match(read(path), /calm\/account_assets\.html/);
  }
  for (const path of ['records/help.html', 'records/subscriptions.html', 'checkout/form.html', 'checkout/status.html']) {
    assert.match(read(path), /extends "frontend_v1\//);
    assert.match(read(path), /calm\/account_assets\.html/);
  }
});

test('CALM account CSS stays scoped and uses only approved breakpoints', () => {
  const rules = css.replace(/\/\*[\s\S]*?\*\//g, '');
  for (const selector of rules.matchAll(/(^|})\s*([^@][^{]+)\{/gm)) {
    if (selector[2].includes('@media')) continue;
    assert.match(selector[2], /^\s*\.s-calm\b/, `unscoped selector: ${selector[2].trim()}`);
  }
  const breakpoints = [...css.matchAll(/@media\s*\(width\s*<\s*(\d+)px\)/g)].map(match => Number(match[1]));
  assert.deepEqual([...new Set(breakpoints)], [900, 560]);
  assert.match(css, /\.d2-payments-body \.f-records-layout[\s\S]*grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(css, /\.d2-profile-head > \.c-button \{ grid-column: 1 \/ -1; width: 100%; \}/);
});

test('dedicated CALM account asset stays within its internal budget', () => {
  const bytes = gzipSync(Buffer.from(css), {level: 9}).length;
  assert.ok(bytes <= 2400, `calm-account.css is ${bytes} gzip bytes`);
});
