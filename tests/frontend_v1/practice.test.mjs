import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

const source = readFileSync(new URL('../../static/frontend_v1/js/practice.js', import.meta.url), 'utf8');
const prefix = 'azurelms:v1:practice:';
const key = prefix + 'session:1:1:assignment-1';
function harness({draft, revision='new', serverAnswer='', serverStatus='', bound=false, blockedStorage=false, online=true, quiz=false, pendingValues, secondFile=false} = {}) {
  const element = () => ({events:{}, dataset:{}, attrs:{}, hidden:true, value:'', type:'textarea', name:'answer_text',
    addEventListener(n,f){this.events[n]=f;}, setAttribute(n,v){this.attrs[n]=v;}, removeAttribute(n){delete this.attrs[n];}, focus(){this.focused=true;}});
  const field=element(), radio=element(), status=element(), conflict=element(), restore=element(), discard=element(), button=element(), count=element(), details={open:false};
  field.value=bound ? 'bound answer' : serverAnswer;
  if (quiz) {field.type='radio';field.name='answer_1';field.value='1';field.checked=false; radio.type='radio';radio.name='answer_1';radio.value='2';radio.checked=false;}
  const fields=quiz?[field,radio]:[field];
  const file={files:[]};
  const question={dataset:{questionName:'answer_1',savedChoice:pendingValues || ''}};
  const form=element();
  form.dataset={practiceForm:quiz?'quiz-1':'assignment-1',revision,serverAnswer,serverStatus,...(bound?{bound:'true'}:{})};
  form.closest=()=>details;
  form.querySelector=s=>({'[data-draft-status]':status,'[data-draft-conflict]':conflict,'[type="submit"]':button,'[data-answer-count]':quiz?count:null,'[data-draft-restore]':restore,'[data-draft-discard]':discard}[s]);
  form.querySelectorAll=s=>({'[data-draft-field]':fields,'[type="file"]':[file],'[data-question-name]':quiz?[question]:[]}[s]||[]);
  const otherForm={...form,events:{},dataset:{...form.dataset,practiceForm:'assignment-2'},querySelectorAll:s=>s==='[type="file"]'?[{files:[{name:'other.pdf'}]}]:form.querySelectorAll(s)};
  const store=new Map([[prefix+'old-session:1:1:assignment-1','old']]);
  const ownKey=quiz?key.replace('assignment-1','quiz-1'):key;
  if (draft) store.set(ownKey,JSON.stringify(draft));
  const sessionStorage={get length(){return store.size;},key:i=>[...store.keys()][i],getItem:k=>store.get(k)||null,removeItem:k=>store.delete(k),setItem:(k,v)=>{if(blockedStorage)throw Error('denied');store.set(k,v);}};
  const root={dataset:{practiceScope:'session',practiceLesson:'1:1'},querySelectorAll:()=>secondFile?[form,otherForm]:[form]};
  const events={},location={reload(){location.reloaded=true;}};
  runInNewContext(source,{document:{querySelector:s=>s==='[data-practice-scope]'?root:null},window:{sessionStorage,navigator:{onLine:online},location,confirm:()=>false,addEventListener:(n,f)=>events[n]=f}});
  const fire=fn=>{const e={prevented:false,preventDefault(){this.prevented=true;}};fn(e);return e;};
  return {form,field,radio,file,status,conflict,restore,discard,button,count,details,store,ownKey,events,location,fire};
}
test('draft serialization only includes marked answer fields, not files/CSRF/password',()=>{
  const h=harness();h.field.value='my answer';h.file.files=[{name:'private.pdf',bytes:'secret'}];h.form.events.input();
  const d=JSON.parse(h.store.get(h.ownKey));assert.deepEqual(d,{revision:'new',values:{answer_text:'my answer'},pending:false,hadFile:true});
  assert.equal(h.store.has(prefix+'old-session:1:1:assignment-1'),false);
});
test('same-session draft restores without submitting',()=>{
  const h=harness({draft:{revision:'new',values:{answer_text:'draft'},pending:false}});
  assert.equal(h.field.value,'draft');assert.match(h.status.textContent,/tiklandi/);assert.equal(h.details.open,true);
});
test('server validation wins over storage and keeps bound text',()=>{
  const h=harness({bound:true,draft:{revision:'new',values:{answer_text:'old'},pending:true}});
  assert.equal(h.field.value,'bound answer');assert.equal(JSON.parse(h.store.get(h.ownKey)).pending,false);
});
test('changed revision blocks until explicit restore; no silent overwrite',()=>{
  const h=harness({revision:'newer',serverAnswer:'server',draft:{revision:'old',values:{answer_text:'draft'},pending:false}});
  assert.equal(h.field.value,'server');assert.equal(h.button.disabled,true);assert.equal(h.conflict.hidden,false);
  assert.equal(h.field.disabled,true);assert.equal(h.file.disabled,true);
  assert.equal(h.fire(h.form.events.submit).prevented,true);h.restore.events.click();assert.equal(h.field.value,'draft');assert.equal(h.button.disabled,false);
  assert.equal(h.field.disabled,false);assert.equal(h.file.disabled,false);
});
test('unknown prior send is not automatically retried',()=>{
  const h=harness({draft:{revision:'new',values:{answer_text:'draft'},pending:true}});
  assert.equal(h.button.disabled,true);h.discard.events.click();assert.equal(h.store.has(h.ownKey),false);assert.equal(h.button.disabled,false);
});
test('new persisted matching answer clears only its pending draft',()=>{
  const h=harness({revision:'saved',serverAnswer:'sent',draft:{revision:'new',values:{answer_text:'sent'},pending:true}});
  assert.equal(h.store.has(h.ownKey),false);assert.match(h.status.textContent,/saqlangan natijaga mos/);
});

