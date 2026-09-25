/* Native forms own writes. Draft inputs are not persisted grades or outcomes. */
(() => {
  'use strict';
  const root = document.querySelector('[data-practice-scope]');
  if (!root) return;
  const prefix = 'azurelms:v1:practice:';
  const scope = prefix + root.dataset.practiceScope + ':';
  const states = [];
  let submitting = false;
  const same = (a, b) => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
  const storage = (operation) => { try { return operation(window.sessionStorage); } catch { return null; } };
  storage(store => {
    for (let i = store.length - 1; i >= 0; i--) {
      const key = store.key(i);
      if (key.startsWith(prefix) && !key.startsWith(scope)) store.removeItem(key);
    }
  });
  root.querySelectorAll('[data-practice-form]').forEach(form => {
    const key = scope + root.dataset.practiceLesson + ':' + form.dataset.practiceForm;
    const fields = [...form.querySelectorAll('[data-draft-field]')];
    const status = form.querySelector('[data-draft-status]');
    const conflict = form.querySelector('[data-draft-conflict]');
    const button = form.querySelector('[type="submit"]');
    const count = form.querySelector('[data-answer-count]');
    const values = () => Object.fromEntries(fields.filter(f => f.type !== 'radio' || f.checked).map(f => [f.name, f.value]));
    const initial = values();
    const files = () => [...form.querySelectorAll('[type="file"]')].some(f => f.files.length);
    const block = value => {
      blocked = value; button.disabled = value; conflict.hidden = !value;
      [...fields, ...form.querySelectorAll('[type="file"]')].forEach(field => { field.disabled = value; });
    };
    const apply = data => fields.forEach(f => { if (f.type === 'radio') f.checked = data[f.name] === f.value; else if (typeof data[f.name] === 'string') f.value = data[f.name]; });
    const saved = form.dataset.practiceForm.startsWith('review-') ? Object.fromEntries(fields.map(f => [f.name, f.dataset.draftSaved])) :
      form.dataset.practiceForm.startsWith('assignment-') ? {answer_text: form.dataset.serverAnswer} :
      Object.fromEntries([...form.querySelectorAll('[data-question-name]')].filter(q => q.dataset.savedChoice).map(q => [q.dataset.questionName, q.dataset.savedChoice]));
    let pending = false, blocked = false;
    let draft = storage(store => JSON.parse(store.getItem(key)));
    if (!draft || typeof draft.values !== 'object' || draft.values === null || Array.isArray(draft.values)) draft = null;
    const updateCount = () => {
      if (count) count.textContent = `${Object.keys(values()).length} / ${form.querySelectorAll('[data-question-name]').length} javob tanlangan`;
    };
    const save = () => {
      const ok = storage(store => {
        store.setItem(key, JSON.stringify({revision: form.dataset.revision, values: values(), pending, hadFile: files()}));
        return true;
      });
      status.textContent = ok ? 'Matn/tanlov shu tabda qoralama. Serverga hali yuborilmagan. Fayl tiklanmaydi.' :
        'Qoralamani brauzerda saqlab bo‘lmadi. Sahifadan chiqishdan oldin javobni nusxalang.';
      updateCount();
    };
    if (form.dataset.bound === 'true') {
      save(); // The authoritative validation response keeps posted text/choices.
    } else if (draft && draft.pending && same(draft.values, saved) && (
      draft.revision !== form.dataset.revision ||
      (draft.hadFile === false && form.dataset.serverStatus === 'pending' && form.dataset.revision !== 'new')
    )) {
      storage(store => store.removeItem(key));
      status.textContent = form.dataset.draftConfirmed === 'true' ?
        'Yuborish serverda tasdiqlandi. Yakuniy qaror va XP saqlangan tekshiruvda.' :
        'Yuborilgan javob serverdagi saqlangan natijaga mos.';
    } else if (draft && (draft.pending || draft.revision !== form.dataset.revision)) {
      block(true);
      const details = form.closest('details');
      if (details) details.open = true;
    } else if (draft) {
      apply(draft.values);
      status.textContent = 'Shu tabdagi qoralama tiklandi; hali yuborilmagan. Faylni qayta tanlang.';
      const details = form.closest('details');
      if (details) details.open = true;
    }
    form.querySelector('[data-draft-restore]').addEventListener('click', () => {
      if (draft) apply(draft.values);
      block(false); pending = false;
      const details = form.closest('details');
      if (details) details.open = true;
      save(); fields[0]?.focus();
    });
    form.querySelector('[data-draft-discard]').addEventListener('click', () => {
      storage(store => store.removeItem(key));
      draft = null; block(false); pending = false;
      status.textContent = 'Eski qoralama olib tashlandi. Serverdagi natija o‘zgarmadi.';
    });
    form.addEventListener('input', () => { if (!blocked && !submitting) save(); });
    form.addEventListener('change', () => { if (!blocked && !submitting) save(); });
    form.addEventListener('submit', event => {
      if (blocked || submitting) { event.preventDefault(); return; }
      if (window.navigator.onLine === false) {
        event.preventDefault(); save();
        status.textContent = 'Aloqa yo‘q. Javob yuborilmadi; ulanish tiklangach o‘zingiz qayta yuboring.';
        return;
      }
      // Do not silently discard another form's unpersistable file selection.
      if (states.some(s => s.form !== form && s.hasFiles()) && !window.confirm('Boshqa topshiriqda tanlangan fayl bu yuborishga kirmaydi. Davom etasizmi?')) {
        event.preventDefault(); return;
      }
      pending = true; save(); submitting = true;
      form.setAttribute('aria-busy', 'true'); button.disabled = true;
      status.textContent = 'Yuborilmoqda… Natija keyingi server sahifasida tasdiqlanadi.';
    });
    states.push({form, hasFiles: files, dirty: () => files() || !same(values(), initial), reset: () => {
      pending = false; form.removeAttribute('aria-busy'); button.disabled = blocked;
    }});
    updateCount();
  });
  window.addEventListener('beforeunload', event => {
    if (!submitting && states.some(s => s.dirty())) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) { window.location.reload(); return; } // Recheck auth and persisted outcomes on Back.
    submitting = false; states.forEach(s => s.reset());
  });
  document.querySelector('[data-form-errors]')?.focus();
})();
