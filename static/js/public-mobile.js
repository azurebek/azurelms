(function () {
  const mobileQuery = window.matchMedia("(max-width: 520px)");
  const header = document.querySelector(".public-header");
  const button = document.querySelector(".public-mobile-menu");
  const nav = document.querySelector(".public-main-nav");
  const actions = document.querySelector(".public-header-actions");

  if (!header || !button || !nav) {
    return;
  }

  const panel = document.createElement("div");
  const panelId = "public-mobile-panel";
  panel.className = "public-mobile-panel";
  panel.id = panelId;
  panel.hidden = true;

  const panelInner = document.createElement("div");
  panelInner.className = "public-wrap public-mobile-panel-inner";

  const panelNav = document.createElement("nav");
  panelNav.className = "public-mobile-panel-nav";
  panelNav.setAttribute("aria-label", "Mobile navigation");

  nav.querySelectorAll("a").forEach((link) => {
    panelNav.appendChild(link.cloneNode(true));
  });

  panelInner.appendChild(panelNav);

  if (actions) {
    const panelActions = document.createElement("div");
    panelActions.className = "public-mobile-panel-actions";

    actions.querySelectorAll("a, form").forEach((link) => {
      panelActions.appendChild(link.cloneNode(true));
    });

    panelInner.appendChild(panelActions);
  }

  panel.appendChild(panelInner);
  header.insertAdjacentElement("afterend", panel);

  button.setAttribute("aria-controls", panelId);
  button.setAttribute("aria-expanded", "false");

  const setOpen = (isOpen) => {
    panel.hidden = !isOpen;
    button.classList.toggle("is-open", isOpen);
    button.setAttribute("aria-expanded", String(isOpen));
  };

  const toggle = () => {
    setOpen(panel.hidden);
  };

  button.addEventListener("click", toggle);

  panel.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      setOpen(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setOpen(false);
    }
  });

  document.addEventListener("click", (event) => {
    if (panel.hidden) {
      return;
    }

    const target = event.target;
    if (panel.contains(target) || button.contains(target)) {
      return;
    }

    setOpen(false);
  });

  const setupFooterAccordion = () => {
    const footerGroups = Array.from(document.querySelectorAll(".public-footer-grid > div"));

    footerGroups.forEach((group, index) => {
      if (group.querySelector(".public-footer-toggle")) {
        return;
      }

      const heading = Array.from(group.children).find((child) => child.tagName === "H4");

      if (!heading) {
        return;
      }

      group.classList.add("public-footer-group");

      const toggle = document.createElement("button");
      const panel = document.createElement("div");
      const panelId = `public-footer-panel-${index}`;

      toggle.type = "button";
      toggle.className = "public-footer-toggle";
      toggle.textContent = heading.textContent.trim();
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-controls", panelId);

      panel.className = "public-footer-panel";
      panel.id = panelId;

      const contentNodes = [];
      let sibling = heading.nextSibling;

      while (sibling) {
        const nextSibling = sibling.nextSibling;
        contentNodes.push(sibling);
        sibling = nextSibling;
      }

      contentNodes.forEach((node) => {
        panel.appendChild(node);
      });

      heading.insertAdjacentElement("afterend", toggle);
      toggle.insertAdjacentElement("afterend", panel);

      toggle.addEventListener("click", () => {
        const shouldOpen = toggle.getAttribute("aria-expanded") !== "true";

        footerGroups.forEach((otherGroup) => {
          const otherToggle = otherGroup.querySelector(".public-footer-toggle");
          const otherPanel = otherGroup.querySelector(".public-footer-panel");

          if (!otherToggle || !otherPanel) {
            return;
          }

          otherToggle.setAttribute("aria-expanded", "false");
          if (mobileQuery.matches) {
            otherPanel.hidden = true;
          }
        });

        if (shouldOpen) {
          toggle.setAttribute("aria-expanded", "true");
          panel.hidden = false;
        }
      });
    });
  };

  const syncFooterAccordion = () => {
    document.querySelectorAll(".public-footer-group").forEach((group) => {
      const heading = group.querySelector("h4");
      const toggle = group.querySelector(".public-footer-toggle");
      const panel = group.querySelector(".public-footer-panel");

      if (!toggle || !panel) {
        return;
      }

      if (mobileQuery.matches) {
        if (heading) {
          heading.setAttribute("aria-hidden", "true");
        }
        panel.hidden = toggle.getAttribute("aria-expanded") !== "true";
        return;
      }

      if (heading) {
        heading.removeAttribute("aria-hidden");
      }
      panel.hidden = false;
      toggle.setAttribute("aria-expanded", "false");
    });
  };

  setupFooterAccordion();
  syncFooterAccordion();

  mobileQuery.addEventListener("change", (event) => {
    if (!event.matches) {
      setOpen(false);
    }

    syncFooterAccordion();
  });
})();
