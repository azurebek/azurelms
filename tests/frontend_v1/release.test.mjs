import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

const source = readFileSync(new URL('../../static/frontend_v1/js/release.js', import.meta.url), 'utf8');
function harness({dialogSupport = true, error = false} = {}) {
  const element = () => ({
    events: {}, attrs: {}, hidden: false, value: '', focused: false,
    addEventListener(name, fn) {this.events[name] = fn;},
    setAttribute(name, value) {this.attrs[name] = value;},
    removeAttribute(name) {delete this.attrs[name];},
    focus() {this.focused = true;},
  });
  const note = element(), cancel = element(), form = element(), errorNode = element();
  form.elements = {note};
  form.querySelector = () => cancel;
  const section = element();
  section.querySelector = selector => selector === '[data-release-form]' ? form : (error ? errorNode : null);
  section.before = () => {};
  const dialog = element(), reopen = element();
  dialog.append = () => {};
  if (dialogSupport) dialog.showModal = () => {dialog.open = true;};
  dialog.close = () => {dialog.open = false; dialog.events.close();};
  const events = {};
  runInNewContext(source, {
    document: {querySelector: () => section, createElement: tag => tag === 'dialog' ? dialog : reopen},
    window: {addEventListener: (name, fn) => events[name] = fn},
  });
  const fire = (handler) => {
    const e = {prevented: false, preventDefault() {this.prevented = true;}};
    handler(e);
    return e;
  };
  return {note, cancel, form, dialog, reopen, events, fire, errorNode};
}
test('modal opens with note focus; cancel/reopen preserves unsaved note', () => {
  const h = harness();
  assert.equal(h.dialog.open, true);
  assert.equal(h.note.focused, true);
  h.note.value = 'not saved';
  assert.equal(h.fire(h.cancel.events.click).prevented, true);
  assert.equal(h.dialog.open, false);
  assert.equal(h.reopen.focused, true);
  h.reopen.events.click();
  assert.equal(h.note.value, 'not saved');
  assert.equal(h.dialog.open, true);
});
test('dirty navigation warns, native submit does not; duplicate submit is blocked', () => {
  const h = harness();
  assert.equal(h.fire(h.events.beforeunload).prevented, false);
  h.note.value = 'draft';
  assert.equal(h.fire(h.events.beforeunload).prevented, true);
  assert.equal(h.fire(h.form.events.submit).prevented, false);
  assert.equal(h.fire(h.events.beforeunload).prevented, false);
  assert.equal(h.fire(h.form.events.submit).prevented, true);
  assert.equal(h.form.attrs['aria-busy'], 'true');
  h.events.pageshow();
  assert.equal(h.fire(h.form.events.submit).prevented, false);
});
test('unsupported dialog leaves native inline form intact', () => {
  const h = harness({dialogSupport: false});
  assert.equal(h.cancel.events.click, undefined);
  assert.equal(h.fire(h.form.events.submit).prevented, false);
});
test('validation error receives focus instead of textarea', () => {
  const h = harness({error: true});
  assert.equal(h.errorNode.focused, true);
  assert.equal(h.note.focused, false);
});
test('page without confirmation has no side effects', () => {
  runInNewContext(source, {document: {querySelector: () => null}});
});
