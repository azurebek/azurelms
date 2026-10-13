import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source = readFileSync(new URL('../../static/backoffice/practice.js', import.meta.url), 'utf8');
const keyFor = scope => `azurelms:practice:draft:v1:${scope}`;
const event = target => ({target, defaultPrevented: false,
  preventDefault() { this.defaultPrevented = true; }});

class Element {
  constructor(properties = {}) {
    Object.assign(this, {events: {}, hidden: true, textContent: '', children: []}, properties);
  }
  addEventListener(name, callback) { this.events[name] = callback; }
  matches() { return false; }
  append(child) { this.children.push(child); }
  submit() { this.submitted = (this.submitted || 0) + 1; }
}

const field = (name, value, type = 'text', extra = {}) => new Element({name, value, type, id: name, ...extra});
function makeForm(scope, {title = 'Saqlangan test', bound = false, transfer = '', getUrl = '', questions = 1,
  choices = 2, selected = '0', xp = '20'} = {}) {
  const form = new Element({action: 'http://workspace.test/backoffice/workspace/courses/3/lessons/42/practice/quiz/',
    dataset: {draftScope: scope, boundForm: String(bound), draftTransferId: transfer, draftGetUrl: getUrl}});
  const actionAttribute = form.action;
  form.getAttribute = name => name === 'action' ? actionAttribute : null;
  form.fields = [field('title', title), field('xp_reward', xp),
    field('questions-TOTAL_FORMS', String(questions), 'hidden'),
    field('csrfmiddlewaretoken', 'fresh-csrf', 'hidden'), field('editor_revision', 'fresh-revision', 'hidden'),
    field('confirm_save', 'on', 'checkbox', {checked: true}), field('file', 'private-file.pdf', 'file'),
    field('description', 'private-upload.bin', 'file'), field('password', 'private-password', 'password')];
  for (let index = 0; index < questions; index++) {
    form.fields.push(field(`questions-${index}-id`, String(101 + index), 'hidden'),
      field(`questions-${index}-text`, `${index + 1}-savol matni`, 'textarea'),
      field(`questions-${index}-choices-TOTAL_FORMS`, String(choices), 'hidden'));
    for (let option = 0; option < choices; option++) form.fields.push(
      field(`questions-${index}-choices-${option}-id`, String(201 + index * 10 + option), 'hidden'),
      field(`questions-${index}-choices-${option}-text`, `${option + 1}-variant`),
      field(`questions-${index}-correct`, String(option), 'radio', {checked: String(option) === selected}));
  }
  form.controls = Object.fromEntries(['status', 'recovery', 'restore', 'discard'].map(name => [name, new Element()]));
  form.querySelectorAll = () => form.fields;
  form.querySelector = selector => {
    const control = selector.match(/^\[data-draft-(.+)\]$/)?.[1];
    if (control) return form.controls[control] || null;
    const name = selector.match(/^\[name="(.+)"\]$/)?.[1];
    return form.fields.find(item => item.name === name) || null;
  };
  form.matches = selector => selector === '[data-practice-draft]';
  form.append = child => form.fields.push(child);
  return form;
}

function harness({forms = [], stored = new Map(), receipts = [], failWrites = false, online = true,
  failHistory = false, editors = {}} = {}) {
  const historyCalls = [];
  const document = new Element({body: new Element(),
    querySelectorAll(selector) {
      if (selector === '[data-practice-draft]') return forms;
      if (selector === '[data-practice-saved]') return receipts.map(({scope, nonce}) => ({
        dataset: {savedScope: scope, savedSubmissionId: nonce},
      }));
      return [];
    },
    createElement: tag => new Element({tagName: tag.toUpperCase()}),
  });
  let nonceNumber = 0;
  const editorCallbacks = {};
  const window = new Element({editors, navigator: {onLine: online},
    ckeditorRegisterCallback(id, callback) { editorCallbacks[id] = callback; },
    crypto: {randomUUID: () => `transfer-${++nonceNumber}`},
    history: {state: {retained: true}, replaceState(state, title, url) {
      if (failHistory) throw Error('History unavailable');
      historyCalls.push({state, title, url});
    }}});
  const sessionStorage = {
    get length() { return stored.size; }, key: index => [...stored.keys()][index],
    getItem: key => stored.get(key) ?? null,
    setItem(key, value) { if (failWrites) throw Error('Storage unavailable'); stored.set(key, value); },
    removeItem: key => stored.delete(key),
  };
  const location = new URL('http://workspace.test/backoffice/workspace/courses/3/lessons/42/practice/quiz/?quiz=5');
  runInNewContext(source, {document, window, sessionStorage, location, URL});
  return {document, window, stored, historyCalls, editorCallbacks,
    read: scope => JSON.parse(stored.get(keyFor(scope)) ?? 'null'),
    edit(form, name, value) {
      const target = form.fields.find(item => item.name === name);
      target.value = value;
      form.events.input(event(target));
    },
    submit(form, action = 'save') {
      const submission = {...event(form), submitter: {value: action}};
      form.events.submit(submission);
      document.events.submit(submission);
      return submission;
    },
  };
}
const postedValues = form => Object.fromEntries(form.children.map(item => [item.name, item.value]));

