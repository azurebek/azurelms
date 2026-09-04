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
