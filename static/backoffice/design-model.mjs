// Presentation projection of core/design_catalog.json. The server validates every write.
export const clone = value => JSON.parse(JSON.stringify(value));
const record = value => value && typeof value === 'object' && !Array.isArray(value);
export const fields = catalog => catalog.groups.flatMap(group => group.fields);
export function defaults(catalog) {
  const result = {version: catalog.version, light: {}, dark: {}, values: {}};
  for (const field of fields(catalog)) {
    if (field.mode) for (const mode of ['light', 'dark']) result[mode][field.key] = field.default[mode];
    else result.values[field.key] = field.default;
  }
  return result;
}
export function validate(catalog, value) {
  if (!record(value) || value.version !== catalog.version || Object.keys(value).sort().join() !== 'dark,light,values,version') throw Error('Qoralama formati mos emas.');
  const expected = defaults(catalog);
  for (const section of ['light', 'dark', 'values']) {
    if (!record(value[section]) || Object.keys(value[section]).sort().join() !== Object.keys(expected[section]).sort().join()) throw Error('Qoralama maydonlari mos emas.');
  }
  for (const field of fields(catalog)) for (const section of field.mode ? ['light','dark'] : ['values']) {
    const item = value[section][field.key];
    let ok = false;
    if (field.kind === 'color') ok = (item === null && Boolean(field.inherit)) || (typeof item === 'string' && /^#[0-9a-f]{6}$/i.test(item));
    if (field.kind === 'select') ok = field.options.some(option => option.value === item);
    if (field.kind === 'number') ok = item === null || (typeof item === 'number' && Number.isFinite(item) && item >= field.min && item <= field.max && Math.abs((item-field.min)/field.step-Math.round((item-field.min)/field.step)) < 1e-7);
    if (!ok) throw Error(`${field.label}: ruxsat etilgan qiymatni kiriting.`);
  }
  return clone(value);
}
export function edit(catalog, state, key, section, raw) {
  const field = fields(catalog).find(item => item.key === key);
  if (!field || !(field.mode ? ['light','dark'] : ['values']).includes(section)) throw Error('Noma’lum maydon.');
  const next = clone(state);
  next[section][key] = field.kind === 'number' ? (raw === '' ? null : Number(raw)) : field.inherit && raw === '' ? null : raw;
  return validate(catalog, next);
}
export function diff(catalog, before, after) {
  const changes = [];
  for (const field of fields(catalog)) for (const section of field.mode ? ['light','dark'] : ['values']) {
    if (before[section][field.key] !== after[section][field.key]) changes.push({key:field.key, section, label:field.label, before:before[section][field.key], after:after[section][field.key]});
  }
  return changes;
}
export function compile(catalog, draft, mode) {
  validate(catalog, draft);
  if (!['light','dark'].includes(mode)) throw Error('Noma’lum ko‘rinish.');
  const props = {};
  for (const field of fields(catalog)) {
    let value = draft[field.mode ? mode : 'values'][field.key];
    if (value === null) continue;
    if (field.kind === 'select') value = field.options.find(item => item.value === value).css;
    else if (field.kind === 'number') value = field.key === 'overlay' ? `rgb(0 0 0 / ${value}%)` : field.key.startsWith('text-') ? `${value/16}rem` : `${value}${field.unit}`;
    if (value !== '') {
      props[field.css] = value;
      if (field.kind === 'number' && field.key.startsWith('text-')) props[`--dc-${field.key}`] = value;
    }
  }
  return props;
}
export function builtin(catalog, id) {
  const preset = catalog.presets.find(item => item.id === id);
  if (!preset) throw Error('Variant topilmadi.');
  const value = defaults(catalog);
  Object.assign(value.values, preset.values);
  return validate(catalog, value);
}
export function presetName(name) {
  if (typeof name !== 'string' || !name.trim() || name.trim().length > 60 || /[\u0000-\u001f\u007f]/.test(name)) throw Error('Variant nomi 1–60 belgi bo‘lsin.');
  return name.trim();
}

// WCAG sRGB relative luminance. Decisions use unrounded ratios.
export function contrast(a,b) {
  function luminance(hex) {
    if(typeof hex!=='string'||!/^#[0-9a-f]{6}$/i.test(hex)) throw Error('RGB rang kerak.');
    const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(c=>c<=0.04045?c/12.92:((c+0.055)/1.055)**2.4);
    return rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722;
  }
  const x=luminance(a),y=luminance(b);
  return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05);
}
export function effectiveColor(catalog,draft,mode,key) {
  const seen=new Set();
  while(draft[mode][key]===null) {
    if(seen.has(key)) throw Error('Rang merosi siklik.');
    seen.add(key);key=fields(catalog).find(f=>f.key===key)?.inherit;
  }
  const color=draft[mode][key];
  if(typeof color!=='string') throw Error('Rang manbasi topilmadi.');
  return color;
}
export function inspectDesign(catalog,draft) {
  validate(catalog,draft);
  const labels=Object.fromEntries(fields(catalog).map(f=>[f.key,f.label]));
  const {contrastPairs,typeDefaults,bodyLeadingMin}=catalog.validation;
  const checks=[];
  for(const mode of ['light','dark']) for(const [fg,bg,min] of contrastPairs) {
    const foreground=effectiveColor(catalog,draft,mode,fg),background=effectiveColor(catalog,draft,mode,bg);
    const ratio=contrast(foreground,background);
    checks.push({kind:'contrast',mode,keys:[fg,bg],foreground,background,ratio,min,ok:ratio>=min,
      message:`${mode==='light'?'Yorug‘':'Qorong‘i'} · ${labels[fg]} / ${labels[bg]}: ${Math.floor(ratio*100)/100}:1; kamida ${min}:1.`});
  }
  const keys=Object.keys(typeDefaults),range=key=>draft.values[key]===null?typeDefaults[key]:[draft.values[key],draft.values[key]];
  for(let i=1;i<keys.length;i++) {
    const lower=keys[i-1],upper=keys[i];
    checks.push({kind:'hierarchy',mode:'values',keys:[lower,upper],ok:range(lower)[1]<=range(upper)[0],
      message:`${labels[upper]} (${range(upper).join('–')}) ${labels[lower]} (${range(lower).join('–')})dan kichik bo‘lmasin. Bo‘sh sarlavha ekran eniga qarab o‘sadi.`});
  }
  checks.push({kind:'leading',mode:'values',keys:['body-leading'],ok:(draft.values['body-leading']??1.6)>=bodyLeadingMin,
    message:'Asosiy matn satr oralig‘i kamida 1.5 bo‘lsin (o‘qish uchun loyiha chegarasi).'});
  return {checks,errors:checks.filter(c=>!c.ok)};
}
export function assertSafe(catalog,value) {
  const report=inspectDesign(catalog,value);
  if(report.errors.length) throw Error('Saqlashdan oldin tuzating: '+report.errors[0].message);
  return clone(value);
}

function comparable(value) {
  if (Array.isArray(value)) return value.map(comparable);
  if (record(value)) return Object.fromEntries(Object.keys(value).sort().map(key=>[key,comparable(value[key])]));
  return typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value) ? value.toLowerCase() : value;
}
export const same = (first, second) => JSON.stringify(comparable(first)) === JSON.stringify(comparable(second));
export function resetKeys(catalog, value, keys) {
  const next = clone(value), original = defaults(catalog);
  for (const field of fields(catalog).filter(item => keys.includes(item.key))) {
    for (const section of field.mode ? ['light', 'dark'] : ['values']) next[section][field.key] = original[section][field.key];
  }
  return validate(catalog, next);
}
export function setValues(catalog, value, values) {
  const next = clone(value);
  Object.assign(next.values, values);
  return validate(catalog, next);
}
export function compileStyle(catalog, value) {
  return '@media screen{' + ['light', 'dark'].map(mode => {
    const selector = mode === 'light' ? ':root:not([data-theme="dark"])' : ':root[data-theme="dark"]';
    return selector + '{' + Object.entries(compile(catalog, value, mode)).map(([key, val]) => `${key}:${val};`).join('') + '}';
  }).join('') + '}';
}
export function parseRecovery(catalog, raw) {
  if (!raw) return null;
  if (raw.length > 150000) throw Error('Brauzerdagi nusxa hajmi mos emas.');
  const entry = JSON.parse(raw);
  if (!record(entry) || entry.version !== 1 || !record(entry.base)
      || !Number.isSafeInteger(entry.base.draft_revision) || !Number.isSafeInteger(entry.base.base_version)) throw Error('Brauzerdagi nusxa formati mos emas.');
  entry.value = validate(catalog, entry.value);
  if (entry.pending && (!record(entry.pending) || !/^[0-9a-f-]{36}$/i.test(entry.pending.operation)
      || !['save_draft','publish','rollback','save_preset','delete_preset'].includes(entry.pending.command))) throw Error('Kutilayotgan amal formati mos emas.');
  if (entry.pending) entry.pending.value = validate(catalog, entry.pending.value);
  return entry;
}
// A receipt must match the exact pending command; absence is never success.
export function matchesReceipt(pending, receipt) {
  return Boolean(pending && receipt && pending.operation === receipt.operation && pending.command === receipt.command);
}
// Confirmed save/publish must never replace edits made after the request began.
export function afterReceipt(current, submitted, canonical) {
  return same(current, submitted) ? clone(canonical) : clone(current);
}
// Unresolved recovery belongs to the user until they explicitly restore/discard it.
// Receipt updates may change pending metadata, never that original local value/base.
export function recoveryEnvelope(value, base, pending, recovery = null) {
  return {version:1,value:clone(recovery ? recovery.value : value),base:clone(recovery ? recovery.base : base),pending:pending ? clone(pending) : null};
}
export function reconcileReceipt(current, base, intent, result, state) {
  if (!matchesReceipt(intent,result)) throw Error('Server tasdig‘i kutilayotgan amalga mos kelmadi.');
  const outcome={value:clone(current),base:clone(base),conflict:false,advanced:false};
  if (intent.command === 'rollback') {
    // Rollback changes publication only. The private draft and local edits remain owned by the user.
    outcome.advanced=result.version !== state.published.version;
    outcome.conflict=outcome.advanced || base.base_version !== state.published.version;
    return outcome;
  }
  if (!['save_draft','publish'].includes(intent.command)) return outcome;
  const matchingDraft = intent.command === 'save_draft'
    ? result.draft_revision === state.draft.revision
    : intent.payload.draft_revision === state.draft.revision;
  if (result.version !== state.published.version || !matchingDraft) {
    // A durable receipt proves the old outcome, not that fresh state still contains that value.
    outcome.advanced=true; outcome.conflict=true; return outcome;
  }
  outcome.value=afterReceipt(current,intent.value,intent.command === 'save_draft' ? state.draft.value : state.published.value);
  outcome.base={draft_revision:state.draft.revision,base_version:state.published.version};
  return outcome;
}
export function appendHistoryPage(state, page, before) {
  if (state.history_before !== before) return state;
  if (!Number.isSafeInteger(before) || before < 0 || !Array.isArray(page.history)
      || (page.history_before !== null && (!Number.isSafeInteger(page.history_before) || page.history_before < 0 || page.history_before >= before))) {
    throw Error('Oldingi nashrlarni yuklab bo‘lmadi. Qayta urinib ko‘ring.');
  }
  const byVersion=new Map(state.history.map(entry=>[entry.version,entry]));
  for (const entry of page.history) {
    if (Number.isSafeInteger(entry.version) && entry.version >= 0 && entry.version < before && !byVersion.has(entry.version)) byVersion.set(entry.version,entry);
  }
  // Paging is read-only UI enrichment. Fresh response draft/publication/receipt must not be adopted.
  return {...state,history:[...byVersion.values()].sort((first,second)=>second.version-first.version),history_before:page.history_before};
}
