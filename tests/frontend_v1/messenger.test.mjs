import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import * as helpers from '../../static/frontend_v1/js/messenger-state.mjs';
import {draftKey, parseDraft, canSend, confirms, mergeMessages, composeShortcut} from '../../static/frontend_v1/js/messenger-state.mjs';

test('draft identity is session and room scoped', () => {
  assert.notEqual(draftKey('one', 1), draftKey('one', 2));
  assert.notEqual(draftKey('one', 1), draftKey('two', 1));
});
test('unknown delivery marker and text survive reload', () => {
  const draft = {text: 'Keep this', pending: {id: 'abc', kind: 'text'}, edits: {}};
  assert.deepEqual(parseDraft(JSON.stringify(draft)), draft);
  assert.equal(parseDraft('broken').text, '');
});
test('send requires connection, loaded history and explicit unblocked intent', () => {
  const ready = {connected: true, loaded: true, text: 'Salom'};
  assert.equal(canSend(ready), true);
  for (const update of [{connected: false}, {loaded: false}, {blocked: true}, {pending: {id: 'a'}}, {text: '  '}]) {
    assert.equal(canSend({...ready, ...update}), false);
  }
  assert.equal(canSend({...ready, text: '', file: {name: 'a.pdf'}}), true);
});
test('only exact server echo clears a pending text, never matching text or peer nonce', () => {
  const pending = {id: 'one'}, echo = {client_message_id: 'one', sender_id: 1, room_id: 2, message_id: 3};
  assert.equal(confirms(pending, echo, '1', '2'), true);
  for (const update of [{client_message_id: 'two'}, {sender_id: 9}, {room_id: 8}, {message_id: null}]) {
    assert.equal(confirms(pending, {...echo, ...update}, 1, 2), false);
  }
});
test('snapshot and concurrent socket events deduplicate by server ID, updates replace', () => {
  const data = mergeMessages([{id: 2, text: 'Old'}, {id: 1}], [{message_id: 2, text: 'New'}, {id: 3}]);
  assert.equal(data.length, 3); assert.equal(data[1].text, 'New');
  assert.equal(mergeMessages(data, [{id: -1}, {id: 'bad'}]).length, 3);
});
test('Enter is newline and composition never submits', () => {
  assert.equal(composeShortcut({key: 'Enter'}), false);
  assert.equal(composeShortcut({key: 'Enter', ctrlKey: true, isComposing: true}), false);
  assert.equal(composeShortcut({key: 'Enter', ctrlKey: true}), true);
  assert.equal(composeShortcut({key: 'Enter', metaKey: true}), true);
});

const controller = readFileSync(new URL('../../static/frontend_v1/js/messenger.mjs', import.meta.url), 'utf8')
  .replace('await import(root.dataset.stateUrl)', 'helpers');
