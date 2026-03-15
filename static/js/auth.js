document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      const selector = button.getAttribute("data-password-toggle");
      const input = document.querySelector(selector);
      if (!input) {
        return;
      }

      const nextType = input.getAttribute("type") === "password" ? "text" : "password";
      input.setAttribute("type", nextType);

      const icon = button.querySelector("i");
      if (!icon) {
        return;
      }

      icon.classList.toggle("bi-eye", nextType === "password");
      icon.classList.toggle("bi-eye-slash", nextType === "text");
    });
  });
});
