/* =========================================
   MENU SMART - DASHBOARD JAVASCRIPT
   الإصدار الموحد
========================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* =========================================
       DASHBOARD SIDEBAR
    ========================================= */

    const sidebar =
        document.querySelector(".dashboard-sidebar");

    const overlay =
        document.querySelector(".dashboard-overlay");

    const menuButton =
        document.querySelector(".dashboard-menu-button");

    const closeButton =
        document.querySelector(".dashboard-close-sidebar");


    function openDashboardSidebar() {

        if (sidebar) {
            sidebar.classList.add("open");
        }

        if (overlay) {
            overlay.classList.add("show");
        }

        document.body.classList.add("sidebar-open");
    }


    function closeDashboardSidebar() {

        if (sidebar) {
            sidebar.classList.remove("open");
        }

        if (overlay) {
            overlay.classList.remove("show");
        }

        document.body.classList.remove("sidebar-open");
    }


    if (menuButton) {
        menuButton.addEventListener(
            "click",
            openDashboardSidebar
        );
    }


    if (closeButton) {
        closeButton.addEventListener(
            "click",
            closeDashboardSidebar
        );
    }


    if (overlay) {
        overlay.addEventListener(
            "click",
            closeDashboardSidebar
        );
    }


    /* =========================================
       ACTIVE SIDEBAR LINK
    ========================================= */

    const currentPath =
        window.location.pathname;

    document.querySelectorAll(
        ".dashboard-nav a"
    ).forEach(function (link) {

        const href =
            link.getAttribute("href");

        if (!href || href === "#") {
            return;
        }

        if (
            href === currentPath ||
            currentPath.endsWith(href)
        ) {
            link.classList.add("active");
        }

    });


    /* =========================================
       SIDEBAR CLOSE ON MOBILE
    ========================================= */

    document.querySelectorAll(
        ".dashboard-nav a"
    ).forEach(function (link) {

        link.addEventListener(
            "click",
            function () {

                if (window.innerWidth <= 900) {
                    closeDashboardSidebar();
                }

            }
        );

    });


    /* =========================================
       TABLE SEARCH
    ========================================= */

    document.querySelectorAll(
        "[data-dashboard-search]"
    ).forEach(function (input) {

        const selector =
            input.getAttribute(
                "data-dashboard-search"
            );

        const rows =
            document.querySelectorAll(selector);

        input.addEventListener(
            "input",
            function () {

                const value =
                    input.value
                        .trim()
                        .toLowerCase();

                rows.forEach(function (row) {

                    const text =
                        row.textContent
                            .toLowerCase();

                    row.style.display =
                        !value ||
                        text.includes(value)
                            ? ""
                            : "none";

                });

            }
        );

    });


    /* =========================================
       SELECT ALL TABLE CHECKBOXES
    ========================================= */

    document.querySelectorAll(
        "[data-select-all]"
    ).forEach(function (selectAll) {

        const target =
            selectAll.getAttribute(
                "data-select-all"
            );

        const checkboxes =
            document.querySelectorAll(target);

        selectAll.addEventListener(
            "change",
            function () {

                checkboxes.forEach(
                    function (checkbox) {

                        checkbox.checked =
                            selectAll.checked;

                    }
                );

            }
        );

    });


    /* =========================================
       DELETE SELECTED ITEMS
    ========================================= */

    document.querySelectorAll(
        "[data-delete-selected]"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const selector =
                    button.getAttribute(
                        "data-delete-selected"
                    );

                const selected =
                    document.querySelectorAll(
                        selector + ":checked"
                    );

                if (!selected.length) {

                    showDashboardMessage(
                        "لم يتم اختيار أي عنصر",
                        "warning"
                    );

                    return;
                }

                if (
                    !window.confirm(
                        "هل أنت متأكد من حذف العناصر المحددة؟"
                    )
                ) {
                    return;
                }

                const form =
                    button.closest("form");

                if (form) {
                    form.submit();
                }

            }
        );

    });


    /* =========================================
       MODAL
    ========================================= */

    document.querySelectorAll(
        "[data-modal-open]"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const modalId =
                    button.getAttribute(
                        "data-modal-open"
                    );

                const modal =
                    document.getElementById(modalId);

                if (!modal) {
                    return;
                }

                modal.classList.add("show");

                document.body.classList.add(
                    "modal-open"
                );

            }
        );

    });


    document.querySelectorAll(
        "[data-modal-close]"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const modal =
                    button.closest(
                        ".dashboard-modal"
                    );

                if (!modal) {
                    return;
                }

                modal.classList.remove("show");

                document.body.classList.remove(
                    "modal-open"
                );

            }
        );

    });


    document.querySelectorAll(
        ".dashboard-modal"
    ).forEach(function (modal) {

        modal.addEventListener(
            "click",
            function (event) {

                if (
                    event.target === modal &&
                    modal.dataset.closeOverlay !== "false"
                ) {

                    modal.classList.remove("show");

                    document.body.classList.remove(
                        "modal-open"
                    );

                }

            }
        );

    });


    /* =========================================
       ESCAPE MODAL
    ========================================= */

    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key !== "Escape") {
                return;
            }

            document.querySelectorAll(
                ".dashboard-modal.show"
            ).forEach(function (modal) {

                modal.classList.remove("show");

            });

            document.body.classList.remove(
                "modal-open"
            );

        }
    );


    /* =========================================
       IMAGE PREVIEW
    ========================================= */

    document.querySelectorAll(
        "[data-dashboard-image]"
    ).forEach(function (input) {

        input.addEventListener(
            "change",
            function () {

                const previewId =
                    input.getAttribute(
                        "data-dashboard-image"
                    );

                const preview =
                    document.getElementById(
                        previewId
                    );

                if (!preview) {
                    return;
                }

                const file =
                    input.files &&
                    input.files[0];

                if (!file) {
                    return;
                }

                if (
                    !file.type.startsWith(
                        "image/"
                    )
                ) {

                    showDashboardMessage(
                        "الملف المختار ليس صورة",
                        "error"
                    );

                    return;
                }

                const reader =
                    new FileReader();

                reader.onload =
                    function (event) {

                        preview.src =
                            event.target.result;

                        preview.style.display =
                            "block";

                    };

                reader.readAsDataURL(file);

            }
        );

    });


    /* =========================================
       PRICE INPUT
    ========================================= */

    document.querySelectorAll(
        "[data-price-input]"
    ).forEach(function (input) {

        input.addEventListener(
            "input",
            function () {

                let value =
                    input.value;

                value =
                    value.replace(
                        /[^0-9.]/g,
                        ""
                    );

                const parts =
                    value.split(".");

                if (parts.length > 2) {

                    value =
                        parts[0] +
                        "." +
                        parts.slice(1).join("");

                }

                input.value =
                    value;

            }
        );

    });


    /* =========================================
       AUTO CALCULATE TOTAL
    ========================================= */

    document.querySelectorAll(
        "[data-auto-total]"
    ).forEach(function (container) {

        const quantity =
            container.querySelector(
                "[data-quantity]"
            );

        const price =
            container.querySelector(
                "[data-unit-price]"
            );

        const total =
            container.querySelector(
                "[data-total]"
            );

        if (
            !quantity ||
            !price ||
            !total
        ) {
            return;
        }


        function calculateTotal() {

            const quantityValue =
                parseFloat(
                    quantity.value
                ) || 0;

            const priceValue =
                parseFloat(
                    price.value
                ) || 0;

            total.value =
                (
                    quantityValue *
                    priceValue
                ).toFixed(2);

        }


        quantity.addEventListener(
            "input",
            calculateTotal
        );

        price.addEventListener(
            "input",
            calculateTotal
        );

        calculateTotal();

    });


    /* =========================================
       STATUS FILTER
    ========================================= */

    document.querySelectorAll(
        "[data-status-filter]"
    ).forEach(function (select) {

        const selector =
            select.getAttribute(
                "data-status-filter"
            );

        const items =
            document.querySelectorAll(selector);

        select.addEventListener(
            "change",
            function () {

                const selected =
                    select.value
                        .trim()
                        .toLowerCase();

                items.forEach(function (item) {

                    if (
                        !selected ||
                        selected === "all"
                    ) {

                        item.style.display = "";

                        return;
                    }

                    const status =
                        (
                            item.dataset.status ||
                            item.getAttribute(
                                "data-status"
                            ) ||
                            ""
                        ).toLowerCase();

                    item.style.display =
                        status === selected
                            ? ""
                            : "none";

                });

            }
        );

    });


    /* =========================================
       CATEGORY SORT
    ========================================= */

    const categoryContainer =
        document.querySelector(
            "[data-category-sort]"
        );

    if (categoryContainer) {

        const items =
            categoryContainer.querySelectorAll(
                "[data-category-item]"
            );

        items.forEach(function (item) {

            const up =
                item.querySelector(
                    "[data-sort-up]"
                );

            const down =
                item.querySelector(
                    "[data-sort-down]"
                );


            if (up) {

                up.addEventListener(
                    "click",
                    function () {

                        const previous =
                            item.previousElementSibling;

                        if (previous) {

                            categoryContainer.insertBefore(
                                item,
                                previous
                            );

                        }

                    }
                );

            }


            if (down) {

                down.addEventListener(
                    "click",
                    function () {

                        const next =
                            item.nextElementSibling;

                        if (next) {

                            categoryContainer.insertBefore(
                                next,
                                item
                            );

                        }

                    }
                );

            }

        });

    }


    /* =========================================
       TOGGLE SETTINGS
    ========================================= */

    document.querySelectorAll(
        "[data-dashboard-toggle]"
    ).forEach(function (toggle) {

        toggle.addEventListener(
            "change",
            function () {

                const target =
                    toggle.getAttribute(
                        "data-dashboard-toggle"
                    );

                const element =
                    document.querySelector(target);

                if (!element) {
                    return;
                }

                element.classList.toggle(
                    "enabled",
                    toggle.checked
                );

            }
        );

    });


    /* =========================================
       COPY URL
    ========================================= */

    document.querySelectorAll(
        "[data-copy-url]"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            async function () {

                const url =
                    button.getAttribute(
                        "data-copy-url"
                    ) ||
                    window.location.href;

                try {

                    await navigator.clipboard.writeText(
                        url
                    );

                    const original =
                        button.innerHTML;

                    button.innerHTML =
                        "تم النسخ ✓";

                    setTimeout(
                        function () {

                            button.innerHTML =
                                original;

                        },
                        1500
                    );

                } catch (error) {

                    showDashboardMessage(
                        "تعذر نسخ الرابط",
                        "error"
                    );

                }

            }
        );

    });


    /* =========================================
       DASHBOARD NOTIFICATION
    ========================================= */

    window.showDashboardMessage =
        showDashboardMessage;


    /* =========================================
       NEW ORDER NOTIFICATIONS
    ========================================= */

    initOrderNotifications();


    /* =========================================
       AUTO REFRESH
    ========================================= */

    const refreshElement =
        document.querySelector(
            "[data-auto-refresh]"
        );

    if (refreshElement) {

        const seconds =
            parseInt(
                refreshElement.getAttribute(
                    "data-auto-refresh"
                )
            );

        if (
            !Number.isNaN(seconds) &&
            seconds > 0
        ) {

            setInterval(
                function () {

                    window.location.reload();

                },
                seconds * 1000
            );

        }

    }

});


