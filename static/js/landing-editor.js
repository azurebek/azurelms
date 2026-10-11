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
    var picker = document.querySelector("[data-lc-picker]");
    if (!sections.length || !tabs.length) return;

    // Tab rejimini yoqamiz (CSS shu klass bilan bo'limlarni yashiradi).
    form.classList.add("lc-tabbed");

    function activate(key) {
      if (!sections.some(function (section) { return section.getAttribute("data-lc-section") === key; })) return;
      form.classList.add("lc-tabbed");
      sections.forEach(function (section) {
        section.classList.toggle("is-active", section.getAttribute("data-lc-section") === key);
      });
      tabs.forEach(function (tab) {
        tab.classList.toggle("is-active", tab.getAttribute("data-lc-target") === key);
        if (tab.getAttribute("data-lc-target") === key) tab.setAttribute("aria-current", "true");
        else tab.removeAttribute("aria-current");
      });
      if (picker) picker.value = key;
      if (history.replaceState) {
        try { history.replaceState(history.state, "", "#lc-" + key); } catch (_) { /* Navigation still works if history is unavailable. */ }
      }
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        activate(tab.getAttribute("data-lc-target"));
      });
    });
    if (picker) picker.addEventListener("change", function () { activate(picker.value); });

    // Native validation checks every field, including inactive sections. Reveal
    // all sections during that pass so even multiple invalid fields can receive
    // browser focus. The next explicit section choice restores the compact view.
    var invalidPass = false;
    form.addEventListener("invalid", function (event) {
      var section = event.target.closest("[data-lc-section]");
      if (!invalidPass) {
        invalidPass = true;
        if (section) activate(section.getAttribute("data-lc-section"));
        window.setTimeout(function () { invalidPass = false; }, 0);
      }
      form.classList.remove("lc-tabbed");
    }, true);

    // A returned field error takes priority over the previously selected hash.
    var keys = sections.map(function (s) { return s.getAttribute("data-lc-section"); });
    var initial = null;

    var hash = (window.location.hash || "").replace(/^#lc-/, "");
    var errored = sections.filter(function (s) { return s.getAttribute("data-lc-error") === "1"; });
    if (errored.length) initial = errored[0].getAttribute("data-lc-section");
    if (!initial && hash && keys.indexOf(hash) !== -1) initial = hash;
    if (!initial) initial = keys[0];

    activate(initial);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
