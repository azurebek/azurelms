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

  // Telegram orqali kirish (PUB1.0d kontrakti, PUB1.4e UX) — V1 va legacy sahifalar
  // bitta belgilashni (`components/telegram_auth_panel.html`) ishlatadi.
  const panel = document.querySelector("[data-telegram-auth]");
  if (!panel) return;
  const part = name => panel.querySelector(`[data-telegram-${name}]`);
  const start = part("start"), waiting = part("waiting"), link = part("link"), code = part("code");
  const countdown = part("countdown"), status = part("status"), check = part("check"), cancel = part("cancel");
  const qrBox = part("qr-box"), qr = part("qr");
  // JS'siz panel yashirin turadi (o'lik tugma qolmasin); skript ishlasa ko'rinadi.
  panel.hidden = false;
  let timer = null, token, request, generation = 0, pollMs = 0, budget = 0, polls = 0, warned = false;
  // Fallback only: init returns the server's poll interval and token lifetime,
  // and the server alone decides expiry.
  const POLL_MS = 2000, LIFETIME_S = 300, SLOW_AFTER = 15, LAST_MINUTE_MS = 60000;
  const COPY = {
    preparing: "Kirish havolasi tayyorlanmoqda…",
    waiting: "Telegramda tasdiqlang. Natija shu sahifada o‘zi tekshiriladi.",
    closed: "Kirish havolasi eskirgan yoki yopilgan. Qayta boshlang.",
    declined: "Telegramda kirish tasdiqlanmadi — sababi botdagi xabarda. Email va parol bilan kiring yoki qaytadan boshlang.",
    uncertain: "Natija aniqlanmadi. Aloqani tekshirib, «Tasdiqladim — tekshirish»ni bosing.",
    initFailed: "Havola olinmadi. Aloqani tekshirib, qayta urinib ko‘ring.",
    cancelled: "To‘xtatildi. Email va parol bilan kirishingiz yoki qaytadan boshlashingiz mumkin.",
    throttled: "Urinishlar ko‘payib ketdi. Birozdan keyin qayta urinib ko‘ring.",
    success: "Kirish tasdiqlandi. Davom etilmoqda…",
    lastMinute: "Havola muddati tugashiga 1 daqiqadan kam qoldi.",
  };
  const tokenUrl = template => template.replace("TOKEN", encodeURIComponent(token));
  const positive = (value, fallback) => Number.isFinite(value) && value > 0 ? value : fallback;
  // Countdown har so'rovda daqiqalarda yangilanadi: soniyama-soniya o'zgaruvchi matn
  // ekran o'qigichni bezovta qiladi va alohida taymer talab qiladi.
  const remainingText = ms => ms < LAST_MINUTE_MS
    ? "Havola 1 daqiqadan kam amal qiladi."
    : `Havola yana taxminan ${Math.ceil(ms / 60000)} daqiqa amal qiladi.`;
  // Jonli hudud faqat holat o'zgarganda gapiradi — bir xil matn qayta o'qilmaydi.
  function say(text) {
    if (status.textContent !== text) status.textContent = text;
  }
  function stop() {
    generation += 1;
    clearTimeout(timer);
    timer = null;
    request?.abort();
    request = null;
    token = null;
    start.disabled = false;
    start.hidden = false;
    start.removeAttribute("aria-busy");
    waiting.hidden = true;
    link.removeAttribute("href");
    code.textContent = countdown.textContent = "";
    if (qrBox) qrBox.hidden = true;
    qr?.removeAttribute("src");
  }
  function finish(text) {
    stop();
    say(text);
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
    start.disabled = start.hidden = true;
    say(COPY.success);
    // LoginView rechecks the authenticated session and validates `next`.
    window.dispatchEvent(new Event("frontend-v1:auth-redirect"));
    window.location.assign(panel.dataset.loginUrl);
  }
  function schedule(run) {
    // Gentle backoff while the user is still in Telegram; never past the token lifetime.
    const delay = polls < SLOW_AFTER ? pollMs : pollMs * 2;
    if (budget < delay) {
      finish(COPY.closed);
      return;
    }
    budget -= delay;
    polls += 1;
    countdown.textContent = remainingText(budget);
    if (budget < LAST_MINUTE_MS && !warned) {
      warned = true;
      say(COPY.lastMinute);
    }
    timer = setTimeout(() => { timer = null; return poll(run); }, delay);
  }
  async function poll(run) {
    if (!token || run !== generation) return;
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
        if (!warned) say(COPY.waiting);
        schedule(run);
      } else {
        finish(result.ok && result.status === "declined" ? COPY.declined : COPY.closed);
      }
    } catch {
      if (run !== generation) return;
      // The same token is checked again on request; `used` then means this browser already signed in.
      say(COPY.uncertain);
    } finally { check.disabled = false; }
  }
  start.addEventListener("click", async () => {
    stop();
    const run = generation;
    start.disabled = true;
    start.setAttribute("aria-busy", "true");
    say(COPY.preparing);
    try {
      const result = await send(panel.dataset.initUrl, "POST");
      if (run !== generation) return;
      if (result.status === "throttled") {
        finish(result.message || COPY.throttled);
        return;
      }
      if (!result.ok || typeof result.token !== "string") throw new Error("Init");
      const botUrl = new URL(result.bot_link);
      if (botUrl.protocol !== "https:" || botUrl.hostname !== "t.me") throw new Error("Link");
      token = result.token;
      pollMs = positive(result.poll_ms, POLL_MS);
      budget = positive(result.expires_in, LIFETIME_S) * 1000;
      polls = 0;
      warned = false;
      link.href = botUrl.href;
      // Kod faqat server bergan 3 raqam bo'lsa ko'rsatiladi.
      code.textContent = /^\d{3}$/.test(String(result.code ?? "")) ? result.code : "";
      // QR faqat server bergan SVG `data:` rasm bo'lsa — tashqi manzil yuklanmaydi.
      const qrSrc = String(result.qr ?? "");
      if (qr && qrBox && qrSrc.startsWith("data:image/svg+xml")) {
        qr.src = qrSrc;
        qrBox.hidden = false;
      }
      start.hidden = true;
      start.removeAttribute("aria-busy");
      waiting.hidden = false;
      say(COPY.waiting);
      schedule(run);
    } catch {
      if (run !== generation) return;
      finish(COPY.initFailed);
    }
  });
  // Tekshiruvni darhol boshlaydi; navbatdagi rejalashtirilgan so'rov bekor qilinadi.
  function pollNow() {
    if (!token || request) return undefined;
    clearTimeout(timer);
    timer = null;
    return poll(generation);
  }
  check.addEventListener("click", pollNow);
  cancel.addEventListener("click", () => {
    finish(COPY.cancelled);
    // Closes this browser's flow on the server too; best effort, nothing waits on it.
    fetch(panel.dataset.cancelUrl, {
      method: "POST", credentials: "same-origin", keepalive: true,
      headers: {"X-CSRFToken": panel.dataset.csrfToken || ""},
    }).catch(() => {});
  });
  // Telefonda odam Telegramdan qaytgan zahoti natija tekshiriladi — navbatdagi
  // so'rovni yoki uxlab qolgan fon taymerini kutmasdan.
  document.addEventListener?.("visibilitychange", () => document.visibilityState === "visible" ? pollNow() : undefined);
  window.addEventListener("pagehide", stop);
})();