/* =========================================
   NEW ORDER NOTIFICATIONS
   نظام واحد فقط
========================================= */

let latestKnownOrderId = null;

let orderAudioContext = null;

let orderSoundEnabled = false;

let orderNotificationInitialized = false;


/* =========================================
   INITIALIZE ORDER NOTIFICATIONS
========================================= */

function initOrderNotifications() {

    if (orderNotificationInitialized) {
        return;
    }

    orderNotificationInitialized = true;


    const isDashboard =
        window.location.pathname === "/dashboard";

    const isOrders =
        window.location.pathname === "/orders";


    if (!isDashboard && !isOrders) {
        return;
    }


    /*
     * المتصفح يمنع تشغيل الصوت تلقائيًا
     * قبل تفاعل المستخدم.
     */

    document.addEventListener(
        "click",
        enableOrderSound,
        {
            once: true
        }
    );


    document.addEventListener(
        "keydown",
        enableOrderSound,
        {
            once: true
        }
    );


    /*
     * أول فحص:
     * حفظ آخر رقم طلب بدون صوت.
     */

    fetchLatestOrders(true);


    /*
     * فحص كل 10 ثواني.
     */

    setInterval(
        function () {

            fetchLatestOrders(false);

        },
        10000
    );

}


/* =========================================
   ENABLE ORDER SOUND
========================================= */

