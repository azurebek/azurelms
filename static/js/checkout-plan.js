/* The server resolves the actual cohort, price and billing period together. */
document.querySelectorAll('[data-checkout-plan]').forEach(function (input) {
  input.addEventListener('change', function () {
    const url = new URL(window.location.href);
    url.searchParams.set('plan_id', input.value);
    const promo = document.querySelector('[name="promo_code"]');
    if (promo) url.searchParams.set('promo_code', promo.value);
    window.location.assign(url.toString());
  });
});

/* Karta raqamini nusxalash: raqamni qo'lda ko'chirish xato qilishning eng
   oson yo'li, ayniqsa telefonda. */
const copyButton = document.querySelector('[data-copy-card]');
if (copyButton) {
  copyButton.addEventListener('click', function () {
    const source = document.querySelector('[data-card-number]');
    const label = copyButton.querySelector('[data-copy-label]');
    if (!source || !navigator.clipboard) return;
    navigator.clipboard.writeText(source.textContent.trim()).then(function () {
      const previous = label.textContent;
      label.textContent = 'Nusxalandi';
      setTimeout(function () { label.textContent = previous; }, 2000);
    });
  });
}
