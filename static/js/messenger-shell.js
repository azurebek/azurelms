/* ============================================================
   AzureLMS — Messenger shell behavior
   Chat mantig'i messenger-chat.js da. Bu yerda faqat layout:
   - telefon rejimida suhbatlar ro'yxatini drawer sifatida ochish/yopish
   ============================================================ */
(() => {
  const msgr = document.querySelector('.msgr');
  if (!msgr) return;

  const close = () => msgr.classList.remove('list-open');

  document.querySelectorAll('[data-msgr-list-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => msgr.classList.toggle('list-open'));
  });

  // Tashqariga bosish yopadi (scrim ham shu yo'l bilan ishlaydi).
  document.addEventListener('click', (e) => {
    if (!msgr.classList.contains('list-open')) return;
    const list = msgr.querySelector('.msgr-list');
    const toggle = e.target.closest('[data-msgr-list-toggle]');
    if (list && !list.contains(e.target) && !toggle) close();
  });

  // Overlay ochiq bo'lsa Escape uni yopadi.
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
  });
})();
