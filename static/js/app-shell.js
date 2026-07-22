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

  // Profil menyusi (hisob amallari)
  const userMenu = app.querySelector('[data-app-user-menu]');
  const userTrigger = userMenu && userMenu.querySelector('[data-app-user-trigger]');
  const userPop = userMenu && userMenu.querySelector('[data-app-user-pop]');

  const closeUserMenu = () => {
    if (!userMenu || !userMenu.classList.contains('is-open')) return;
    userMenu.classList.remove('is-open');
    userTrigger.setAttribute('aria-expanded', 'false');
    userPop.hidden = true;
  };

  if (userMenu && userTrigger && userPop) {
    userTrigger.addEventListener('click', () => {
      const open = userMenu.classList.toggle('is-open');
      userTrigger.setAttribute('aria-expanded', String(open));
      userPop.hidden = !open;
    });
    document.addEventListener('click', (e) => {
      if (!userMenu.contains(e.target)) closeUserMenu();
    });
  }

  // Sidebar yig'ish (desktop)
  document.querySelectorAll('[data-app-collapse]').forEach((btn) => {
    btn.addEventListener('click', () => {
      // Kenglik o'zgargani uchun ochiq menyu noto'g'ri joyda qolib ketmasin.
      closeUserMenu();
      app.classList.toggle('collapsed');
    });
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
  // Drawer va profil menyusi overlay bo'lgani uchun Escape ikkalasini yopadi.
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    app.classList.remove('side-open');
    closeUserMenu();
  });

  // Nav-guruh yig'ish
  document.querySelectorAll('[data-app-group]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.app-nav-group');
      if (group) group.classList.toggle('collapsed');
    });
  });
})();
