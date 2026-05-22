(function () {
  function readArgs(el) {
    if (!el.dataset.uiArgs) {
      return [];
    }

    try {
      return JSON.parse(el.dataset.uiArgs);
    } catch (_) {
      return [];
    }
  }

  function buildArgs(el, event) {
    const args = [];
    const pass = (el.dataset.uiPass || "").split(/\s+/).filter(Boolean);

    if (pass.includes("this")) {
      args.push(el);
    }

    if (pass.includes("event")) {
      args.push(event);
    }

    if (pass.includes("parent")) {
      args.push(el.parentElement);
    }

    if (pass.includes("value")) {
      args.push(el.value);
    }

    if (el.dataset.uiTargetArg) {
      args.push(document.querySelector(el.dataset.uiTargetArg));
    }

    return args.concat(readArgs(el));
  }

  function callNamed(el, event, attrName) {
    const fnName = el.dataset[attrName];
    if (!fnName || typeof window[fnName] !== "function") {
      return false;
    }

    window[fnName].apply(el, buildArgs(el, event));
    return true;
  }

  function toggleThemeFallback() {
    const html = document.documentElement;
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);

    try {
      localStorage.setItem("az-theme", next);
    } catch (_) {}
  }

  function runAction(el, event) {
    switch (el.dataset.uiAction) {
      case "theme":
        if (typeof window.toggleTheme === "function") {
          window.toggleTheme();
        } else {
          toggleThemeFallback();
        }
        return true;
      case "toggle-on":
        el.classList.toggle("on");
        return true;
      case "toggle-on-theme":
        el.classList.toggle("on");
        if (typeof window.toggleTheme === "function") {
          window.toggleTheme();
        } else {
          toggleThemeFallback();
        }
        return true;
      case "history-back":
        window.history.back();
        return true;
      case "reload":
        window.location.reload();
        return true;
      case "scroll-bottom":
        window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
        return true;
      default:
        return false;
    }
  }

  function activate(el, event) {
    if (el.dataset.uiHref) {
      window.location.href = el.dataset.uiHref;
      return true;
    }

    if (el.dataset.uiClickTarget) {
      const target = document.querySelector(el.dataset.uiClickTarget);
      if (target) {
        target.click();
      }
      return true;
    }

    if (el.dataset.uiFocusTarget) {
      const target = document.querySelector(el.dataset.uiFocusTarget);
      if (target) {
        target.focus();
      }
      return true;
    }

    if (el.dataset.uiAction && runAction(el, event)) {
      return true;
    }

    return callNamed(el, event, "uiCall");
  }

  function setupSidebarAccordions() {
    document.querySelectorAll(".sidebar-nav").forEach(function (nav) {
      const groups = Array.from(nav.children).filter(function (child) {
        return child.matches && child.matches(".nav-accordion");
      });

      if (groups.length < 2) {
        return;
      }

      const preferred =
        groups.find(function (group) {
          return group.querySelector(".nav-item.active");
        }) ||
        groups.find(function (group) {
          return group.open;
        }) ||
        groups[0];

      groups.forEach(function (group) {
        group.open = group === preferred;
      });

      groups.forEach(function (group) {
        group.addEventListener("toggle", function () {
          if (!group.open) {
            return;
          }

          groups.forEach(function (other) {
            if (other !== group) {
              other.open = false;
            }
          });
        });
      });
    });
  }

  document.addEventListener("click", function (event) {
    const el = event.target.closest("[data-ui-href], [data-ui-click-target], [data-ui-focus-target], [data-ui-action], [data-ui-call]");
    if (!el) {
      return;
    }

    const handled = activate(el, event);
    if (handled && (el.tagName === "A" || el.tagName === "BUTTON")) {
      event.preventDefault();
    }
  });

  document.addEventListener("keydown", function (event) {
    const callEl = event.target.closest("[data-ui-keydown-call]");
    if (callEl) {
      callNamed(callEl, event, "uiKeydownCall");
    }

    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    const el = event.target.closest("[data-ui-href], [data-ui-click-target], [data-ui-focus-target], [data-ui-action], [data-ui-call]");
    if (!el) {
      return;
    }

    if (activate(el, event)) {
      event.preventDefault();
    }
  });

  document.addEventListener("input", function (event) {
    const el = event.target.closest("[data-ui-input-call]");
    if (el) {
      callNamed(el, event, "uiInputCall");
    }
  });

  document.addEventListener("change", function (event) {
    const el = event.target.closest("[data-ui-change-call]");
    if (el) {
      callNamed(el, event, "uiChangeCall");
    }
  });

  setupSidebarAccordions();
})();
