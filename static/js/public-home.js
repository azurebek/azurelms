(function () {
  "use strict";

  const html = document.documentElement;
  const toggleBtn = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");

  function applyTheme(dark) {
    html.setAttribute("data-theme", dark ? "dark" : "light");
    if (themeIcon) {
      themeIcon.className = dark ? "bi bi-sun" : "bi bi-moon";
    }
    try {
      localStorage.setItem("az-theme", dark ? "dark" : "light");
    } catch (_) {}
  }

  (function initTheme() {
    let saved;
    try {
      saved = localStorage.getItem("az-theme");
    } catch (_) {}
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(saved ? saved === "dark" : prefersDark);
  })();

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      applyTheme(html.getAttribute("data-theme") !== "dark");
    });
  }

  const nav = document.getElementById("nav");
  if (nav) {
    window.addEventListener(
      "scroll",
      function () {
        nav.classList.toggle("is-scrolled", window.scrollY > 6);
      },
      { passive: true }
    );
  }

  (function setupMobileMenu() {
    const button = document.querySelector(".nav-toggle");
    const navLinks = document.querySelector(".nav-links");
    const navActions = document.querySelector(".nav-actions");
    const navRoot = document.querySelector(".nav");
    if (!button || !navLinks || !navActions || !navRoot) {
      return;
    }

    const panel = document.createElement("div");
    const panelId = "public-mobile-panel";
    panel.className = "public-mobile-panel";
    panel.id = panelId;
    panel.hidden = true;

    const inner = document.createElement("div");
    inner.className = "wrap public-mobile-panel-inner";

    const mobileNav = document.createElement("div");
    mobileNav.className = "public-mobile-panel-nav";
    navLinks.querySelectorAll("a").forEach(function (link) {
      mobileNav.appendChild(link.cloneNode(true));
    });

    const mobileActions = document.createElement("div");
    mobileActions.className = "public-mobile-panel-actions";
    navActions.querySelectorAll("a").forEach(function (link) {
      mobileActions.appendChild(link.cloneNode(true));
    });

    inner.appendChild(mobileNav);
    inner.appendChild(mobileActions);
    panel.appendChild(inner);
    navRoot.insertAdjacentElement("afterend", panel);

    button.setAttribute("aria-controls", panelId);
    button.setAttribute("aria-expanded", "false");

    function setOpen(open) {
      panel.hidden = !open;
      button.setAttribute("aria-expanded", open ? "true" : "false");
    }

    button.addEventListener("click", function () {
      setOpen(panel.hidden);
    });

    panel.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        setOpen(false);
      }
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth >= 900) {
        setOpen(false);
      }
    });
  })();

  if ("IntersectionObserver" in window) {
    const fadeObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) {
            return;
          }
          entry.target.classList.add("vis");
          fadeObserver.unobserve(entry.target);
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -36px 0px" }
    );

    document.querySelectorAll(".fi:not(.vis)").forEach(function (el) {
      fadeObserver.observe(el);
    });
  } else {
    document.querySelectorAll(".fi").forEach(function (el) {
      el.classList.add("vis");
    });
  }

  const wrap = document.getElementById("hscrollWrap");
  const track = document.getElementById("hscrollTrack");
  const progressFill = document.getElementById("hscrollProgress");
  let maxShift = 0;
  let headingHeight = 0;

  function setupHorizontalScroll() {
    if (!wrap || !track || window.innerWidth < 768) {
      return;
    }

    const heading = wrap.querySelector(".hscroll-heading");
    headingHeight = heading ? heading.offsetHeight : 0;
    maxShift = Math.max(0, track.scrollWidth - window.innerWidth);
    wrap.style.height = headingHeight + maxShift + window.innerHeight + "px";
  }

  function updateHorizontalScroll() {
    if (!wrap || !track || window.innerWidth < 768 || maxShift === 0) {
      return;
    }

    const rect = wrap.getBoundingClientRect();
    const stickyTop = rect.top + headingHeight;

    if (stickyTop > 0 || rect.bottom < window.innerHeight) {
      if (stickyTop > 0) {
        track.style.transform = "translateX(0)";
        if (progressFill) {
          progressFill.style.width = "0%";
        }
      }
      return;
    }

    const scrolled = -(rect.top + headingHeight);
    const progress = Math.min(1, Math.max(0, scrolled / maxShift));
    track.style.transform = "translateX(" + -progress * maxShift + "px)";
    if (progressFill) {
      progressFill.style.width = progress * 100 + "%";
    }
  }

  setupHorizontalScroll();
  updateHorizontalScroll();
  window.addEventListener("scroll", updateHorizontalScroll, { passive: true });
  window.addEventListener("resize", function () {
    setupHorizontalScroll();
    updateHorizontalScroll();
  });

  if ("IntersectionObserver" in window) {
    const counterObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) {
            return;
          }
          const el = entry.target;
          const target = parseInt(el.dataset.target, 10);
          const suffix = el.dataset.suffix || "";
          if (Number.isNaN(target)) {
            return;
          }

          const duration = 1200;
          const startTime = performance.now();

          function step(now) {
            const p = Math.min(1, (now - startTime) / duration);
            const eased = 1 - (1 - p) * (1 - p);
            const value = Math.round(eased * target);
            el.textContent = (value >= 1000 ? value.toLocaleString() : value) + suffix;
            if (p < 1) {
              requestAnimationFrame(step);
            }
          }

          requestAnimationFrame(step);
          counterObserver.unobserve(el);
        });
      },
      { threshold: 0.6 }
    );

    document.querySelectorAll("[data-target]").forEach(function (el) {
      counterObserver.observe(el);
    });
  }
})();