function enableOrderSound() {

    try {

        const AudioContext =
            window.AudioContext ||
            window.webkitAudioContext;

        if (!AudioContext) {
            return;
        }


        if (!orderAudioContext) {

            orderAudioContext =
                new AudioContext();

        }


        if (
            orderAudioContext.state ===
            "suspended"
        ) {

            orderAudioContext.resume();

        }


        orderSoundEnabled = true;


        /*
         * لا تظهر الرسالة أكثر من مرة.
         */

        if (
            typeof window.showDashboardMessage ===
            "function"
        ) {

            window.showDashboardMessage(
                "🔔 تم تفعيل تنبيه الطلبات والصوت",
                "success"
            );

        }

    } catch (error) {

        console.warn(
            "Audio initialization error:",
            error
        );

    }

}


/* =========================================
   FETCH LATEST ORDERS
========================================= */

async function fetchLatestOrders(
    firstCheck = false
) {

    try {

        const response =
            await fetch(
                "/api/orders/latest",
                {
                    method: "GET",
                    cache: "no-store",
                    headers: {
                        "Accept":
                            "application/json"
                    }
                }
            );


        if (!response.ok) {

            console.warn(
                "تعذر جلب الطلبات الجديدة:",
                response.status
            );

            return;

        }


        const orders =
            await response.json();


        if (
            !Array.isArray(orders) ||
            orders.length === 0
        ) {

            return;

        }


        /*
         * الـ API يرجع الأحدث أولاً.
         */

        const newestOrder =
            orders[0];


        const newestId =
            Number(
                newestOrder.id
            );


        if (
            !Number.isFinite(newestId)
        ) {

            return;

        }


        /*
         * أول فحص:
         * نحفظ آخر طلب بدون تنبيه.
         */

        if (
            firstCheck ||
            latestKnownOrderId === null
        ) {

            latestKnownOrderId =
                newestId;

            return;

        }


        /*
         * لو رقم الطلب الجديد أكبر،
         * إذن يوجد طلب جديد.
         */

        if (
            newestId >
            latestKnownOrderId
        ) {

            const newOrders =
                orders.filter(
                    function (order) {

                        return (
                            Number(order.id) >
                            latestKnownOrderId
                        );

                    }
                );


            latestKnownOrderId =
                newestId;


            newOrders
                .reverse()
                .forEach(
                    function (order) {

                        notifyNewOrder(order);

                    }
                );

        }

    } catch (error) {

        console.warn(
            "Order notification error:",
            error
        );

    }

}


