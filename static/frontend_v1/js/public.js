"use strict";
// Reactions use the canonical endpoints. No optimistic counts or automatic retries.
document.querySelectorAll('[data-public-reaction]').forEach(form => {
  const button = form.querySelector('button[type="submit"]');
  const status = form.querySelector('[data-reaction-status]');
  let busy = false;
  button.disabled = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy) return;
    busy = true; button.disabled = true; status.textContent = 'Yuborilmoqda…';
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(form.action, {method: 'POST', body: new FormData(form), credentials: 'same-origin', signal: controller.signal, headers: {'Accept': 'application/json'}});
      const data = await response.json();
      const count = form.dataset.publicReaction === 'clap' ? data.clap_count : data.like_count;
      if (!response.ok || !data.ok || !Number.isInteger(count) || count < 0) throw new Error('unconfirmed');
      form.querySelector('[data-reaction-count]').textContent = String(count);
      if (form.dataset.publicReaction === 'like') button.setAttribute('aria-pressed', String(data.liked));
      status.textContent = 'Saqlandi.';
      busy = false; button.disabled = false;
      if (form.dataset.publicReaction === 'clap' && data.added === false) {
        button.disabled = true; busy = true; status.textContent = 'Olqish chegarasiga yetdingiz.';
      }
    } catch {
      status.textContent = 'Natija tasdiqlanmadi. Qayta yuborishdan oldin sahifadagi holatni yangilang.';
      form.querySelector('[data-reaction-reload]').hidden = false;
      // The request may have committed; keep this action blocked until explicit reload.
    } finally { clearTimeout(timer); }
  });
});
let leavingBySubmit = false;
document.querySelectorAll('[data-public-comment]').forEach(form => {
  form.addEventListener('submit', () => { leavingBySubmit = true; });
});
window.addEventListener('beforeunload', event => {
  if (!leavingBySubmit && [...document.querySelectorAll('[data-public-comment] textarea')].some(input => input.value.trim())) {
    event.preventDefault(); event.returnValue = '';
  }
});
window.addEventListener('pageshow', () => { leavingBySubmit = false; });
