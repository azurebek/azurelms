(() => {
  "use strict";
  const forms = [...document.querySelectorAll('[data-account-form]')];
  const fields = form => [...form.querySelectorAll('input:not([type="hidden"]), textarea')];
  const snapshot = form => JSON.stringify(fields(form).map(field => field.type === 'file' ? field.files.length : field.value));
  // A rejected POST is still an unsaved draft, even before the next keystroke.
  const baseline = new Map(forms.map(form => [form, form.hasAttribute('data-account-unsaved') ? null : snapshot(form)]));
  let submitting = null;
  const dirty = () => forms.some(form => snapshot(form) !== baseline.get(form));
  forms.forEach(form => form.addEventListener('submit', event => {
    if (event.defaultPrevented) return;
    if (submitting) { event.preventDefault(); return; }
    const offlineNotice = form.querySelector('[data-account-offline]');
    if (navigator.onLine === false) {
      event.preventDefault();
      if (offlineNotice) offlineNotice.hidden = false;
      return;
    }
    if (offlineNotice) offlineNotice.hidden = true;
    if (forms.some(other => other !== form && snapshot(other) !== baseline.get(other)) &&
        !window.confirm('Boshqa formadagi saqlanmagan o‘zgarishlar yo‘qoladi. Davom etasizmi?')) {
      event.preventDefault(); return;
    }
    submitting = form;
    form.querySelectorAll('button[type="submit"]').forEach(button => {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    });
    // Native POST owns validation, redirect and success. Never retry here.
  }));
  window.addEventListener('beforeunload', event => {
    if (!submitting && dirty()) { event.preventDefault(); event.returnValue = ''; }
  });
  const clearPasswords = () => forms.forEach(form => {
    form.querySelectorAll('input[type="password"]').forEach(field => { field.value = ''; });
  });
  window.addEventListener('pagehide', clearPasswords);
  window.addEventListener('pageshow', () => {
    submitting = null;
    clearPasswords();
    forms.forEach(form => form.querySelectorAll('button[type="submit"]').forEach(button => {
      button.disabled = false;
      button.removeAttribute('aria-busy');
    }));
  });
})();
