// Eski (V1 bo'lmagan) kirish va ro'yxat sahifalarida "Telegram orqali davom etish".
// Kontrakt V1 `frontend_v1/js/login.js` bilan bir xil (PUB1.0d): init va consume —
// CSRF'li POST, status — faqat o'qiydigan GET. Login faqat consume'da bo'ladi.
(function () {
  "use strict";
  var button = document.getElementById("telegram-auth-btn");
  if (!button || !button.dataset.initUrl) return;
  var original = button.innerHTML;
  // Zaxira qiymatlar: init javobi server oralig'i va token umrini beradi.
  var POLL_MS = 2000, LIFETIME_S = 300, SLOW_AFTER = 15;
  var EXPIRED = "Eskirdi. Qayta urinib ko'ring.";
  var busy = false, timer = null, token = null, pollMs = POLL_MS, budget = 0, polls = 0;

  function post(url, body) {
    return fetch(url, {
      method: "POST", credentials: "same-origin", cache: "no-store",
      headers: {"X-CSRFToken": button.dataset.csrfToken || ""}, body: body
    });
  }
  function json(response) {
    // 429 serverning umumiy cheklov matnini olib keladi.
    if (!response.ok && response.status !== 429) throw new Error("HTTP " + response.status);
    return response.json();
  }
  function tokenUrl(template) {
    return template.replace("TOKEN", encodeURIComponent(token));
  }
  function sameOrigin(url) {
    try {
      return typeof url === "string" && new URL(url, window.location.href).origin === window.location.origin;
    } catch (error) {
      return false;
    }
  }
  function reset(message) {
    clearTimeout(timer);
    timer = null;
    token = null;
    busy = false;
    button.innerHTML = '<i class="bi bi-exclamation-circle" style="color:var(--red);font-size:16px;"></i> ';
    button.appendChild(document.createTextNode(message));
    button.style.pointerEvents = "auto";
    button.style.opacity = "1";
    setTimeout(function () { if (!busy) button.innerHTML = original; }, 3000);
  }
  function leave(url) {
    token = null;
    clearTimeout(timer);
    button.innerHTML = '<i class="bi bi-check-circle" style="color:#28a745;font-size:16px;"></i> Kirish tasdiqlandi!';
    setTimeout(function () { window.location.href = url; }, 500);
  }
  function schedule() {
    // Foydalanuvchi Telegramda ekan, oraliq asta kattalashadi; token umridan oshmaydi.
    var delay = polls < SLOW_AFTER ? pollMs : pollMs * 2;
    if (budget < delay) {
      reset(EXPIRED);
      return;
    }
    budget -= delay;
    polls += 1;
    timer = setTimeout(poll, delay);
  }
  function consume() {
    return post(tokenUrl(button.dataset.consumeUrl)).then(json).then(function (data) {
      if (!token) return;
      if (data.ok && data.status === "authenticated") {
        leave(sameOrigin(data.redirect_url) ? data.redirect_url : button.dataset.loginUrl);
      } else if (data.ok && data.status === "used") {
        leave(button.dataset.loginUrl);
      } else if (data.ok && data.status === "pending") {
        schedule();
      } else {
        reset(EXPIRED);
      }
    });
  }
  function poll() {
    if (!token) return;
    fetch(tokenUrl(button.dataset.statusUrl), {credentials: "same-origin", cache: "no-store"})
      .then(json)
      .then(function (data) {
        if (!token) return;
        if (data.ok && data.status === "authenticated") return consume();
        if (data.ok && data.status === "pending") return schedule();
        // `used` — shu brauzer allaqachon kirgan (javob yo'qolgan bo'lishi mumkin).
        if (data.ok && data.status === "used") return leave(button.dataset.loginUrl);
        reset(EXPIRED);
      })
      .catch(function () {
        // Natija noaniq: shu tokenning holati keyingi so'rovda qayta tekshiriladi.
        if (token) schedule();
      });
  }
  button.addEventListener("click", function (event) {
    event.preventDefault();
    if (busy) return;
    busy = true;
    button.innerHTML = '<i class="bi bi-arrow-repeat spin-anim" style="font-size:16px;"></i> Kutilmoqda...';
    button.style.pointerEvents = "none";
    button.style.opacity = "0.7";
    var body = new FormData();
    body.append("next", button.dataset.next || "");
    post(button.dataset.initUrl, body).then(json).then(function (data) {
      if (data.status === "throttled") return reset(data.message || "Urinishlar ko'payib ketdi. Birozdan keyin qayta urinib ko'ring.");
      if (!data.ok || typeof data.token !== "string") return reset("Xatolik yuz berdi.");
      var link = new URL(data.bot_link);
      if (link.protocol !== "https:" || link.hostname !== "t.me") return reset("Xatolik yuz berdi.");
      token = data.token;
      pollMs = data.poll_ms > 0 ? data.poll_ms : POLL_MS;
      budget = (data.expires_in > 0 ? data.expires_in : LIFETIME_S) * 1000;
      polls = 0;
      window.open(link.href, "_blank", "noopener");
      schedule();
    }).catch(function () {
      reset("Ulanish xatosi.");
    });
  });
})();
