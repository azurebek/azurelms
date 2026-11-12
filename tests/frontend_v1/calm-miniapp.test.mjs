import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {runInNewContext} from 'node:vm';
import {gzipSync} from 'node:zlib';

const root = new URL('../../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const home = read('templates/frontend_v1/calm/bot/miniapp_home.html');
const base = read('templates/frontend_v1/calm/bot/miniapp_base.html');
const entry = read('templates/frontend_v1/calm/bot/miniapp_entry.html');
const css = read('static/frontend_v1/css/calm-miniapp.css');
const code = read('static/frontend_v1/js/calm-miniapp.js');
const entryCode = read('static/frontend_v1/js/calm-miniapp-entry.js');
const frameCode = read('static/frontend_v1/js/mini-frame.js');

test('Mini App owns one home and opens canonical product pages in tgmini', () => {
  assert.match(home, /<iframe name="tgmini"/);
  assert.match(home, /target="tgmini" data-mini-open/);
  for (const route of ['my_courses', 'messenger:ai', 'exam_center', 'attendance_calendar',
                        'certificates', 'profile', 'settings', 'subscriptions', 'help_center']) {
    assert.match(home, new RegExp(`url '${route.replace(':', '\\:')}'`), route);
  }
  assert.match(home, /data-mini-tab="home"[\s\S]*data-mini-tab="courses"[\s\S]*data-mini-tab="menu"[\s\S]*data-mini-tab="ai"/);
  assert.doesNotMatch(home, /1 240|4-o['’]rin|19:00|Noyabr oqimi|Aziz Karimov/);
});

test('Mini App base is the isolated CALM bundle and keeps Telegram entry states', () => {
  for (const asset of ['tokens.css', 'base.css', 'calm.css', 'calm-miniapp.css',
                        'theme.js', 'calm-miniapp.js']) assert.ok(base.includes(asset), asset);
  assert.match(base, /https:\/\/telegram\.org\/js\/telegram-web-app\.js/);
  assert.doesNotMatch(base, /css\/miniapp\.css|js\/miniapp\.js/);
  assert.match(entry, /data-miniapp-entry/);
  assert.match(entry, /Kirilmoqda…/);
  assert.match(entry, /data-mini-retry hidden/);
});

test('quiet Mini App CSS is scoped, flat, responsive and budgeted', () => {
  const clean = css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/@keyframes[^}]+\{[^}]+\}\s*/g, '');
  const selectors = [...clean.matchAll(/([^{}]+)\{[^{}]*\}/g)]
    .map(match => match[1].trim()).filter(selector => !selector.startsWith('@'));
  for (const selector of selectors) {
    for (const part of selector.split(',')) assert.match(part.trim(), /^\.s-calm-miniapp\b/);
  }
  const media = [...css.matchAll(/@media\s*\(width\s*<\s*(\d+)px\)/g)].map(match => Number(match[1]));
  assert.deepEqual([...new Set(media)], [560]);
  assert.doesNotMatch(clean, /gradient\s*\(|box-shadow\s*:/i);
  assert.match(css, /grid-template-columns:\s*repeat\(4,/);
  assert.ok(gzipSync(css, {level: 9}).length <= 3000, gzipSync(css, {level: 9}).length);
  assert.ok(gzipSync(code, {level: 9}).length <= 1500, gzipSync(code, {level: 9}).length);
});

test('Telegram back and theme APIs control presentation without duplicating domain writes', () => {
  assert.match(code, /BackButton\.onClick\(goBack\)/);
  assert.match(code, /telegram\?\.close/);
  assert.match(code, /window\.name|tgmini|data-mini-open/);
  assert.match(code, /themeChanged/);
  assert.doesNotMatch(code, /\bfetch\s*\(|localStorage|sessionStorage|XMLHttpRequest/);
  assert.match(entryCode, /method:\s*"POST"/);
  assert.match(entryCode, /init_data:\s*initData/);
  assert.doesNotMatch(entryCode, /localStorage|sessionStorage/);
});

test('canonical child bootstrap marks only the named Telegram frame', () => {
  const makeRoot = () => ({attributes: {}, setAttribute(key, value) { this.attributes[key] = value; }});
  const framed = makeRoot();
  const framedBody = makeRoot();
  runInNewContext(frameCode, {window: {name: 'tgmini'}, document: {documentElement: framed, body: framedBody}});
  assert.equal(framed.attributes['data-mini'], '');
  assert.equal(framedBody.attributes['data-mini'], '');
  const regular = makeRoot();
  runInNewContext(frameCode, {window: {name: ''}, document: {documentElement: regular}});
  assert.equal(regular.attributes['data-mini'], undefined);
});