test('draft records the selected radio, including no selection, and only safe authored fields', () => {
  for (const selected of ['0', '1', '']) {
    const form = makeForm('quiz-a', {selected}), current = harness({forms: [form]});
    current.edit(form, 'title', 'Yangi test');
    const record = current.read('quiz-a');
    assert.equal(record.values['questions-0-correct'], selected);
    assert.equal(record.values['questions-0-id'], '101');
    assert.equal(record.values['questions-0-choices-0-id'], '201');
    for (const name of ['csrfmiddlewaretoken', 'editor_revision', 'confirm_save', 'file', 'password', 'description'])
      assert.equal(record.values[name], undefined);
    assert.doesNotMatch(current.stored.get(keyFor('quiz-a')), /fresh-csrf|fresh-revision|private-/);
  }
});

test('matching add-question and add-choice responses persist expanded structure across reload', () => {
  const form = makeForm('quiz-a'), first = harness({forms: [form]});
  first.edit(form, 'title', 'Uch savolli test');
  first.submit(form, 'add_question');
  const transfer = first.read('quiz-a').lastTransfer.id;
  const expanded = makeForm('quiz-a', {title: 'Uch savolli test', questions: 3, choices: 4,
    bound: true, transfer});
  const returned = harness({forms: [expanded], stored: first.stored});
  assert.equal(returned.read('quiz-a').values['questions-TOTAL_FORMS'], '3');
  assert.equal(returned.read('quiz-a').values['questions-2-choices-TOTAL_FORMS'], '4');
  assert.equal(returned.read('quiz-a').values['questions-2-choices-3-text'], '4-variant');
  assert.equal(returned.read('quiz-a').lastSubmission, undefined);
  const reload = makeForm('quiz-a');
  const reopened = harness({forms: [reload], stored: returned.stored});
  assert.equal(reload.controls.recovery.hidden, false);
  assert.equal(reload.fields.find(item => item.name === 'questions-TOTAL_FORMS').value, '1');
  assert.equal(reopened.document.body.children.length, 0);
  reload.controls.restore.events.click();
  const restored = reopened.document.body.children[0];
  assert.equal(restored.submitted, 1);
  assert.equal(postedValues(restored)['questions-TOTAL_FORMS'], '3');
  assert.equal(postedValues(restored)['questions-2-choices-3-text'], '4-variant');
});

test('explicit recovery posts safe draft fields with current CSRF and revision and never saves implicitly', () => {
  const form = makeForm('quiz-a'), first = harness({forms: [form]});
  first.edit(form, 'title', 'Tiklanadigan test');
  const fresh = makeForm('quiz-a'), reopened = harness({forms: [fresh], stored: first.stored});
  assert.equal(fresh.fields[0].value, 'Saqlangan test');
  assert.equal(reopened.document.body.children.length, 0);
  fresh.controls.restore.events.click();
  const posted = reopened.document.body.children[0], values = postedValues(posted);
  assert.equal(posted.method, 'post');
  assert.equal(posted.action, fresh.action);
  assert.equal(values.action, 'restore');
  assert.equal(values.title, 'Tiklanadigan test');
  assert.equal(values.csrfmiddlewaretoken, 'fresh-csrf');
  assert.equal(values.editor_revision, 'fresh-revision');
  assert.equal(values.confirm_save, undefined);
  assert.equal(values.draft_submission_id, undefined);
  assert.equal(values.file, undefined);
  assert.equal(reopened.read('quiz-a').lastTransfer.id, values.draft_transfer_id);
  fresh.controls.restore.events.click();
  assert.equal(reopened.document.body.children.length, 1, 'a second click cannot send another restoration');
});

