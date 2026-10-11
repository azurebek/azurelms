/* Reveal invalid native controls without submitting, changing or saving values. */
(() => {
  document.addEventListener("invalid", event => {
    const field = event.target;
    if (!(field instanceof Element) || !field.closest(".bo-editor, [data-library-root], [data-editor-root]")) return;
    let disclosure = field.closest("details");
    while (disclosure) {
      disclosure.open = true;
      disclosure = disclosure.parentElement?.closest("details");
    }
  }, true);
})();
