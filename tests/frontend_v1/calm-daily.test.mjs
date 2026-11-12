import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';

const css = readFileSync(new URL('../../static/frontend_v1/css/calm-pages.css', import.meta.url), 'utf8');
const read = path => readFileSync(new URL(`../../templates/frontend_v1/calm/${path}`, import.meta.url), 'utf8');

test('daily learner bundle stays CALM-scoped with only approved breakpoints', () => {
  const clean = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const selectors = clean.split('\n').map(line => line.trim()).filter(line => line.endsWith('{') && !line.startsWith('@media')).map(line => line.slice(0, -1).trim());
  assert.ok(selectors.every(selector => selector.split(',').every(part => part.trim().startsWith('.s-calm'))));
  const media = [...css.matchAll(/@media\s*\(width\s*<\s*(\d+)px\)/g)].map(match => Number(match[1]));
  assert.deepEqual(media, [900, 560]);
  assert.doesNotMatch(css, /#[0-9a-f]{3,8}\b/i);
});

test('daily flow templates are real-data views with calm page identities', () => {
  for (const [file, marker] of [['dashboard.html', 'dashboard'], ['courses.html', 'courses'], ['lesson.html', 'lesson']]) {
    const source = read(file);
    assert.match(source, new RegExp(`data-calm-page="${marker}"`));
    assert.match(source, /frontend_v1\/calm\/platform\.html/);
    assert.doesNotMatch(source, /\/_preview\/|fixture|demo runtime/i);
  }
  assert.match(read('lesson.html'), /calm\/practice_assignments\.html/);
  assert.match(read('lesson.html'), /calm\/practice_quizzes\.html/);
});

test('learner home follows the sketch single-column reading order', () => {
  const dashboard = read('dashboard.html');
  assert.match(dashboard, /d2-next-card[\s\S]*d2-before[\s\S]*d2-my-learning/);
  assert.doesNotMatch(dashboard, /d2-(?:journey|dashboard-grid|action-list)/);
  assert.match(css, /\.d2-page--dashboard \{ width: min\(100%, 47\.5rem\)/);
  assert.match(css, /\.d2-page\[data-calm-page="lesson"\] \{ width: min\(100%, 65rem\)/);
});

test('messenger, AI, notifications and practice preserve their canonical parents', () => {
  assert.match(read('messenger.html'), /extends "frontend_v1\/messenger\.html"/);
  assert.match(read('ai_messenger.html'), /extends "frontend_v1\/ai_messenger\.html"/);
  assert.match(read('records/notifications.html'), /extends "frontend_v1\/records\/notifications\.html"/);
  assert.match(read('practice_assignments.html'), /include "frontend_v1\/practice_assignments\.html"/);
  assert.match(read('practice_quizzes.html'), /include "frontend_v1\/practice_quizzes\.html"/);
});

test('daily CALM asset stays inside the internal page budget', () => {
  const bytes = gzipSync(Buffer.from(css), {level: 9}).length;
  assert.ok(bytes <= 4300, `calm-pages.css is ${bytes} gzip bytes`);
});
