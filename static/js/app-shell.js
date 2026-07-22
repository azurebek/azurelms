/* ============================================================
   AzureLMS — AppShell behavior
   Tema almashtirish shared/app.js da. Bu yerda:
   - sidebar yig'ish (desktop)
   - mobil sidebar ochish/yopish
   - nav-guruhlarni yig'ish
   ============================================================ */
(() => {
  const app = document.querySelector('.app');
  if (!app) return;

  // Sidebar yig'ish (desktop)
  document.querySelectorAll('[data-app-collapse]').forEach((btn) => {
    btn.addEventListener('click', () => app.classList.toggle('collapsed'));
  });

  // Mobil sidebar
  document.querySelectorAll('[data-app-menu]').forEach((btn) => {
    btn.addEventListener('click', () => app.classList.toggle('side-open'));
  });
  document.addEventListener('click', (e) => {
    if (!app.classList.contains('side-open')) return;
    const side = app.querySelector('.app-side');
    const menu = e.target.closest('[data-app-menu]');
    if (side && !side.contains(e.target) && !menu) app.classList.remove('side-open');
  });
  // Drawer overlay bo'lgani uchun Escape ham yopadi.
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') app.classList.remove('side-open');
  });

  // Nav-guruh yig'ish
  document.querySelectorAll('[data-app-group]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.app-nav-group');
      if (group) group.classList.toggle('collapsed');
    });
  });
})();
