"use strict";
// Native disclosure remains usable without JavaScript; no navigation/network side effects.
const publicMenu = document.querySelector('[data-public-menu]');
if (publicMenu) {
  const summary = publicMenu.querySelector('summary');
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && publicMenu.open) {
      publicMenu.open = false;
      summary.focus();
    }
  });
  document.addEventListener('click', event => {
    if (publicMenu.open && !publicMenu.contains(event.target)) publicMenu.open = false;
  });
  // `public.css` bilan bir chegara: undan kengda desktop menyu ko'rinadi.
  const desktop = window.matchMedia('(min-width: 1200px)');
  desktop.addEventListener('change', event => {
    if (event.matches) publicMenu.open = false;
  });
  window.addEventListener('pageshow', () => { publicMenu.open = false; });
}

// Footer guruhlari telefonda yig'iladi; kengroq ekranda doim ochiq ustun.
// Server `open` bilan chizadi — JS bo'lmasa hech narsa yashirinmaydi.
const footerFolds = [...document.querySelectorAll('[data-footer-fold]')];
if (footerFolds.length) {
  const compact = window.matchMedia('(max-width: 639.98px)');
  const syncFolds = () => footerFolds.forEach(fold => {
    fold.open = !compact.matches;
    fold.querySelector('summary').tabIndex = compact.matches ? 0 : -1;
  });
  footerFolds.forEach(fold => fold.querySelector('summary').addEventListener('click', event => {
    if (!compact.matches) event.preventDefault();
  }));
  compact.addEventListener('change', syncFolds);
  syncFolds();
}
