import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';

const read = path => readFileSync(new URL(`../../${path}`, import.meta.url), 'utf8');
const css = read('static/frontend_v1/css/calm-backoffice.css');
const base = read('templates/backoffice/workspace/base.html');
const nav = read('templates/backoffice/workspace/nav.html');
const home = read('templates/frontend_v1/calm/backoffice/workspace/home.html');
const courses = read('templates/frontend_v1/calm/backoffice/workspace/course_list.html');

test('CALM backoffice is an opt-in asset with dedicated sketch renderers', () => {
  assert.match(base, /if platform_calm_v1 %}<link rel="stylesheet" href="{% static 'frontend_v1\/css\/calm-backoffice\.css'/);
  assert.match(base, /workspace-body{% if platform_calm_v1 %} d2-backoffice-body/);
  assert.match(home, /data-calm-page="admin-home"/);
  assert.match(home, /d2-admin-search[\s\S]*d2-admin-priority[\s\S]*Keyingi navbat[\s\S]*Kurslar/);
  assert.match(courses, /data-calm-page="admin-courses"/);
  assert.match(courses, /d2-admin-filters[\s\S]*d2-admin-course-rows/);
  assert.match(nav, /ws-nav-key-\{\{ item\.key \}\}/);
});

test('CALM backoffice CSS stays scoped and follows the approved responsive frame', () => {
  const rules = css.replace(/\/\*[\s\S]*?\*\//g, '');
  for (const selector of rules.matchAll(/(^|})\s*([^@][^{]+)\{/gm)) {
    if (selector[2].includes('@media')) continue;
    assert.match(selector[2], /^\s*\.s-calm\b/, `unscoped selector: ${selector[2].trim()}`);
  }
  const breakpoints = [...css.matchAll(/@media\s*\(width\s*<\s*(\d+)px\)/g)].map(match => Number(match[1]));
  assert.deepEqual([...new Set(breakpoints)], [900, 560]);
  assert.match(css, /\.ws-shell \{ grid-template-columns: 14\.5rem minmax\(0, 1fr\)/);
  assert.match(css, /\.ws-main \{ width: min\(100%, 51\.25rem\)/);
  assert.match(css, /\.d2-admin-page \{ width: min\(100%, 45rem\)/);
  assert.match(css, /\.ws-nav-link\.ws-nav-key-design \{ display: none; \}/);
});

test('dedicated CALM backoffice asset stays within its internal budget', () => {
  const bytes = gzipSync(Buffer.from(css), {level: 9}).length;
  assert.ok(bytes <= 4200, `calm-backoffice.css is ${bytes} gzip bytes`);
});
