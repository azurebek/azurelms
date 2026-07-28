// SIT prototip — oq/qora (light/dark) mavzu toggle.
// Saqlangan tanlov media query'dan ustun turadi; localStorage'da saqlanadi.
(function () {
  "use strict";
  var KEY = "sit-theme";
  var root = document.documentElement;

  // FOUC'ni kamaytirish uchun saqlangan mavzuni darhol qo'llaymiz.
  try {
    var saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  } catch (e) {}

  function current() {
    var attr = root.getAttribute("data-theme");
    if (attr) return attr;
    return (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
  }

  function setIcons(theme) {
    var cls = theme === "dark" ? "bi bi-sun" : "bi bi-moon";
    document.querySelectorAll(".theme-toggle i").forEach(function (ic) { ic.className = cls; });
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    try { localStorage.setItem(KEY, theme); } catch (e) {}
    setIcons(theme);
  }

  function wire() {
    setIcons(current());
    document.querySelectorAll(".theme-toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        apply(current() === "dark" ? "light" : "dark");
      });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();
