/* Auth formalari: aniq, bir martalik xatolar (PUB1.4b, UX-04 porti).
 *
 * JS bo'lmasa server tekshiruvi to'liq ishlaydi; bu skript faqat qulaylik:
 *  - brauzerning native pufakchalari o'rniga xato maydon yonida, server ishlatadigan
 *    ayni joyda (`<id>_error`) va maydonga `aria-invalid`/`aria-describedby` bilan;
 *  - bitta xulosa — nechta maydonni tekshirish kerakligi, xatoni takrorlamaydi;
 *  - yuborishda va xato bilan qaytgan sahifada fokus birinchi xatoga;
 *  - tuzatilgan maydonning eskirgan xabari darhol olinadi.
 * Parol qoidalari va hisob mavjudligi faqat serverda tekshiriladi (soxta “kuch”
 * o'lchagich yo'q). Parol hech qayerga yozilmaydi.
 */
(() => {
  'use strict';
  const MESSAGES = {
    required: 'Bu maydonni to‘ldiring.',
    email: 'Email manzilini to‘g‘ri kiriting, masalan: ism@misol.uz.',
    mismatch: 'Ikkala parol bir xil emas — ikkalasini ham tekshiring.',
    pattern: 'Kiritilgan qiymat talabga mos emas.',
    other: 'Qiymatni tekshiring.',
  };
  // [asosiy, tasdiqlash] juftliklari — tasdiq maydonida xato ko'rsatiladi (server ham shunday).
  const PAIRS = [['password1', 'password2'], ['new_password1', 'new_password2']];

  function messageFor(field) {
    const validity = field.validity || {};
    if (validity.valid !== false) return '';
    if (validity.valueMissing) return MESSAGES.required;
    if (validity.typeMismatch && field.type === 'email') return MESSAGES.email;
    if (validity.tooLong) return `Ko‘pi bilan ${field.maxLength} belgi kiriting.`;
    if (validity.tooShort) return `Kamida ${field.minLength} belgi kiriting.`;
    if (validity.patternMismatch) return MESSAGES.pattern;
    return MESSAGES.other;
  }

  function summaryText(count) {
    return `${count} ta maydonni tekshiring.`;
  }

  /** `fields` — formadagi kiritish maydonlari (DOM tartibida). `[{field, message}]` qaytaradi. */
  function validate(fields) {
    const byName = new Map(fields.map(field => [field.name, field]));
    const problems = new Map();
    for (const field of fields) {
      const message = messageFor(field);
      if (message) problems.set(field, message);
    }
    for (const [first, second] of PAIRS) {
      const a = byName.get(first), b = byName.get(second);
      if (a && b && a.value && b.value && a.value !== b.value && !problems.has(b)) problems.set(b, MESSAGES.mismatch);
    }
    return fields.filter(field => problems.has(field)).map(field => ({field, message: problems.get(field)}));
  }

  const api = {messageFor, summaryText, validate, MESSAGES};
  globalThis.AzAuthValidation = api;
  if (typeof document === 'undefined' || !document.querySelectorAll) return;

  const inputs = form => [...form.querySelectorAll('input, select, textarea')]
    .filter(field => !['hidden', 'submit', 'button'].includes(field.type) && !field.disabled);
  const summary = () => document.querySelector('[data-form-errors]');

  function describedBy(field, id, add) {
    const ids = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean).filter(value => value !== id);
    if (add) ids.push(id);
    if (ids.length) field.setAttribute('aria-describedby', ids.join(' '));
    else field.removeAttribute('aria-describedby');
  }

  function showError(form, field, message) {
    const id = `${field.id}_error`;
    let slot = document.getElementById(id);
    if (!slot) {
      const legacy = form.dataset.errorClass && form.dataset.errorClass !== 'errorlist';
      slot = document.createElement(legacy ? 'div' : 'ul');
      slot.className = legacy ? form.dataset.errorClass : 'errorlist';
      slot.id = id;
      const anchor = field.parentElement && field.parentElement.classList.contains('p-auth-input') ? field.parentElement : field;
      anchor.insertAdjacentElement('afterend', slot);
    }
    slot.replaceChildren();
    const line = document.createElement(slot.tagName === 'UL' ? 'li' : 'div');
    line.textContent = message;
    slot.append(line);
    field.setAttribute('aria-invalid', 'true');
    describedBy(field, id, true);
  }

  function clearError(field) {
    const id = `${field.id}_error`;
    document.getElementById(id)?.remove();
    field.removeAttribute('aria-invalid');
    describedBy(field, id, false);
  }

  function refreshSummary(form, {dropServerNotice = false} = {}) {
    const box = summary();
    if (!box) return 0;
    if (dropServerNotice) box.querySelectorAll('.nonfield, .errorlist').forEach(list => list.remove());
    const count = form.querySelectorAll('[aria-invalid="true"]').length;
    let line = box.querySelector('[data-error-count]');
    if (!line) {
      line = document.createElement('p');
      line.setAttribute('data-error-count', '');
      box.append(line);
    }
    line.textContent = summaryText(count);
    line.hidden = count === 0;
    box.hidden = count === 0 && !box.querySelector('.nonfield, .errorlist');
    return count;
  }

  function firstInvalid(form) {
    return form.querySelector('[aria-invalid="true"]');
  }

  for (const form of document.querySelectorAll('form[data-auth-validate]')) {
    // Native pufakchalar o'rniga maydon yonidagi matn; server tekshiruvi baribir oxirgi so'z.
    form.noValidate = true;
    form.addEventListener('submit', event => {
      const problems = validate(inputs(form));
      const failing = new Set(problems.map(problem => problem.field));
      for (const field of inputs(form)) {
        if (!failing.has(field) && field.dataset.clientError) { clearError(field); delete field.dataset.clientError; }
      }
      if (!problems.length) return;
      event.preventDefault();
      for (const {field, message} of problems) { showError(form, field, message); field.dataset.clientError = '1'; }
      refreshSummary(form, {dropServerNotice: true});
      problems[0].field.focus();
    }, true);
    form.addEventListener('input', event => {
      const field = event.target;
      if (!(field instanceof HTMLElement) || !field.matches('[aria-invalid="true"], [data-client-error]')) {
        // Juftlikdagi sherigi tuzatilsa ham tasdiq maydonidagi “bir xil emas” xabari eskiradi.
        const partner = PAIRS.find(([first]) => first === field.name);
        const confirm = partner && form.querySelector(`[name="${partner[1]}"][aria-invalid="true"]`);
        if (!confirm) return;
        const still = validate(inputs(form)).find(problem => problem.field === confirm);
        if (still) showError(form, confirm, still.message); else clearError(confirm);
        refreshSummary(form);
        return;
      }
      // Tuzatish: maydonning eski (server yoki mijoz) xabari olinadi; qayta yuborishda yana tekshiriladi.
      const still = validate(inputs(form)).find(problem => problem.field === field);
      if (still && field.dataset.clientError) showError(form, field, still.message); else clearError(field);
      delete field.dataset.clientError;
      refreshSummary(form);
    });
  }

  // Xato bilan qaytgan sahifa: fokus birinchi xato maydoniga, bo'lmasa xulosaga.
  const box = summary();
  if (box && !box.hidden) {
    const form = document.querySelector('form[data-auth-validate]');
    const target = (form && firstInvalid(form)) || box;
    target.focus();
  }
})();
