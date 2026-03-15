(function () {
    function getCsrfToken() {
        const input = document.querySelector('#blogCsrfForm input[name="csrfmiddlewaretoken"]');
        return input ? input.value : "";
    }

    function setProgressBar() {
        const progressBar = document.getElementById("readingProgress");
        const articleBody = document.getElementById("articleBody");
        if (!progressBar || !articleBody) {
            if (progressBar) {
                progressBar.style.width = "0%";
            }
            return;
        }

        const rect = articleBody.getBoundingClientRect();
        const top = window.scrollY + rect.top - 120;
        const height = articleBody.offsetHeight;
        const viewport = window.scrollY + window.innerHeight;
        const progress = Math.max(0, Math.min(1, (viewport - top) / Math.max(height, 1)));
        progressBar.style.width = `${progress * 100}%`;
    }

    function slugify(text) {
        return (text || "")
            .toLowerCase()
            .trim()
            .replace(/[^\w\s-]/g, "")
            .replace(/\s+/g, "-")
            .replace(/-+/g, "-");
    }

    function buildToc() {
        const container = document.getElementById("articleToc");
        const articleBody = document.getElementById("articleBody");
        if (!container || !articleBody) {
            return;
        }

        const headings = articleBody.querySelectorAll("h2, h3");
        if (!headings.length) {
            container.innerHTML = "<span class='text-muted'>Heading topilmadi</span>";
            return;
        }

        const usedIds = new Set();
        const fragment = document.createDocumentFragment();

        headings.forEach((heading) => {
            let baseId = heading.id || slugify(heading.textContent);
            if (!baseId) {
                baseId = `section-${usedIds.size + 1}`;
            }

            let finalId = baseId;
            let index = 2;
            while (usedIds.has(finalId)) {
                finalId = `${baseId}-${index}`;
                index += 1;
            }

            usedIds.add(finalId);
            heading.id = finalId;

            const link = document.createElement("a");
            link.href = `#${finalId}`;
            link.textContent = heading.textContent.trim();
            if (heading.tagName === "H3") {
                link.classList.add("is-sub");
            }
            fragment.appendChild(link);
        });

        container.appendChild(fragment);
    }

    function bindClap() {
        const button = document.querySelector("[data-clap-url]");
        if (!button) {
            return;
        }

        button.addEventListener("click", async function () {
            const response = await fetch(button.dataset.clapUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({ action: "clap" }),
            });

            if (!response.ok) {
                return;
            }

            const payload = await response.json();
            const totalLabel = button.querySelector("[data-clap-total-label]");
            const myLabel = button.querySelector("[data-my-clap-label]");

            if (totalLabel) {
                totalLabel.textContent = payload.clap_count;
            }
            if (myLabel) {
                myLabel.textContent = `${payload.my_clap_count} sizniki`;
            }

            button.classList.remove("is-bursting");
            window.requestAnimationFrame(function () {
                button.classList.add("is-bursting");
            });
        });
    }

    function bindCopyShare() {
        document.querySelectorAll("[data-share-copy]").forEach((button) => {
            button.addEventListener("click", async function () {
                const shareUrl = button.dataset.shareCopy;
                try {
                    await navigator.clipboard.writeText(shareUrl);
                    const helper = button.querySelector("small");
                    if (helper) {
                        helper.textContent = "Nusxalandi";
                    }
                } catch (error) {
                    const helper = button.querySelector("small");
                    if (helper) {
                        helper.textContent = shareUrl;
                    }
                }
            });
        });

        document.querySelectorAll("[data-native-share]").forEach((button) => {
            button.addEventListener("click", async function () {
                if (!navigator.share) {
                    return;
                }

                try {
                    await navigator.share({
                        title: button.dataset.nativeTitle,
                        text: button.dataset.nativeText,
                        url: button.dataset.nativeShare,
                    });
                } catch (error) {
                    return;
                }
            });
        });
    }

    function bindCommentLikes() {
        document.querySelectorAll("[data-comment-like-url]").forEach((button) => {
            button.addEventListener("click", async function () {
                const response = await fetch(button.dataset.commentLikeUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken(),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: JSON.stringify({ action: "toggle" }),
                });

                if (response.status === 403) {
                    const payload = await response.json();
                    const next = encodeURIComponent(window.location.pathname + window.location.search + window.location.hash);
                    window.location.href = `${payload.login_url}?next=${next}`;
                    return;
                }

                if (!response.ok) {
                    return;
                }

                const payload = await response.json();
                button.classList.toggle("is-active", payload.liked);
                const likeLabel = button.querySelector("[data-like-label]");
                if (likeLabel) {
                    likeLabel.textContent = payload.like_count;
                }
            });
        });
    }

    function bindReplyToggles() {
        document.querySelectorAll("[data-reply-toggle]").forEach((button) => {
            button.addEventListener("click", function () {
                const panel = document.getElementById(button.dataset.replyToggle);
                if (!panel) {
                    return;
                }
                panel.classList.toggle("d-none");
                if (!panel.classList.contains("d-none")) {
                    const input = panel.querySelector("textarea");
                    if (input) {
                        input.focus();
                    }
                }
            });
        });
    }

    window.addEventListener("scroll", setProgressBar, { passive: true });
    window.addEventListener("resize", setProgressBar);
    window.addEventListener("load", setProgressBar);

    buildToc();
    bindClap();
    bindCopyShare();
    bindCommentLikes();
    bindReplyToggles();
})();
