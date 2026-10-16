import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

const source = readFileSync(new URL('../../static/frontend_v1/js/login.js', import.meta.url), 'utf8');

function harness({registration = false} = {}) {
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
    dataset: {initUrl: '/users/telegram-auth/init/', statusUrl: '/users/telegram-auth/status/TOKEN/',
      consumeUrl: '/users/telegram-auth/consume/TOKEN/', cancelUrl: '/users/telegram-auth/cancel/',
      csrfToken: 'synthetic-csrf', loginUrl: '/users/login/?next=%2Fusers%2Fmy-courses%2F'},
    querySelector: select,
  };
  const email = {value: 'typed@example.test', defaultValue: ''};
  const form = {hasAttribute: () => false, querySelectorAll: () => [email],
    addEventListener() {}, removeAttribute() {}};
  const context = {
    document: {
      querySelector: selector => selector === '[data-telegram-auth]' ? panel : select(selector),
      getElementById: () => password,
      querySelectorAll: selector => registration && selector === '[data-auth-form]' ? [form] : [],
    },
    window: {
      location: {assign: url => {
        const leaving = {defaultPrevented: false, preventDefault() {this.defaultPrevented = true;}};
        events.beforeunload?.(leaving);
        if (!leaving.defaultPrevented) navigation.push(url);
      }},
      addEventListener: (name, fn) => {
        const previous = events[name];
        events[name] = event => {previous?.(event); return fn(event);};
      },
      dispatchEvent: event => events[event.type]?.(event),
    },
    URL, AbortController, Event,
    setTimeout: (fn, delay) => { const id = ++sequence; timers.set(id, {fn, delay}); return id; },
    clearTimeout: id => timers.delete(id),
    fetch: async (url, options) => {
      requests.push({url, options});
      const value = queue.shift();
      if (value instanceof Error) throw value;
      const data = await value;
      if (data?.httpStatus) return {ok: false, status: data.httpStatus, json: async () => data};
      return {ok: true, status: 200, json: async () => data};
    },
  };
  if (registration) runInNewContext(readFileSync(new URL('../../static/frontend_v1/js/auth-form.js', import.meta.url), 'utf8'), context);
  runInNewContext(source, context);
  const tick = async () => {
    const polls = [...timers].filter(([, timer]) => timer.delay !== 15000);
    assert.equal(polls.length, 1, 'a single poll should be scheduled');
    const [id, timer] = polls[0];
    timers.delete(id);
    await timer.fn();
    return timer.delay;
  };
  const init = async (extra = {}) => {
    queue.push({ok: true, token: 'temporary-token', bot_link: 'https://t.me/test_bot?start=auth_temporary-token', ...extra});
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

test('explicit Telegram start uses a same-origin CSRF POST and does not repeat while pending', async () => {
  const h = harness();
  await h.init();
  await h.elements['telegram-start'].click();
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].options.credentials, 'same-origin');
  assert.equal(h.requests[0].options.method, 'POST');
  assert.equal(h.requests[0].options.headers['X-CSRFToken'], 'synthetic-csrf');
  assert.equal(h.elements['telegram-link'].hidden, false);
  h.queue.push({ok: true, status: 'pending'});
  await h.tick();
  assert.equal(h.requests[1].url, '/users/telegram-auth/status/temporary-token/');
  assert.equal(h.requests[1].options.method, 'GET');
  assert.equal(h.requests[1].options.headers, undefined);
  assert.equal(h.navigation.length, 0);
  h.events.pagehide();
  assert.equal(h.timers.size, 0);
});

test('authenticated status is consumed by one CSRF POST, then Django rechecks safe-next', async () => {
  const h = harness();
  await h.init();
  h.queue.push({ok: true, status: 'authenticated'});
  h.queue.push({ok: true, status: 'authenticated', redirect_url: 'https://untrusted.example'});
  await h.tick();
  assert.equal(h.requests[2].url, '/users/telegram-auth/consume/temporary-token/');
  assert.equal(h.requests[2].options.method, 'POST');
  assert.equal(h.requests[2].options.headers['X-CSRFToken'], 'synthetic-csrf');
  assert.equal(h.requests.length, 3);
  assert.deepEqual(h.navigation, [h.panel.dataset.loginUrl]);
  assert.equal(h.timers.size, 0);
});

