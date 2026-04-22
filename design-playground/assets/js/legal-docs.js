(function () {
  const params = new URLSearchParams(window.location.search);
  const currentPath = window.location.pathname.split("/").pop();
  const legalPagePattern = /^legal-(privacy|terms|faq)\.html$/;

  function isLegalPath(pathname) {
    return legalPagePattern.test(pathname.split("/").pop() || "");
  }

  function normalizeRelative(urlLike) {
    try {
      const absolute = new URL(urlLike, window.location.href);
      const relative = absolute.pathname.split("/").pop() || absolute.pathname;
      return `${relative}${absolute.search}${absolute.hash}`;
    } catch (_error) {
      return urlLike;
    }
  }

  let returnTarget = params.get("return");

  if (!returnTarget && document.referrer) {
    try {
      const ref = new URL(document.referrer);
      if (ref.origin === window.location.origin && !isLegalPath(ref.pathname)) {
        returnTarget = normalizeRelative(ref.href);
      }
    } catch (_error) {
      // Ignore malformed referrers.
    }
  }

  const authFromParam = params.get("auth") === "1";
  const authFromReturn = Boolean(returnTarget && /(?:app-shell|app-course|learning-shell|exam-|messenger-shell)/.test(returnTarget));
  const isAuthedContext = authFromParam || authFromReturn;

  const backButton = document.querySelector("[data-legal-back]");
  const contextBadge = document.querySelector("[data-legal-context]");

  if (contextBadge) {
    contextBadge.textContent = returnTarget
      ? "Return-aware view"
      : isAuthedContext
        ? "App-linked document"
        : "Public document";
  }

  if (backButton) {
    const labelNode = backButton.querySelector("[data-legal-back-label]");
    let target = returnTarget;
    let label = "Oldingi sahifaga qaytish";

    if (!target) {
      target = isAuthedContext ? "./app-shell.html" : "./public-shell.html";
      label = isAuthedContext ? "Dashboardga qaytish" : "Bosh sahifaga qaytish";
    }

    if (labelNode) {
      labelNode.textContent = label;
    }

    backButton.addEventListener("click", function () {
      window.location.href = target;
    });
  }

  document.querySelectorAll("[data-legal-tab]").forEach(function (link) {
    const href = link.getAttribute("href");
    if (!href) return;

    const nextUrl = new URL(href, window.location.href);
    if (isAuthedContext) {
      nextUrl.searchParams.set("auth", "1");
    }
    if (returnTarget) {
      nextUrl.searchParams.set("return", returnTarget);
    }

    link.setAttribute("href", `${nextUrl.pathname.split("/").pop()}${nextUrl.search}${nextUrl.hash}`);

    if (nextUrl.pathname.split("/").pop() === currentPath) {
      link.classList.add("is-active");
      link.setAttribute("aria-current", "page");
    } else {
      link.classList.remove("is-active");
      link.removeAttribute("aria-current");
    }
  });

  document.querySelectorAll("[data-accordion-group]").forEach(function (group) {
    const items = Array.from(group.querySelectorAll("[data-accordion-item]"));
    items.forEach(function (item) {
      item.addEventListener("toggle", function () {
        if (!item.open) return;
        items.forEach(function (other) {
          if (other !== item) {
            other.open = false;
          }
        });
      });
    });
  });
})();
