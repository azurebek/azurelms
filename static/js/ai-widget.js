/* AzureAI floating widget — toggle, lazy room creation, send/receive.
   Xona FAQAT birinchi xabar yuborilganda (server tomonda) yaratiladi.
   Bo'sh ochib-yopilsa hech narsa saqlanmaydi. */
(function () {
  "use strict";

  const widget = document.getElementById("azaiWidget");
  if (!widget) return;
  // Skript ikki marta ulansa ham listener'lar bir marta bog'lanadi
  // (dublikat toggle panelni ochib-darhol yopadi, submit ikki marta ketadi).
  if (widget.dataset.azaiInit) return;
  widget.dataset.azaiInit = "1";

  const launcher = document.getElementById("azaiLauncher");
  const panel = document.getElementById("azaiPanel");
  const closeBtn = document.getElementById("azaiClose");
  const expandBtn = document.getElementById("azaiExpand");
  const messages = document.getElementById("azaiMessages");
  const form = document.getElementById("azaiCompose");
  const input = document.getElementById("azaiInput");
  const sendBtn = document.getElementById("azaiSend");

  const endpoint = widget.dataset.endpoint;
  const csrfInput = widget.querySelector('[name="csrfmiddlewaretoken"]');
  const csrfToken = csrfInput ? csrfInput.value : "";

  // Suhbat holati — sahifa hayoti davomida saqlanadi.
  let roomId = null;
  let sending = false;

  // ---- Panelni ochish/yopish ----
  function openPanel() {
    widget.classList.add("is-open");
    launcher.setAttribute("aria-expanded", "true");
    panel.setAttribute("aria-hidden", "false");
    window.setTimeout(() => input && input.focus(), 220);
  }
  function closePanel() {
    widget.classList.remove("is-open");
    launcher.setAttribute("aria-expanded", "false");
    panel.setAttribute("aria-hidden", "true");
  }
  function togglePanel() {
    widget.classList.contains("is-open") ? closePanel() : openPanel();
  }

  launcher.addEventListener("click", togglePanel);
  closeBtn.addEventListener("click", closePanel);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && widget.classList.contains("is-open")) closePanel();
  });

  // ---- Expand → to'liq messenger suhbatiga o'tish ----
  expandBtn.addEventListener("click", (e) => {
    e.preventDefault();
    if (roomId) window.location.href = "/messenger/ai/" + roomId + "/";
  });

  // ---- Textarea auto-resize ----
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 110) + "px";
  });
  // Enter yuboradi, Shift+Enter yangi qator
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  // ---- Xabar bubblelari ----
  function clearWelcome() {
    const welcome = messages.querySelector(".azai-welcome");
    if (welcome) welcome.remove();
  }
  function addBubble(text, variant) {
    clearWelcome();
    const el = document.createElement("div");
    el.className = "azai-msg azai-msg--" + variant;
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }
  function showTyping() {
    clearWelcome();
    const el = document.createElement("div");
    el.className = "azai-typing";
    el.id = "azaiTyping";
    el.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }
  function hideTyping() {
    const t = document.getElementById("azaiTyping");
    if (t) t.remove();
  }

  // ---- Xabar yuborish ----
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text || sending) return;

    sending = true;
    sendBtn.disabled = true;
    addBubble(text, "user");
    input.value = "";
    input.style.height = "auto";
    showTyping();

    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ message: text, room_id: roomId }),
      });
      const data = await resp.json();
      hideTyping();

      if (resp.ok && data.status === "success") {
        roomId = data.room_id; // birinchi javobdan keyin suhbat davom etadi
        addBubble(data.ai_message.text, "ai");
        // Endi to'liq suhbatga o'tish mumkin
        if (expandBtn.hidden) expandBtn.hidden = false;
      } else {
        addBubble(data.message || "Xatolik yuz berdi. Qayta urinib ko'ring.", "error");
      }
    } catch (err) {
      hideTyping();
      addBubble("Ulanishda xatolik. Internetni tekshirib, qayta urinib ko'ring.", "error");
    } finally {
      sending = false;
      sendBtn.disabled = false;
      input.focus();
    }
  });
})();
