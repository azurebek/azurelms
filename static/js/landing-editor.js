// Landing editor — o'ng TOC'dan bo'lim tanlash (tab rejimi).
// Barcha maydonlar bitta formada qoladi (bitta "Saqlash" hammasini yuboradi);
// bu skript faqat aktiv bo'limni ko'rsatadi, qolganini yashiradi.
(function () {
  "use strict";

  function init() {
    var form = document.querySelector(".lc-form");
    if (!form) return;

    var sections = Array.prototype.slice.call(document.querySelectorAll("[data-lc-section]"));
    var tabs = Array.prototype.slice.call(document.querySelectorAll(".lc-toc-item[data-lc-target]"));
    if (!sections.length || !tabs.length) return;

    // Tab rejimini yoqamiz (CSS shu klass bilan bo'limlarni yashiradi).
    form.classList.add("lc-tabbed");

    function activate(key) {
      sections.forEach(function (section) {
        section.classList.toggle("is-active", section.getAttribute("data-lc-section") === key);
      });
      tabs.forEach(function (tab) {
        tab.classList.toggle("is-active", tab.getAttribute("data-lc-target") === key);
      });
      if (history.replaceState) {
        history.replaceState(null, "", "#lc-" + key);
      }
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        activate(tab.getAttribute("data-lc-target"));
      });
    });

    // Boshlang'ich bo'lim: (1) URL hash, (2) birinchi xatoli bo'lim, (3) birinchi bo'lim.
    var keys = sections.map(function (s) { return s.getAttribute("data-lc-section"); });
    var initial = null;

    var hash = (window.location.hash || "").replace(/^#lc-/, "");
    if (hash && keys.indexOf(hash) !== -1) {
      initial = hash;
    }
    if (!initial) {
      var errored = sections.filter(function (s) { return s.getAttribute("data-lc-error") === "1"; });
      if (errored.length) initial = errored[0].getAttribute("data-lc-section");
    }
    if (!initial) initial = keys[0];

    activate(initial);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
