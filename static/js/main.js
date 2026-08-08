/* =========================================
   MENU SMART - MAIN JAVASCRIPT
========================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* =========================================
       MOBILE MENU
    ========================================= */

    const menuButton = document.querySelector(".dashboard-menu-button");
    const sidebar = document.querySelector(".dashboard-sidebar");
    const closeSidebar = document.querySelector(".dashboard-close-sidebar");
    const overlay = document.querySelector(".dashboard-overlay");

    function openSidebar() {
        if (sidebar) {
            sidebar.classList.add("open");
        }

        if (overlay) {
            overlay.classList.add("show");
        }

        document.body.classList.add("sidebar-open");
    }

    function closeSidebarMenu() {
        if (sidebar) {
            sidebar.classList.remove("open");
        }

        if (overlay) {
            overlay.classList.remove("show");
        }

        document.body.classList.remove("sidebar-open");
    }

    if (menuButton) {
        menuButton.addEventListener("click", openSidebar);
    }

    if (closeSidebar) {
        closeSidebar.addEventListener("click", closeSidebarMenu);
    }

    if (overlay) {
        overlay.addEventListener("click", closeSidebarMenu);
    }


    /* =========================================
       CLOSE SIDEBAR AFTER LINK CLICK
    ========================================= */

    document.querySelectorAll(".dashboard-sidebar a").forEach(function (link) {

        link.addEventListener("click", function () {

            if (window.innerWidth <= 900) {
                closeSidebarMenu();
            }

        });

    });


    /* =========================================
       DROPDOWNS
    ========================================= */

    document.querySelectorAll("[data-dropdown-toggle]").forEach(function (button) {

        button.addEventListener("click", function (event) {

            event.stopPropagation();

            const targetId = button.getAttribute("data-dropdown-toggle");
            const target = document.getElementById(targetId);

            if (!target) {
                return;
            }

            document.querySelectorAll(".dropdown-menu.show").forEach(function (menu) {

                if (menu !== target) {
                    menu.classList.remove("show");
                }

            });

            target.classList.toggle("show");

        });

    });


    document.addEventListener("click", function () {

        document.querySelectorAll(".dropdown-menu.show").forEach(function (menu) {
            menu.classList.remove("show");
        });

    });


    /* =========================================
       ALERT AUTO HIDE
    ========================================= */

    document.querySelectorAll(".dashboard-alert[data-auto-hide]").forEach(function (alert) {

        const duration =
            parseInt(alert.getAttribute("data-auto-hide")) || 5000;

        setTimeout(function () {

            alert.style.opacity = "0";
            alert.style.transform = "translateY(-5px)";

            setTimeout(function () {
                alert.remove();
            }, 300);

        }, duration);

    });


    /* =========================================
       CONFIRM DELETE
    ========================================= */

    document.querySelectorAll("[data-confirm-delete]").forEach(function (element) {

        element.addEventListener("click", function (event) {

            const message =
                element.getAttribute("data-confirm-delete") ||
                "هل أنت متأكد من الحذف؟";

            if (!window.confirm(message)) {
                event.preventDefault();
            }

        });

    });


    /* =========================================
       FORM DOUBLE SUBMIT PROTECTION
    ========================================= */

    document.querySelectorAll("form").forEach(function (form) {

        form.addEventListener("submit", function () {

            if (form.dataset.submitted === "true") {
                return;
            }

            form.dataset.submitted = "true";

            const submitButtons =
                form.querySelectorAll(
                    'button[type="submit"], input[type="submit"]'
                );

            submitButtons.forEach(function (button) {

                button.disabled = true;

                if (button.tagName.toLowerCase() === "button") {

                    const originalText = button.innerHTML;

                    button.dataset.originalText = originalText;

                    button.innerHTML =
                        '<span class="loading-spinner"></span> جاري التنفيذ...';

                }

            });

        });

    });


    /* =========================================
       PASSWORD VISIBILITY
    ========================================= */

    document.querySelectorAll("[data-password-toggle]").forEach(function (button) {

        button.addEventListener("click", function () {

            const targetId =
                button.getAttribute("data-password-toggle");

            const input =
                document.getElementById(targetId);

            if (!input) {
                return;
            }

            if (input.type === "password") {

                input.type = "text";

                button.setAttribute("aria-label", "إخفاء كلمة المرور");

                if (button.dataset.showText) {
                    button.textContent = button.dataset.hideText || "إخفاء";
                }

            } else {

                input.type = "password";

                button.setAttribute("aria-label", "إظهار كلمة المرور");

                if (button.dataset.showText) {
                    button.textContent = button.dataset.showText;
                }

            }

        });

    });


    /* =========================================
       FILE INPUT PREVIEW
    ========================================= */

    document.querySelectorAll("[data-image-preview]").forEach(function (input) {

        input.addEventListener("change", function () {

            const previewId =
                input.getAttribute("data-image-preview");

            const preview =
                document.getElementById(previewId);

            if (!preview) {
                return;
            }

            const file = input.files && input.files[0];

            if (!file) {
                preview.removeAttribute("src");
                preview.style.display = "none";
                return;
            }

            if (!file.type.startsWith("image/")) {
                return;
            }

            const reader = new FileReader();

            reader.onload = function (event) {

                preview.src = event.target.result;
                preview.style.display = "block";

            };

            reader.readAsDataURL(file);

        });

    });


    /* =========================================
       DRAG & DROP UPLOAD
    ========================================= */

    document.querySelectorAll("[data-file-drop]").forEach(function (dropArea) {

        const inputId =
            dropArea.getAttribute("data-file-drop");

        const input =
            document.getElementById(inputId);

        if (!input) {
            return;
        }

        ["dragenter", "dragover"].forEach(function (eventName) {

            dropArea.addEventListener(eventName, function (event) {

                event.preventDefault();
                event.stopPropagation();

                dropArea.classList.add("dragging");

            });

        });


        ["dragleave", "drop"].forEach(function (eventName) {

            dropArea.addEventListener(eventName, function (event) {

                event.preventDefault();
                event.stopPropagation();

                dropArea.classList.remove("dragging");

            });

        });


        dropArea.addEventListener("drop", function (event) {

            const files = event.dataTransfer.files;

            if (!files || !files.length) {
                return;
            }

            input.files = files;

            input.dispatchEvent(new Event("change", {
                bubbles: true
            }));

        });


        dropArea.addEventListener("click", function () {

            input.click();

        });

    });


    /* =========================================
       SEARCH
    ========================================= */

    document.querySelectorAll("[data-search-input]").forEach(function (input) {

        const targetSelector =
            input.getAttribute("data-search-input");

        const items =
            document.querySelectorAll(targetSelector);

        input.addEventListener("input", function () {

            const searchValue =
                input.value.trim().toLowerCase();

            items.forEach(function (item) {

                const text =
                    item.textContent.toLowerCase();

                if (!searchValue || text.includes(searchValue)) {

                    item.style.display = "";

                } else {

                    item.style.display = "none";

                }

            });

        });

    });


    /* =========================================
       TABS
    ========================================= */

    document.querySelectorAll("[data-tab]").forEach(function (button) {

        button.addEventListener("click", function () {

            const tabName =
                button.getAttribute("data-tab");

            const group =
                button.getAttribute("data-tab-group");

            document.querySelectorAll(
                '[data-tab][data-tab-group="' + group + '"]'
            ).forEach(function (tabButton) {

                tabButton.classList.remove("active");

            });

            document.querySelectorAll(
                '[data-tab-content][data-tab-group="' + group + '"]'
            ).forEach(function (content) {

                content.classList.remove("active");

            });

            button.classList.add("active");

            const content =
                document.querySelector(
                    '[data-tab-content="' +
                    tabName +
                    '"][data-tab-group="' +
                    group +
                    '"]'
                );

            if (content) {
                content.classList.add("active");
            }

        });

    });


    /* =========================================
       SMOOTH SCROLL
    ========================================= */

    document.querySelectorAll('a[href^="#"]').forEach(function (link) {

        link.addEventListener("click", function (event) {

            const href =
                link.getAttribute("href");

            if (!href || href === "#") {
                return;
            }

            const target =
                document.querySelector(href);

            if (!target) {
                return;
            }

            event.preventDefault();

            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        });

    });


    /* =========================================
       NUMBER INPUT CONTROLS
    ========================================= */

    document.querySelectorAll("[data-number-control]").forEach(function (container) {

        const input =
            container.querySelector("input[type='number']");

        const decrease =
            container.querySelector("[data-decrease]");

        const increase =
            container.querySelector("[data-increase]");

        if (!input) {
            return;
        }

        function getValue() {

            const value =
                parseFloat(input.value);

            return Number.isNaN(value)
                ? 0
                : value;

        }

        function getStep() {

            const step =
                parseFloat(input.step);

            return Number.isNaN(step)
                ? 1
                : step;

        }

        if (decrease) {

            decrease.addEventListener("click", function () {

                const step = getStep();
                const min = parseFloat(input.min);

                let value = getValue() - step;

                if (!Number.isNaN(min)) {
                    value = Math.max(value, min);
                }

                input.value = value;

                input.dispatchEvent(new Event("change", {
                    bubbles: true
                }));

            });

        }


        if (increase) {

            increase.addEventListener("click", function () {

                const step = getStep();
                const max = parseFloat(input.max);

                let value = getValue() + step;

                if (!Number.isNaN(max)) {
                    value = Math.min(value, max);
                }

                input.value = value;

                input.dispatchEvent(new Event("change", {
                    bubbles: true
                }));

            });

        }

    });


    /* =========================================
       COPY TO CLIPBOARD
    ========================================= */

    document.querySelectorAll("[data-copy]").forEach(function (button) {

        button.addEventListener("click", async function () {

            const value =
                button.getAttribute("data-copy");

            if (!value) {
                return;
            }

            try {

                await navigator.clipboard.writeText(value);

                const original =
                    button.innerHTML;

                button.innerHTML = "تم النسخ ✓";

                setTimeout(function () {
                    button.innerHTML = original;
                }, 1500);

            } catch (error) {

                const temporary =
                    document.createElement("textarea");

                temporary.value = value;

                document.body.appendChild(temporary);

                temporary.select();

                document.execCommand("copy");

                temporary.remove();

            }

        });

    });


    /* =========================================
       BACK TO TOP
    ========================================= */

    const backToTop =
        document.querySelector("[data-back-to-top]");

    if (backToTop) {

        window.addEventListener("scroll", function () {

            if (window.scrollY > 400) {

                backToTop.classList.add("show");

            } else {

                backToTop.classList.remove("show");

            }

        });


        backToTop.addEventListener("click", function () {

            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });

        });

    }


    /* =========================================
       PREVENT EMPTY LINKS
    ========================================= */

    document.querySelectorAll('a[href="#"]').forEach(function (link) {

        link.addEventListener("click", function (event) {
            event.preventDefault();
        });

    });

});


/* =========================================
   GLOBAL HELPERS
========================================= */

function formatPrice(value) {

    const number =
        Number(value);

    if (Number.isNaN(number)) {
        return "0";
    }

    return new Intl.NumberFormat("ar-EG", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    }).format(number);

}


function escapeHtml(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value == null ? "" : String(value);

    return div.innerHTML;

}


function showToast(message, type = "success") {

    let container =
        document.querySelector(".menusmart-toast-container");

    if (!container) {

        container =
            document.createElement("div");

        container.className =
            "menusmart-toast-container";

        document.body.appendChild(container);

    }

    const toast =
        document.createElement("div");

    toast.className =
        "menusmart-toast " + type;

    toast.textContent =
        message;

    container.appendChild(toast);

    requestAnimationFrame(function () {
        toast.classList.add("show");
    });

    setTimeout(function () {

        toast.classList.remove("show");

        setTimeout(function () {
            toast.remove();
        }, 300);

    }, 3000);

}


function debounce(callback, delay = 300) {

    let timer;

    return function (...args) {

        clearTimeout(timer);

        timer =
            setTimeout(function () {

                callback.apply(this, args);

            }, delay);

    };

}