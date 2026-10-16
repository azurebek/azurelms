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
  let timer, token, request, generation = 0, pollMs = 0, budget = 0, polls = 0;
  // Fallback only: init returns the server's poll interval and token lifetime,
  // and the server alone decides expiry.
  const POLL_MS = 2000, LIFETIME_S = 300, SLOW_AFTER = 15;
  const CLOSED = "Kirish havolasi eskirgan yoki yopilgan. Qayta boshlang.";
  const tokenUrl = template => template.replace("TOKEN", encodeURIComponent(token));
  const positive = (value, fallback) => Number.isFinite(value) && value > 0 ? value : fallback;
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
  // Status is a read-only GET; init, consume and cancel change state, so they are CSRF-checked POSTs.
  async function send(url, method = "GET") {
    const controller = new AbortController();
    request = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    const options = {method, credentials: "same-origin", cache: "no-store", signal: controller.signal};
    if (method === "POST") options.headers = {"X-CSRFToken": panel.dataset.csrfToken || ""};
    try {
      const response = await fetch(url, options);
      // 429 carries the server's generic throttle copy.
      if (!response.ok && response.status !== 429) throw new Error("HTTP");
      return await response.json();
    } finally {
      clearTimeout(timeout);
      if (request === controller) request = null;
    }
  }
  function leave() {
    stop();
    status.textContent = "Kirish tasdiqlandi. Davom etilmoqda…";
    // LoginView rechecks the authenticated session and validates `next`.
    window.dispatchEvent(new Event("frontend-v1:auth-redirect"));
    window.location.assign(panel.dataset.loginUrl);
  }
  function schedule(run) {
    // Gentle backoff while the user is still in Telegram; never past the token lifetime.
    const delay = polls < SLOW_AFTER ? pollMs : pollMs * 2;
    if (budget < delay) {
      stop();
      status.textContent = CLOSED;
      return;
    }
    budget -= delay;
    polls += 1;
    timer = setTimeout(() => poll(run), delay);
  }
  async function poll(run) {
    if (!token || run !== generation) return;
    check.hidden = true;
    check.disabled = true;
    try {
      let result = await send(tokenUrl(panel.dataset.statusUrl));
      if (run !== generation) return;
      if (result.ok && result.status === "authenticated") {
        // Polling never logs in: only this explicit one-time POST does.
        result = await send(tokenUrl(panel.dataset.consumeUrl), "POST");
        if (run !== generation) return;
      }
      if (result.ok && (result.status === "authenticated" || result.status === "used")) {
        leave();
      } else if (result.ok && result.status === "pending") {
        schedule(run);
      } else {
        stop();
        status.textContent = CLOSED;
      }
    } catch {
      if (run !== generation) return;
      // The same token is checked again on request; `used` then means this browser already signed in.
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
      const result = await send(panel.dataset.initUrl, "POST");
      if (run !== generation) return;
      if (result.status === "throttled") {
        stop();
        status.textContent = result.message || "Urinishlar ko‘payib ketdi. Birozdan keyin qayta urinib ko‘ring.";
        return;
      }
      if (!result.ok || typeof result.token !== "string") throw new Error("Init");
      const botUrl = new URL(result.bot_link);
      if (botUrl.protocol !== "https:" || botUrl.hostname !== "t.me") throw new Error("Link");
      token = result.token;
      pollMs = positive(result.poll_ms, POLL_MS);
      budget = positive(result.expires_in, LIFETIME_S) * 1000;
      polls = 0;
      link.href = botUrl.href;
      link.hidden = false;
      start.removeAttribute("aria-busy");
      status.textContent = "Telegramni oching va botdagi kirishni tasdiqlang. Natija shu oynada tekshiriladi.";
      schedule(run);
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
    // Closes this browser's flow on the server too; best effort, nothing waits on it.
    fetch(panel.dataset.cancelUrl, {
      method: "POST", credentials: "same-origin", keepalive: true,
      headers: {"X-CSRFToken": panel.dataset.csrfToken || ""},
    }).catch(() => {});
  });
  window.addEventListener("pagehide", stop);
})();
