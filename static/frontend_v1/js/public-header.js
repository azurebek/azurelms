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
  const desktop = window.matchMedia('(min-width: 1024px)');
  desktop.addEventListener('change', event => {
    if (event.matches) publicMenu.open = false;
  });
  window.addEventListener('pageshow', () => { publicMenu.open = false; });
}
