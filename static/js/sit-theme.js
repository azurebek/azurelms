(function () {
  "use strict";
  var KEY = "sit-theme";
  var root = document.documentElement;

  try {
    var saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  } catch (error) {}

  function current() {
    var attr = root.getAttribute("data-theme");
    if (attr) return attr;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function setIcons(theme) {
    var iconClass = theme === "dark" ? "bi bi-sun" : "bi bi-moon";
    document.querySelectorAll(".theme-toggle i").forEach(function (icon) {
      icon.className = iconClass;
    });
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(KEY, theme);
    } catch (error) {}
    setIcons(theme);
  }

  function wire() {
    setIcons(current());
    document.querySelectorAll(".theme-toggle").forEach(function (button) {
      button.addEventListener("click", function () {
        apply(current() === "dark" ? "light" : "dark");
      });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();
