import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const code = readFileSync(new URL('../../static/frontend_v1/js/public-header.js', import.meta.url), 'utf8');
function harness() {
  const events = {}, summary = {focus(){this.focused = true;}};
  const menu = {open: false, querySelector: () => summary, contains: node => node === summary};
  runInNewContext(code, {
    document: {querySelector: () => menu, addEventListener: (type, fn) => {events[type] = fn;}},
    window: {matchMedia: () => ({addEventListener: (type, fn) => {events.breakpoint = fn;}}), addEventListener: (type, fn) => {events[type] = fn;}}
  });
  return {events, menu, summary};
}
test('native public menu closes on Escape and returns keyboard focus', () => {
  const h = harness(); h.menu.open = true;
  h.events.keydown({key:'Escape'});
  assert.equal(h.menu.open, false); assert.equal(h.summary.focused, true);
});
test('outside click closes public menu but inside click preserves native toggle', () => {
  const h = harness(); h.menu.open = true;
  h.events.click({target:h.summary}); assert.equal(h.menu.open, true);
  h.events.click({target:{}}); assert.equal(h.menu.open, false);
});
test('desktop transition and Back never leave an unexpected open menu', () => {
  const h = harness(); h.menu.open = true;
  h.events.breakpoint({matches:false}); assert.equal(h.menu.open, true);
  h.events.breakpoint({matches:true}); assert.equal(h.menu.open, false);
  h.menu.open = true; h.events.pageshow(); assert.equal(h.menu.open, false);
});
