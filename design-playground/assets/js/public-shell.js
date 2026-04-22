(function () {
  const carousels = document.querySelectorAll("[data-carousel]");

  carousels.forEach((carousel) => {
    const slides = Array.from(carousel.querySelectorAll("[data-carousel-slide]"));
    const dots = Array.from(carousel.querySelectorAll("[data-carousel-dot]"));
    const prev = carousel.querySelector("[data-carousel-prev]");
    const next = carousel.querySelector("[data-carousel-next]");

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
        slide.classList.toggle("is-active", slideIndex === currentIndex);
      });

      dots.forEach((dot, dotIndex) => {
        dot.classList.toggle("is-active", dotIndex === currentIndex);
      });
    };

    const startAutoplay = () => {
      stopAutoplay();
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

    setActive(currentIndex);
    startAutoplay();
  });
})();
