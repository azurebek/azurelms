(() => {
  'use strict';
  const forms = [...document.querySelectorAll('[data-auth-form]')];
  const passwords = [...document.querySelectorAll('[data-auth-password]')];
  const toggles = [...document.querySelectorAll('[data-auth-toggle]')];
  let submitting = false;
  const dirty = () => forms.some(form => form.hasAttribute('data-auth-unsaved') ||
    [...form.querySelectorAll('input:not([type="hidden"])')].some(field => field.value !== field.defaultValue));
  for (const button of toggles) {
    button.addEventListener('click', () => {
      const field = document.getElementById(button.getAttribute('aria-controls'));
      const visible = field.type === 'password';
      field.type = visible ? 'text' : 'password';
      button.setAttribute('aria-pressed', String(visible));
      button.textContent = visible ? 'Yashirish' : 'Ko‘rsatish';
    });
  }
  for (const form of forms) {
    form.addEventListener('submit', event => {
      if (event.defaultPrevented) return;
      if (submitting) { event.preventDefault(); return; }
      const notice = document.querySelector('[data-auth-offline]');
      if (navigator.onLine === false) {
        event.preventDefault();
        if (notice) { notice.hidden = false; notice.focus(); }
        return;
      }
      if (notice) notice.hidden = true;
      submitting = true;
      form.setAttribute('aria-busy', 'true');
      // Native POST owns success; never disable password fields before serialization.
    });
  }
  window.addEventListener('beforeunload', event => {
    if (!submitting && dirty()) { event.preventDefault(); event.returnValue = ''; }
  });
  const clearPasswords = () => {
    for (const field of passwords) { field.value = ''; field.type = 'password'; }
    for (const button of toggles) { button.setAttribute('aria-pressed', 'false'); button.textContent = 'Ko‘rsatish'; }
  };
  window.addEventListener('pagehide', clearPasswords);
  window.addEventListener('pageshow', () => {
    submitting = false;
    clearPasswords();
    for (const form of forms) form.removeAttribute('aria-busy');
  });
})();
