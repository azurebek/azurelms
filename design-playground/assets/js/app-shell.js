document.addEventListener("DOMContentLoaded", () => {
  const groups = document.querySelectorAll(".app-sidebar-group");
  const shell = document.body;
  const layout = document.querySelector(".app-layout");
  const sidebar = document.querySelector(".app-sidebar");
  const topbar = document.querySelector(".app-topbar");
  const term = document.querySelector(".app-term");
  const mobileQuery = window.matchMedia("(max-width: 960px)");

  groups.forEach((group) => {
    const toggle = group.querySelector(".app-group-toggle");
    if (!toggle) return;

    toggle.addEventListener("click", () => {
      const isOpen = group.classList.contains("is-open");

      groups.forEach((item) => {
        item.classList.remove("is-open");
        const itemToggle = item.querySelector(".app-group-toggle");
        if (itemToggle) itemToggle.setAttribute("aria-expanded", "false");
      });

      if (!isOpen) {
        group.classList.add("is-open");
        toggle.setAttribute("aria-expanded", "true");
      }
    });
  });

  if (!layout || !sidebar || !topbar || !term) {
    return;
  }

  const overlay = document.createElement("button");
  overlay.type = "button";
  overlay.className = "app-sidebar-overlay";
  overlay.setAttribute("aria-label", "Navigation panelni yopish");

  const menuButton = document.createElement("button");
  menuButton.type = "button";
  menuButton.className = "app-menu-btn";
  menuButton.setAttribute("aria-label", "Navigation panelni ochish");
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.innerHTML = '<i class="bi bi-list"></i>';

  layout.insertBefore(overlay, layout.firstChild);
  topbar.insertBefore(menuButton, term);

  const setSidebarOpen = (isOpen) => {
    shell.classList.toggle("app-sidebar-open", isOpen);
    menuButton.setAttribute("aria-expanded", String(isOpen));
    menuButton.setAttribute("aria-label", isOpen ? "Navigation panelni yopish" : "Navigation panelni ochish");
  };

  menuButton.addEventListener("click", () => {
    setSidebarOpen(!shell.classList.contains("app-sidebar-open"));
  });

  overlay.addEventListener("click", () => setSidebarOpen(false));

  sidebar.addEventListener("click", (event) => {
    if (event.target.closest("a") && mobileQuery.matches) {
      setSidebarOpen(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setSidebarOpen(false);
    }
  });

  mobileQuery.addEventListener("change", (event) => {
    if (!event.matches) {
      setSidebarOpen(false);
    }
  });
});
