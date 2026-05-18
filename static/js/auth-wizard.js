/* AzureLMS register wizard — frontend-only multi-step.
 * - Step navigation
 * - Per-step validation (required, email, min length, password match, terms)
 * - localStorage persistence (refresh-safe; parol saqlanmaydi)
 * - Heading/lede har step uchun yangilanadi
 * - Stepbar va step counter ni boshqaradi
 * - Server form_invalid bo'lsa, xato bor step'ga sakraydi
 */
(function () {
  'use strict';

  const form = document.getElementById('registerWizard');
  if (!form) return;

  const STORAGE_KEY = 'azurelms_register_wizard_v1';
  const steps = Array.from(form.querySelectorAll('.wizard-step'));
  const total = steps.length;
  if (!total) return;

  const headingEl = document.querySelector('[data-wizard-heading]');
  const ledeEl = document.querySelector('[data-wizard-lede]');
  const stepbarEl = document.getElementById('wizardStepbar');
  const stepbarDots = stepbarEl ? Array.from(stepbarEl.querySelectorAll('span')) : [];
  const stepNumEl = document.getElementById('wizardStepNum');
  const backBtn = document.getElementById('wizardBack');
  const nextBtn = document.getElementById('wizardNext');
  const submitBtn = document.getElementById('wizardSubmit');

  let current = 0;

  /* ---------- Persistence ---------- */
  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      Object.entries(data.fields || {}).forEach(([name, value]) => {
        const inputs = form.querySelectorAll(`[name="${name}"]`);
        inputs.forEach((el) => {
          if (el.type === 'radio') {
            el.checked = el.value === value;
          } else if (el.type === 'checkbox') {
            el.checked = value === true;
          } else {
            el.value = value;
          }
        });
      });
      if (typeof data.step === 'number' && data.step < total) {
        current = data.step;
      }
    } catch (e) { /* ignore */ }
  }

  function saveState() {
    const fields = {};
    form.querySelectorAll('input, select, textarea').forEach((el) => {
      if (!el.name) return;
      if (el.type === 'password') return; // parol localStorage'ga kirmasin
      if (el.type === 'radio') {
        if (el.checked) fields[el.name] = el.value;
      } else if (el.type === 'checkbox') {
        if (el.checked) fields[el.name] = true;
      } else if (el.value) {
        fields[el.name] = el.value;
      }
    });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ step: current, fields }));
    } catch (e) { /* ignore */ }
  }

  function clearState() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
  }

  /* ---------- Render ---------- */
  function pad2(n) { return String(n).padStart(2, '0'); }

  function render() {
    steps.forEach((s, i) => s.classList.toggle('is-active', i === current));

    if (stepNumEl) stepNumEl.textContent = pad2(current + 1);
    stepbarDots.forEach((dot, i) => dot.classList.toggle('is-active', i <= current));

    const stepData = steps[current].dataset;
    if (headingEl && stepData.heading) headingEl.textContent = stepData.heading;
    if (ledeEl && stepData.lede) ledeEl.textContent = stepData.lede;

    if (backBtn) backBtn.hidden = current === 0;
    const isLast = current === total - 1;
    if (nextBtn) nextBtn.hidden = isLast;
    if (submitBtn) submitBtn.hidden = !isLast;

    if (isLast) updateSummary();

    // birinchi inputga fokus
    const firstInput = steps[current].querySelector(
      'input:not([type=hidden]):not([type=radio]):not([type=checkbox]), textarea, select'
    );
    if (firstInput) setTimeout(() => firstInput.focus({ preventScroll: true }), 80);

    // xato matnlarini tozalash
    steps[current].querySelectorAll('.wizard-field-error').forEach((el) => (el.textContent = ''));
  }

  function updateSummary() {
    const get = (name) => {
      const checked = form.querySelector(`[name="${name}"]:checked`);
      if (checked) {
        const label = checked.closest('.wizard-choice')?.querySelector('.wizard-choice-body span:last-child, .wizard-choice-text');
        return label ? label.textContent.trim() : checked.value;
      }
      const el = form.querySelector(`[name="${name}"]:not([type=radio]):not([type=checkbox])`);
      return el ? (el.value || '').trim() : '';
    };
    form.querySelectorAll('[data-summary]').forEach((el) => {
      el.textContent = get(el.dataset.summary) || '—';
    });
  }

  /* ---------- Validation ---------- */
  function showError(target, message) {
    const errEl = steps[current].querySelector(`.wizard-field-error[data-for="${target}"]`);
    if (errEl) errEl.textContent = message;
  }

  function validateStep() {
    let valid = true;
    const stepEl = steps[current];

    stepEl.querySelectorAll('.wizard-field-error').forEach((el) => (el.textContent = ''));

    // Inputs with data-required
    stepEl.querySelectorAll('input[data-required="1"]').forEach((input) => {
      const id = input.id || input.name;
      const value = (input.value || '').trim();

      if (input.type === 'checkbox') {
        if (!input.checked) {
          valid = false;
          showError(id, "Davom etish uchun rozilik kerak.");
        }
        return;
      }

      if (!value) {
        valid = false;
        showError(id, "Bu maydon to'ldirilishi shart.");
        return;
      }
      const min = parseInt(input.dataset.min || '0', 10);
      if (min && value.length < min) {
        valid = false;
        showError(id, `Kamida ${min} ta belgi kiriting.`);
        return;
      }
      if (input.dataset.email) {
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          valid = false;
          showError(id, "Email format noto'g'ri.");
          return;
        }
      }
      if (input.dataset.match) {
        const other = document.getElementById(input.dataset.match);
        if (other && other.value !== value) {
          valid = false;
          showError(id, "Parollar mos kelmadi.");
          return;
        }
      }
    });

    // Radio guruhlari
    stepEl.querySelectorAll('[data-choice-group]').forEach((group) => {
      const name = group.dataset.choiceGroup;
      const checked = group.querySelector(`input[name="${name}"]:checked`);
      if (!checked) {
        valid = false;
        showError(name, "Bittasini tanlang.");
      }
    });

    return valid;
  }

  /* ---------- Navigation ---------- */
  function goNext() {
    if (!validateStep()) return;
    saveState();
    if (current < total - 1) {
      current += 1;
      render();
    }
  }

  function goBack() {
    if (current > 0) {
      current -= 1;
      render();
    }
  }

  /* ---------- Wire up ---------- */
  if (nextBtn) nextBtn.addEventListener('click', goNext);
  if (backBtn) backBtn.addEventListener('click', goBack);

  form.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
      if (current < total - 1) {
        e.preventDefault();
        goNext();
      }
    }
  });

  form.addEventListener('input', saveState);
  form.addEventListener('change', saveState);

  form.addEventListener('submit', (e) => {
    if (!validateStep()) {
      e.preventDefault();
      return;
    }
    clearState();
  });

  /* Password toggle — auth.js bilan ham ishlaydi, lekin safety net */
  form.querySelectorAll('[data-password-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = form.querySelector(btn.dataset.passwordToggle);
      if (!target) return;
      target.type = target.type === 'password' ? 'text' : 'password';
      const icon = btn.querySelector('i');
      if (icon) {
        icon.classList.toggle('bi-eye');
        icon.classList.toggle('bi-eye-slash');
      }
    });
  });

  /* ---------- Server-side error recovery ---------- */
  // Agar Django serverdan form errors qaytsa, xato bor step'ga sakraymiz.
  const errorStep = steps.findIndex((s) => s.querySelector('.auth-field-error:not(.wizard-field-error)'));
  if (errorStep >= 0) {
    current = errorStep;
    clearState();
  } else {
    loadState();
  }

  render();
})();
