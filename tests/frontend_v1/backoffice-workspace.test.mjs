import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source = readFileSync(new URL('../../static/backoffice/workspace.js', import.meta.url), 'utf8');
const keyFor = scope => `azurelms:workspace:draft:v1:${scope}`;
const event = target => ({target, defaultPrevented: false,
  preventDefault() { this.defaultPrevented = true; }});

class Element {
  constructor(properties = {}) {
    Object.assign(this, {events: {}, hidden: true, textContent: '',
      classList: {toggle() {}, add() {}}}, properties);
  }
  addEventListener(name, callback) { this.events[name] = callback; }
  matches() { return false; }
  focus() { this.focused = true; }
}

function makeForm(scope, {title = 'Saved title', bound = false, getUrl = ''} = {}) {
  const form = new Element({dataset: {draftScope: scope, boundForm: String(bound), draftGetUrl: getUrl}});
  form.fields = [
    new Element({name: 'title', id: 'title', type: 'text', value: title}),
    new Element({name: 'content', id: 'content', type: 'textarea', value: '<p>Saved body</p>'}),
    new Element({name: 'lesson_id', type: 'hidden', value: '42'}),
    new Element({name: 'lesson_revision', type: 'hidden', value: 'server-revision'}),
    new Element({name: 'csrfmiddlewaretoken', type: 'hidden', value: 'csrf-token'}),
    new Element({name: 'file', type: 'file', value: 'private-file.pdf'}),
  ];
  form.controls = Object.fromEntries(['status', 'recovery', 'recovery-text', 'restore', 'discard']
    .map(name => [name, new Element()]));
  form.querySelectorAll = () => form.fields;
  form.querySelector = selector => {
    const control = selector.match(/^\[data-draft-(.+)\]$/)?.[1];
    if (control) return form.controls[control] || null;
    const name = selector.match(/^\[name="(.+)"\]$/)?.[1];
    return form.fields.find(field => field.name === name) || null;
  };
  form.matches = selector => selector === '[data-workspace-draft]';
  form.append = field => form.fields.push(field);
  return form;
}

function harness({forms = [], receipts = [], stored = new Map(), failWrites = false,
  workbench = null, switcher = null, hash = '', failHistory = false} = {}) {
  const document = new Element({
    documentElement: new Element(),
    querySelector(selector) {
      if (selector === '[data-workbench]') return workbench;
      if (selector === '[data-pane-switch]') return switcher;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === '[data-workspace-draft]') return forms;
      if (selector === '[data-workspace-saved]') return receipts.map(({scope, nonce}) => ({
        dataset: {savedScope: scope, savedSubmissionId: nonce},
      }));
      return [];
    },
    createElement() { return new Element(); },
  });
  let nonceNumber = 0;
  const historyCalls = [];
  const history = {
    state: {existing: 'entry-state'},
    replaceState(state, title, url) {
      if (failHistory) throw Error('History update denied');
      historyCalls.push({state, title, url});
    },
  };
  const window = new Element({history, crypto: {randomUUID: () => `submission-${++nonceNumber}`}});
  const sessionStorage = {
    get length() { return stored.size; },
    key: index => [...stored.keys()][index],
    getItem: key => stored.get(key) ?? null,
    setItem(key, value) { if (failWrites) throw Error('Storage denied'); stored.set(key, value); },
    removeItem: key => stored.delete(key),
  };
  const location = new URL('http://workspace.test/backoffice/workspace/courses/3/?lesson=42' + hash);
  runInNewContext(source, {document, window, sessionStorage, location, URL});
  return {
    stored, document, window, historyCalls,
    read: scope => JSON.parse(stored.get(keyFor(scope)) ?? 'null'),
    edit(form, text) {
      const field = form.fields.find(item => item.name === 'title');
      field.value = text;
      form.events.input(event(field));
    },
    submit(form, action = 'lesson_save') {
      const submission = {...event(form), submitter: {value: action}};
      form.events.submit(submission);
      document.events.submit(submission);
      return form.fields.find(field => field.name === 'draft_submission_id')?.value;
    },
  };
}

