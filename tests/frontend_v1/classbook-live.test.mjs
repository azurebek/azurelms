import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source = readFileSync(new URL('../../static/frontend_v1/js/classbook-live.js', import.meta.url), 'utf8');
const module = {exports:{}};
runInNewContext(source, {module, Event:class {}, queueMicrotask:fn => fn()});
const {answerFlow, renderExercise} = module.exports;
const live = () => ({enabled:true, submitted:false, expired:false, status:'open', session_status:'open'});
const deferred = () => {let resolve, reject; const promise = new Promise((a,b) => {resolve=a; reject=b;}); return {promise,resolve,reject};};
function setup() {
  const h = {posts:[], readCount:0, online:true, data:live(), reply:{ok:true, code:'submitted', message:'Accepted'}};
  h.flow = answerFlow({online:() => h.online, changed:s => {h.last=s;},
    read:async () => {h.readCount++; if (h.readError) throw Error('Offline'); return h.data;},
    send:async answer => {h.posts.push(answer); if (h.error) throw Error('Network'); return h.reply;}});
  return h;
}
test('no POST until state read; offline preserves draft without send', async () => {
  const h=setup(); await h.flow.submit('draft'); assert.equal(h.posts.length,0);
  await h.flow.refresh(); h.online=false; await h.flow.submit('draft'); assert.equal(h.posts.length,0);
  assert.equal(h.flow.state.submitted,false);
});
test('pending and accepted duplicate submits are never resent', async () => {
  const h=setup(), pending=deferred(); h.reply=pending.promise;
  await h.flow.refresh(); const first=h.flow.submit('first'); await h.flow.submit('second');
  assert.deepEqual(h.posts,['first']); pending.resolve({ok:true,code:'submitted',message:'Accepted'}); await first;
  await h.flow.submit('third'); assert.deepEqual(h.posts,['first']);
});
test('unknown outcome permits GET only and no false acknowledgement', async () => {
  const h=setup(); await h.flow.refresh(); h.error=true; await h.flow.submit('draft');
  assert.equal(h.flow.state.unknown,true); assert.equal(h.flow.state.submitted,false);
  h.error=false; await h.flow.refresh(); await h.flow.submit('draft'); assert.equal(h.posts.length,1);
  h.data.submitted=true; await h.flow.refresh(); assert.equal(h.flow.state.submitted,true); assert.equal(h.flow.state.unknown,false);
});
test('read failure fails closed and recovery never sends automatically', async () => {
  const h=setup(); await h.flow.refresh(); h.readError=true;
  await assert.rejects(h.flow.refresh()); await h.flow.submit('draft'); assert.equal(h.posts.length,0);
  h.readError=false; await h.flow.refresh(); assert.equal(h.posts.length,0);
});
test('canonical rejection retains editable answer only for invalid input', async () => {
  const h=setup(); await h.flow.refresh(); h.reply={ok:false,code:'invalid_answer',message:'Choose an option'};
  await h.flow.submit(null); assert.equal(h.flow.state.blocked,false); assert.equal(h.flow.state.submitted,false);
  h.reply={ok:false,code:'deadline',message:'Closed'}; await h.flow.submit('draft'); assert.equal(h.flow.state.blocked,true);
});
test('reveal, expired, closed session and flag rollback block writes', async () => {
  for (const patch of [{status:'revealed'}, {status:'closed'}, {expired:true}, {session_status:'closed'}, {enabled:false}]) {
    const h=setup(); Object.assign(h.data,patch); await h.flow.refresh(); await h.flow.submit('draft');
    assert.equal(h.posts.length,0);
  }
});
test('another tab acknowledgement wins over an older failed POST response', async () => {
  const h=setup(), pending=deferred(); h.reply=pending.promise;
  await h.flow.refresh(); const first=h.flow.submit('draft');
  h.data.submitted=true; await h.flow.refresh(); pending.reject(Error('Lost ack')); await first;
  assert.equal(h.flow.state.submitted,true); assert.equal(h.flow.state.unknown,false);
});
test('malformed acknowledgement is unknown, malformed read fails closed', async () => {
  const h=setup(); await h.flow.refresh(); h.reply={}; await h.flow.submit('draft');
  assert.equal(h.flow.state.unknown,true); h.data={}; await assert.rejects(h.flow.refresh());
  assert.equal(h.flow.state.blocked,true);
});

class Element {
  constructor(tag){this.tagName=tag; this.children=[]; this.handlers={}; this.value=''; this.checked=false;}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(){this.children=[];}
  setAttribute(name,value){this[name]=value;}
  addEventListener(name,fn){this.handlers[name]=fn;}
  dispatchEvent(){}
  focus(){this.focused=true;}
  querySelector(){return this.children.find(c=>c.tagName==='button'&&!c.disabled);}
}
const flatten = node => [node,...node.children.flatMap(flatten)];
test('ten kinds collect canonical shapes; markup is text, not HTML', () => {
  const choices=[{id:'opaqueA',text:'<script>unsafe</script>'},{id:'opaqueB',text:'Second'}];
  const cases=[
    ['single_choice',{options:choices},'opaqueA'],['true_false',{options:choices},'opaqueA'],['poll',{options:choices},'opaqueA'],
    ['multiple_choice',{options:choices},['opaqueA']],['short_answer',{},'Merhaba'],['fill_blank',{},'Merhaba'],
    ['ordering',{items:choices},['opaqueA','opaqueB']],['unscramble',{items:choices},['opaqueA','opaqueB']],
    ['matching',{left:[{id:'left',text:'Left'}],right:choices},{left:'opaqueB'}],
    ['categorization',{items:[{id:'left',text:'Left'}],categories:choices},{left:'opaqueB'}],
  ];
  for (const [kind,config,expected] of cases) {
    const root=new Element('div'); const collect=renderExercise({createElement:tag=>new Element(tag)},root,{kind,config});
    for (const el of flatten(root)) {
      if (el.tagName==='input'&&el.value==='opaqueA') el.checked=true;
      if (el.tagName==='textarea') el.value='Merhaba';
      if (el.tagName==='select') el.value='opaqueB';
      assert.equal(el.innerHTML,undefined);
    }
    assert.deepEqual(JSON.parse(JSON.stringify(collect())),expected,kind);
  }
});
test('ordering buttons change order and have named accessible controls', () => {
  const root=new Element('div'); const collect=renderExercise({createElement:tag=>new Element(tag)},root,{kind:'ordering',config:{items:[{id:'a',text:'One'},{id:'b',text:'Two'}]}});
  const down=flatten(root).find(el=>el.tagName==='button'&&el.textContent==='↓');
  assert.match(down['aria-label'],/One/); down.handlers.click();
  assert.deepEqual(JSON.parse(JSON.stringify(collect())),['b','a']);
});
test('live controller never auto-navigates, auto-resends or persists answers', () => {
  assert.doesNotMatch(source,/location\.(assign|replace|reload)|localStorage|sessionStorage|innerHTML/);
  assert.match(source,/beforeunload/); assert.match(source,/X-CSRFToken/);
});
