import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const root = new URL('../../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const css = read('static/frontend_v1/css/calm-public.css');
const clean = css.replace(/\/\*[\s\S]*?\*\//g, '').trim();

test('CALM public frame is opt-in and keeps the existing editorial fallback path', () => {
  const registry = read('frontend/public_v1.py');
  const base = read('templates/frontend_v1/calm/public/base.html');
  const editorialBase = read('templates/frontend_v1/editorial/base.html');
  assert.match(registry, /CALM:\s*"frontend_v1\/calm\/public\/base\.html"/);
  assert.match(base, /extends "frontend_v1\/editorial\/base\.html"/);
  assert.match(base, /s-editorial d2-public/);
  assert.match(base, /d2-public-body/);
  assert.match(editorialBase, /if not platform_calm_v1[\s\S]*public-editorial\.css[\s\S]*if platform_calm_v1[\s\S]*calm-public\.css/);
});

test('ported public and auth templates receive the selected frame instead of forking contracts', () => {
  const editorialPages = [
    'index.html', 'about.html', 'legal_page.html', 'courses/course_list.html',
    'courses/course_detail.html', 'subscriptions/pricing.html', 'blog/post_list.html',
    'blog/post_detail.html', 'sit/home.html', 'sit/university_list.html',
    'sit/university_detail.html', 'sit/knowledge_detail.html',
  ];
  for (const page of editorialPages) {
    assert.match(read(`templates/frontend_v1/editorial/${page}`),
      /extends public_frame\|default:"frontend_v1\/editorial\/base\.html"/, page);
  }
  assert.match(read('templates/frontend_v1/editorial/auth_base.html'),
    /extends auth_public_frame\|default:"frontend_v1\/editorial\/base\.html"/);
  assert.match(read('templates/frontend_v1/editorial/auth_base.html'), /class="d2-auth-tabs"/);
});

test('quiet public stylesheet stays scoped, uses only DESIGN-02 breakpoints and has no gradients', () => {
  const selectors = [...clean.matchAll(/([^{}]+)\{[^{}]*\}/g)]
    .map(match => match[1].trim()).filter(selector => !selector.startsWith('@'));
  assert.ok(selectors.length > 50, selectors.length);
  for (const selector of selectors) {
    for (const part of selector.split(',')) assert.match(part.trim(), /^\.s-calm\s/);
  }
  const media = [...clean.matchAll(/@media\s*\(([^)]+)\)/g)].map(match => match[1]);
  assert.deepEqual(media, ['width < 900px', 'width < 560px']);
  assert.doesNotMatch(clean, /gradient\s*\(/i);
  assert.match(clean, /width:\s*min\(100%,\s*75rem\)/);
  assert.match(clean, /min-height:\s*4\.5rem/);
  assert.match(clean, /minmax\(0,\s*25rem\)/);
  assert.ok(gzipSync(css).length <= 3600, gzipSync(css).length);
});

test('certificate verifier keeps privacy states in the standalone quiet shell', () => {
  const template = read('templates/frontend_v1/calm/public/certificate_verify.html');
  for (const marker of ['noindex, nofollow, noarchive', 'data-verify-state="blocked"',
                        'data-verify-state="{{ result.status }}"', 'data-verify-state="not_found"']) {
    assert.ok(template.includes(marker), marker);
  }
  assert.doesNotMatch(template, /https?:\/\//);
  assert.match(template, /calm-public\.css/);
});
