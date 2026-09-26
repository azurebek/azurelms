(() => {
  'use strict';
  const forms = [...document.querySelectorAll('[data-library-form]')];
  let submitting = false;
  // Browsers implicitly select the first option when HTML has no `selected`.
  // Capture the actual initial selection, otherwise a clean form looks dirty.
  const initialSelections = new Map();
  for (const form of forms) {
    for (const field of form.querySelectorAll('select')) {
      if (field.tagName === 'SELECT') initialSelections.set(field, [...field.options].map(option => option.selected));
    }
  }
  const dirty = form => form.hasAttribute('data-library-unsaved') || [...form.querySelectorAll('input:not([type="hidden"]):not([name="confirm_scope"]), select, textarea')].some(field =>
    field.tagName === 'SELECT' ? [...field.options].some((option, i) => option.selected !== initialSelections.get(field)[i]) :
      field.type === 'file' ? field.files.length > 0 :
        field.type === 'checkbox' ? field.checked !== field.defaultChecked : field.value !== field.defaultValue);
  const offline = document.querySelector('[data-library-offline]');
  const pending = document.querySelector('[data-library-pending]');
  const error = document.querySelector('[data-library-error]');
  if (error) error.focus();
  for (const form of forms) {
    const updateHint = () => {
      const hint = form.querySelector('[data-library-filter-hint]');
      if (hint) hint.textContent = dirty(form) ? 'Tanlov hali qo‘llanmagan. “Filtrni qo‘llash”ni bosing.' : 'Tanlashning o‘zi natijani o‘zgartirmaydi. “Filtrni qo‘llash”ni bosing.';
    };
    form.addEventListener('input', updateHint);
    form.addEventListener('change', updateHint);
    form.addEventListener('submit', event => {
      if (event.defaultPrevented) return;
      if (submitting) { event.preventDefault(); return; }
      if (navigator.onLine === false) {
        event.preventDefault();
        if (offline) { offline.hidden = false; offline.focus(); }
        return;
      }
      if (forms.some(other => other !== form && dirty(other)) && !window.confirm('Boshqa formadagi saqlanmagan o‘zgarishlar qoladi. Ularni saqlamasdan davom etasizmi?')) {
        event.preventDefault(); return;
      }
      if (offline) offline.hidden = true;
      if (pending) pending.hidden = false;
      submitting = true;
      form.setAttribute('aria-busy', 'true');
      // Native multipart/CSRF/PRG owns acknowledgement. No retry or disabled fields.
    });
  }
  window.addEventListener('beforeunload', event => {
    if (!submitting && forms.some(dirty)) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    if (pending) pending.hidden = true;
    for (const form of forms) form.removeAttribute('aria-busy');
  });
})();
