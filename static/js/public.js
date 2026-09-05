/* ============================================================
   AzureLMS — PublicShell behavior
   Tema almashtirish shared/app.js da. Bu yerda:
   1) scroll'da header soyasi (sticky nav uchun)
   2) reveal-on-scroll (landing seksiyalari uchun)
   ============================================================ */
(() => {
  const menu = document.querySelector('[data-public-menu]');
  if (menu) {
    document.addEventListener('click', (event) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
    // Escape hujjat darajasida tinglanadi. Menyuning o'zida tinglansa
    // faqat fokus menyu ichida turganda ishlardi — sichqoncha bilan
    // ochgan odam (Safari tugmaga fokus bermaydi) uni yopa olmasdi.
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && menu.open) {
        menu.open = false;
        menu.querySelector('summary').focus();
      }
    });
    menu.querySelector('nav').addEventListener('click', (event) => {
      if (event.target.closest('a')) menu.open = false;
    });
    window.matchMedia('(max-width: 1040px)').addEventListener('change', () => {
      menu.open = false;
    });
  }
  // 1) Sticky header soyasi (nav+footer varianti)
  const header = document.querySelector('[data-pub-header]');
  if (header) {
    const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // 2) Reveal-on-scroll ([data-reveal] elementlari ko'rinishga chiqqanda)
  const reveals = [...document.querySelectorAll('[data-reveal]')];
  if (reveals.length) {
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.style.opacity = '1';
            e.target.style.transform = 'none';
            io.unobserve(e.target);
          }
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
      reveals.forEach((el) => io.observe(el));
    } else {
      reveals.forEach((el) => { el.style.opacity = '1'; el.style.transform = 'none'; });
    }
  }
})();
