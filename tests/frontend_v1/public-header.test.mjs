import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const code = readFileSync(new URL('../../static/frontend_v1/js/public-header.js', import.meta.url), 'utf8');
const DESKTOP_MENU = '(min-width: 1200px)';
const COMPACT_FOOTER = '(max-width: 639.98px)';

function fold() {
  const listeners = {};
  const summary = {tabIndex: 0, addEventListener: (type, fn) => {listeners[type] = fn;}};
  return {open: true, summary, listeners, querySelector: () => summary};
}
function harness({folds = [], compact = false} = {}) {
  const events = {}, media = {}, summary = {focus(){this.focused = true;}};
  const menu = {open: false, querySelector: () => summary, contains: node => node === summary};
  runInNewContext(code, {
    document: {
      querySelector: () => menu,
      querySelectorAll: selector => (selector === '[data-footer-fold]' ? folds : []),
      addEventListener: (type, fn) => {events[type] = fn;},
    },
    window: {
      matchMedia: query => {
        const list = {matches: query === COMPACT_FOOTER ? compact : false, addEventListener: (type, fn) => {list.change = fn;}};
        media[query] = list;
        return list;
      },
      addEventListener: (type, fn) => {events[type] = fn;},
    },
  });
  return {events, media, menu, summary};
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
  // public.css dagi mobil menyu chegarasi bilan bir xil.
  assert.ok(h.media[DESKTOP_MENU]);
  h.media[DESKTOP_MENU].change({matches:false}); assert.equal(h.menu.open, true);
  h.media[DESKTOP_MENU].change({matches:true}); assert.equal(h.menu.open, false);
  h.menu.open = true; h.events.pageshow(); assert.equal(h.menu.open, false);
});
test('footer folds collapse on phones and stay open columns on wider screens', () => {
  const folds = [fold(), fold()];
  const h = harness({folds, compact: true});
  assert.deepEqual(folds.map(f => [f.open, f.summary.tabIndex]), [[false, 0], [false, 0]]);
  h.media[COMPACT_FOOTER].matches = false; h.media[COMPACT_FOOTER].change();
  assert.deepEqual(folds.map(f => [f.open, f.summary.tabIndex]), [[true, -1], [true, -1]]);
});
test('footer summary toggles only on phones', () => {
  const folds = [fold()];
  const h = harness({folds, compact: false});
  let prevented = false;
  folds[0].listeners.click({preventDefault: () => {prevented = true;}});
  assert.equal(prevented, true);
  h.media[COMPACT_FOOTER].matches = true; h.media[COMPACT_FOOTER].change();
  prevented = false;
  folds[0].listeners.click({preventDefault: () => {prevented = true;}});
  assert.equal(prevented, false);
});
test('without footer folds nothing is wired', () => {
  const h = harness();
  assert.equal(h.media[COMPACT_FOOTER], undefined);
});