/* =========================================
   NOTIFY NEW ORDER
========================================= */

function notifyNewOrder(order) {

    const orderId =
        order.id || "";

    const customerName =
        order.customer_name ||
        "عميل جديد";

    const total =
        order.total || 0;


    /*
     * صوت
     */

    playNewOrderSound();


    /*
     * إشعار المتصفح
     */

    requestBrowserNotification(
        order
    );


    /*
     * تنبيه داخل الموقع
     */

    showNewOrderAlert(
        orderId,
        customerName,
        total
    );


    /*
     * اهتزاز الهاتف
     */

    if (
        navigator.vibrate
    ) {

        navigator.vibrate(
            [
                200,
                100,
                200
            ]
        );

    }

}


/* =========================================
   BROWSER NOTIFICATION
========================================= */

function requestBrowserNotification(
    order
) {

    if (
        !("Notification" in window)
    ) {
        return;
    }


    if (
        Notification.permission ===
        "default"
    ) {

        Notification.requestPermission()
            .then(function (permission) {

                if (
                    permission === "granted"
                ) {

                    createBrowserNotification(
                        order
                    );

                }

            })
            .catch(function () {});

        return;
    }


    if (
        Notification.permission ===
        "granted"
    ) {

        createBrowserNotification(
            order
        );

    }

}


/* =========================================
   CREATE BROWSER NOTIFICATION
========================================= */

