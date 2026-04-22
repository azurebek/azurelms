document.addEventListener("DOMContentLoaded", () => {
  const groups = document.querySelectorAll(".app-sidebar-group");

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
});
