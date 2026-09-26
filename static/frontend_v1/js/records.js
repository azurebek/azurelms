(() => {
  'use strict';
  const forms = [...document.querySelectorAll('[data-record-filter], [data-record-write]')];
  let submitting = false;
  const changed = form => [...form.querySelectorAll('input:not([type="hidden"]), select')].some(field =>
    field.tagName === 'SELECT' ? [...field.options].some(option => option.selected !== option.defaultSelected) :
      field.type === 'file' ? field.files.length > 0 : field.value !== field.defaultValue);
  for (const form of forms) {
    form.addEventListener('change', () => {
      const hint = document.querySelector('[data-record-filter-hint]');
      if (form.hasAttribute('data-record-filter') && hint) hint.textContent = changed(form) ?
        'Tanlov hali qo‘llanmagan. Natijani almashtirish uchun “Qo‘llash”ni bosing.' :
        'Tanlashning o‘zi natijani o‘zgartirmaydi. “Qo‘llash”ni bosing.';
    });
    form.addEventListener('submit', event => {
      if (event.defaultPrevented) return;
      if (submitting) { event.preventDefault(); return; }
      const notice = document.querySelector('[data-record-offline]');
      if (navigator.onLine === false) {
        event.preventDefault();
        if (notice) { notice.hidden = false; notice.focus(); }
        return;
      }
      if (notice) notice.hidden = true;
      submitting = true;
      form.setAttribute('aria-busy', 'true');
      // Native serialization owns the upload. No disabled fields, retry or fake ack.
    });
  }
  window.addEventListener('beforeunload', event => {
    if (!submitting && forms.some(changed)) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    for (const form of forms) form.removeAttribute('aria-busy');
  });
})();
