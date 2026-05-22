(function () {
  const html = document.documentElement;

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return "";
  }

  function applyTheme(isDark) {
    html.setAttribute("data-theme", isDark ? "dark" : "light");
    document.querySelectorAll("#themeIcon").forEach((icon) => {
      icon.className = isDark ? "bi bi-sun" : "bi bi-moon";
    });
    try {
      localStorage.setItem("az-theme", isDark ? "dark" : "light");
      localStorage.setItem("lms-theme", isDark ? "dark" : "light");
    } catch (_) {}
  }

  window.toggleTheme = function toggleTheme() {
    applyTheme(html.getAttribute("data-theme") !== "dark");
  };

  function bootTheme() {
    let saved = null;
    try {
      saved = localStorage.getItem("az-theme") || localStorage.getItem("lms-theme");
    } catch (_) {}
    applyTheme(saved ? saved === "dark" : html.getAttribute("data-theme") === "dark");
  }

  window.filterPosts = function filterPosts(btn, cat) {
    document.querySelectorAll(".filter-btn").forEach((item) => item.classList.remove("active"));
    if (btn) {
      btn.classList.add("active");
    }
    document.querySelectorAll(".article-card").forEach((card) => {
      if (cat === "all") {
        card.style.display = "";
        return;
      }
      card.style.display = (card.dataset.cat || "").includes(cat) ? "" : "none";
    });
  };

  window.copyLink = function copyLink() {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href).catch(() => {});
    }
  };

  window.toggleBookmark = function toggleBookmark() {
    const button = document.getElementById("bookmarkBtn");
    const icon = document.getElementById("bmIcon");
    if (!button || !icon) {
      return;
    }
    const active = !button.classList.contains("liked");
    button.classList.toggle("liked", active);
    icon.className = active ? "bi bi-bookmark-fill" : "bi bi-bookmark";
  };

  window.toggleLike = function toggleLike() {
    const button = document.getElementById("likeBtn");
    if (!button || !button.dataset.clapUrl) {
      return;
    }
    fetch(button.dataset.clapUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (!data.ok) {
          return;
        }
        const icon = document.getElementById("likeIcon");
        const count = document.getElementById("likeCount");
        button.classList.add("liked");
        if (icon) {
          icon.className = "bi bi-heart-fill";
        }
        if (count) {
          count.textContent = data.clap_count;
        }
      })
      .catch(() => {});
  };

  window.scrollTo2 = function scrollTo2(id) {
    const target = document.getElementById(id);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  window.openDrawer = function openDrawer() {
    document.getElementById("drawerBackdrop")?.classList.add("open");
    document.getElementById("publishDrawer")?.classList.add("open");
  };

  window.closeDrawer = function closeDrawer() {
    document.getElementById("drawerBackdrop")?.classList.remove("open");
    document.getElementById("publishDrawer")?.classList.remove("open");
  };

  window.toggleFocus = function toggleFocus() {
    document.body.classList.toggle("focus-mode");
  };

  window.toggleReplyForm = function toggleReplyForm(button) {
    const item = button.closest(".comment-item");
    const form = item && item.querySelector(".comment-reply-form");
    if (form) {
      form.classList.toggle("open");
    }
  };

  function setupReadProgress() {
    const fill = document.getElementById("readFill");
    const navTitle = document.getElementById("navTitleSmall");
    if (!fill && !navTitle) {
      return;
    }
    const update = () => {
      const total = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const pct = total > 0 ? (document.documentElement.scrollTop / total) * 100 : 0;
      if (fill) {
        fill.style.width = `${pct}%`;
      }
      if (navTitle) {
        navTitle.classList.toggle("show", document.documentElement.scrollTop > 300);
      }
    };
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  function setupMessages() {
    document.querySelectorAll(".blog-message").forEach((message) => {
      const dismiss = () => {
        message.classList.add("is-hiding");
        window.setTimeout(() => {
          message.remove();
        }, 220);
      };

      message.addEventListener("click", dismiss);
      window.setTimeout(dismiss, 4500);
    });
  }

  function setupToc() {
    const list = document.querySelector("[data-blog-toc]");
    const body = document.querySelector(".article-body");
    if (!list || !body) {
      return;
    }
    const headings = Array.from(body.querySelectorAll("h2, h3")).slice(0, 8);
    if (!headings.length) {
      list.innerHTML = '<div class="toc-item active">Maqola</div>';
      return;
    }
    list.innerHTML = "";
    headings.forEach((heading, index) => {
      if (!heading.id) {
        heading.id = `section-${index + 1}`;
      }
      const item = document.createElement("button");
      item.type = "button";
      item.className = `toc-item${index === 0 ? " active" : ""}`;
      item.textContent = heading.textContent;
      item.addEventListener("click", () => {
        document.querySelectorAll(".toc-item").forEach((el) => el.classList.remove("active"));
        item.classList.add("active");
        heading.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      list.appendChild(item);
    });
  }

  function setupCommentLikes() {
    document.querySelectorAll("[data-comment-like-url]").forEach((button) => {
      button.addEventListener("click", () => {
        fetch(button.dataset.commentLikeUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "X-Requested-With": "XMLHttpRequest",
          },
        })
          .then((response) => {
            if (response.status === 403) {
              return response.json().then((data) => {
                if (data.login_url) {
                  window.location.href = data.login_url;
                }
              });
            }
            return response.json();
          })
          .then((data) => {
            if (!data || !data.ok) {
              return;
            }
            button.classList.toggle("liked", data.liked);
            const count = button.querySelector("[data-like-count]");
            if (count) {
              count.textContent = data.like_count;
            }
          })
          .catch(() => {});
      });
    });
  }

  function setupMiniChart() {
    const chart = document.getElementById("miniChart");
    if (!chart || chart.children.length) {
      return;
    }
    [55, 70, 62, 85, 90, 78, 100].forEach((value, index) => {
      const bar = document.createElement("div");
      bar.className = `mc-bar${index === 6 ? " today" : ""}`;
      bar.style.height = `${value}%`;
      chart.appendChild(bar);
    });
  }

  function setupStudioForm() {
    const form = document.getElementById("postForm");
    if (!form) {
      return;
    }

    const statusField = form.querySelector('[name="status"]');
    document.querySelectorAll("[data-blog-status]").forEach((button) => {
      const active = statusField && statusField.value === button.dataset.blogStatus;
      button.classList.toggle("active", active);
      button.addEventListener("click", () => {
        if (statusField) {
          statusField.value = button.dataset.blogStatus;
        }
        document.querySelectorAll("[data-blog-status]").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
      });
    });

    document.querySelectorAll("[data-submit-status]").forEach((button) => {
      button.addEventListener("click", () => {
        if (statusField) {
          statusField.value = button.dataset.submitStatus;
        }
        form.requestSubmit();
      });
    });

    const coverInput = document.getElementById("coverFile");
    const coverArea = document.getElementById("coverArea");
    const coverImg = document.getElementById("coverImg");
    if (coverArea && coverInput) {
      coverArea.addEventListener("click", () => coverInput.click());
    }
    if (coverInput && coverImg) {
      coverInput.addEventListener("change", () => {
        const file = coverInput.files && coverInput.files[0];
        if (!file) {
          return;
        }
        const url = URL.createObjectURL(file);
        coverImg.src = url;
        coverImg.style.display = "block";
        const placeholder = document.getElementById("coverPlaceholder");
        if (placeholder) {
          placeholder.style.display = "none";
        }
      });
    }
    document.getElementById("coverRemove")?.addEventListener("click", (event) => {
      event.stopPropagation();
      if (coverInput) {
        coverInput.value = "";
      }
      if (coverImg) {
        coverImg.src = "";
        coverImg.style.display = "none";
      }
      const placeholder = document.getElementById("coverPlaceholder");
      if (placeholder) {
        placeholder.style.display = "";
      }
    });

    const titleInput = form.querySelector(".title-input");
    const wordCount = document.getElementById("tbWordCount");
    const updateCount = () => {
      const raw = form.innerText || form.textContent || "";
      const words = raw.trim() ? raw.trim().split(/\s+/).length : 0;
      if (wordCount) {
        wordCount.textContent = `${words} so'z`;
      }
    };
    if (titleInput) {
      titleInput.addEventListener("input", updateCount);
    }
    form.addEventListener("input", updateCount);
    updateCount();
  }

  function bootBlogRuntime() {
    bootTheme();
    setupMessages();
    setupReadProgress();
    setupToc();
    setupCommentLikes();
    setupMiniChart();
    setupStudioForm();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootBlogRuntime, { once: true });
  } else {
    bootBlogRuntime();
  }
})();
