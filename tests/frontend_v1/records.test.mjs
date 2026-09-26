import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

function setup() {
  const events = {}, navigator = {onLine:true};
  const select = {tagName:'SELECT', options:[{selected:true, defaultSelected:true}, {selected:false, defaultSelected:false}]};
  const file = {tagName:'INPUT', type:'file', files:[]};
  const forms = [select, file].map((field, i) => ({field, busy:false,
    querySelectorAll: () => [field], hasAttribute: () => i === 0,
    addEventListener(name, fn) {this[name] = fn;}, setAttribute() {this.busy = true;}, removeAttribute() {this.busy = false;}}));
  const notice = {hidden:true, focus() {this.focused = true;}}, hint = {textContent:''};
  const storage = {setItem() {throw Error('No private draft persistence');}};
  runInNewContext(readFileSync(new URL('../../static/frontend_v1/js/records.js', import.meta.url), 'utf8'), {
    navigator, localStorage:storage, sessionStorage:storage,
    document: {querySelectorAll: () => forms, querySelector: s => s.includes('hint') ? hint : notice},
    window:{addEventListener(name, fn) {events[name] = fn;}}});
  return {forms, select, file, notice, hint, navigator, events,
    event: () => ({defaultPrevented:false, preventDefault() {this.defaultPrevented = true;}})};
}
test('selection does not auto-submit and pending filters warn on exit', () => {
  const h = setup(); h.select.options[0].selected = false; h.select.options[1].selected = true;
  h.forms[0].change(); assert.match(h.hint.textContent, /hali qo‘llanmagan/); assert.equal(h.forms[0].busy, false);
  const e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, true);
  h.select.options[0].selected = true; h.select.options[1].selected = false;
  const reset = h.event(); h.events.beforeunload(reset); assert.equal(reset.defaultPrevented, false);
});
test('file draft warns and is not stored or disabled during native upload', () => {
  const h = setup(); h.file.files = ['synthetic-file'];
  const e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, true);
  h.forms[1].submit(h.event()); assert.equal(h.file.files.length, 1); assert.equal(h.file.disabled, undefined);
  const leaving = h.event(); h.events.beforeunload(leaving); assert.equal(leaving.defaultPrevented, false);
});
test('offline blocks send, focuses warning and preserves pending file', () => {
  const h = setup(); h.navigator.onLine = false; h.file.files = ['synthetic-file'];
  const e = h.event(); h.forms[1].submit(e); assert.equal(e.defaultPrevented, true);
  assert.equal(h.notice.focused, true); assert.equal(h.forms[1].busy, false); assert.equal(h.file.files.length, 1);
});
test('native duplicate/cross-form submits locked, pageshow restores controls', () => {
  const h = setup(); h.forms[0].submit(h.event());
  const e = h.event(); h.forms[1].submit(e); assert.equal(e.defaultPrevented, true);
  h.events.pageshow(); assert.equal(h.forms[0].busy, false);
  const fresh = h.event(); h.forms[1].submit(fresh); assert.equal(fresh.defaultPrevented, false);
});
test('previously canceled submit never creates a false busy state', () => {
  const h = setup(); const e = h.event(); e.preventDefault(); h.forms[0].submit(e);
  assert.equal(h.forms[0].busy, false);
});
