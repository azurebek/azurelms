import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';
import {runInNewContext} from 'node:vm';

const code = readFileSync(new URL('../../static/frontend_v1/js/shell.js', import.meta.url), 'utf8');
const themeCode = readFileSync(new URL('../../static/frontend_v1/js/theme.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../../static/frontend_v1/css/calm-shell.css', import.meta.url), 'utf8');
const calmNav = readFileSync(new URL('../../templates/frontend_v1/calm/nav.html', import.meta.url), 'utf8');

function popover(open = false) {
  const listeners = {};
  const summary = {focus() { this.focused = true; }};
  return {
    open,
    listeners,
    summary,
    addEventListener(type, fn) { listeners[type] = fn; },
    querySelector(selector) { return selector === 'summary' ? summary : null; },
  };
}

function harness({popovers = [], name = '', search = ''} = {}) {
  const documentEvents = {};
  const windowEvents = {};
  const root = {
    dataset: {},
    attributes: {},
    setAttribute(key, value) { this.attributes[key] = value; },
  };
  runInNewContext(code, {
    URLSearchParams,
    document: {
      documentElement: root,
      querySelector: () => null,
      querySelectorAll: selector => selector === '[data-calm-popover]' ? popovers : [],
      addEventListener(type, fn) { documentEvents[type] = fn; },
    },
    window: {
      name,
      location: {search},
      addEventListener(type, fn) { windowEvents[type] = fn; },
    },
    sessionStorage: {length: 0},
  });
  return {documentEvents, windowEvents, root};
}

test('calm popovers are mutually exclusive and outside click closes them', () => {
  const account = popover(true);
  const notices = popover(false);
  const h = harness({popovers: [account, notices]});
  notices.open = true;
  notices.listeners.toggle();
  assert.equal(account.open, false);
  assert.equal(notices.open, true);
  h.documentEvents.click({target: {closest: () => null}});
  assert.equal(notices.open, false);
});

test('Escape closes the active calm popover and returns focus to its summary', () => {
  const account = popover(true);
  const h = harness({popovers: [account]});
  let prevented = false;
  h.documentEvents.keydown({
    key: 'Escape',
    target: {closest: selector => selector === '[data-calm-popover][open]' ? account : null},
    preventDefault() { prevented = true; },
  });
  assert.equal(account.open, false);
  assert.equal(account.summary.focused, true);
  assert.equal(prevented, true);
});

test('Back navigation closes stale popovers', () => {
  const account = popover(true);
  const h = harness({popovers: [account]});
  h.windowEvents.pageshow();
  assert.equal(account.open, false);
});

test('Telegram frame name and mini query activate the shared mini shell', () => {
  assert.equal(harness({name: 'tgmini'}).root.attributes['data-mini'], '');
  assert.equal(harness({search: '?mini'}).root.attributes['data-mini'], '');
  assert.equal(harness().root.attributes['data-mini'], undefined);
});

test('account theme choices store and expose the selected light or dark mode', () => {
  const events = {};
  const stored = {};
  const button = value => ({dataset: {themeValue: value}, attrs: {}, setAttribute(key, setting) { this.attrs[key] = setting; }});
  const light = button('light');
  const dark = button('dark');
  const root = {dataset: {}};
  runInNewContext(themeCode, {
    document: {
      documentElement: root,
      querySelectorAll: selector => selector === '[data-action="theme.set"]' ? [light, dark] : [],
      addEventListener(type, fn) { events[type] = fn; },
    },
    localStorage: {
      getItem: key => stored[key] || null,
      setItem: (key, value) => { stored[key] = value; },
    },
    window: {
      matchMedia: () => ({matches: false, addEventListener() {}}),
      addEventListener() {},
    },
  });
  assert.equal(light.attrs['aria-pressed'], 'true');
  events.click({target: {closest: selector => selector === '[data-action="theme.set"]' ? dark : null}});
  assert.equal(root.dataset.theme, 'dark');
  assert.equal(dark.attrs['aria-pressed'], 'true');
  assert.equal(stored['az-v2-theme'], 'dark');
});

test('calm shell keeps the two approved breakpoints and a five-slot mobile nav', () => {
  assert.match(css, /@media \(width < 900px\)/);
  assert.match(css, /@media \(width < 560px\)/);
  assert.match(css, /grid-template-columns:\s*repeat\(5,/);
  assert.match(calmNav, /data-calm-desktop-only/);
  assert.match(calmNav, />Hisob<\/span>/);
});

test('internal shell stays inside its measured compressed asset budget', () => {
  assert.ok(gzipSync(Buffer.from(css), {level: 9}).length <= 2700, 'calm-shell.css exceeds 2700 gzip bytes');
  assert.ok(gzipSync(Buffer.from(code), {level: 9}).length <= 1100, 'shell.js exceeds 1100 gzip bytes');
});