test('save receipt clears only its scope and matching nonce and submitted snapshot', () => {
  const first = makeForm('quiz-a'), second = makeForm('quiz-b');
  const current = harness({forms: [first, second]});
  current.edit(first, 'title', 'Saqlanadi');
  current.edit(second, 'title', 'Boshqa qoralama');
  current.submit(first);
  const nonce = current.read('quiz-a').lastSubmission.id;
  harness({stored: current.stored, receipts: [{scope: 'quiz-b', nonce}, {scope: 'quiz-a', nonce: 'older'}]});
  assert.equal(current.read('quiz-a').values.title, 'Saqlanadi');
  assert.equal(current.read('quiz-b').values.title, 'Boshqa qoralama');
  harness({stored: current.stored, receipts: [{scope: 'quiz-a', nonce}]});
  assert.equal(current.read('quiz-a'), null);
  assert.equal(current.read('quiz-b').values.title, 'Boshqa qoralama');
});

test('a save acknowledgement never erases typing after the submitted snapshot', () => {
  const form = makeForm('quiz-a'), current = harness({forms: [form]});
  current.edit(form, 'title', 'Yuborilgan matn');
  current.submit(form);
  const nonce = current.read('quiz-a').lastSubmission.id;
  current.edit(form, 'title', 'Keyin yozilgan matn');
  harness({stored: current.stored, receipts: [{scope: 'quiz-a', nonce}]});
  assert.equal(current.read('quiz-a').values.title, 'Keyin yozilgan matn');
});

test('unrelated rejected response preserves the older recoverable draft and warns before leaving', () => {
  for (const transfer of ['', 'unrelated-transfer']) {
    const first = makeForm('quiz-a'), previous = harness({forms: [first]});
    previous.edit(first, 'title', 'Oldingi qoralama');
    previous.submit(first, 'preview');
    const bound = makeForm('quiz-a', {bound: true, transfer, title: 'Rad etilgan matn'});
    const current = harness({forms: [bound], stored: previous.stored});
    assert.equal(bound.fields[0].value, 'Rad etilgan matn');
    assert.equal(bound.controls.recovery.hidden, false);
    current.window.events.pagehide();
    assert.equal(current.read('quiz-a').values.title, 'Oldingi qoralama');
    const leaving = event();
    current.window.events.beforeunload(leaving);
    assert.equal(leaving.defaultPrevented, true);
  }
});

test('a matching transfer does not overwrite newer typing in the stored draft', () => {
  const first = makeForm('quiz-a'), previous = harness({forms: [first]});
  previous.edit(first, 'title', 'Yuborilgan');
  previous.submit(first, 'add_question');
  const transfer = previous.read('quiz-a').lastTransfer.id;
  previous.edit(first, 'title', 'Yangi matn');
  const bound = makeForm('quiz-a', {bound: true, transfer, questions: 2, title: 'Yuborilgan'});
  const current = harness({forms: [bound], stored: previous.stored});
  assert.equal(current.read('quiz-a').values.title, 'Yangi matn');
  assert.equal(current.read('quiz-a').values['questions-TOTAL_FORMS'], '1');
  assert.equal(bound.controls.recovery.hidden, false);
});

test('invalid numeric input stays raw through bound persistence and explicit recovery', () => {
  const bound = makeForm('quiz-a', {bound: true, xp: 'not-a-number'});
  bound.fields.push(field('max_xp', '-x12'));
  const current = harness({forms: [bound]});
  assert.equal(current.read('quiz-a').values.xp_reward, 'not-a-number');
  assert.equal(current.read('quiz-a').values.max_xp, '-x12');
  const fresh = makeForm('quiz-a'), reopened = harness({forms: [fresh], stored: current.stored});
  fresh.controls.restore.events.click();
  const values = postedValues(reopened.document.body.children[0]);
  assert.equal(values.xp_reward, 'not-a-number');
  assert.equal(values.max_xp, '-x12');
});

