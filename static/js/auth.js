/* AzureLMS — Auth shell interactions
 * Lightweight, vanilla JS. No frameworks.
 *
 * Features:
 *  - Password visibility toggle (data-password-toggle="#input-id")
 *  - OTP input auto-advance (.auth-otp-input siblings)
 *  - Locale switcher visual state (.auth-locale a)
 *  - Choice row segmented control (.auth-choice within .auth-choice-row)
 */

(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }

  function initPasswordToggles() {
    document.querySelectorAll('[data-password-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var selector = btn.getAttribute('data-password-toggle');
        var input = selector ? document.querySelector(selector) : null;
        if (!input) return;
        var isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        var icon = btn.querySelector('i');
        if (icon) {
          icon.classList.toggle('bi-eye', !isPassword);
          icon.classList.toggle('bi-eye-slash', isPassword);
        }
      });
    });
  }

  function initOtpInputs() {
    var inputs = Array.from(document.querySelectorAll('.auth-otp-input'));
    if (!inputs.length) return;

    inputs.forEach(function (input, idx) {
      input.setAttribute('inputmode', 'numeric');
      input.setAttribute('autocomplete', 'one-time-code');

      input.addEventListener('input', function () {
        input.value = input.value.replace(/\D/g, '').slice(0, 1);
        if (input.value && inputs[idx + 1]) {
          inputs[idx + 1].focus();
        }
      });

      input.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && !input.value && inputs[idx - 1]) {
          inputs[idx - 1].focus();
        }
      });

      input.addEventListener('paste', function (e) {
        var data = (e.clipboardData || window.clipboardData).getData('text');
        var digits = data.replace(/\D/g, '').split('').slice(0, inputs.length - idx);
        if (!digits.length) return;
        e.preventDefault();
        digits.forEach(function (d, i) {
          if (inputs[idx + i]) inputs[idx + i].value = d;
        });
        var next = inputs[idx + digits.length] || inputs[inputs.length - 1];
        if (next) next.focus();
      });
    });
  }

  function initLocaleSwitch() {
    var groups = document.querySelectorAll('.auth-locale');
    groups.forEach(function (group) {
      var links = group.querySelectorAll('a');
      links.forEach(function (link) {
        link.addEventListener('click', function (e) {
          if (link.getAttribute('href') === '#') {
            e.preventDefault();
          }
          links.forEach(function (l) { l.classList.remove('is-active'); });
          link.classList.add('is-active');
        });
      });
    });
  }

  function initChoiceRows() {
    document.querySelectorAll('.auth-choice-row').forEach(function (row) {
      var buttons = row.querySelectorAll('.auth-choice');
      buttons.forEach(function (btn) {
        btn.addEventListener('click', function () {
          buttons.forEach(function (b) { b.classList.remove('is-active'); });
          btn.classList.add('is-active');
          var target = row.dataset.target;
          if (target) {
            var hidden = document.querySelector(target);
            if (hidden) hidden.value = btn.dataset.value || btn.textContent.trim();
          }
        });
      });
    });
  }

  ready(function () {
    initPasswordToggles();
    initOtpInputs();
    initLocaleSwitch();
    initChoiceRows();
  });
})();