test('a lost consume response recovers through the same token without a second consume', async () => {
  const h = harness();
  await h.init();
  h.queue.push({ok: true, status: 'authenticated'});
  h.queue.push(new Error('network'));
  await h.tick();
  assert.equal(h.elements['telegram-check'].hidden, false);
  assert.equal(h.navigation.length, 0);
  h.queue.push({ok: true, status: 'used'});
  await h.elements['telegram-check'].click();
  assert.equal(h.requests[3].url, h.requests[1].url);
  assert.equal(h.requests.length, 4);
  assert.deepEqual(h.navigation, [h.panel.dataset.loginUrl]);
});

test('polling follows the server interval, backs off and stops at the token lifetime', async () => {
  const h = harness();
  await h.init({poll_ms: 1000, expires_in: 20});
  const delays = [];
  for (let poll = 0; poll < 17; poll += 1) {
    h.queue.push({ok: true, status: 'pending'});
    delays.push(await h.tick());
  }
  assert.deepEqual(delays, [...Array(15).fill(1000), 2000, 2000]);
  assert.equal(h.timers.size, 0);
  assert.equal(h.requests.length, 18);
  assert.equal(h.elements['telegram-start'].disabled, false);
  assert.match(h.elements['telegram-status'].textContent, /eskirgan/);
});

test('throttled init shows the server copy and restores explicit start', async () => {
  const h = harness();
  h.queue.push({httpStatus: 429, ok: false, status: 'throttled', message: 'Synthetic throttle copy'});
  await h.elements['telegram-start'].click();
  assert.equal(h.elements['telegram-status'].textContent, 'Synthetic throttle copy');
  assert.equal(h.elements['telegram-start'].disabled, false);
  assert.equal(h.elements['telegram-link'].hidden, true);
  assert.equal(h.timers.size, 0);
});

test('cancel stops polling and closes this browser flow with a CSRF POST', async () => {
  const h = harness();
  await h.init();
  await h.elements['telegram-cancel'].click();
  assert.equal(h.timers.size, 0);
  const closing = h.requests.at(-1);
  assert.equal(closing.url, '/users/telegram-auth/cancel/');
  assert.equal(closing.options.method, 'POST');
  assert.equal(closing.options.headers['X-CSRFToken'], 'synthetic-csrf');
  assert.equal(h.elements['telegram-start'].disabled, false);
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

for (const status of ['authenticated', 'used']) {
  test(`dirty registration cannot block Telegram ${status} redirect; pageshow restores protection`, async () => {
    const h = harness({registration: true});
    await h.init();
    let leave = {preventDefault() {this.blocked = true;}};
    h.events.beforeunload(leave); assert.equal(leave.blocked, true);
    h.queue.push({ok: true, status});
    if (status === 'authenticated') h.queue.push({ok: true, status});
    await h.tick();
    assert.deepEqual(h.navigation, [h.panel.dataset.loginUrl]);
    h.events.pageshow();
    leave = {preventDefault() {this.blocked = true;}};
    h.events.beforeunload(leave); assert.equal(leave.blocked, true);
  });
}

test('pending, failed and cancelled Telegram attempts retain the registration dirty guard', async () => {
  for (const result of [{ok: true, status: 'pending'}, {ok: true, status: 'expired'}, new Error('network')]) {
    const h = harness({registration: true});
    await h.init(); h.queue.push(result); await h.tick();
    await h.elements['telegram-cancel'].click();
    const leave = {preventDefault() {this.blocked = true;}};
    h.events.beforeunload(leave);
    assert.equal(leave.blocked, true); assert.equal(h.navigation.length, 0);
  }
});
