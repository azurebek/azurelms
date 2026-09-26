import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

function setup(implicit = false) {
  const events = {}, navigator = {onLine:true};
  const text = {tagName:'TEXTAREA', value:'saved', defaultValue:'saved'};
  const checkbox = {tagName:'INPUT', type:'checkbox', checked:false, defaultChecked:false};
  const file = {tagName:'INPUT', type:'file', files:[]};
  const select = {tagName:'SELECT', options:[{selected:true, defaultSelected:!implicit}, {selected:false, defaultSelected:false}]};
  const hint = {textContent:''};
  const forms = [[text, checkbox, file], [select], []].map((fields, i) => ({fields, busy:false, unsaved:false,
    querySelectorAll: () => fields, querySelector: () => i === 1 ? hint : null,
    hasAttribute() {return this.unsaved;}, addEventListener(name, fn) {this[name] = fn;},
    setAttribute() {this.busy = true;}, removeAttribute() {this.busy = false;}}));
  const notice = {hidden:true, focus() {this.focused = true;}}, pending = {hidden:true}, error = {focus() {this.focused = true;}};
  const confirm = {answer:false, calls:0};
  const storage = {setItem() {throw Error('No private draft persistence');}};
  runInNewContext(readFileSync(new URL('../../static/frontend_v1/js/library.js', import.meta.url), 'utf8'), {
    navigator, localStorage:storage, sessionStorage:storage,
    document: {querySelectorAll: () => forms, querySelector: s => s.includes('offline') ? notice : s.includes('pending') ? pending : error},
    window:{addEventListener(name, fn) {events[name] = fn;}, confirm() {confirm.calls++; return confirm.answer;}}});
  return {forms, text, checkbox, file, select, notice, pending, error, hint, confirm, navigator, events,
    event: () => ({defaultPrevented:false, preventDefault() {this.defaultPrevented = true;}})};
}

test('text/checkbox/file drafts warn on exit without persisting them', () => {
  for (const change of [h => h.text.value = 'draft', h => h.checkbox.checked = true, h => h.file.files = ['synthetic']]) {
    const h = setup(); change(h); const e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, true);
  }
});
test('bound rejected draft warns even though values are new DOM defaults', () => {
  const h = setup(); h.forms[0].unsaved = true; const e = h.event(); h.events.beforeunload(e);
  assert.equal(e.defaultPrevented, true); assert.equal(h.error.focused, true);
});
test('filter change is explicit and reverting clears dirty state', () => {
  const h = setup(); h.select.options[0].selected = false; h.select.options[1].selected = true;
  h.forms[1].change(); assert.match(h.hint.textContent, /hali qo‘llanmagan/); assert.equal(h.forms[1].busy, false);
  h.select.options[0].selected = true; h.select.options[1].selected = false;
  const e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented, false);
});
test('offline preserves file and focuses warning without locking form', () => {
  const h = setup(); h.navigator.onLine = false; h.file.files = ['synthetic']; const e = h.event(); h.forms[0].submit(e);
  assert.equal(e.defaultPrevented, true); assert.equal(h.notice.focused, true); assert.equal(h.forms[0].busy, false); assert.equal(h.file.files.length, 1);
});
test('different action cannot silently discard edited metadata', () => {
  const h = setup(); h.text.value = 'draft'; const e = h.event(); h.forms[2].submit(e);
  assert.equal(e.defaultPrevented, true); assert.equal(h.confirm.calls, 1); assert.equal(h.forms[2].busy, false);
  h.confirm.answer = true; const approved = h.event(); h.forms[2].submit(approved); assert.equal(approved.defaultPrevented, false);
});
test('native submit locks duplicate but never disables upload, pageshow resets', () => {
  const h = setup(); h.file.files = ['synthetic']; h.forms[0].submit(h.event());
  assert.equal(h.file.disabled, undefined); assert.equal(h.pending.hidden, false);
  const duplicate = h.event(); h.forms[0].submit(duplicate); assert.equal(duplicate.defaultPrevented, true);
  const leaving = h.event(); h.events.beforeunload(leaving); assert.equal(leaving.defaultPrevented, false);
  h.events.pageshow(); assert.equal(h.forms[0].busy, false); assert.equal(h.pending.hidden, true);
});
test('already canceled submission does not show pending acknowledgement', () => {
  const h = setup(); const e = h.event(); e.preventDefault(); h.forms[0].submit(e);
  assert.equal(h.forms[0].busy, false); assert.equal(h.pending.hidden, true);
});
test('implicit first-option selection is not an unsaved edit', () => {
  const h = setup(true); const e = h.event(); h.events.beforeunload(e);
  assert.equal(e.defaultPrevented, false); h.forms[0].submit(h.event()); assert.equal(h.confirm.calls, 0);
});
