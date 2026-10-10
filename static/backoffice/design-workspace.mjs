import {clone, fields, defaults, validate, edit, diff, builtin, inspectDesign, compileStyle, effectiveColor,
  same, resetKeys, setValues, parseRecovery, matchesReceipt, reconcileReceipt, recoveryEnvelope, appendHistoryPage, presetName} from './design-model.mjs';

const app = document.querySelector('#design-workspace');
if (app) start(app);

function start(app) {
  const $ = selector => app.querySelector(selector), $$ = selector => [...app.querySelectorAll(selector)];
  const catalog = JSON.parse($('#design-catalog').textContent), initial = JSON.parse($('#design-state').textContent);
  const storageKey = `azurelms:design:v1:${app.dataset.scope}`;
  let server = initial, working = clone(server.draft.value), base = baseOf(server), pending = null;
  let recovery = null, busy = false, stored = false, mode = 'light', page = 'course', comparison = 'draft';
  let conflict = server.draft.revision > 0 && server.draft.base_version !== server.published.version && !same(server.draft.value,server.published.value);
  let dialogAction = null, previewTimer = null, historyBusy = false;
  const fieldControls = new Map(), invalidInputs = new Map();
  const typeKeys = Object.keys(catalog.validation.typeDefaults);
  const largeType = Object.fromEntries(typeKeys.map(key => [key, ({'text-xs':14,'text-sm':16,'text-md':18,'text-lg':20,'text-xl':24,'text-2xl':30,'text-title':36,'text-display':44})[key]]));
  const colors = ['action','action-hover','on-action','action-soft','action-border','focus','hero'];
  const sectionKeys = {colors, text:['body-font',...typeKeys], shape:['button-radius','card-radius'], spacing:['density']};
  const palette = {
    azure:{light:['#1257e6','#1048bf','#ffffff','#edf3ff','#cfdefc','#1257e6','#edf3ff'],dark:['#9bb8ff','#b2c8ff','#12203c','#233552','#3b527c','#b2c8ff','#1c2b44']},
    forest:{light:['#146c4b','#10563c','#ffffff','#eaf6ef','#c2ddcf','#146c4b','#eaf6ef'],dark:['#93d7b4','#b1e5ca','#142b21','#203c32','#3d6853','#b1e5ca','#203c32']},
    plum:{light:['#7540b3','#60318f','#ffffff','#f4eefb','#ddcdef','#7540b3','#f4eefb'],dark:['#cdb2ef','#dfcaf6','#291a3c','#352443','#654b7e','#dfcaf6','#352443']},
  };
  function baseOf(state) { return {draft_revision:state.draft.revision, base_version:state.draft.base_version}; }
  function feedback(text, kind = '') { $('[data-feedback]').textContent = text; $('[data-feedback]').dataset.kind = kind; }
  function dirty() { return !same(working, server.draft.value); }
  function persist() {
    try { sessionStorage.setItem(storageKey, JSON.stringify(recoveryEnvelope(working,base,pending,recovery))); stored = true; return true; }
    catch { stored = false; feedback('Brauzer nusxani saqlay olmadi. O‘zgarishlar ochiq sahifada qoldi; sahifani yopmang.', 'error'); return false; }
  }
  try {
    recovery = parseRecovery(catalog, sessionStorage.getItem(storageKey));
    if (recovery) { pending = recovery.pending || null; stored = true; if (same(recovery.value, working)) recovery = null; }
  } catch (error) { feedback(error.message, 'error'); }

  function clearInvalid(keys) {
    for (const input of invalidInputs.keys()) if (keys.includes(input.dataset.field)) {
      invalidInputs.delete(input); input.setAttribute('aria-invalid','false'); input.value=working[input.dataset.area][input.dataset.field] ?? '';
    }
  }
  function choose(next, replacedKeys = []) {
    if (recovery) { feedback('Avval brauzerdagi nusxani tiklash yoki o‘chirishni tanlang.'); render(); return; }
    try { working = validate(catalog, next); clearInvalid(replacedKeys); comparison = 'draft'; persist(); render(); }
    catch (error) { feedback(error.message, 'error'); }
  }
  function setField(key, section, raw) {
    try { choose(edit(catalog, working, key, section, raw),[key]); }
    catch (error) { feedback(error.message, 'error'); }
  }
  function node(tag, text, className) { const element = document.createElement(tag); if (text) element.textContent = text; if (className) element.className = className; return element; }
  function option(value, label) { const element = node('option', label); element.value = value; return element; }
  function buildAdvanced() {
    const host = $('[data-advanced]');
    for (const group of catalog.groups.filter(group => group.fields.length)) {
      const section = node('details', '', 'dw-advanced-group'); section.append(node('summary', group.title));
      for (const field of group.fields) for (const area of field.mode ? ['light','dark'] : ['values']) {
        const box = node('div', '', 'dw-advanced-field'), id = `dw-field-${area}-${field.key}`;
        const label = node('label', field.label + (field.mode ? (area === 'light' ? ' · yorug‘' : ' · qorong‘i') : ''));
        label.htmlFor = id; box.append(label);
        let input;
        if (field.kind === 'select') { input = node('select'); for (const item of field.options) input.append(option(item.value, item.label)); }
        else { input = node('input'); input.type = field.kind === 'number' ? 'number' : 'text';
          if (field.kind === 'number') { input.min = field.min; input.max = field.max; input.step = field.step; input.placeholder = 'Odatdagi'; }
          else { input.maxLength = 7; input.pattern = '#[0-9A-Fa-f]{6}'; input.placeholder = '#1257e6'; }
        }
        input.id = id; input.dataset.field = field.key; input.dataset.area = area;
        const updateValue = () => {
          try { working = edit(catalog, working, field.key, area, input.value); input.setAttribute('aria-invalid','false'); invalidInputs.delete(input); comparison = 'draft'; persist(); render(); }
          catch (error) { input.setAttribute('aria-invalid','true'); invalidInputs.set(input,error.message); feedback(error.message, 'error'); render(); }
        };
        input.addEventListener('change', updateValue);
        if (field.kind !== 'select') input.addEventListener('input', updateValue);
        box.append(input);
        let inherited;
        if (field.inherit) { const wrapper = node('label', '', 'dw-inherit'); inherited = node('input'); inherited.type = 'checkbox'; wrapper.append(inherited,document.createTextNode('Bog‘liq rangdan olinsin')); inherited.addEventListener('change', () => setField(field.key, area, inherited.checked ? '' : effectiveColor(catalog,working,area,field.key))); box.append(wrapper); }
        if (field.kind === 'number') box.append(node('small',`${field.min}–${field.max}${field.unit ? ' ' + field.unit : ''}. Bo‘sh bo‘lsa odatdagi qiymat.`));
        if (field.key === 'card-pad') box.append(node('small','Umumiy mazmun panellari va yangi boshqaruvdagi vazifa hamda o‘quvchi kartalariga qo‘llanadi. Ayrim sahifalarning maxsus kartalari o‘z oralig‘ini saqlaydi.'));
        fieldControls.set(`${area}:${field.key}`,{input,inherited,section}); section.append(box);
      }
      host.append(section);
    }
  }
  function syncControls() {
    for (const [key, control] of fieldControls) {
      const [area, name] = key.split(':'), value = working[area][name];
      if (document.activeElement !== control.input && !invalidInputs.has(control.input)) control.input.value = value ?? '';
      if (control.inherited) { control.inherited.checked = value === null; control.input.disabled = value === null; }
    }
    for (const input of $$('[data-simple]')) input.value = working.values[input.dataset.simple];
    for (const input of $$('[data-shape]')) { const value = working.values[input.dataset.shape]; input.value = [...input.options].some(item => item.value === String(value ?? '')) ? String(value ?? '') : 'custom'; }
    $('[data-text-size]').value = typeKeys.every(key => working.values[key] === null) ? 'default' : typeKeys.every(key => working.values[key] === largeType[key]) ? 'large' : 'custom';
    $('[data-brand-color]').value = working[mode].action; $('[data-brand-hex]').textContent = working[mode].action;
    $('[data-color-mode]').textContent = mode === 'light' ? '· yorug‘ ko‘rinish' : '· qorong‘i ko‘rinish';
    for (const button of $$('[data-palette]')) button.setAttribute('aria-pressed', String(['light','dark'].every(area => colors.every((key,i) => working[area][key] === palette[button.dataset.palette][area][i]))));
  }
  function renderPresets() {
    const select = $('[data-preset]');
    select.replaceChildren(option('', 'Moslashtirilgan'));
    const built = node('optgroup'); built.label = 'Tayyor uslublar';
    for (const preset of catalog.presets) built.append(option(`builtin:${preset.id}`,preset.title)); select.append(built);
    if (server.presets.length) { const saved = node('optgroup'); saved.label = 'Saqlangan uslublar'; for (const preset of server.presets) saved.append(option(`saved:${preset.id}`,preset.name)); select.append(saved); }
    const builtMatch=catalog.presets.find(preset=>same(builtin(catalog,preset.id),working)), savedMatch=server.presets.find(preset=>same(preset.value,working));
    select.value = savedMatch ? `saved:${savedMatch.id}` : builtMatch ? `builtin:${builtMatch.id}` : '';
    $('[data-delete-preset]').hidden = !select.value.startsWith('saved:');
  }
  function renderHistory() {
    const host = $('[data-history]'); host.replaceChildren();
    if (!server.history.length) host.append(node('p','Hali nashr qilingan o‘zgarish yo‘q.','dw-help'));
    for (const entry of server.history) {
      const box = node('article','','dw-history-entry'); box.append(node('strong',`Nashr ${entry.version}${entry.version === server.published.version ? ' · amalda' : ''}`));
      if (entry.created_at) { const time = node('time', new Date(entry.created_at).toLocaleString('uz-UZ')); time.dateTime = entry.created_at; box.append(time); }
      box.append(node('p',entry.reason));
      if (entry.version !== server.published.version) { const button = node('button','Shu ko‘rinishga qaytish','ws-link-button'); button.type='button'; button.disabled=Boolean(busy || pending || recovery); button.addEventListener('click', () => confirmAction({title:`Nashr ${entry.version} ga qaytish`,copy:'Oldingi ko‘rinish yangi nashr sifatida qo‘llanadi. Tarix saqlanib qoladi.',reason:true,changes:entry.value ? diff(catalog,server.published.value,entry.value) : [],run:reason => command('rollback',{target_version:entry.version,base_version:server.published.version,reason,confirmed:true})})); box.append(button); }
      host.append(box);
    }
    if (server.history_before != null) {
      const more=node('button',historyBusy?'Nashrlar yuklanmoqda…':'Oldingi nashrlarni ko‘rish','ws-button');
      more.type='button';more.dataset.historyMore='';more.disabled=Boolean(busy || historyBusy);
      more.addEventListener('click',loadOlderHistory);host.append(more);
    }
  }
  function renderValidation() {
    const errors = inspectDesign(catalog,working).errors, host = $('[data-validation-list]'); host.replaceChildren(); $('[data-validation]').hidden = !errors.length && !invalidInputs.size;
    for (const [input,message] of invalidInputs) { const item=node('li'),button=node('button',message);button.type='button';button.addEventListener('click',()=>{ $('.dw-advanced').open=true;input.closest('details').open=true;input.focus();});item.append(button);host.append(item); }
    for (const error of errors) {
      const item = node('li'), button = node('button'); button.type='button';
      button.textContent = error.kind === 'contrast' ? `${error.mode === 'light' ? 'Yorug‘' : 'Qorong‘i'} ko‘rinishda ${catalog.groups.flatMap(group=>group.fields).find(field=>field.key===error.keys[0]).label.toLowerCase()} fondan yetarlicha ajralmayapti. Rangni to‘g‘rilash` : error.message;
      button.addEventListener('click', () => { const control = fieldControls.get(`${error.mode}:${error.keys[0]}`); if (control) { $('.dw-advanced').open=true; control.section.open=true; control.input.focus(); control.input.scrollIntoView({block:'center',behavior:'smooth'}); } });
      item.append(button); host.append(item);
    }
    return errors.length === 0 && !invalidInputs.size;
  }
  function preview() {
    const value = comparison === 'published' ? server.published.value : working;
    const head = $('#design-sample-head').innerHTML, sample = $(`#design-sample-${page}`).innerHTML;
    const csp = `default-src 'none'; style-src ${location.origin} 'unsafe-inline'; img-src 'none'; font-src 'none'; form-action 'none'; base-uri 'none'`;
    $('[data-preview-frame]').srcdoc = `<!doctype html><html lang="uz" data-theme="${mode}"><head><meta http-equiv="Content-Security-Policy" content="${csp}"><title>Dizayn namunasi</title>${head}<style>${compileStyle(catalog,value)}</style>${$('#design-sample-runtime').innerHTML}</head><body data-frontend="v1">${sample}</body></html>`;
  }
  function render() {
    syncControls(); renderPresets(); const safe = renderValidation();
    $('[data-recovery]').hidden = !recovery; $('[data-pending]').hidden = !pending; $('[data-conflict]').hidden = !conflict;
    $('[data-save-status]').textContent = busy ? 'Server javobi kutilmoqda…' : pending ? 'Amal natijasi tekshirilishi kerak' : dirty() ? 'Hali serverga saqlanmagan' : server.draft.base_version !== server.published.version && !same(working,server.published.value) ? 'Qoralama eski nashrga asoslangan' : same(working,server.published.value) ? 'Joriy nashr bilan bir xil' : 'Qoralama serverda saqlangan';
    $('[data-published-label]').textContent = `Amaldagi nashr: ${server.published.version || 'boshlang‘ich ko‘rinish'} · Saqlash saytga tatbiq qilmaydi`;
    $('[data-save]').disabled = busy || Boolean(pending) || Boolean(recovery) || conflict || !safe || (!dirty() && base.base_version === server.published.version);
    $('[data-publish]').disabled = busy || Boolean(pending) || Boolean(recovery) || conflict || !safe || dirty() || !server.draft.revision || server.draft.base_version !== server.published.version || same(working,server.published.value);
    for (const input of $$('.dw-controls input,.dw-controls select,.dw-controls button')) input.disabled = Boolean(busy || recovery) || (input.dataset.field && fieldControls.get(`${input.dataset.area}:${input.dataset.field}`).inherited?.checked);
    for (const selector of ['[data-save-preset]','[data-delete-preset]','[data-rebase]','[data-readback]']) $(selector).disabled = busy || (selector !== '[data-readback]' && (Boolean(pending) || Boolean(recovery) || !safe));
    $('[data-preview-label]').textContent = comparison === 'published' ? 'Joriy nashr' : dirty() ? 'Saqlanmagan o‘zgarish' : 'Qoralama';
    for (const button of $$('[data-compare]')) button.setAttribute('aria-pressed',String(button.dataset.compare===comparison));
    for (const button of $$('[data-mode]')) button.setAttribute('aria-pressed',String(button.dataset.mode===mode));
    renderHistory(); clearTimeout(previewTimer); previewTimer=setTimeout(preview,100);
  }
  function confirmAction(action) {
    dialogAction=action; $('[data-confirm-title]').textContent=action.title; $('[data-confirm-copy]').textContent=action.copy;
    $('[data-reason-fields]').hidden=!action.reason; $('#dw-reason').value=''; $('[data-confirm-check]').checked=false; $('[data-confirm-error]').textContent='';
    const host=$('[data-confirm-changes]'); host.replaceChildren();
    for(const change of (action.changes || []).slice(0,8)) host.append(node('li',`${change.label}${change.section==='values'?'':change.section==='light'?' · yorug‘':' · qorong‘i'}`));
    if((action.changes || []).length>8) host.append(node('li',`Yana ${action.changes.length-8} ta o‘zgarish.`));
    $('[data-confirm-submit]').textContent=action.reason?'Tasdiqlash va qo‘llash':'Davom etish'; $('[data-confirm-dialog]').showModal();
  }
  $('[data-confirm-submit]').addEventListener('click', () => {
    const reason=$('#dw-reason').value.trim();
    if(dialogAction.reason && (reason.length<3 || !$('[data-confirm-check]').checked)) { $('[data-confirm-error]').textContent='Sababni yozing va tasdiq belgisini qo‘ying.'; return; }
    $('[data-confirm-dialog]').close(); const action=dialogAction; dialogAction=null; action.run(reason);
  });
  async function getState(operation,historyBefore) {
    const url=new URL(app.dataset.stateUrl,location.origin); if(operation) url.searchParams.set('operation',operation);
    if(historyBefore != null) url.searchParams.set('history_before',String(historyBefore));
    const response=await fetch(url,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}});
    if(!response.ok) throw Error('Server holatini tekshirib bo‘lmadi. Birozdan keyin qayta tekshiring.');
    return response.json();
  }
  async function loadOlderHistory() {
    if(busy || historyBusy || server.history_before == null) return;
    const source=server, before=server.history_before;
    historyBusy=true;renderHistory();
    try {
      const page=await getState(undefined,before);
      // A command/readback may have replaced current state while this GET was in flight.
      if(server !== source) return;
      server=appendHistoryPage(server,page,before);
      feedback('Oldingi nashrlar qo‘shildi. Ochiq qoralamangiz o‘zgarmadi.');
    } catch(error) { feedback(error.message,'error'); }
    finally { historyBusy=false;renderHistory(); }
  }
  function accept(result, next, intent) {
    const outcome=reconcileReceipt(working,base,intent,result,next);
    server=next;working=outcome.value;base=outcome.base;
    if(['save_draft','publish','rollback'].includes(intent.command)) conflict=outcome.conflict;
    pending=null; persist(); renderPresets();
    const messages={save_draft:'Qoralama serverda saqlandi. Saytning amaldagi ko‘rinishi o‘zgarmadi.',publish:'Ko‘rinish nashr qilindi. Yangi ochilgan sahifalarda qo‘llanadi.',rollback:'Oldingi ko‘rinish yangi nashr sifatida qo‘llandi.',save_preset:'Uslub serverda saqlandi.',delete_preset:'Saqlangan uslub o‘chirildi.'};
    let message=result.changed===false?'O‘zgarish yo‘q. Serverdagi holat tasdiqlandi.':messages[intent.command];
    if(outcome.advanced) message=`Oldingi amal bajarilgani tasdiqlandi, ammo server keyinroq yangilangan. Sizning o‘zgarishlaringiz saqlab qolindi; joriy nashr bilan solishtiring.`;
    else if(intent.command==='rollback') message+=' Ochiq qoralamangiz almashtirilmadi.';
    feedback(message,outcome.advanced?'':'success');
  }
  async function command(name,payload) {
    if(busy || pending || recovery || invalidInputs.size) return;
    const intent={operation:crypto.randomUUID(),command:name,payload:clone(payload),value:clone(working)};
    pending=intent; if(!persist()) { pending=null; render(); return; }
    busy=true; feedback('Amal serverga yuborilmoqda…'); render();
    const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),20000);
    try {
      const response=await fetch(app.dataset.commandUrl,{method:'POST',credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRFToken':$('[name=csrfmiddlewaretoken]').value,Accept:'application/json'},body:JSON.stringify({operation:intent.operation,command:name,payload})});
      const data=await response.json();
      if(!response.ok) {
        if(response.status>=500 || !data.error) throw Error('Server natijasi noma’lum. Natijani tekshiring.');
        pending=null;
        if(response.status===409) { conflict=true; try { server=data.state || await getState(); } catch {} }
        persist(); feedback(data.error.message || 'Amal bajarilmadi.','error');
      } else accept(data.result,data.state,intent);
    } catch(error) { feedback('Javob tasdiqlanmadi. O‘zgarishlar saqlab qolindi. «Natijani tekshirish» orqali davom eting.','error'); }
    finally { clearTimeout(timeout); busy=false; render(); }
  }
  async function readback() {
    if(!pending || busy) return; busy=true; render(); const intent=clone(pending);
    try { const next=await getState(intent.operation), receipt=next.receipt?.result;
      if(matchesReceipt(intent,receipt)) accept(receipt,next,intent);
      else { server=next; $('[data-abandon]').hidden=false; feedback('Bu amal uchun tasdiq topilmadi. Natija noma’lum; serverdagi holat va o‘zgarishlaringizni solishtiring.','error'); }
    } catch(error) { feedback(error.message,'error'); }
    finally { busy=false; render(); }
  }
  $('[data-save]').addEventListener('click',()=>command('save_draft',{value:working,...base}));
  $('[data-publish]').addEventListener('click',()=>confirmAction({title:'Ko‘rinishni nashr qilish',copy:'Saqlangan qoralama platformaning amaldagi ko‘rinishiga aylanadi. Avval namunaning yorug‘, qorong‘i va telefon ko‘rinishini tekshiring.',reason:true,changes:diff(catalog,server.published.value,working),run:reason=>command('publish',{draft_revision:server.draft.revision,base_version:server.published.version,reason,confirmed:true})}));
  $('[data-readback]').addEventListener('click',readback);
  $('[data-abandon]').addEventListener('click',()=>confirmAction({title:'Noma’lum natijadan davom etish',copy:'Oxirgi amal tasdig‘i topilmadi. Uni avtomatik qayta yubormaymiz. O‘zgarishlaringizni serverning hozirgi holati bilan solishtirib davom etasiz.',run:()=>{pending=null;conflict=true;$('[data-abandon]').hidden=true;persist();render();}}));
  $('[data-rebase]').addEventListener('click',()=>confirmAction({title:'Yangi asosda saqlash',copy:'Sizning barcha sozlamalaringiz serverning joriy nashriga asoslangan yangi qoralama bo‘ladi. Bu sayt ko‘rinishini hali o‘zgartirmaydi.',changes:diff(catalog,server.draft.value,working),run:()=>{base={draft_revision:server.draft.revision,base_version:server.published.version};conflict=false;command('save_draft',{value:working,...base});}}));
  $('[data-load-server]').addEventListener('click',()=>confirmAction({title:'Serverdagi qoralamani ochish',copy:'Ochiq sahifadagi o‘zgarishlar o‘rniga serverdagi qoralama olinadi.',run:()=>{working=clone(server.draft.value);clearInvalid(fields(catalog).map(field=>field.key));base=baseOf(server);conflict=false;recovery=null;persist();render();}}));
  $('[data-restore]').addEventListener('click',()=>{working=clone(recovery.value);clearInvalid(fields(catalog).map(field=>field.key));base=clone(recovery.base);conflict=base.draft_revision!==server.draft.revision || base.base_version!==server.published.version;recovery=null;persist();render();feedback('Brauzerdagi nusxa tiklandi. U hali serverga saqlanmagan.');});
  $('[data-discard]').addEventListener('click',()=>{recovery=null;persist();render();});
  for(const input of $$('[data-simple]')) input.addEventListener('change',()=>choose(setValues(catalog,working,{[input.dataset.simple]:input.value}),[input.dataset.simple]));
  for(const input of $$('[data-shape]')) input.addEventListener('change',()=>choose(setValues(catalog,working,{[input.dataset.shape]:input.value===''?null:Number(input.value)}),[input.dataset.shape]));
  $('[data-text-size]').addEventListener('change',event=>choose(setValues(catalog,working,event.target.value==='large'?largeType:Object.fromEntries(typeKeys.map(key=>[key,null]))),typeKeys));
  $('[data-brand-color]').addEventListener('input',event=>setField('action',mode,event.target.value));
  for(const button of $$('[data-palette]')) button.addEventListener('click',()=>{const next=clone(working);for(const area of ['light','dark']) colors.forEach((key,i)=>{next[area][key]=palette[button.dataset.palette][area][i];});choose(next,colors);});
  for(const button of $$('[data-reset]')) button.addEventListener('click',()=>choose(resetKeys(catalog,working,sectionKeys[button.dataset.reset]),sectionKeys[button.dataset.reset]));
  $('[data-reset-all]').addEventListener('click',()=>confirmAction({title:'Asl ko‘rinishga qaytarish',copy:'Barcha ochiq sozlamalar boshlang‘ich qiymatga qaytadi. Serverdagi qoralama va joriy nashr hozircha o‘zgarmaydi.',run:()=>choose(defaults(catalog),fields(catalog).map(field=>field.key))}));
  $('[data-preset]').addEventListener('change',()=>{$('[data-delete-preset]').hidden=!$('[data-preset]').value.startsWith('saved:');});
  $('[data-apply-preset]').addEventListener('click',()=>{const selected=$('[data-preset]').value;if(!selected)return;const [kind,id]=selected.split(':');const value=kind==='builtin'?builtin(catalog,id):server.presets.find(item=>String(item.id)===id)?.value;if(!value)return;confirmAction({title:'Uslubni qo‘llash',copy:'Tanlangan uslub ochiq sozlamalarni almashtiradi. Joriy nashr o‘zgarmaydi; natijani avval namunada ko‘rasiz.',run:()=>choose(value,fields(catalog).map(field=>field.key))});});
  $('[data-save-preset]').addEventListener('click',()=>{try{const name=presetName($('#dw-preset-name').value);if(inspectDesign(catalog,working).errors.length)throw Error('Uslubni saqlashdan oldin ko‘rsatilgan rang yoki matn xatosini to‘g‘rilang.');command('save_preset',{name,value:working});}catch(error){feedback(error.message,'error');}});
  $('[data-delete-preset]').addEventListener('click',()=>{const id=Number($('[data-preset]').value.split(':')[1]);if(!id)return;confirmAction({title:'Saqlangan uslubni o‘chirish',copy:'Bu uslub ro‘yxatdan o‘chadi. Joriy nashr va ochiq sozlamalar saqlanib qoladi.',run:()=>command('delete_preset',{preset_id:id})});});
  for(const button of $$('[data-mode]')) button.addEventListener('click',()=>{mode=button.dataset.mode;render();});
  for(const button of $$('[data-width]')) button.addEventListener('click',()=>{$('[data-frame-stage]').dataset.width=button.dataset.width;for(const item of $$('[data-width]')) item.setAttribute('aria-pressed',String(item===button));});
  for(const button of $$('[data-compare]')) button.addEventListener('click',()=>{comparison=button.dataset.compare;render();});
  $('[data-preview-page]').addEventListener('change',event=>{page=event.target.value;preview();});
  window.addEventListener('beforeunload',event=>{if((dirty() && !stored) || pending || recovery || invalidInputs.size){event.preventDefault();event.returnValue='';}});
  buildAdvanced();renderPresets();render();
}
