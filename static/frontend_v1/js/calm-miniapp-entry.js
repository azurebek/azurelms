(() => {
  "use strict";

  const root = document.querySelector("[data-miniapp-entry]");
  if (!root) return;
  const telegram = window.Telegram?.WebApp;
  const spinner = root.querySelector("[data-mini-spinner]");
  const title = root.querySelector("[data-mini-entry-title]");
  const message = root.querySelector("[data-mini-entry-message]");
  const retry = root.querySelector("[data-mini-retry]");

  const fail = text => {
    spinner.hidden = true;
    title.hidden = false;
    retry.hidden = false;
    message.textContent = text;
    message.setAttribute("role", "alert");
  };

  const start = async () => {
    const initData = telegram?.initData || "";
    if (!initData) {
      const join = root.dataset.loginUrl.includes("?") ? "&" : "?";
      window.location.replace(`${root.dataset.loginUrl}${join}next=${encodeURIComponent(root.dataset.nextPath)}`);
      return;
    }
    spinner.hidden = false;
    title.hidden = true;
    retry.hidden = true;
    message.textContent = "Kirilmoqda…";
    message.removeAttribute("role");
    try {
      telegram.ready();
      telegram.expand();
      const response = await fetch(root.dataset.authUrl, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({init_data: initData, next: root.dataset.nextPath}),
      });
      const payload = await response.json();
      if (!response.ok || payload.status !== "success") {
        fail(payload.message || "Kirishda xatolik. Botga qaytib /start bosing.");
        return;
      }
      window.location.replace(payload.redirect);
    } catch {
      fail("Ulanishda xatolik — qayta urinib ko‘ring.");
    }
  };

  root.querySelector("[data-mini-close]")?.addEventListener("click", () => {
    try {
      if (telegram?.close) telegram.close();
      else if (window.history.length > 1) window.history.back();
    } catch { /* Telegram'dan tashqarida tugma xavfsiz no-op. */ }
  });
  retry.addEventListener("click", start);
  start();
})();
