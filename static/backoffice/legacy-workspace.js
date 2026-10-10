/* Do not intercept submission or alter values. Native validation must be able
   to focus a required field even when its optional section was collapsed. */
(() => {
  document.addEventListener("invalid", (event) => {
    const field = event.target;
    if (!(field instanceof Element) || !field.closest("[data-workspace-legacy]")) return;
    let section = field.closest("details");
    while (section) {
      section.open = true;
      section = section.parentElement?.closest("details");
    }
  }, true);
})();
