(() => {
  "use strict";
  const key = "az-v2-theme";
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const read = () => {
    try { const value = localStorage.getItem(key); return ["light", "dark"].includes(value) ? value : null; }
    catch { return null; }
  };
  let preference = read();
  function apply() {
    const dark = (preference || (system.matches ? "dark" : "light")) === "dark";
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    document.querySelectorAll('[data-action="theme.toggle"]').forEach((button) => {
      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute("aria-label", dark ? "Yorug‘ temaga o‘tish" : "Qorong‘i temaga o‘tish");
    });
  }
  apply();
  document.addEventListener("DOMContentLoaded", apply, {once: true});
  document.addEventListener("click", (event) => {
    if (!event.target.closest('[data-action="theme.toggle"]')) return;
    preference = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem(key, preference); } catch { /* In-memory preference still works. */ }
    apply();
  });
  system.addEventListener("change", () => { if (!preference) apply(); });
  window.addEventListener("storage", (event) => {
    if (event.key === key) { preference = read(); apply(); }
  });
})();
