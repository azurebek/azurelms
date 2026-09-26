(() => {
  const forms = [...document.querySelectorAll('[data-settings-form]')];
  const initial = new Map();
  let submitting = false;
  const snapshot = form => JSON.stringify([...form.querySelectorAll('select')].map(field => field.value));
  const dirty = form => form.hasAttribute('data-settings-unsaved') || snapshot(form) !== initial.get(form);
  for (const form of forms) {
    initial.set(form, snapshot(form));
    form.addEventListener('submit', event => {
      if (event.defaultPrevented) return;
      if (submitting) { event.preventDefault(); return; }
      const notice = document.querySelector('[data-settings-offline]');
      if (navigator.onLine === false) {
        event.preventDefault();
        if (notice) { notice.hidden = false; notice.scrollIntoView({block: 'nearest'}); }
        return;
      }
      if (forms.some(other => other !== form && dirty(other)) && !window.confirm('Boshqa saqlanmagan tanlovlar bor. Shu amalni bajarib, ularni bekor qilasizmi?')) {
        event.preventDefault(); return;
      }
      if (notice) notice.hidden = true;
      submitting = true;
      form.setAttribute('aria-busy', 'true');
      // Native POST owns success. No fetch, optimistic state or automatic retry.
    });
  }
  window.addEventListener('beforeunload', event => {
    if (!submitting && forms.some(dirty)) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    for (const form of forms) form.removeAttribute('aria-busy');
  });
})();
