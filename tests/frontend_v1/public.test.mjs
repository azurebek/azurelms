import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const code = readFileSync(new URL('../../static/frontend_v1/js/public.js', import.meta.url), 'utf8');
function harness(kind='clap') {
  const events={}, nodes={};
  const q=key=>nodes[key]??=( {disabled:true,hidden:true,textContent:'7',setAttribute(k,v){this[k]=v;}} );
  const form={action:'/reaction/',dataset:{publicReaction:kind},querySelector:q,addEventListener:(name,fn)=>events['reaction:'+name]=fn};
  const input={value:''}, comment={addEventListener:(name,fn)=>events['comment:'+name]=fn};
  const requests=[],timers=new Map();
  let implementation=async()=>({ok:true,json:async()=>({ok:true,clap_count:8,like_count:8,liked:true,added:true})});
  runInNewContext(code, {
    document:{querySelectorAll:selector=>selector==='[data-public-reaction]'?[form]:selector==='[data-public-comment]'?[comment]:[input]},
    window:{addEventListener:(name,fn)=>events[name]=fn},FormData:class{},AbortController,
    fetch:async(url,options)=>{requests.push({url,options});return implementation();},
    setTimeout:fn=>{timers.set(1,fn);return 1;},clearTimeout:id=>timers.delete(id)
  });
  return {q,events,requests,timers,input,setFetch:fn=>implementation=fn,submit:()=>events['reaction:submit']({preventDefault(){}})};
}
test('public reactions have no startup writes and use canonical POST response',async()=>{
  const h=harness();assert.equal(h.requests.length,0);await h.submit();
  assert.equal(h.requests[0].options.method,'POST');assert.equal(h.requests[0].options.credentials,'same-origin');
  assert.equal(h.q('[data-reaction-count]').textContent,'8');assert.equal(h.timers.size,0);
});
test('unknown network result blocks repeat and keeps previous count, no retry',async()=>{
  const h=harness();h.setFetch(async()=>{throw Error('offline');});await h.submit();await h.submit();
  assert.equal(h.requests.length,1);assert.equal(h.q('button[type="submit"]').disabled,true);
  assert.equal(h.q('[data-reaction-count]').textContent,'7');assert.equal(h.q('[data-reaction-reload]').hidden,false);
});
test('in-flight double submit is blocked, like state waits for server',async()=>{
  const h=harness('like');let finish;h.setFetch(()=>new Promise(resolve=>finish=resolve));
  const pending=h.submit();await h.submit();assert.equal(h.requests.length,1);
  finish({ok:true,json:async()=>({ok:true,like_count:4,liked:false})});await pending;
  assert.equal(h.q('button[type="submit"]').disabled,false);assert.equal(h.q('button[type="submit"]')['aria-pressed'],'false');
});
test('server failure or invalid payload cannot appear saved',async()=>{
  for(const data of [{ok:false},{ok:true,clap_count:'<script>'}]){
    const h=harness();h.setFetch(async()=>({ok:true,json:async()=>data}));await h.submit();
    assert.equal(h.q('button[type="submit"]').disabled,true);assert.equal(h.q('[data-reaction-count]').textContent,'7');
  }
});
test('unsent native comment warns, submit leaves naturally, Back re-arms protection',()=>{
  const h=harness();h.input.value='Retain draft';const e=()=>({preventDefault(){this.prevented=true;}});
  let event=e();h.events.beforeunload(event);assert.equal(event.prevented,true);
  h.events['comment:submit']();event=e();h.events.beforeunload(event);assert.equal(event.prevented,undefined);
  h.events.pageshow();event=e();h.events.beforeunload(event);assert.equal(event.prevented,true);assert.equal(h.input.value,'Retain draft');
});
