import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {defaults, fields, builtin, validate, assertSafe, compileStyle, resetKeys, edit,
  inspectDesign, parseRecovery, matchesReceipt, afterReceipt, recoveryEnvelope, reconcileReceipt, appendHistoryPage, draftBase, same} from '../../static/backoffice/design-model.mjs';

const catalog = JSON.parse(readFileSync(new URL('../../core/design_catalog.json', import.meta.url), 'utf8'));
const fresh = () => defaults(catalog);
const operation = '11111111-2222-4333-8444-555555555555';

test('reopening a just-published draft starts new edits from that publication and retains the draft revision', () => {
  const value=edit(catalog,fresh(),'button-radius','values','17');
  const state={published:{version:5,value:structuredClone(value)},draft:{revision:7,base_version:4,value}};
  assert.deepEqual(draftBase(state),{draft_revision:7,base_version:5});
  assert.equal(state.draft.base_version,4);
  // A publication of a different design still requires an explicit conflict decision.
  state.published={version:6,value:edit(catalog,value,'card-radius','values','23')};
  assert.deepEqual(draftBase(state),{draft_revision:7,base_version:4});
  // A newer draft must never retain a revision from the earlier page.
  state.draft={revision:8,base_version:6,value:state.published.value};
  assert.deepEqual(draftBase(state),{draft_revision:8,base_version:6});
});

test('all canonical fields and built-in styles remain valid without filling inherited overrides', () => {
  assert.equal(fields(catalog).length, 87);
  assert.equal(assertSafe(catalog, fresh()).values['button-radius'], null);
  for (const preset of catalog.presets) assert.equal(inspectDesign(catalog,builtin(catalog,preset.id)).errors.length,0,preset.id);
});

test('unsafe CSS, foreign keys and invalid numeric types never reach the preview compiler', () => {
  for (const value of ['url(https://example.com/a)', '#fff;display:none', true, Infinity, NaN]) {
    const candidate=fresh(); candidate.values['button-radius']=value;
    assert.throws(()=>compileStyle(catalog,candidate));
  }
  const extra=fresh();extra.values['foreign-css']='display:none';assert.throws(()=>validate(catalog,extra));
  const palette=fresh();palette.dark.action='red';assert.throws(()=>validate(catalog,palette));
  const unsafe=fresh();unsafe.dark.text=unsafe.dark.surface;
  assert.throws(()=>assertSafe(catalog,unsafe));
  // Recovery keeps a typed but unreadable color edit available for repair.
  assert.equal(validate(catalog,unsafe).dark.text,unsafe.dark.surface);
});

test('preview compiles light/dark screen-only roles and explicit typography aliases', () => {
  const value=edit(catalog,fresh(),'text-md','values','18');
  const css=compileStyle(catalog,value);
  assert.ok(css.startsWith('@media screen{'));
  assert.ok(css.includes(':root[data-theme="dark"]'));
  assert.ok(css.includes('--az-text-md:1.125rem;--dc-text-md:1.125rem;'));
  assert.ok(!css.includes('--dc-button-radius:'));
  assert.ok(!compileStyle(catalog,fresh()).includes('--dc-text-md:'));
});

test('simple section reset preserves custom values elsewhere and both palettes', () => {
  let value=edit(catalog,fresh(),'button-radius','values','17');
  value=edit(catalog,value,'card-radius','values','23');
  value=edit(catalog,value,'body-leading','values','1.8');
  value=edit(catalog,value,'chat-own','dark','#203c32');
  const reset=resetKeys(catalog,value,['button-radius']);
  assert.equal(reset.values['button-radius'],null);
  assert.equal(reset.values['card-radius'],23);
  assert.equal(reset.values['body-leading'],1.8);
  assert.equal(reset.dark['chat-own'],'#203c32');
  assert.equal(value.values['button-radius'],17);
});

test('missing or unrelated operation receipt cannot establish success', () => {
  const pending={operation,command:'save_draft',value:fresh()};
  assert.equal(matchesReceipt(pending,null),false);
  assert.equal(matchesReceipt(pending,{operation:'22222222-2222-4333-8444-555555555555',command:'save_draft'}),false);
  assert.equal(matchesReceipt(pending,{operation,command:'publish'}),false);
  assert.equal(matchesReceipt(pending,{operation,command:'save_draft',changed:true}),true);
});

test('receipt readback adopts canonical state only when no newer edits exist', () => {
  const submitted=fresh(), canonical=edit(catalog,submitted,'button-radius','values','12');
  const newer=edit(catalog,submitted,'card-radius','values','23');
  assert.ok(same(afterReceipt(submitted,submitted,canonical),canonical));
  assert.ok(same(afterReceipt(newer,submitted,canonical),newer));
  assert.notEqual(afterReceipt(newer,submitted,canonical),newer);
});

test('recovery retains the original revision and pending intent; malformed entries are rejected', () => {
  const value=edit(catalog,fresh(),'button-radius','values','17');
  const entry={version:1,value,base:{draft_revision:3,base_version:2},pending:{operation,command:'save_draft',value,payload:{value,draft_revision:3,base_version:2}}};
  const restored=parseRecovery(catalog,JSON.stringify(entry));
  assert.equal(restored.base.base_version,2);
  assert.equal(restored.value.values['button-radius'],17);
  assert.equal(restored.pending.operation,operation);
  assert.equal(restored.pending.payload.draft_revision,3);
  assert.throws(()=>parseRecovery(catalog,JSON.stringify({...entry,base:{draft_revision:'3',base_version:2}})));
  assert.throws(()=>parseRecovery(catalog,JSON.stringify({...entry,pending:{...entry.pending,command:'unknown'}})));
});

