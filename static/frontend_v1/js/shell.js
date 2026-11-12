(() => {
  "use strict";

  const hasWindow = typeof window !== "undefined";
  if (hasWindow && (window.name === "tgmini" || new URLSearchParams(window.location.search).has("mini"))) {
    document.documentElement.setAttribute("data-mini", "");
  }

  const drawer = document.querySelector("#nav-dialog");
  const opener = document.querySelector("[data-nav-open]");
  if (drawer && opener) {
    opener.addEventListener("click", () => {
      if (!drawer.open) drawer.showModal();
      opener.setAttribute("aria-expanded", "true");
    });
    drawer.querySelector("[data-nav-close]").addEventListener("click", () => drawer.close());
    drawer.addEventListener("close", () => {
      opener.setAttribute("aria-expanded", "false");
      if (opener.getClientRects().length) opener.focus();
    });
    drawer.addEventListener("click", (event) => {
      if (event.target !== drawer) return;
      const rect = drawer.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) drawer.close();
    });
    window.matchMedia("(min-width: 1024px)").addEventListener("change", (event) => {
      if (event.matches && drawer.open) drawer.close();
    });
  }

  const popovers = [...document.querySelectorAll("[data-calm-popover]")];
  const closePopover = (popover, restoreFocus = false) => {
    if (!popover?.open) return;
    popover.open = false;
    if (restoreFocus) popover.querySelector("summary")?.focus();
  };
  const closePopovers = (except = null) => {
    popovers.forEach((popover) => {
      if (popover !== except) closePopover(popover);
    });
  };
  popovers.forEach((popover) => popover.addEventListener("toggle", () => {
    if (popover.open) closePopovers(popover);
  }));
  document.addEventListener("click", (event) => {
    if (!event.target.closest?.("[data-calm-popover]")) closePopovers();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const calmPopover = event.target.closest?.("[data-calm-popover][open]") || popovers.find((popover) => popover.open);
    if (calmPopover) {
      event.preventDefault();
      closePopover(calmPopover, true);
      return;
    }
    const account = event.target.closest(".v1-account[open]");
    if (account) {
      event.preventDefault();
      account.open = false;
      account.querySelector("summary").focus();
    }
  });
  if (hasWindow) window.addEventListener("pageshow", () => closePopovers());
  document.querySelector("[data-form-errors]")?.focus();
  document.querySelectorAll('[data-v1-logout]').forEach(form => form.addEventListener('submit', () => {
    try {
      for (let i = sessionStorage.length - 1; i >= 0; i--) {
        const key = sessionStorage.key(i);
        if (key.startsWith('azurelms:v1:practice:') || key.startsWith('azurelms:v1:messenger:') || key.startsWith('azurelms:v1:exam:')) sessionStorage.removeItem(key);
      }
    } catch { /* Storage denied: native POST logout still works. */ }
  }));
})();
