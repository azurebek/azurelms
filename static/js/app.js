/* ============================================================
   AzureLMS — Shared runtime (global)
   Tema almashtirish, progress barlar, hisoblagichlar, typing,
   scroll-spy. Har shell shuni yuklaydi; shell'ga xos xulq
   <shell>/<shell>.js da bo'ladi.
   ============================================================ */
(() => {
  const storage = {
    get(key, fallback) { try { return localStorage.getItem(key) || fallback; } catch { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch {} }
  };

  function applyTheme(root, theme) {
    if (!root) return;
    root.setAttribute('data-theme', theme);
    root.querySelectorAll('[aria-label="Mavzu"] i').forEach((icon) => {
      icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon';
    });
  }

  function initTheme() {
    document.querySelectorAll('[data-theme]').forEach((root) => applyTheme(root, storage.get('az-v2-theme', root.getAttribute('data-theme') || 'light')));
    document.querySelectorAll('[aria-label="Mavzu"]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const root = btn.closest('[data-theme]') || document.querySelector('[data-theme]');
        const next = (root?.getAttribute('data-theme') || 'light') === 'dark' ? 'light' : 'dark';
        applyTheme(root, next);
        storage.set('az-v2-theme', next);
      });
    });
  }

  function initProgress() {
    requestAnimationFrame(() => {
      document.querySelectorAll('[data-meter],[data-bar]').forEach((bar) => {
        const target = bar.getAttribute('data-target') || '0';
        bar.style.width = target + '%';
      });
      document.querySelectorAll('[data-grow]').forEach((bar) => {
        bar.style.height = (bar.getAttribute('data-h') || '0') + '%';
      });
    });
  }

  function initCounters() {
    const counters = [...document.querySelectorAll('[data-count]')];
    const format = (el, val) => {
      const dec = parseInt(el.getAttribute('data-dec') || '0', 10);
      const prefix = el.getAttribute('data-prefix') || '';
      const suffix = el.getAttribute('data-suffix') || '';
      return prefix + (dec ? val.toFixed(dec) : Math.round(val).toLocaleString('en-US')) + suffix;
    };
    const run = (el) => {
      const target = parseFloat(el.getAttribute('data-count') || '0');
      const start = performance.now();
      const tick = (now) => {
        const p = Math.min(1, (now - start) / 900);
        el.textContent = format(el, target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver((entries) => entries.forEach((entry) => {
        if (entry.isIntersecting) { run(entry.target); io.unobserve(entry.target); }
      }), { threshold: 0.45 });
      counters.forEach((el) => io.observe(el));
    } else {
      counters.forEach(run);
    }
  }

  function initTyping() {
    document.querySelectorAll('[data-typing]').forEach((el) => {
      const text = el.getAttribute('data-text') || el.textContent || '';
      let i = 0;
      const tick = () => {
        el.textContent = text.slice(0, i);
        i = i >= text.length ? 0 : i + 1;
        setTimeout(tick, i === 0 ? 2200 : 34);
      };
      tick();
    });
  }

  function initSpy() {
    const sections = [...document.querySelectorAll('[data-section]')];
    const navs = [...document.querySelectorAll('[data-nav]')];
    if (!sections.length || !navs.length || !('IntersectionObserver' in window)) return;
    const setActive = (id) => navs.forEach((nav) => {
      const active = nav.getAttribute('data-nav') === id;
      nav.style.color = active ? 'var(--ink)' : 'var(--ink-3)';
      const bar = nav.querySelector('[data-navbar]');
      if (bar) { bar.style.width = active ? '18px' : '0'; bar.style.opacity = active ? '1' : '0'; }
    });
    const io = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) setActive(entry.target.getAttribute('data-section'));
    }), { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach((section) => io.observe(section));
  }

  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initProgress();
    initCounters();
    initTyping();
    initSpy();
  });
})();
