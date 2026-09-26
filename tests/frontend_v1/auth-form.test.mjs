import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

function setup({bound = false} = {}) {
  const events = {}, navigator = {onLine:true};
  const fields = [{id:'email', value:'', defaultValue:'', type:'email'}, ...['p1','p2'].map(id => ({id, value:'', defaultValue:'', type:'password'}))];
  const passwords = fields.slice(1);
  const toggles = passwords.map(field => ({attrs:{'aria-controls':field.id}, textContent:'Ko‘rsatish',
    addEventListener(name, fn) {this[name] = fn;}, getAttribute(name) {return this.attrs[name];}, setAttribute(name, value) {this.attrs[name] = value;}}));
  const form = {busy:false, hasAttribute() {return bound;}, querySelectorAll() {return fields;},
    addEventListener(name, fn) {this[name] = fn;}, setAttribute() {this.busy = true;}, removeAttribute() {this.busy = false;}};
  const notice = {hidden:true, focus() {this.focused = true;}};
  const storage = {setItem() {throw Error('Auth draft must not persist');}};
  runInNewContext(readFileSync(new URL('../../static/frontend_v1/js/auth-form.js', import.meta.url),'utf8'), {
    navigator, localStorage:storage, sessionStorage:storage,
    document: {querySelectorAll: s => s === '[data-auth-form]' ? [form] : s === '[data-auth-password]' ? passwords : toggles,
      querySelector: () => notice, getElementById: id => fields.find(f => f.id === id)},
    window:{addEventListener(name, fn) {events[name] = fn;}}});
  return {fields, passwords, toggles, events, form, navigator, notice,
    event: () => ({defaultPrevented:false, preventDefault() {this.defaultPrevented = true;}})};
}
test('both visibility buttons affect only their own native field', () => {
  const h = setup(); h.passwords[0].value = 'synthetic'; h.toggles[0].click();
  assert.equal(h.passwords[0].type, 'text'); assert.equal(h.passwords[1].type, 'password');
  assert.equal(h.toggles[0].attrs['aria-pressed'], 'true'); assert.equal(h.passwords[0].value, 'synthetic');
});
test('known offline blocks submission, focuses message and preserves all input', () => {
  const h = setup(); h.navigator.onLine = false; h.passwords[0].value = 'synthetic';
  const e = h.event(); h.form.submit(e);
  assert.equal(e.defaultPrevented,true); assert.equal(h.notice.focused,true); assert.equal(h.notice.hidden,false);
  assert.equal(h.passwords[0].value,'synthetic'); assert.equal(h.form.busy,false);
});
test('native POST not duplicated and passwords survive until browser serializes', () => {
  const h = setup(); h.passwords[0].value = 'synthetic';
  h.form.submit(h.event()); const second = h.event(); h.form.submit(second);
  assert.equal(second.defaultPrevented,true); assert.equal(h.form.busy,true); assert.equal(h.passwords[0].value,'synthetic');
  const leave = h.event(); h.events.beforeunload(leave); assert.equal(leave.defaultPrevented,false);
});
test('page lifecycle clears even revealed passwords, not ordinary text, and unlocks form', () => {
  const h = setup(); h.fields[0].value = 'synthetic@example.test'; h.passwords[0].value = 'synthetic'; h.toggles[0].click();
  h.form.submit(h.event()); h.events.pagehide(); h.events.pageshow();
  assert.equal(h.passwords[0].value,''); assert.equal(h.passwords[0].type,'password');
  assert.equal(h.toggles[0].attrs['aria-pressed'],'false'); assert.equal(h.form.busy,false);
  assert.equal(h.fields[0].value,'synthetic@example.test');
});
test('ordinary input and bound rejected forms warn before leaving without storage', () => {
  const h = setup(); h.fields[0].value = 'typed'; let e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented,true);
  h.fields[0].value = ''; e = h.event(); h.events.beforeunload(e); assert.equal(e.defaultPrevented,false);
  const bound = setup({bound:true}); e = bound.event(); bound.events.beforeunload(e); assert.equal(e.defaultPrevented,true);
});
test('already canceled submission does not lock the form', () => {
  const h = setup(); const e = h.event(); e.preventDefault(); h.form.submit(e); assert.equal(h.form.busy,false);
});
