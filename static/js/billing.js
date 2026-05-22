(function() {
  const html = document.documentElement;
  const themeBtn = document.getElementById("themeBtn");
  const themeIcon = document.getElementById("themeIcon");

  function formatMoney(value) {
    const number = Number(value || 0);
    return `${number.toLocaleString("uz-UZ")} so'm`;
  }

  function applyTheme(isDark) {
    html.setAttribute("data-theme", isDark ? "dark" : "light");
    if (themeIcon) {
      themeIcon.className = isDark ? "bi bi-sun" : "bi bi-moon";
    }
    try { localStorage.setItem("az-theme", isDark ? "dark" : "light"); } catch (_) {}
  }

  function syncThemeIcon() {
    if (!themeIcon) return;
    themeIcon.className = html.getAttribute("data-theme") === "dark" ? "bi bi-sun" : "bi bi-moon";
  }

  syncThemeIcon();
  themeBtn?.addEventListener("click", () => {
    applyTheme(html.getAttribute("data-theme") !== "dark");
  });

  const form = document.getElementById("checkoutForm");
  const planOptions = document.querySelectorAll("[data-plan-option]");
  const basePrice = document.getElementById("basePrice");
  const totalPrice = document.getElementById("totalPrice");
  const promoRow = document.getElementById("promoRow");
  const promoDiscount = document.getElementById("promoDiscount");
  const promoInput = document.getElementById("promoInput");
  const promoBtn = document.getElementById("promoApplyBtn");
  const promoFeedback = document.getElementById("promoFeedback");
  const pricePlanLabel = document.getElementById("pricePlanLabel");
  let activePromo = null;

  function selectedPlanOption() {
    return document.querySelector("[data-plan-option] .plan-input:checked")?.closest("[data-plan-option]");
  }

  function updateSummaryFromPlan() {
    const option = selectedPlanOption();
    if (!option) return;
    const price = Number(option.dataset.price || 0);
    const discount = activePromo ? Number(activePromo.discount_amount || 0) : 0;
    const finalPrice = activePromo ? Number(activePromo.final_amount || price) : price;

    if (pricePlanLabel) pricePlanLabel.textContent = option.dataset.planName || "Tarif narxi";
    if (basePrice) basePrice.textContent = formatMoney(activePromo ? activePromo.base_amount : price);
    if (totalPrice) totalPrice.textContent = formatMoney(finalPrice);
    if (promoDiscount) promoDiscount.textContent = `-${formatMoney(discount)}`;
    promoRow?.classList.toggle("is-hidden", !activePromo || discount <= 0);
  }

  planOptions.forEach((option) => {
    option.addEventListener("click", () => {
      planOptions.forEach((item) => item.classList.remove("selected"));
      option.classList.add("selected");
      const input = option.querySelector(".plan-input");
      if (input) input.checked = true;
      activePromo = null;
      if (promoFeedback) promoFeedback.textContent = "";
      updateSummaryFromPlan();
    });
  });

  promoBtn?.addEventListener("click", async () => {
    const code = (promoInput?.value || "").trim();
    const option = selectedPlanOption();
    const endpoint = form?.dataset.promoUrl;
    if (!code || !option || !endpoint) {
      if (promoFeedback) promoFeedback.textContent = "Promo-kod kiriting.";
      return;
    }

    const planInput = option.querySelector(".plan-input");
    const params = new URLSearchParams({ plan_id: planInput?.value || "", promo_code: code });
    promoBtn.disabled = true;
    if (promoFeedback) promoFeedback.textContent = "Tekshirilmoqda...";

    try {
      const response = await fetch(`${endpoint}?${params.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const payload = await response.json();
      if (!response.ok || !payload.valid) {
        activePromo = null;
        updateSummaryFromPlan();
        if (promoFeedback) promoFeedback.textContent = payload.error || "Promo-kod ishlamadi.";
        return;
      }
      activePromo = payload;
      updateSummaryFromPlan();
      if (promoFeedback) promoFeedback.textContent = `${payload.promo_code} qo'llandi.`;
    } catch (_) {
      activePromo = null;
      updateSummaryFromPlan();
      if (promoFeedback) promoFeedback.textContent = "Promo-kodni tekshirib bo'lmadi.";
    } finally {
      promoBtn.disabled = false;
    }
  });

  document.querySelectorAll(".pay-method").forEach((method) => {
    method.addEventListener("click", () => {
      document.querySelectorAll(".pay-method").forEach((item) => item.classList.remove("selected"));
      method.classList.add("selected");
    });
  });

  const receiptInput = document.getElementById("receiptImage");
  const receiptFileName = document.getElementById("receiptFileName");
  receiptInput?.addEventListener("change", () => {
    const file = receiptInput.files && receiptInput.files[0];
    if (file && receiptFileName) {
      receiptFileName.textContent = file.name;
    }
  });

  updateSummaryFromPlan();
})();