test('unchanged pending text no-op reconciles without requiring a timestamp change',()=>{
  const h=harness({revision:'saved',serverStatus:'pending',serverAnswer:'sent',draft:{revision:'saved',values:{answer_text:'sent'},pending:true,hadFile:false}});
  assert.equal(h.store.has(h.ownKey),false);assert.match(h.status.textContent,/saqlangan natijaga mos/);
});

test('same revision cannot acknowledge a file replacement or reviewed work',()=>{
  for (const [serverStatus,hadFile] of [['pending',true],['approved',false]]) {
    const h=harness({revision:'saved',serverStatus,serverAnswer:'sent',draft:{revision:'saved',values:{answer_text:'sent'},pending:true,hadFile}});
    assert.equal(h.button.disabled,true);assert.equal(h.store.has(h.ownKey),true);
  }
});

test('another form file requires confirmation before navigating away',()=>{
  const h=harness({secondFile:true});assert.equal(h.fire(h.form.events.submit).prevented,true);
  assert.equal(h.form.attrs['aria-busy'],undefined);
});
test('quiz choices restore/count without any client grading',()=>{
  const h=harness({quiz:true,draft:{revision:'new',values:{answer_1:'2'},pending:false}});
  assert.equal(h.radio.checked,true);assert.equal(h.field.checked,false);assert.equal(h.count.textContent,'1 / 1 javob tanlangan');
});
test('offline keeps draft and never submits or claims success',()=>{
  const h=harness({online:false});h.field.value='offline';assert.equal(h.fire(h.form.events.submit).prevented,true);assert.match(h.status.textContent,/yuborilmadi/);
});
test('native send is guarded against duplicate and leaves pending until server confirms',()=>{
  const h=harness();h.field.value='answer';assert.equal(h.fire(h.form.events.submit).prevented,false);assert.equal(h.fire(h.form.events.submit).prevented,true);
  assert.equal(JSON.parse(h.store.get(h.ownKey)).pending,true);assert.equal(h.form.attrs['aria-busy'],'true');assert.equal(h.fire(h.events.beforeunload).prevented,false);
});
test('storage denied retains values and warns on dirty exit',()=>{
  const h=harness({blockedStorage:true});h.field.value='keep';h.form.events.input();assert.match(h.status.textContent,/saqlab bo‘lmadi/);assert.equal(h.field.value,'keep');assert.equal(h.fire(h.events.beforeunload).prevented,true);
});
test('Back cache forces auth/result recheck',()=>{
  const h=harness();h.events.pageshow({persisted:true});assert.equal(h.location.reloaded,true);
});
test('page without practice has no side effects',()=>{
  runInNewContext(source,{document:{querySelector:()=>null}});
});