async function harness({draft, storageDenied = false} = {}) {
  class Element {
    constructor() { this.events = {}; this.dataset = {}; this.style = {setProperty() {}}; this.value = ''; this.files = []; this.children = []; this.hidden = false; this.scrollHeight = 600; this.clientHeight = 300; this.scrollTop = 300; }
    addEventListener(name, fn) { this.events[name] = fn; }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren(...nodes) { this.children = nodes; }
    querySelector(selector) { return this.selectors?.[selector] || new Element(); }
    querySelectorAll() { return []; }
    closest() { return this.parent || new Element(); }
    focus() { this.focused = true; }
    showModal() { this.open = true; }
    close() { this.open = false; this.events.close?.(); }
  }
  const nodes = new Map(), q = selector => { if (!nodes.has(selector)) nodes.set(selector, new Element()); return nodes.get(selector); };
  q('[data-chat-root]').dataset = {roomId:'2', userId:'1', scope:'session', historyUrl:'/history/', uploadUrl:'/upload/', editUrl:'/message/0/edit/', deleteUrl:'/message/0/delete/'};
  q('[data-composer]').selectors = {'[type=submit]':q('send'), '[name=csrfmiddlewaretoken]':{value:'csrf'}};
  for (const kind of ['edit', 'delete']) {
    q(`[data-${kind}-form]`).parent = q(`[data-${kind}-dialog]`);
    q(`[data-${kind}-form]`).selectors = {'[type=submit]':q(`${kind}-submit`)};
  }
  const store = new Map([[helpers.prefix + 'other-session:2', 'private']]);
  const key = helpers.draftKey('session', '2'); if (draft) store.set(key, JSON.stringify(draft));
  const sessionStorage = {get length(){return store.size;}, key:i=>[...store.keys()][i], getItem:k=>store.get(k)??null, removeItem:k=>store.delete(k), setItem:(k,v)=>{if(storageDenied)throw Error('denied');store.set(k,v);}};
  const sockets = [], timers = new Map(), requests = [];
  class Socket extends Element {
    static OPEN=1; static CONNECTING=0;
    constructor() { super(); this.readyState=0; this.sent=[]; sockets.push(this); }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() { this.readyState=3; this.events.close?.({code:1006}); }
  }
  let fetchImpl = async () => ({ok:true,status:200,json:async()=>({status:'success',messages:[],has_more:false})});
  const events = {}, document = {querySelector:q,querySelectorAll:()=>[],createElement:()=>new Element(),documentElement:new Element()};
  const window = {innerHeight:568, addEventListener:(name,fn)=>events[name]=fn};
  await runInNewContext(`(async()=>{${controller}})()`, {document,window,sessionStorage,helpers,WebSocket:Socket,location:{hash:'',protocol:'http:',host:'local',origin:'http://local'},crypto:{randomUUID:()=> 'nonce'},URL,AbortSignal,
    fetch:async(url,options)=>{requests.push({url,options});return fetchImpl(url,options);},setTimeout:fn=>{const id=timers.size+1;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id)});
  const flush = async () => { for (let i=0;i<8;i++) await Promise.resolve(); };
  await flush();
  const open = async () => { const s=sockets.at(-1);s.readyState=1;s.events.open();await flush();return s; };
  const input = text => { q('#chat-message').value=text; q('#chat-message').events.input(); };
  const submit = () => q('[data-composer]').events.submit({preventDefault(){}});
  const echo = data => sockets.at(-1).events.message({data:JSON.stringify(data)});
  return {q,store,key,sockets,timers,requests,events,open,input,submit,echo,flush,setFetch:fn=>fetchImpl=fn};
}
test('real controller has no startup writes and clears foreign-session storage', async () => {
  const h=await harness(); await h.open();
  assert.equal(h.requests.every(r=>!r.options.method),true);
  assert.equal(h.store.has(helpers.prefix+'other-session:2'),false);
  assert.equal(h.sockets[0].sent.length,0);
});
test('real controller blocks double-send and reconnect never resends unknown text', async () => {
  const h=await harness(); const socket=await h.open();h.input('Pending draft');await h.submit();await h.submit();
  assert.equal(socket.sent.length,1);assert.equal(h.q('send').disabled,true);
  socket.close(); for(const fn of [...h.timers.values()]) fn();
  await h.open();assert.equal(h.sockets.at(-1).sent.length,0);
  assert.equal(h.q('#chat-message').value,'Pending draft');
  assert.equal(JSON.parse(h.store.get(h.key)).pending.id,'nonce');
});
test('real controller clears only the exact echo and keeps server events as text', async () => {
  const h=await harness();await h.open();h.input('<script>hello</script>');await h.submit();
  h.echo({message_id:1,room_id:2,sender_id:9,client_message_id:'nonce',message:'Peer'});
  assert.equal(h.q('#chat-message').value,'<script>hello</script>');
  h.echo({message_id:2,room_id:2,sender_id:1,client_message_id:'nonce',message:'<script>hello</script>'});
  assert.equal(h.q('#chat-message').value,'');assert.equal(JSON.parse(h.store.get(h.key)).pending,null);
});
test('real controller restores pending marker without sending and warns on failed storage exit', async () => {
  const h=await harness({draft:{text:'Retained',pending:{id:'old'},edits:{}},storageDenied:true});await h.open();
  assert.equal(h.q('#chat-message').value,'Retained');assert.equal(h.q('send').disabled,true);assert.equal(h.sockets[0].sent.length,0);
  const e={preventDefault(){this.prevented=true;}};h.events.beforeunload(e);assert.equal(e.prevented,true);
});
test('revoked access disables compose and never schedules a reconnect', async () => {
  const h=await harness();await h.open();h.input('Keep');
  h.echo({type:'access_revoked',message:'Expired'});
  assert.equal(h.q('#chat-message').disabled,true);assert.equal(h.q('#chat-message').value,'Keep');assert.equal(h.timers.size,0);
});
