import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';

const read = path => readFileSync(new URL(`../../templates/frontend_v1/calm/${path}`, import.meta.url), 'utf8');
const css = readFileSync(new URL('../../static/frontend_v1/css/calm-teacher.css', import.meta.url), 'utf8');

test('teacher routes are complete CALM renderer groups', () => {
  const dashboard = read('teacher/dashboard.html');
  assert.match(dashboard, /data-calm-page="teacher-dashboard"/);
  assert.match(dashboard, /calm\/teacher_assets\.html/);
  assert.match(dashboard, /d2-teacher-today[\s\S]*d2-teacher-review[\s\S]*d2-teacher-groups/);
  assert.doesNotMatch(dashboard, /d2-teacher-(?:stats|grid|quick)/);
  for (const path of [
    'attendance.html', 'cohorts.html', 'courses.html', 'grade_assignment.html',
    'grade_exam.html', 'grading.html', 'release.html', 'students.html',
  ]) {
    const source = read(`teacher/${path}`);
    assert.match(source, /extends "frontend_v1\/teacher\//);
    assert.match(source, /d2-teacher-body/);
    assert.match(source, /calm\/teacher_assets\.html/);
  }
});

test('teacher classbook routes keep canonical forms behind CALM wrappers', () => {
  for (const path of [
    'teacher_home.html', 'playbook_form.html', 'exercise_list.html', 'exercise_form.html',
    'teacher_session.html', 'teacher_activity_result.html', 'conflict.html', 'live_conflict.html',
  ]) {
    const source = read(`classbook/${path}`);
    assert.match(source, /extends "frontend_v1\/classbook\//);
    assert.match(source, /d2-(?:teacher|classbook)-body/);
    assert.match(source, /calm\/teacher_assets\.html/);
  }
});

test('teacher review and live session use the sketch focus frame', () => {
  for (const path of ['teacher/grade_assignment.html', 'teacher/grade_exam.html', 'classbook/teacher_session.html']) {
    assert.match(read(path), /block frame_class %}d2-focus-shell/);
  }
  assert.match(read('classbook/teacher_home.html'), /d2-classbook-tabs/);
  assert.match(read('classbook/exercise_list.html'), /d2-classbook-tabs/);
  assert.match(read('classbook/playbook_form.html'), /d2-classbook-playbook-body/);
  assert.match(read('classbook/exercise_form.html'), /d2-classbook-exercise-editor-body/);
});

test('CALM teacher CSS stays scoped and uses only approved breakpoints', () => {
  const rules = css.replace(/\/\*[\s\S]*?\*\//g, '');
  for (const selector of rules.matchAll(/(^|})\s*([^@][^{]+)\{/gm)) {
    if (selector[2].includes('@media')) continue;
    assert.match(selector[2], /^\s*\.s-calm\b/, `unscoped selector: ${selector[2].trim()}`);
  }
  const breakpoints = [...css.matchAll(/@media\s*\(width\s*<\s*(\d+)px\)/g)].map(match => Number(match[1]));
  assert.deepEqual([...new Set(breakpoints)], [900, 560]);
  assert.match(css, /\.d2-teacher-page \{ width: min\(100%, 47\.5rem\)/);
  assert.match(css, /\.d2-teacher-directory-body \.f-directory-groups \{[^}]*grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(css, /\.d2-teacher-review-body \.p-review-layout \{[^}]*grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(css, /\.d2-teacher-queue-body \.p-queue-row \{ grid-template-columns: minmax\(0, 1fr\); \}/);
  assert.match(css, /\.d2-classbook-playbook-body \.s-calm-main > \.f-classbook-stack \{ width: min\(100%, 42\.5rem\); \}/);
  assert.match(css, /\.d2-classbook-exercise-editor-body \.s-calm-main > \.f-classbook-stack \{ width: min\(100%, 45rem\); \}/);
  assert.match(css, /\.d2-classbook-live-body \.s-calm-main > \.f-classbook-stack \{ width: min\(100%, 66\.25rem\); \}/);
});

test('dedicated CALM teacher asset stays within its internal budget', () => {
  const bytes = gzipSync(Buffer.from(css), {level: 9}).length;
  assert.ok(bytes <= 3600, `calm-teacher.css is ${bytes} gzip bytes`);
});