function createBrowserNotification(
    order
) {

    const orderId =
        order.id || "";

    const customerName =
        order.customer_name ||
        "عميل جديد";

    const total =
        order.total || 0;


    try {

        const notification =
            new Notification(
                "🔔 طلب جديد - Menu Smart",
                {
                    body:
                        "طلب #" +
                        orderId +
                        " من " +
                        customerName +
                        "\nالإجمالي: " +
                        total +
                        " جنيه",

                    icon:
                        "/static/images/logo.png",

                    tag:
                        "menusmart-order-" +
                        orderId
                }
            );


        notification.onclick =
            function () {

                window.focus();

                window.location.href =
                    "/orders";

                notification.close();

            };

    } catch (error) {

        console.warn(
            "Browser notification error:",
            error
        );

    }

}


/* =========================================
   PLAY NEW ORDER SOUND
========================================= */

function playNewOrderSound() {

    /*
     * المتصفح يحتاج تفاعل من المستخدم.
     */

    if (!orderSoundEnabled) {
        return;
    }


    try {

        const AudioContext =
            window.AudioContext ||
            window.webkitAudioContext;

        if (!AudioContext) {
            return;
        }


        if (!orderAudioContext) {

            orderAudioContext =
                new AudioContext();

        }


        if (
            orderAudioContext.state ===
            "suspended"
        ) {

            orderAudioContext.resume();

        }


        const ctx =
            orderAudioContext;


        const now =
            ctx.currentTime;


        /*
         * ثلاث نغمات واضحة.
         */

        playTone(
            ctx,
            880,
            now,
            0.18
        );

        playTone(
            ctx,
            1046.50,
            now + 0.20,
            0.18
        );

        playTone(
            ctx,
            1318.51,
            now + 0.40,
            0.28
        );

    } catch (error) {

        console.warn(
            "Order sound error:",
            error
        );

    }

}


/* =========================================
   PLAY TONE
========================================= */

function playTone(
    ctx,
    frequency,
    startTime,
    duration
) {

    const oscillator =
        ctx.createOscillator();

    const gain =
        ctx.createGain();


    oscillator.type =
        "sine";


    oscillator.frequency.setValueAtTime(
        frequency,
        startTime
    );


    gain.gain.setValueAtTime(
        0.0001,
        startTime
    );


    gain.gain.exponentialRampToValueAtTime(
        0.22,
        startTime + 0.02
    );


    gain.gain.exponentialRampToValueAtTime(
        0.0001,
        startTime + duration
    );


    oscillator.connect(gain);

    gain.connect(
        ctx.destination
    );


    oscillator.start(
        startTime
    );


    oscillator.stop(
        startTime + duration
    );

}


/* =========================================
   IN-PAGE NEW ORDER ALERT
========================================= */

function showNewOrderAlert(
    orderId,
    customerName,
    total
) {

    let container =
        document.getElementById(
            "newOrderAlerts"
        );


    if (!container) {

        container =
            document.createElement(
                "div"
            );


        container.id =
            "newOrderAlerts";


        container.style.position =
            "fixed";

        container.style.top =
            "90px";

        container.style.right =
            "20px";

        container.style.width =
            "min(380px, calc(100vw - 40px))";

        container.style.zIndex =
            "99999";

        container.style.display =
            "flex";

        container.style.flexDirection =
            "column";

        container.style.gap =
            "12px";


        document.body.appendChild(
            container
        );

    }


    const alert =
        document.createElement(
            "div"
        );


    alert.style.background =
        "#111";

    alert.style.color =
        "#fff";

    alert.style.border =
        "1px solid #d4af37";

    alert.style.borderRadius =
        "18px";

    alert.style.padding =
        "18px";

    alert.style.boxShadow =
        "0 18px 45px rgba(0,0,0,.25)";

    alert.style.fontFamily =
        "inherit";

    alert.style.direction =
        "rtl";

    alert.style.opacity =
        "0";

    alert.style.transform =
        "translateY(-15px)";

    alert.style.transition =
        "all .3s ease";


    alert.innerHTML = `

        <div style="
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:12px;
            margin-bottom:12px;
        ">

            <strong style="
                font-size:16px;
                color:#d4af37;
            ">
                🔔 طلب جديد
            </strong>

            <button
                type="button"
                data-close-order-alert
                style="
                    border:0;
                    background:rgba(255,255,255,.08);
                    color:#fff;
                    width:30px;
                    height:30px;
                    border-radius:8px;
                    cursor:pointer;
                    font-size:16px;
                "
            >
                ×
            </button>

        </div>


        <div style="
            line-height:1.9;
            font-size:13px;
        ">

            <div>
                <strong>
                    طلب #${escapeOrderText(orderId)}
                </strong>
            </div>

            <div>
                العميل:
                ${escapeOrderText(customerName)}
            </div>

            <div>
                الإجمالي:
                <strong>
                    ${escapeOrderText(total)}
                    جنيه
                </strong>
            </div>

        </div>


        <a
            href="/orders"
            style="
                display:block;
                margin-top:14px;
                padding:10px;
                text-align:center;
                background:#d4af37;
                color:#111;
                border-radius:10px;
                text-decoration:none;
                font-size:12px;
                font-weight:900;
            "
        >
            عرض الطلبات
        </a>

    `;


    container.appendChild(
        alert
    );


    const closeButton =
        alert.querySelector(
            "[data-close-order-alert]"
        );


    if (closeButton) {

        closeButton.addEventListener(
            "click",
            function () {

                removeOrderAlert(
                    alert
                );

            }
        );

    }


    requestAnimationFrame(
        function () {

            alert.style.opacity =
                "1";

            alert.style.transform =
                "translateY(0)";

        }
    );


    setTimeout(
        function () {

            removeOrderAlert(
                alert
            );

        },
        10000
    );

}


