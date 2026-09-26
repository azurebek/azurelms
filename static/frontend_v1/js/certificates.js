(() => {
  'use strict';
  // Only a user gesture opens the native dialog; no automatic success claim.
  for (const button of document.querySelectorAll('[data-certificate-print]')) {
    button.addEventListener('click', () => window.print());
  }
})();