test('preview after attaching material opens the preview pane instead of the retained fragment', () => {
  for (const initialPane of ['editor', 'preview']) {
    const workbench = new Element({dataset: {activePane: initialPane}});
    const buttons = ['editor', 'preview'].map(name => new Element({
      dataset: {paneTarget: name}, setAttribute(key, value) { this[key] = value; },
    }));
    const switcher = new Element({querySelectorAll: () => buttons});
    harness({workbench, switcher, hash: '#materials'});
    assert.equal(workbench.dataset.activePane, initialPane);
    assert.equal(buttons.find(button => button.dataset.paneTarget === initialPane)['aria-pressed'], 'true');
  }
});

test('preview history returns to a GET selection without clearing or auto-restoring its draft', () => {
  const first = makeForm('lesson-a'), original = harness({forms: [first]});
  original.edit(first, 'Preview only');
  original.submit(first, 'lesson_preview');
  const bound = makeForm('lesson-a', {title: 'Preview only', bound: true,
    getUrl: '/backoffice/workspace/courses/3/?lesson=42'});
  const returned = harness({forms: [bound], stored: original.stored, hash: '#materials'});
  assert.deepEqual(returned.historyCalls, [{state: {existing: 'entry-state'}, title: '',
    url: 'http://workspace.test/backoffice/workspace/courses/3/?lesson=42#materials'}]);
  assert.equal(bound.fields[0].value, 'Preview only');
  assert.equal(returned.read('lesson-a').values.title, 'Preview only');
  assert.equal(returned.read('lesson-a').lastSubmission, null);

  returned.edit(bound, 'Changed after preview');
  returned.window.events.pagehide();
  const freshGet = makeForm('lesson-a');
  const back = harness({forms: [freshGet], stored: returned.stored});
  assert.equal(freshGet.fields[0].value, 'Saved title');
  assert.equal(freshGet.controls.recovery.hidden, false);
  assert.equal(back.historyCalls.length, 0);
  freshGet.controls.restore.events.click();
  assert.equal(freshGet.fields[0].value, 'Changed after preview');
  assert.equal(freshGet.querySelector('[name="lesson_revision"]').value, 'server-revision');
});

test('history normalization rejects unrelated URLs and cannot break invalid POST recovery', () => {
  for (const getUrl of ['https://other.test/backoffice/workspace/courses/3/',
    '/backoffice/workspace/courses/99/?lesson=42']) {
    const bound = makeForm('lesson-a', {bound: true, getUrl});
    assert.equal(harness({forms: [bound]}).historyCalls.length, 0);
  }
  for (const failHistory of [false, true]) {
    const originalForm = makeForm('new-module-a'), original = harness({forms: [originalForm]});
    original.edit(originalForm, 'Older recoverable text');
    const bound = makeForm('new-module-a', {title: 'Rejected POST text', bound: true,
      getUrl: '/backoffice/workspace/courses/3/?module=7&new=1'});
    const current = harness({forms: [bound], stored: original.stored, failHistory});
    assert.equal(bound.fields[0].value, 'Rejected POST text');
    assert.equal(bound.controls.recovery.hidden, false);
    current.window.events.pagehide();
    assert.equal(current.read('new-module-a').values.title, 'Older recoverable text');
    const departure = event();
    current.window.events.beforeunload(departure);
    assert.equal(departure.defaultPrevented, true);
    bound.controls.restore.events.click();
    assert.equal(bound.fields[0].value, 'Older recoverable text');
    assert.equal(current.historyCalls.length, failHistory ? 0 : 1);
  }
});

test('a confirmed save clears only its matching submitted draft', () => {
  const first = makeForm('lesson-a'), second = makeForm('lesson-b');
  const h = harness({forms: [first, second]});
  h.edit(first, 'Ready to save');
  h.edit(second, 'Keep the other lesson');
  const nonce = h.submit(first);
  harness({stored: h.stored, receipts: [{scope: 'lesson-a', nonce}]});
  assert.equal(h.read('lesson-a'), null);
  assert.equal(h.read('lesson-b').values.title, 'Keep the other lesson');
});

test('an old receipt cannot clear a different submission or newer typing', () => {
  for (const newerTyping of [false, true]) {
    const form = makeForm('lesson-a'), h = harness({forms: [form]});
    h.edit(form, 'Submitted text');
    const nonce = h.submit(form);
    if (newerTyping) h.edit(form, 'Typed while the response was pending');
    harness({stored: h.stored, receipts: [{scope: 'lesson-a', nonce: newerTyping ? nonce : 'older-submission'}]});
    assert.equal(h.read('lesson-a').values.title,
      newerTyping ? 'Typed while the response was pending' : 'Submitted text');
  }
});

