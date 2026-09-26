import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {makeRow, dirty, blocked, receive, rebase, packDraft, acknowledgedKey, clockLabel, prepareListening} from '../../static/frontend_v1/js/exam-attempt-state.mjs';
const saved = {choice_id: '1', option_ids: [], answer_text: '', flagged: false, audio_url: '', version: 1};
test('editing is draft only and blocks finishing', () => {
  const row = makeRow(saved); row.draft.choice_id = '2';
  assert.equal(row.base.choice_id, '1'); assert.ok(dirty(row)); assert.ok(blocked({q: row}, null, false, false));
});
test('remote change preserves dirty draft until explicit rebase, which does not save', () => {
  const row = makeRow(saved); row.draft.choice_id = '2';
  receive(row, {...saved, choice_id: '3', version: 2});
  assert.ok(row.stale); assert.equal(row.draft.choice_id, '2'); assert.equal(row.base.version, 1);
  rebase(row); assert.equal(row.base.version, 2); assert.equal(row.draft.choice_id, '2'); assert.ok(dirty(row)); assert.equal(row.stale, false);
});
test('clean remote update replaces controls and acknowledgement clears own draft', () => {
  const row = makeRow(saved); receive(row, {...saved, choice_id: '2', version: 2});
  assert.equal(row.draft.choice_id, '2'); assert.equal(dirty(row), false);
  row.draft.choice_id = '3'; receive(row, {...saved, choice_id: '3', version: 3}, true);
  assert.equal(dirty(row), false);
});
test('unknown busy closed and stale independently block submit', () => {
  const rows = {q: makeRow(saved)};
  assert.equal(blocked(rows, null, false, false), false);
  assert.ok(blocked(rows, {}, false, false)); assert.ok(blocked(rows, null, true, false)); assert.ok(blocked(rows, null, false, true));
  rows.q.stale = true; assert.ok(blocked(rows, null, false, false));
});
test('reload restores text draft, detects remote changes and warns lost audio', () => {
  const row = makeRow({...saved, version: 3}, {base: saved, draft: {...saved, answer_text: 'taslak'}, audioLost: true});
  assert.equal(row.draft.answer_text, 'taslak'); assert.ok(row.stale); assert.ok(row.audioLost); assert.ok(dirty(row));
});
test('receipt cannot acknowledge another operation, newer remote answer, or retake', () => {
  const op = {operation_id: 'id', key: 'q', version: 1};
  const receipt = {id: 'id', command: 'save', attempt_id: 1};
  const state = {attempt_id: 1, answers: {q: {...saved, version: 2}}};
  assert.equal(acknowledgedKey(op, receipt, state), 'q');
  assert.equal(acknowledgedKey(op, {...receipt, command: 'cancelled'}, state), null);
  assert.equal(acknowledgedKey(op, {...receipt, id: 'other'}, state), null);
  assert.equal(acknowledgedKey(op, receipt, {...state, attempt_id: 2}), null);
  state.answers.q.version = 3; assert.equal(acknowledgedKey(op, receipt, state), null);
});
test('timer formats server snapshot only, including zero and unlimited', () => {
  assert.equal(clockLabel(61), 'Serverda qolgan: 1:01'); assert.equal(clockLabel(0), 'Serverda qolgan: 0:00');
  assert.equal(clockLabel(null), 'Vaqt cheklanmagan');
});
test('persisted draft is a field allowlist, never credentials or audio bytes', () => {
  const row = makeRow(saved);
  row.base.password = 'do-not-store'; row.draft.csrf = 'do-not-store';
  row.file = {bytes: 'do-not-store'}; row.recording = true;
  const packed = packDraft(row);
  assert.equal(JSON.stringify(packed).includes('do-not-store'), false);
  assert.deepEqual(Object.keys(packed).sort(), ['audioLost', 'base', 'draft']);
  assert.equal(packed.audioLost, true); assert.equal(packed.base.version, 1);
});
test('native logout clears exam drafts and operation IDs but not unrelated storage', () => {
  const source = readFileSync(new URL('../../static/frontend_v1/js/shell.js', import.meta.url), 'utf8');
  const store = new Map([['azurelms:v1:exam:scope:operation','id'],['azurelms:v1:exam:scope:1:drafts','text'],['unrelated','keep']]);
  let logout;
  const form = {addEventListener(name, fn) {if(name === 'submit') logout = fn;}};
  const storage = {get length(){return store.size;}, key(i){return [...store.keys()][i];}, removeItem(key){store.delete(key);}};
  runInNewContext(source, {sessionStorage:storage, document:{querySelector(){return null;},addEventListener(){},querySelectorAll(){return [form];}}});
  logout(); assert.deepEqual([...store.keys()], ['unrelated']);
});

class AudioDouble extends EventTarget {
  plays = 0; loads = 0;
  pause() {}
  play() { this.plays++; }
  load() { this.loads++; }
  removeAttribute(name) { delete this[name]; }
}
test('listening readiness never plays and resolves only after canplay', async () => {
  const player = new AudioDouble(), controller = new AbortController();
  let ready = false;
  const promise = prepareListening(player, '/a.wav', controller.signal).then(() => {ready = true;});
  await Promise.resolve(); assert.equal(ready, false); assert.equal(player.plays, 0);
  player.dispatchEvent(new Event('canplay')); await promise;
  assert.equal(ready, true); assert.equal(player.plays, 0);
  controller.abort(); assert.equal(player.src, '/a.wav'); // listeners cleaned up
});
test('failed or cancelled listening preload cannot reach the mutation step', async () => {
  for (const failure of ['error', 'abort']) {
    const player = new AudioDouble(), controller = new AbortController();
    let mutations = 0;
    const promise = prepareListening(player, '/a.wav', controller.signal).then(() => {mutations++;});
    const rejected = assert.rejects(promise, /media-/);
    if (failure === 'error') player.dispatchEvent(new Event('error')); else controller.abort();
    await rejected; player.dispatchEvent(new Event('canplay'));
    assert.equal(mutations, 0); assert.equal(player.plays, 0);
    if (failure === 'abort') assert.equal(player.src, undefined);
  }
});
test('an already cancelled preload does not attach or start a source', async () => {
  const player = new AudioDouble(), controller = new AbortController(); controller.abort();
  await assert.rejects(prepareListening(player, '/a.wav', controller.signal), /media-cancelled/);
  assert.equal(player.src, undefined); assert.equal(player.plays, 0);
});
