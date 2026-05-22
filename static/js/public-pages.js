(function () {
  "use strict";

  document.querySelectorAll("[data-auto-submit]").forEach(function (field) {
    field.addEventListener("change", function () {
      if (field.form) {
        field.form.submit();
      }
    });
  });

  const courseFilters = document.getElementById("courseFilters");
  if (courseFilters) {
    courseFilters.querySelectorAll("input[name='level']").forEach(function (input) {
      input.addEventListener("change", function () {
        courseFilters.submit();
      });
    });
  }

  document.querySelectorAll(".tab-btn[data-tab]").forEach(function (button) {
    button.addEventListener("click", function () {
      const target = button.dataset.tab;
      const tabRoot = button.closest(".tabs");
      if (tabRoot) {
        tabRoot.querySelectorAll(".tab-btn").forEach(function (item) {
          item.classList.toggle("active", item === button);
        });
      }
      document.querySelectorAll(".tab-panel").forEach(function (panel) {
        panel.classList.toggle("active", panel.id === "tab-" + target);
      });
    });
  });

  document.querySelectorAll(".section-head").forEach(function (button) {
    button.addEventListener("click", function () {
      const group = button.closest(".section-group");
      if (group) {
        group.classList.toggle("open");
      }
    });
  });

  document.querySelectorAll(".faq-q").forEach(function (button) {
    button.addEventListener("click", function () {
      const item = button.closest(".faq-item");
      if (item) {
        item.classList.toggle("open");
      }
    });
  });

  document.querySelectorAll("[data-billing-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      const group = button.closest(".billing-toggle");
      if (!group) {
        return;
      }
      group.querySelectorAll("[data-billing-toggle]").forEach(function (item) {
        item.classList.toggle("active", item === button);
      });
      document.querySelectorAll(".plan-price-period").forEach(function (period) {
        period.textContent = button.dataset.billingToggle === "yearly" ? "so'm/yil" : "so'm/oy";
      });
    });
  });
})();