test('storage failure warns before leaving edited or newly bound content', () => {
  for (const bound of [false, true]) {
    const form = makeForm('quiz-a', {bound}), current = harness({forms: [form], failWrites: true});
    if (!bound) current.edit(form, 'title', 'Yo‘qolmasin');
    assert.equal(current.read('quiz-a'), null);
    assert.match(form.controls.status.textContent, /saqlay olmadi/);
    const leaving = event();
    current.window.events.beforeunload(leaving);
    assert.equal(leaving.defaultPrevented, true);
  }
});

test('offline submit and recovery keep drafts in place and do not submit', () => {
  const form = makeForm('quiz-a'), current = harness({forms: [form], online: false});
  current.edit(form, 'title', 'Oflayn yozilgan');
  assert.equal(current.submit(form).defaultPrevented, true);
  assert.equal(current.read('quiz-a').lastSubmission, undefined);
  assert.match(form.controls.status.textContent, /Aloqa yo‘q/);
  const fresh = makeForm('quiz-a'), reopened = harness({forms: [fresh], stored: current.stored, online: false});
  fresh.controls.restore.events.click();
  assert.equal(reopened.document.body.children.length, 0);
  assert.equal(reopened.read('quiz-a').values.title, 'Oflayn yozilgan');
  reopened.window.navigator.onLine = true;
  fresh.controls.restore.events.click();
  assert.equal(reopened.document.body.children[0].submitted, 1);
});

test('double submit is prevented until returning to the page, then receives a fresh token', () => {
  const form = makeForm('quiz-a'), current = harness({forms: [form]});
  current.edit(form, 'title', 'Bir marta');
  assert.equal(current.submit(form).defaultPrevented, false);
  const first = current.read('quiz-a').lastSubmission.id;
  assert.equal(current.submit(form).defaultPrevented, true);
  assert.equal(current.read('quiz-a').lastSubmission.id, first);
  current.window.events.pageshow();
  assert.equal(current.submit(form).defaultPrevented, false);
  assert.notEqual(current.read('quiz-a').lastSubmission.id, first);
});

test('logout removes only practice drafts and pagehide cannot recreate them', () => {
  const first = makeForm('quiz-a'), second = makeForm('assignment-b');
  const current = harness({forms: [first, second]});
  current.edit(first, 'title', 'Test qoralamasi');
  current.edit(second, 'title', 'Topshiriq qoralamasi');
  current.stored.set('unrelated-setting', 'keep');
  const logout = new Element({matches: selector => selector === '[data-workspace-logout]'});
  current.document.events.submit(event(logout));
  current.window.events.pagehide();
  assert.equal(current.read('quiz-a'), null);
  assert.equal(current.read('assignment-b'), null);
  assert.equal(current.stored.get('unrelated-setting'), 'keep');
});

test('malformed and unsafe stored records cannot be offered or posted as a recovery', () => {
  for (const values of [{title: 'Text', editor_revision: 'old'}, {title: 'Text', confirm_save: 'on'},
    {title: 'Text', 'questions-1000-text': 'too many'}, {title: false}]) {
    const stored = new Map([[keyFor('quiz-a'), JSON.stringify({version: 1, values})]]);
    const form = makeForm('quiz-a'), current = harness({forms: [form], stored});
    assert.equal(form.controls.recovery.hidden, true);
    form.controls.restore.events.click();
    assert.equal(current.document.body.children.length, 0);
  }
});

test('bound history rewrite remains on the same editor and failures preserve recovery', () => {
  const allowed = '/backoffice/workspace/courses/3/lessons/42/practice/quiz/?quiz=5';
  for (const getUrl of [allowed, 'https://other.test' + allowed, '/backoffice/workspace/courses/4/']) {
    const form = makeForm('quiz-a', {bound: true, getUrl});
    const current = harness({forms: [form]});
    assert.equal(current.historyCalls.length, getUrl === allowed ? 1 : 0);
    assert.equal(current.read('quiz-a').values.title, 'Saqlangan test');
  }
  const form = makeForm('quiz-a', {bound: true, getUrl: allowed});
  const current = harness({forms: [form], failHistory: true});
  assert.equal(current.read('quiz-a').values.title, 'Saqlangan test');
});

