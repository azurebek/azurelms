(() => {
  "use strict";
  // Native form submission owns login. Never store credentials or simulate success.
  const visibility = document.querySelector("[data-password-toggle]");
  visibility?.addEventListener("click", () => {
    const field = document.getElementById(visibility.getAttribute("aria-controls"));
    const visible = field.type === "password";
    field.type = visible ? "text" : "password";
    visibility.setAttribute("aria-pressed", String(visible));
    visibility.textContent = visible ? "Yashirish" : "Ko‘rsatish";
  });

  const panel = document.querySelector("[data-telegram-auth]");
  if (!panel) return;
  const start = panel.querySelector("[data-telegram-start]");
  const link = panel.querySelector("[data-telegram-link]");
  const status = panel.querySelector("[data-telegram-status]");
  const check = panel.querySelector("[data-telegram-check]");
  const cancel = panel.querySelector("[data-telegram-cancel]");
  let timer, token, request, generation = 0;
  // Transport cadence only; token expiry remains the canonical server's decision.
  const POLL_MS = 2000;
  function stop() {
    generation += 1;
    clearTimeout(timer);
    request?.abort();
    request = null;
    token = null;
    start.disabled = false;
    start.removeAttribute("aria-busy");
    link.hidden = check.hidden = cancel.hidden = true;
    link.removeAttribute("href");
  }
  async function read(url) {
    const controller = new AbortController();
    request = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, {credentials: "same-origin", cache: "no-store", signal: controller.signal});
      if (!response.ok) throw new Error("HTTP");
      return await response.json();
    } finally {
      clearTimeout(timeout);
      if (request === controller) request = null;
    }
  }
  async function poll(run) {
    if (!token || run !== generation) return;
    check.hidden = true;
    check.disabled = true;
    try {
      const result = await read(panel.dataset.statusUrl.replace("TOKEN", encodeURIComponent(token)));
      if (run !== generation) return;
      if (result.ok && result.status === "authenticated") {
        stop();
        status.textContent = "Kirish tasdiqlandi. Davom etilmoqda…";
        // LoginView rechecks the authenticated session and validates `next`.
        window.location.assign(panel.dataset.loginUrl);
      } else if (result.ok && result.status === "pending") {
        timer = setTimeout(() => poll(run), POLL_MS);
      } else if (result.ok && result.status === "used") {
        stop();
        window.location.assign(panel.dataset.loginUrl);
      } else {
        stop();
        status.textContent = "Kirish havolasi eskirgan yoki yopilgan. Qayta boshlang.";
      }
    } catch {
      if (run !== generation) return;
      status.textContent = "Natija aniqlanmadi. Aloqani tekshirib, natijani qayta tekshiring.";
      check.hidden = false;
    } finally { check.disabled = false; }
  }
  start.addEventListener("click", async () => {
    stop();
    const run = generation;
    start.disabled = true;
    start.setAttribute("aria-busy", "true");
    cancel.hidden = false;
    status.textContent = "Kirish havolasi tayyorlanmoqda…";
    try {
      const result = await read(panel.dataset.initUrl);
      if (run !== generation) return;
      if (!result.ok || typeof result.token !== "string") throw new Error("Init");
      const botUrl = new URL(result.bot_link);
      if (botUrl.protocol !== "https:" || botUrl.hostname !== "t.me") throw new Error("Link");
      token = result.token;
      link.href = botUrl.href;
      link.hidden = false;
      start.removeAttribute("aria-busy");
      status.textContent = "Telegramni oching va botdagi kirishni tasdiqlang. Natija shu oynada tekshiriladi.";
      timer = setTimeout(() => poll(run), POLL_MS);
    } catch {
      if (run !== generation) return;
      stop();
      status.textContent = "Havola olinmadi. Aloqani tekshirib, qayta urinib ko‘ring.";
    }
  });
  check.addEventListener("click", () => poll(generation));
  cancel.addEventListener("click", () => {
    stop();
    status.textContent = "Shu oynadagi tekshirish to‘xtatildi. Email va parol bilan kirishingiz mumkin.";
  });
  window.addEventListener("pagehide", stop);
})();