/* =========================================
   REMOVE ORDER ALERT
========================================= */

function removeOrderAlert(
    alert
) {

    if (!alert) {
        return;
    }


    alert.style.opacity =
        "0";

    alert.style.transform =
        "translateY(-10px)";


    setTimeout(
        function () {

            if (alert.parentNode) {

                alert.parentNode.removeChild(
                    alert
                );

            }

        },
        300
    );

}


/* =========================================
   ESCAPE TEXT
========================================= */

function escapeOrderText(
    value
) {

    return String(value ?? "")
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


/* =========================================
   DASHBOARD MESSAGE
========================================= */

function showDashboardMessage(
    message,
    type = "success"
) {

    let container =
        document.querySelector(
            ".dashboard-message-container"
        );


    if (!container) {

        container =
            document.createElement(
                "div"
            );


        container.className =
            "dashboard-message-container";


        container.style.position =
            "fixed";

        container.style.top =
            "90px";

        container.style.left =
            "20px";

        container.style.zIndex =
            "5000";

        container.style.display =
            "flex";

        container.style.flexDirection =
            "column";

        container.style.gap =
            "10px";


        document.body.appendChild(
            container
        );

    }


    const messageElement =
        document.createElement(
            "div"
        );


    messageElement.textContent =
        message;


    messageElement.style.padding =
        "13px 18px";

    messageElement.style.borderRadius =
        "12px";

    messageElement.style.background =
        "#fff";

    messageElement.style.boxShadow =
        "0 10px 30px rgba(0,0,0,0.12)";

    messageElement.style.fontSize =
        "13px";

    messageElement.style.fontWeight =
        "700";

    messageElement.style.border =
        "1px solid #e7e7ed";


    if (type === "success") {

        messageElement.style.color =
            "#147b4c";

    } else if (type === "error") {

        messageElement.style.color =
            "#c62828";

    } else if (type === "warning") {

        messageElement.style.color =
            "#9a6a00";

    } else {

        messageElement.style.color =
            "#155da8";

    }


    container.appendChild(
        messageElement
    );


    setTimeout(
        function () {

            messageElement.style.opacity =
                "0";

            messageElement.style.transform =
                "translateY(-5px)";

            messageElement.style.transition =
                "0.3s";


            setTimeout(
                function () {

                    messageElement.remove();

                },
                300
            );

        },
        3000
    );

}


/* =========================================
   FORMAT DASHBOARD NUMBERS
========================================= */

function formatDashboardNumber(
    value
) {

    const number =
        Number(value);

    if (Number.isNaN(number)) {
        return "0";
    }


    return new Intl.NumberFormat(
        "en-US"
    ).format(number);

}


/* =========================================
   CONFIRM ACTION
========================================= */

function confirmDashboardAction(
    message =
        "هل أنت متأكد من تنفيذ هذا الإجراء؟"
) {

    return window.confirm(
        message
    );

}
document.addEventListener("click", enableOrderSound, { once: true });
