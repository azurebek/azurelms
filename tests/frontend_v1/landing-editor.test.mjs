import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source = readFileSync(new URL('../../static/js/landing-editor.js', import.meta.url), 'utf8');

function element(attributes = {}) {
  const classes = new Set();
  return {
    attributes, events: {},
    classList: {
      add(name) { classes.add(name); },
      remove(name) { classes.delete(name); },
      contains(name) { return classes.has(name); },
      toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); },
    },
    getAttribute(name) { return attributes[name] ?? null; },
    setAttribute(name, value) { attributes[name] = value; },
    removeAttribute(name) { delete attributes[name]; },
    addEventListener(name, handler, capture) { this.events[name] = {handler, capture}; },
  };
}

function harness({hash = '', errors = [], failHistory = false} = {}) {
  const form = element();
  const sections = ['rail', 'hero', 'demo'].map(key => element({
    'data-lc-section': key, 'data-lc-error': errors.includes(key) ? '1' : '0',
  }));
  const tabs = sections.map(section => element({'data-lc-target': section.getAttribute('data-lc-section')}));
  const picker = element();
  const timeouts = [];
  const history = {state: {existing: true}, replaceState() { if (failHistory) throw Error('blocked'); }};
  runInNewContext(source, {
    document: {
      readyState: 'complete',
      querySelector(selector) { return selector === '.lc-form' ? form : picker; },
      querySelectorAll(selector) { return selector === '[data-lc-section]' ? sections : tabs; },
    },
    window: {location: {hash}, setTimeout(callback) { timeouts.push(callback); }},
    history,
  });
  return {form, sections, tabs, picker, timeouts};
}

test('returned landing field errors take priority over a saved section hash', () => {
  const {sections, picker, tabs} = harness({hash: '#lc-rail', errors: ['hero']});
  assert.equal(sections[1].classList.contains('is-active'), true);
  assert.equal(sections[0].classList.contains('is-active'), false);
  assert.equal(picker.value, 'hero');
  assert.equal(tabs[1].getAttribute('aria-current'), 'true');
});

test('multiple invalid landing fields stay focusable until the owner picks a section', () => {
  const {form, sections, picker, tabs} = harness({hash: '#lc-rail'});
  assert.equal(form.events.invalid.capture, true);
  form.events.invalid.handler({target: {closest: () => sections[1]}});
  form.events.invalid.handler({target: {closest: () => sections[2]}});
  assert.equal(form.classList.contains('lc-tabbed'), false);
  assert.equal(picker.value, 'hero', 'the first invalid section remains selected');
  tabs[2].events.click.handler();
  assert.equal(form.classList.contains('lc-tabbed'), true);
  assert.equal(picker.value, 'demo');
});

test('mobile section selection and error recovery work when history is unavailable', () => {
  const {form, picker, sections, timeouts} = harness({failHistory: true});
  picker.value = 'demo';
  picker.events.change.handler();
  assert.equal(sections[2].classList.contains('is-active'), true);
  form.events.invalid.handler({target: {closest: () => null}});
  assert.equal(form.classList.contains('lc-tabbed'), false);
  timeouts.forEach(callback => callback());
  form.events.invalid.handler({target: {closest: () => sections[1]}});
  assert.equal(picker.value, 'hero');
});