test('rich editor content is captured and synchronized before native preview without acknowledgement', () => {
  const form = makeForm('assignment-a');
  const description = field('description', '<p>Original</p>', 'textarea', {
    matches: selector => selector === 'textarea.django_ckeditor_5',
  });
  form.fields = form.fields.filter(item => item.name !== 'description');
  form.fields.push(description);
  const editorEvents = {};
  let richText = '<p>Original</p>';
  const editor = {getData: () => richText, model: {document: {on(name, callback) { editorEvents[name] = callback; }}}};
  const current = harness({forms: [form], editors: {description: editor}});
  richText = '<p><strong>Yangi shart</strong></p>';
  editorEvents['change:data']();
  assert.equal(current.read('assignment-a').values.description, richText);
  current.submit(form, 'preview');
  assert.equal(description.value, richText);
  assert.equal(current.read('assignment-a').lastSubmission, undefined);
});

test('recovery uses the action attribute when action-named buttons shadow the native form property', () => {
  const first = makeForm('quiz-a'), previous = harness({forms: [first]});
  previous.edit(first, 'title', 'Tiklanadigan test');
  const fresh = makeForm('quiz-a');
  fresh.action = {toString: () => '[object RadioNodeList]'};
  const current = harness({forms: [fresh], stored: previous.stored});
  fresh.controls.restore.events.click();
  const posted = current.document.body.children[0];
  assert.equal(posted.action, fresh.getAttribute('action'));
  assert.equal(posted.submitted, 1);
  assert.equal(postedValues(posted).action, 'restore');
});

test('owned returned transfer absorbs delayed editor normalization without offering a false recovery', () => {
  const first = makeForm('quiz-a'), previous = harness({forms: [first]});
  previous.edit(first, 'title', 'Kengaytirilgan test');
  previous.submit(first, 'add_question');
  const transfer = previous.read('quiz-a').lastTransfer.id;
  const bound = makeForm('quiz-a', {title: 'Kengaytirilgan test', bound: true, transfer, questions: 2});
  for (const item of bound.fields.filter(item => /^questions-\d+-text$/.test(item.name)))
    item.matches = selector => selector === 'textarea.django_ckeditor_5';
  const current = harness({forms: [bound], stored: previous.stored});
  assert.equal(bound.controls.recovery.hidden, true);
  for (const name of ['questions-0-text', 'questions-1-text']) {
    const raw = bound.fields.find(item => item.name === name).value;
    current.editorCallbacks[name]({getData: () => `<p>${raw}</p>`, model: {document: {on() {}}}});
    assert.equal(bound.controls.recovery.hidden, true, 'editor startup is not an older draft');
    assert.equal(current.read('quiz-a').values[name], `<p>${raw}</p>`);
  }
  current.window.events.pagehide();
  assert.equal(current.read('quiz-a').lastTransfer.id, transfer);
  assert.equal(current.read('quiz-a').values['questions-TOTAL_FORMS'], '2');
  const departure = event();
  current.window.events.beforeunload(departure);
  assert.equal(departure.defaultPrevented, false);
});

test('delayed editor normalization never absorbs an unrelated older recovery choice', () => {
  const first = makeForm('quiz-a'), previous = harness({forms: [first]});
  previous.edit(first, 'questions-0-text', 'Oldingi savol qoralamasi');
  previous.submit(first, 'preview');
  const bound = makeForm('quiz-a', {bound: true, transfer: 'another-transfer'});
  const question = bound.fields.find(item => item.name === 'questions-0-text');
  question.matches = selector => selector === 'textarea.django_ckeditor_5';
  const current = harness({forms: [bound], stored: previous.stored});
  current.editorCallbacks[question.name]({getData: () => '<p>Rad etilgan savol</p>', model: {document: {on() {}}}});
  assert.equal(current.read('quiz-a').values[question.name], 'Oldingi savol qoralamasi');
  assert.equal(bound.controls.recovery.hidden, false);
});
