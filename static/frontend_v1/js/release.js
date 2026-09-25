/* Progressive enhancement only. GET prepares; native CSRF POST changes state. */
(() => {
  'use strict';
  const section = document.querySelector('[data-release-confirm]');
  if (!section) return;
  const form = section.querySelector('[data-release-form]');
  const note = form.elements.note;
  let submitting = false;
  window.addEventListener('beforeunload', event => {
    if (!submitting && note.value.trim()) {
      event.preventDefault();
      event.returnValue = '';
    }
  });
  form.addEventListener('submit', event => {
    if (submitting) { event.preventDefault(); return; }
    submitting = true;
    form.setAttribute('aria-busy', 'true');
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    form.removeAttribute('aria-busy');
  });
  // No dialog support / no JS still has the complete server-rendered form.
  const dialog = document.createElement('dialog');
  if (typeof dialog.showModal !== 'function') return;
  dialog.className = 'c-dialog v1-release-dialog';
  dialog.setAttribute('aria-labelledby', 'release-title');
  const reopen = document.createElement('button');
  reopen.type = 'button';
  reopen.className = 'c-button c-button--secondary';
  reopen.textContent = 'Tasdiqlashni qayta ochish';
  section.before(reopen, dialog);
  dialog.append(section);
  const open = () => {
    reopen.hidden = true;
    dialog.showModal();
    const error = section.querySelector('[data-release-error]');
    (error || note).focus();
  };
  reopen.addEventListener('click', open);
  dialog.addEventListener('close', () => {
    reopen.hidden = false;
    reopen.focus();
  });
  form.querySelector('[data-release-cancel]').addEventListener('click', event => {
    event.preventDefault();
    dialog.close(); // note stays only in this page, never shared browser storage
  });
  open();
})();
