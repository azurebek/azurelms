import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

function harness() {
  const events = {};
  const forms = ['text', 'file', 'password'].map(type => {
    const field = { type, value: '', files: [] };
    const button = { disabled: false, setAttribute() {}, removeAttribute() {} };
    const status = {hidden:true};
    return { field, button, status, querySelector() { return status; }, querySelectorAll(selector) {
      if (selector.startsWith('button')) return [button];
      if (selector === 'input[type="password"]') return type === 'password' ? [field] : [];
      return [field];
    }, addEventListener(name, callback) { this[name] = callback; } };
  });
  let consent = false;
  const window = { addEventListener(name, callback) { events[name] = callback; }, confirm() { return consent; } };
  const navigator = {onLine:true};
  runInNewContext(readFileSync(new URL('../../static/frontend_v1/js/account.js', import.meta.url), 'utf8'), {
    document: { querySelectorAll() { return forms; } }, window, navigator,
    localStorage: { setItem() { throw Error('Private data must not persist'); } },
    sessionStorage: { setItem() { throw Error('Private data must not persist'); } },
  });
  const event = () => ({ defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } });
  return { forms, events, event, navigator, accept() { consent = true; } };
}

test('dirty navigation warns, restored value no longer dirty', () => {
  const h = harness();
  h.forms[0].field.value = 'Yangi ism';
  let e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, true);
  h.forms[0].field.value = '';
  e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, false);
});

test('native submit locks duplicate requests, bfcache restores controls', () => {
  const h = harness(); h.forms[0].field.value = 'Yangi';
  h.forms[0].submit(h.event()); assert.equal(h.forms[0].button.disabled, true);
  const duplicate = h.event(); h.forms[0].submit(duplicate); assert.equal(duplicate.defaultPrevented, true);
  const leave = h.event(); h.events.beforeunload(leave); assert.equal(leave.defaultPrevented, false);
  h.events.pageshow(); assert.equal(h.forms[0].button.disabled, false);
  const backLeave = h.event(); h.events.beforeunload(backLeave); assert.equal(backLeave.defaultPrevented, true);
});

test('saving another form requires consent before discarding dirty text/file', () => {
  const h = harness(); h.forms[0].field.value = 'Keep me'; h.forms[1].field.files = [{}];
  const cancel = h.event(); h.forms[1].submit(cancel);
  assert.equal(cancel.defaultPrevented, true); assert.equal(h.forms[1].button.disabled, false);
  assert.equal(h.forms[0].field.value, 'Keep me');
  h.accept(); const submit = h.event(); h.forms[1].submit(submit); assert.equal(submit.defaultPrevented, false);
});

test('passwords clear on departure and bfcache; profile text is retained only in DOM', () => {
  const h = harness(); h.forms[0].field.value = 'Keep me'; h.forms[2].field.value = 'private';
  h.events.pagehide(); assert.equal(h.forms[2].field.value, ''); assert.equal(h.forms[0].field.value, 'Keep me');
  h.forms[2].field.value = 'restored'; h.events.pageshow(); assert.equal(h.forms[2].field.value, '');
});

test('already cancelled submit does not lock form', () => {
  const h = harness(); const e = h.event(); e.preventDefault(); h.forms[0].submit(e);
  assert.equal(h.forms[0].button.disabled, false);
});

test('known offline keeps values and does not post or lock controls', () => {
  const h = harness(); h.navigator.onLine = false; h.forms[0].field.value = 'Qoralama';
  const e = h.event(); h.forms[0].submit(e);
  assert.equal(e.defaultPrevented, true); assert.equal(h.forms[0].button.disabled, false);
  assert.equal(h.forms[0].status.hidden, false); assert.equal(h.forms[0].field.value, 'Qoralama');
});
