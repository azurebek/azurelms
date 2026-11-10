import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';

const read = path => readFileSync(new URL(`../../templates/frontend_v1/calm/${path}`, import.meta.url), 'utf8');
const css = readFileSync(new URL('../../static/frontend_v1/css/calm-pages.css', import.meta.url), 'utf8');

test('results renderers wrap canonical contracts behind CALM', () => {
  for (const path of ['exams/center.html', 'exams/attempt.html', 'exams/result.html']) {
    assert.match(read(path), /extends "frontend_v1\/exams\//);
    assert.match(read(path), /calm\/page_assets\.html/);
  }
  for (const path of ['records/certificates.html', 'records/attendance.html', 'records/leaderboard.html']) {
    assert.match(read(path), /extends "frontend_v1\/records\//);
    assert.match(read(path), /d2-results-body/);
  }
  for (const path of ['certificates/detail.html', 'certificates/appendix.html']) {
    assert.match(read(path), /extends "frontend_v1\/certificates\//);
    assert.match(read(path), /d2-certificate-body/);
  }
});

test('exam attempt is a focus page and certificate remains neutral for print', () => {
  assert.match(read('exams/attempt.html'), /d2-focus-shell/);
  assert.match(css, /\.d2-focus-shell \.s-calm-sidebar \{ display: none; \}/);
  assert.match(css, /\.d2-certificate-body \.f-certificate-document \{[^}]*background: white;/);
  const certificateCss = readFileSync(new URL('../../static/frontend_v1/css/certificates.css', import.meta.url), 'utf8');
  assert.match(certificateCss, /@media print/);
  assert.match(certificateCss, /background: white/);
});

test('shared CALM page asset remains inside its internal budget after results', () => {
  const bytes = gzipSync(Buffer.from(css), {level: 9}).length;
  assert.ok(bytes <= 4300, `calm-pages.css is ${bytes} gzip bytes`);
});
