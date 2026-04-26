(function () {
  const copyButton = document.querySelector("[data-copy-card]");
  const cardNumber = document.querySelector("[data-card-number]");
  const checkoutForm = document.querySelector("[data-checkout-form]");
  const successMessage = document.querySelector("[data-checkout-success]");
  const statusCard = document.querySelector("[data-checkout-status]");
  const uploadInput = document.querySelector("#receipt-file");
  const uploadLabel = document.querySelector("[data-upload-label]");

  copyButton?.addEventListener("click", async () => {
    const number = cardNumber?.textContent?.replace(/\s+/g, " ").trim();

    if (!number) {
      return;
    }

    try {
      await navigator.clipboard.writeText(number);
      copyButton.innerHTML = '<i class="bi bi-check2"></i>';
      window.setTimeout(() => {
        copyButton.innerHTML = '<i class="bi bi-copy"></i>';
      }, 1400);
    } catch (error) {
      copyButton.innerHTML = '<i class="bi bi-check2"></i>';
    }
  });

  uploadInput?.addEventListener("change", () => {
    const fileName = uploadInput.files?.[0]?.name;
    const hint = uploadLabel?.querySelector("em");

    if (fileName && hint) {
      hint.textContent = fileName;
    }
  });

  checkoutForm?.addEventListener("submit", (event) => {
    event.preventDefault();

    if (successMessage) {
      successMessage.hidden = false;
      successMessage.focus();
    }

    if (statusCard) {
      statusCard.classList.add("is-pending");
      statusCard.innerHTML = `
        <span>Holat</span>
        <strong>Qabul qilindi, tasdiqlash kutilmoqda</strong>
        <p>Kvitansiya admin tomonidan tekshiriladi. Tez orada obuna holati yangilanadi.</p>
      `;
    }

    checkoutForm.querySelector("button[type='submit']")?.setAttribute("disabled", "disabled");
  });
})();
