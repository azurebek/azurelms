import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

function setup({unsaved = false} = {}) {
  const events = {}, notice = {hidden: true, scrollIntoView() {}}, navigator = {onLine:true};
  const forms = ['friendly', 'lite', 'light'].map((value, i) => ({
    field: {value}, busy: false,
    hasAttribute() {return i === 0 && unsaved;}, querySelectorAll() {return [this.field];},
    setAttribute() {this.busy = true;}, removeAttribute() {this.busy = false;},
    addEventListener(name, callback) {this[name] = callback;},
  }));
  let consent = false;
  const window = {addEventListener(name, callback) {events[name] = callback;}, confirm() {return consent;}};
  runInNewContext(readFileSync(new URL('../../static/frontend_v1/js/settings.js', import.meta.url), 'utf8'), {
    window, navigator, document: {querySelectorAll() {return forms;}, querySelector() {return notice;}},
    localStorage: {setItem() {throw Error('Private data must not persist');}},
    sessionStorage: {setItem() {throw Error('Private data must not persist');}},
  });
  return {forms, events, notice, navigator, accept() {consent = true;}, event() {return {defaultPrevented:false, preventDefault() {this.defaultPrevented = true;}};}};
}

test('selects do not auto-submit and dirty navigation warns until restored', () => {
  const h = setup(); h.forms[0].field.value = 'formal';
  let e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, true);
  assert.equal(h.forms[0].busy, false);
  h.forms[0].field.value = 'friendly'; e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, false);
});
test('another preference must not be silently discarded by native POST', () => {
  const h = setup(); h.forms[1].field.value = 'other';
  let e = h.event(); h.forms[0].submit(e); assert.equal(e.defaultPrevented, true);
  assert.equal(h.forms[0].busy, false);
  h.accept(); e = h.event(); h.forms[0].submit(e); assert.equal(e.defaultPrevented, false);
});
test('duplicate and cross-form submission locked without disabling submitted values', () => {
  const h = setup(); h.forms[0].submit(h.event());
  const duplicate = h.event(); h.forms[1].submit(duplicate); assert.equal(duplicate.defaultPrevented, true);
  const leave = h.event(); h.events.beforeunload(leave); assert.equal(leave.defaultPrevented, false);
  h.events.pageshow(); assert.equal(h.forms[0].busy, false);
  const fresh = h.event(); h.forms[1].submit(fresh); assert.equal(fresh.defaultPrevented, false);
});
test('known offline leaves pending selection untouched and announces no send', () => {
  const h = setup(); h.navigator.onLine = false; h.forms[0].field.value = 'formal';
  const e = h.event(); h.forms[0].submit(e);
  assert.equal(e.defaultPrevented, true); assert.equal(h.notice.hidden, false);
  assert.equal(h.forms[0].busy, false); assert.equal(h.forms[0].field.value, 'formal');
  h.navigator.onLine = true; h.forms[0].submit(h.event()); assert.equal(h.notice.hidden, true);
});
test('bound rejected selection already dirty; canceled submit does not lock', () => {
  const h = setup({unsaved:true}); const e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, true);
  const cancelled = h.event(); cancelled.preventDefault(); h.forms[0].submit(cancelled); assert.equal(h.forms[0].busy, false);
});
