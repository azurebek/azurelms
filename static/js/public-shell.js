(function () {
  const carousels = document.querySelectorAll("[data-carousel]");

  carousels.forEach((carousel) => {
    const slides = Array.from(carousel.querySelectorAll("[data-carousel-slide]"));
    const dots = Array.from(carousel.querySelectorAll("[data-carousel-dot]"));
    const prev = carousel.querySelector("[data-carousel-prev]");
    const next = carousel.querySelector("[data-carousel-next]");
    const mobileQuery = window.matchMedia("(max-width: 520px)");

    if (!slides.length) {
      return;
    }

    let currentIndex = slides.findIndex((slide) => slide.classList.contains("is-active"));
    let intervalId = null;

    if (currentIndex < 0) {
      currentIndex = 0;
    }

    const setActive = (index) => {
      currentIndex = (index + slides.length) % slides.length;

      slides.forEach((slide, slideIndex) => {
        const isActive = slideIndex === currentIndex;
        slide.classList.toggle("is-active", isActive);
        slide.setAttribute("aria-hidden", String(!isActive));
      });

      dots.forEach((dot, dotIndex) => {
        dot.classList.toggle("is-active", dotIndex === currentIndex);
      });
    };

    const startAutoplay = () => {
      stopAutoplay();

      if (mobileQuery.matches) {
        return;
      }

      intervalId = window.setInterval(() => {
        setActive(currentIndex + 1);
      }, 5200);
    };

    const stopAutoplay = () => {
      if (intervalId !== null) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
    };

    prev?.addEventListener("click", () => {
      setActive(currentIndex - 1);
      startAutoplay();
    });

    next?.addEventListener("click", () => {
      setActive(currentIndex + 1);
      startAutoplay();
    });

    dots.forEach((dot, dotIndex) => {
      dot.addEventListener("click", () => {
        setActive(dotIndex);
        startAutoplay();
      });
    });

    carousel.addEventListener("mouseenter", stopAutoplay);
    carousel.addEventListener("mouseleave", startAutoplay);
    mobileQuery.addEventListener("change", startAutoplay);

    // Keyboard navigation (WCAG AA) — Arrow keys when carousel is focused.
    // tabindex orqali fokus olishi uchun atribut qo'shamiz (yo'q bo'lsa).
    if (!carousel.hasAttribute("tabindex")) {
      carousel.setAttribute("tabindex", "0");
    }
    carousel.setAttribute("role", carousel.getAttribute("role") || "region");
    if (!carousel.hasAttribute("aria-roledescription")) {
      carousel.setAttribute("aria-roledescription", "carousel");
    }

    carousel.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setActive(currentIndex - 1);
        startAutoplay();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setActive(currentIndex + 1);
        startAutoplay();
      } else if (event.key === "Home") {
        event.preventDefault();
        setActive(0);
        startAutoplay();
      } else if (event.key === "End") {
        event.preventDefault();
        setActive(slides.length - 1);
        startAutoplay();
      }
    });

    // Foydalanuvchi fokus ichida bo'lsa autoplay'ni to'xtatamiz.
    carousel.addEventListener("focusin", stopAutoplay);
    carousel.addEventListener("focusout", startAutoplay);

    setActive(currentIndex);
    startAutoplay();
  });
})();
