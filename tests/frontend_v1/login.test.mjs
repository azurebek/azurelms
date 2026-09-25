import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

const source = readFileSync(new URL('../../static/frontend_v1/js/login.js', import.meta.url), 'utf8');

function harness() {
  const elements = {};
  function element(name) {
    return elements[name] = {
      handlers: {}, attrs: {}, hidden: false, disabled: false, textContent: '',
      addEventListener(event, fn) { this.handlers[event] = fn; },
      setAttribute(name, value) { this.attrs[name] = value; },
      getAttribute(name) { return this.attrs[name]; },
      removeAttribute(name) { delete this.attrs[name]; if (name === 'href') delete this.href; },
      click() { if (!this.disabled) return this.handlers.click?.(); },
    };
  }
  for (const name of ['password-toggle', 'telegram-start', 'telegram-link', 'telegram-status', 'telegram-check', 'telegram-cancel']) element(name);
  elements['password-toggle'].attrs['aria-controls'] = 'password';
  elements['telegram-link'].hidden = elements['telegram-check'].hidden = elements['telegram-cancel'].hidden = true;
  const password = {type: 'password', value: 'synthetic-test-password'};
  const queue = [], requests = [], navigation = [], timers = new Map(), events = {};
  let sequence = 0;
  const select = selector => elements[selector.slice(6, -1)];
  const panel = {
    dataset: {initUrl: '/users/telegram-auth/init/', statusUrl: '/users/telegram-auth/status/TOKEN/', loginUrl: '/users/login/?next=%2Fusers%2Fmy-courses%2F'},
    querySelector: select,
  };
  runInNewContext(source, {
    document: {
      querySelector: selector => selector === '[data-telegram-auth]' ? panel : select(selector),
      getElementById: () => password,
    },
    window: {location: {assign: url => navigation.push(url)}, addEventListener: (name, fn) => events[name] = fn},
    URL, AbortController,
    setTimeout: (fn, delay) => { const id = ++sequence; timers.set(id, {fn, delay}); return id; },
    clearTimeout: id => timers.delete(id),
    fetch: async (url, options) => {
      requests.push({url, options});
      const value = queue.shift();
      if (value instanceof Error) throw value;
      const data = await value;
      return {ok: true, json: async () => data};
    },
  });
  const tick = async () => {
    const entry = [...timers].find(([, timer]) => timer.delay === 2000);
    assert.ok(entry, 'a single poll should be scheduled');
    timers.delete(entry[0]);
    await entry[1].fn();
  };
  const init = async () => {
    queue.push({ok: true, token: 'temporary-token', bot_link: 'https://t.me/test_bot?start=auth_temporary-token'});
    await elements['telegram-start'].click();
  };
  return {elements, password, queue, requests, navigation, timers, events, tick, init, panel};
}

test('loading the page sends no authentication request', () => {
  const h = harness();
  assert.equal(h.requests.length, 0);
  assert.equal(h.navigation.length, 0);
});

test('password visibility changes only the native input type', async () => {
  const h = harness();
  await h.elements['password-toggle'].click();
  assert.equal(h.password.type, 'text');
  assert.equal(h.elements['password-toggle'].attrs['aria-pressed'], 'true');
  await h.elements['password-toggle'].click();
  assert.equal(h.password.type, 'password');
  assert.equal(h.password.value, 'synthetic-test-password');
  assert.equal(h.requests.length, 0);
});

test('explicit Telegram start uses same-origin init and does not repeat while pending', async () => {
  const h = harness();
  await h.init();
  await h.elements['telegram-start'].click();
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].options.credentials, 'same-origin');
  assert.equal(h.elements['telegram-link'].hidden, false);
  h.queue.push({ok: true, status: 'pending'});
  await h.tick();
  assert.equal(h.requests[1].url, '/users/telegram-auth/status/temporary-token/');
  assert.equal(h.navigation.length, 0);
  h.events.pagehide();
  assert.equal(h.timers.size, 0);
});

test('authenticated result rechecks Django safe-next instead of trusting redirect_url', async () => {
  const h = harness();
  await h.init();
  h.queue.push({ok: true, status: 'authenticated', redirect_url: 'https://untrusted.example'});
  await h.tick();
  assert.deepEqual(h.navigation, [h.panel.dataset.loginUrl]);
  assert.equal(h.timers.size, 0);
});

test('expired and unknown results restore explicit start without false success', async () => {
  for (const result of [{ok: true, status: 'expired'}, {ok: false, status: 'not_found'}]) {
    const h = harness();
    await h.init();
    h.queue.push(result);
    await h.tick();
    assert.equal(h.elements['telegram-start'].disabled, false);
    assert.equal(h.elements['telegram-link'].hidden, true);
    assert.equal(h.navigation.length, 0);
    assert.equal(h.timers.size, 0);
  }
});

test('uncertain polling stops automatic retry and checks the SAME token manually', async () => {
  const h = harness();
  await h.init();
  h.queue.push(new Error('network'));
  await h.tick();
  assert.equal(h.elements['telegram-check'].hidden, false);
  assert.equal(h.timers.size, 0);
  h.queue.push({ok: true, status: 'used'});
  await h.elements['telegram-check'].click();
  assert.equal(h.requests[2].url, h.requests[1].url);
  assert.deepEqual(h.navigation, [h.panel.dataset.loginUrl]);
});

test('cancelled init ignores its late response', async () => {
  const h = harness();
  let resolve;
  h.queue.push(new Promise(done => resolve = done));
  const pending = h.elements['telegram-start'].click();
  await h.elements['telegram-cancel'].click();
  resolve({ok: true, token: 'late', bot_link: 'https://t.me/test_bot'});
  await pending;
  assert.equal(h.elements['telegram-link'].hidden, true);
  assert.equal(h.elements['telegram-start'].disabled, false);
  assert.equal(h.timers.size, 0);
});

test('unexpected external deep-link is never offered', async () => {
  const h = harness();
  h.queue.push({ok: true, token: 'token', bot_link: 'https://untrusted.example'});
  await h.elements['telegram-start'].click();
  assert.equal(h.elements['telegram-link'].hidden, true);
  assert.equal(h.navigation.length, 0);
  assert.equal(h.elements['telegram-start'].disabled, false);
});