test('readback after reload cannot overwrite unresolved newer browser edits', () => {
  const submitted=edit(catalog,fresh(),'button-radius','values','12');
  const newer=edit(catalog,submitted,'card-radius','values','23');
  const originalBase={draft_revision:3,base_version:2};
  const pending={operation,command:'save_draft',value:submitted};
  const recovery=parseRecovery(catalog,JSON.stringify(recoveryEnvelope(newer,originalBase,pending)));
  // Reload renders canonical submitted data while the newer local copy awaits a decision.
  const canonical=submitted, canonicalBase={draft_revision:4,base_version:2};
  assert.equal(matchesReceipt(pending,{operation,command:'save_draft'}),true);
  const afterReadback=recoveryEnvelope(canonical,canonicalBase,null,recovery);
  const secondReload=parseRecovery(catalog,JSON.stringify(afterReadback));
  assert.ok(same(secondReload.value,newer));
  assert.deepEqual(secondReload.base,originalBase);
  assert.equal(secondReload.pending,null);
  // Only an explicit discard replaces the preserved local copy.
  assert.ok(same(recoveryEnvelope(canonical,canonicalBase,null,null).value,canonical));
});

test('delayed publish or draft receipt cannot replace local design with newer server design', () => {
  const original=edit(catalog,fresh(),'button-radius','values','12');
  const newerServer=edit(catalog,fresh(),'card-radius','values','23');
  const base={draft_revision:1,base_version:0};
  const state={published:{version:2,value:newerServer},draft:{revision:2,base_version:2,value:newerServer}};
  for (const command of ['publish','save_draft']) {
    const intent={operation,command,value:original,payload:{draft_revision:1}};
    const receipt={operation,command,version:1,draft_revision:1};
    const outcome=reconcileReceipt(original,base,intent,receipt,state);
    assert.ok(same(outcome.value,original));assert.deepEqual(outcome.base,base);
    assert.equal(outcome.advanced,true);assert.equal(outcome.conflict,true);
  }
});

test('rollback confirms publication while preserving a private draft and unsaved edits', () => {
  const draft=edit(catalog,fresh(),'button-radius','values','12');
  const privateEdit=edit(catalog,draft,'card-radius','values','23');
  const intent={operation,command:'rollback',value:privateEdit,payload:{base_version:1,target_version:0}};
  const state={published:{version:2,value:fresh()},draft:{revision:1,base_version:1,value:draft}};
  const base={draft_revision:1,base_version:1};
  const outcome=reconcileReceipt(privateEdit,base,intent,{operation,command:'rollback',version:2},state);
  assert.ok(same(outcome.value,privateEdit));assert.deepEqual(outcome.base,base);
  assert.equal(outcome.advanced,false);assert.equal(outcome.conflict,true);
});

test('matching save receipt can normalize its own value but never a later local edit', () => {
  const sent=fresh(); sent.light.action='#1257E6';
  const canonical=fresh(), newer=edit(catalog,sent,'button-radius','values','17');
  const intent={operation,command:'save_draft',value:sent,payload:{draft_revision:1}};
  const receipt={operation,command:'save_draft',version:1,draft_revision:2};
  const state={published:{version:1,value:fresh()},draft:{revision:2,base_version:1,value:canonical}};
  const base={draft_revision:1,base_version:1};
  assert.ok(same(reconcileReceipt(sent,base,intent,receipt,state).value,canonical));
  assert.ok(same(reconcileReceipt(newer,base,intent,receipt,state).value,newer));
});

test('server JSON key order and normalized hex case cannot create false custom or dirty state', () => {
  const original=fresh();
  const reordered=Object.fromEntries(Object.entries(original).reverse().map(([key,value])=>[key,
    value && typeof value==='object' ? Object.fromEntries(Object.entries(value).reverse()) : value]));
  reordered.light.action=reordered.light.action.toUpperCase();
  assert.equal(same(original,reordered),true);
  reordered.values['button-radius']=17;
  assert.equal(same(original,reordered),false);
});

test('older history pages deduplicate versions without adopting fresh draft, publication or receipt', () => {
  const original={published:{version:23,value:fresh()},draft:{revision:4,base_version:23,value:fresh()},receipt:{operation:'original'},
    history:[{version:23,value:fresh()},{version:22,value:fresh()}],history_before:22};
  const page={published:{version:99,value:fresh()},draft:{revision:99,base_version:99,value:fresh()},receipt:{operation:'unrelated'},
    history:[{version:22,value:{foreign:true}},{version:21,value:fresh()},{version:21,value:{foreign:true}},{version:20,value:fresh()}],history_before:20};
  const result=appendHistoryPage(original,page,22);
  assert.deepEqual(result.history.map(entry=>entry.version),[23,22,21,20]);
  assert.equal(result.history_before,20);
  assert.equal(result.published,original.published);assert.equal(result.draft,original.draft);assert.equal(result.receipt,original.receipt);
  assert.equal(result.history[1],original.history[1]);assert.equal(result.history[2],page.history[1]);
  assert.deepEqual(original.history.map(entry=>entry.version),[23,22]);
});

test('history paging ignores a stale cursor and stops when no older publications remain', () => {
  const state={history:[{version:2,value:fresh()}],history_before:2};
  assert.equal(appendHistoryPage(state,{history:[{version:0}],history_before:null},5),state);
  const last=appendHistoryPage(state,{history:[{version:1,value:fresh()},{version:0,value:fresh()}],history_before:null},2);
  assert.equal(last.history_before,null);assert.deepEqual(last.history.map(entry=>entry.version),[2,1,0]);
  assert.throws(()=>appendHistoryPage(state,{history:[],history_before:2},2));
});
