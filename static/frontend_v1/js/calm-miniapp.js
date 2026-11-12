(() => {
  "use strict";

  const root = document.querySelector("[data-calm-miniapp]");
  if (!root) return;

  const frame = root.querySelector("[data-mini-frame]");
  const back = root.querySelector("[data-mini-back]");
  const views = new Map([...root.querySelectorAll("[data-mini-view]")].map(node => [node.dataset.miniView, node]));
  const tabs = [...root.querySelectorAll("[data-mini-tab]")];
  const telegram = window.Telegram?.WebApp;
  const inTelegram = Boolean(telegram?.initData);
  let currentView = root.dataset.initialView || "home";
  let returnView = "home";
  let currentTab = root.dataset.initialTab || "home";

  const syncTelegramBack = () => {
    try {
      if (!inTelegram || !telegram?.BackButton || !telegram.isVersionAtLeast?.("6.1")) return;
      if (currentView === "home") telegram.BackButton.hide();
      else telegram.BackButton.show();
    } catch { /* Eski Telegram versiyasida sahifa oddiy web sifatida qoladi. */ }
  };

  const setCurrentTab = tab => {
    currentTab = tab || "";
    tabs.forEach(item => {
      if (item.dataset.miniTab === currentTab) item.setAttribute("aria-current", "page");
      else item.removeAttribute("aria-current");
    });
  };

  const showView = (name, tab = name) => {
    currentView = views.has(name) ? name : "home";
    views.forEach((node, key) => { node.hidden = key !== currentView; });
    back.textContent = currentView === "home" ? "Yopish" : "‹ Orqaga";
    setCurrentTab(tab);
    syncTelegramBack();
  };

  const openFrame = link => {
    const url = link.getAttribute("href");
    if (!url || !frame) return;
    returnView = link.dataset.miniReturn || (currentView === "menu" ? "menu" : "home");
    frame.title = link.dataset.frameTitle || "Platforma sahifasi";
    if (frame.getAttribute("src") !== url) frame.setAttribute("src", url);
    showView("frame", link.dataset.miniTab || "");
  };

  const goBack = () => {
    if (currentView === "home") {
      try {
        if (inTelegram && telegram?.close) telegram.close();
        else if (window.history.length > 1) window.history.back();
      } catch { /* Yopish imkoniyati bo'lmasa bosh sahifa ochiq qoladi. */ }
      return;
    }
    showView(returnView, returnView);
  };

  root.addEventListener("click", event => {
    const frameLink = event.target.closest("[data-mini-open]");
    if (frameLink) {
      event.preventDefault();
      openFrame(frameLink);
      return;
    }
    const menuLink = event.target.closest("[data-mini-menu]");
    if (menuLink) {
      event.preventDefault();
      returnView = "home";
      showView("menu", "menu");
      return;
    }
    const homeLink = event.target.closest("[data-mini-home]");
    if (homeLink) {
      event.preventDefault();
      returnView = "home";
      showView("home", "home");
    }
  });
  back?.addEventListener("click", goBack);

  try {
    if (inTelegram) telegram.ready();
    if (inTelegram) telegram.expand();
    if (inTelegram && (telegram?.colorScheme === "dark" || telegram?.colorScheme === "light")) {
      document.documentElement.dataset.theme = telegram.colorScheme;
    }
    if (inTelegram) telegram?.onEvent?.("themeChanged", () => {
      if (telegram.colorScheme === "dark" || telegram.colorScheme === "light") {
        document.documentElement.dataset.theme = telegram.colorScheme;
      }
    });
    if (inTelegram && telegram?.isVersionAtLeast?.("6.1")) {
      if (telegram?.BackButton?.onClick) telegram.BackButton.onClick(goBack);
      else telegram?.onEvent?.("backButtonClicked", goBack);
    }
  } catch { /* Telegram SDK bo'lmagan lokal ko'rikda native havolalar qoladi. */ }

  showView(currentView, currentTab);
})();
