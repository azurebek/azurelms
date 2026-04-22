document.querySelectorAll("[data-toggle-panel]").forEach((button) => {
  button.addEventListener("click", () => {
    const panelId = button.getAttribute("data-toggle-panel");
    const panel = document.getElementById(panelId);
    if (!panel) return;

    const nextOpen = !panel.classList.contains("is-open");
    panel.classList.toggle("is-open", nextOpen);
    button.setAttribute("aria-expanded", String(nextOpen));
  });
});

document.querySelectorAll("[data-close-panel]").forEach((button) => {
  button.addEventListener("click", () => {
    const panelId = button.getAttribute("data-close-panel");
    const panel = document.getElementById(panelId);
    if (!panel) return;

    panel.classList.remove("is-open");

    const launcher = document.querySelector(`[data-toggle-panel="${panelId}"]`);
    if (launcher) {
      launcher.setAttribute("aria-expanded", "false");
    }
  });
});