test('recovery is scoped and explicit, and never replaces the fresh server revision', () => {
  const previous = makeForm('user-session-lesson-a'), first = harness({forms: [previous]});
  first.edit(previous, 'Recover this lesson');
  const bound = makeForm('user-session-lesson-a', {title: 'Latest rejected POST', bound: true});
  const other = makeForm('other-user-session-lesson-a');
  const current = harness({stored: first.stored, forms: [bound, other]});
  assert.equal(bound.fields[0].value, 'Latest rejected POST');
  assert.equal(bound.controls.recovery.hidden, false);
  assert.equal(other.controls.recovery.hidden, true);
  const leaveBound = event();
  current.window.events.beforeunload(leaveBound);
  assert.equal(leaveBound.defaultPrevented, true);
  current.window.events.pagehide();
  assert.equal(first.read('user-session-lesson-a').values.title, 'Recover this lesson');
  bound.controls.restore.events.click();
  assert.equal(bound.fields[0].value, 'Recover this lesson');
  assert.equal(other.fields[0].value, 'Saved title');
  assert.equal(bound.querySelector('[name="lesson_revision"]').value, 'server-revision');
});

test('preview retains text without a save receipt, file payload, or revision tokens', () => {
  const form = makeForm('lesson-a'), h = harness({forms: [form]});
  h.edit(form, 'Preview only');
  assert.equal(h.submit(form, 'lesson_preview'), undefined);
  h.window.events.pagehide();
  const record = h.read('lesson-a');
  assert.equal(record.values.title, 'Preview only');
  assert.equal(record.lastSubmission, null);
  assert.deepEqual(Object.keys(record.values).sort(), ['content', 'title']);
  assert.doesNotMatch(h.stored.get(keyFor('lesson-a')), /csrf-token|server-revision|private-file/);
});

test('unavailable browser storage warns before navigating away or submitting another form', () => {
  const form = makeForm('lesson-a'), h = harness({forms: [form], failWrites: true});
  h.edit(form, 'Do not lose this text');
  assert.equal(h.read('lesson-a'), null);
  assert.match(form.controls.status.textContent, /saqlay olmadi/);
  const navigation = event();
  h.window.events.beforeunload(navigation);
  assert.equal(navigation.defaultPrevented, true);
  const otherForm = new Element();
  h.document.events.submit(event(otherForm));
  const otherSubmission = event();
  h.window.events.beforeunload(otherSubmission);
  assert.equal(otherSubmission.defaultPrevented, true);
  assert.equal(form.fields[0].value, 'Do not lose this text');

  // The response to preview/invalid POST must protect submitted text before any edit.
  const bound = makeForm('lesson-b', {title: 'Unsaved POST response', bound: true});
  const returned = harness({forms: [bound], failWrites: true});
  const immediateDeparture = event();
  returned.window.events.beforeunload(immediateDeparture);
  assert.equal(immediateDeparture.defaultPrevented, true);
  assert.equal(bound.fields[0].value, 'Unsaved POST response');
  assert.equal(returned.read('lesson-b'), null);

  // A successful browser recovery copy makes a normal preview return safe to leave.
  const normal = makeForm('lesson-a', {title: 'Preview text'});
  const savedBrowserCopy = harness({forms: [normal]});
  savedBrowserCopy.submit(normal, 'lesson_preview');
  const previewReturn = harness({stored: savedBrowserCopy.stored,
    forms: [makeForm('lesson-a', {title: 'Preview text', bound: true})]});
  const protectedDeparture = event();
  previewReturn.window.events.beforeunload(protectedDeparture);
  assert.equal(protectedDeparture.defaultPrevented, false);
});

test('logout clears workspace drafts without pagehide recreating them or deleting unrelated state', () => {
  const form = makeForm('lesson-a'), h = harness({forms: [form]});
  h.edit(form, 'Session-private text');
  h.stored.set('unrelated-preference', 'keep');
  const logout = new Element({matches: selector => selector === '[data-workspace-logout]'});
  h.document.events.submit(event(logout));
  h.window.events.pagehide();
  assert.equal(h.read('lesson-a'), null);
  assert.equal(h.stored.get('unrelated-preference'), 'keep');
});
