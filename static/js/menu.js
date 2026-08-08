document.addEventListener("DOMContentLoaded", function () {

    /* =========================================
       MENU SEARCH
    ========================================= */

    const searchInput =
        document.querySelector(".menu-search, #menuSearch");

    const productCards =
        document.querySelectorAll(
            ".menu-product-card, .public-product-card"
        );

    if (searchInput) {

        searchInput.addEventListener("input", function () {

            const value =
                searchInput.value.trim().toLowerCase();

            let visible = 0;

            productCards.forEach(function (card) {

                const text =
                    (
                        card.textContent ||
                        ""
                    ).toLowerCase();

                const name =
                    (
                        card.dataset.name ||
                        ""
                    ).toLowerCase();

                const matched =
                    !value ||
                    text.includes(value) ||
                    name.includes(value);

                card.style.display =
                    matched ? "" : "none";

                if (matched) {
                    visible++;
                }

            });

            const searchEmpty =
                document.getElementById("searchEmpty");

            if (searchEmpty) {
                searchEmpty.style.display =
                    visible ? "none" : "";
            }

        });

    }


    /* =========================================
       CATEGORY FILTER
    ========================================= */

    const categoryButtons =
        document.querySelectorAll(
            ".menu-category"
        );

    let activeCategory = "all";

    function filterCategories() {

        const searchValue =
            searchInput
                ? searchInput.value.trim().toLowerCase()
                : "";

        let visible = 0;

        productCards.forEach(function (card) {

            const category =
                String(
                    card.dataset.category || ""
                );

            const name =
                String(
                    card.dataset.name ||
                    card.textContent ||
                    ""
                ).toLowerCase();

            const categoryOK =
                activeCategory === "all" ||
                category === activeCategory;

            const searchOK =
                !searchValue ||
                name.includes(searchValue);

            if (categoryOK && searchOK) {

                card.style.display = "";
                visible++;

            } else {

                card.style.display = "none";

            }

        });

        const searchEmpty =
            document.getElementById("searchEmpty");

        if (searchEmpty) {
            searchEmpty.style.display =
                visible ? "none" : "";
        }

    }


    categoryButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            categoryButtons.forEach(function (item) {
                item.classList.remove("active");
            });

            button.classList.add("active");

            activeCategory =
                String(
                    button.dataset.category || "all"
                );

            filterCategories();

        });

    });


    /* =========================================
       CART
    ========================================= */

    updateCartInterface();
    renderCartPage();


    /* =========================================
       ADD PRODUCT
       يدعم الكود القديم والجديد
    ========================================= */

    document.querySelectorAll(
        ".add-product-btn, [data-add-to-cart], [data-add-product]"
    ).forEach(function (button) {

        if (
            button.disabled ||
            button.hasAttribute("data-cart-listener")
        ) {
            return;
        }

        button.setAttribute(
            "data-cart-listener",
            "true"
        );

        button.addEventListener("click", function () {

            const product =
                getProductFromButton(button);

            if (!product) {
                showMenuToast(
                    "تعذر إضافة المنتج",
                    "error"
                );
                return;
            }

            addToCart(product);

            /* فتح السلة تلقائيًا إذا كانت موجودة */
            openCart();

        });

    });


    /* =========================================
       CART BUTTON
    ========================================= */

    document.querySelectorAll(
        ".menu-cart-button, [data-open-cart]"
    ).forEach(function (button) {

        button.addEventListener("click", function () {

            openCart();

        });

    });


    /* =========================================
       CLOSE CART
    ========================================= */

    const closeCartButton =
        document.getElementById("closeCartBtn");

    if (closeCartButton) {

        closeCartButton.addEventListener(
            "click",
            closeCart
        );

    }


    const cartOverlay =
        document.getElementById("cartOverlay");

    if (cartOverlay) {

        cartOverlay.addEventListener(
            "click",
            closeCart
        );

    }


    /* =========================================
       CART QUANTITY
    ========================================= */

    document.addEventListener(
        "click",
        function (event) {

            const increase =
                event.target.closest(
                    "[data-cart-increase]"
                );

            const decrease =
                event.target.closest(
                    "[data-cart-decrease]"
                );

            const oldIncrease =
                event.target.closest(
                    "[data-cart-increase]"
                );

            if (increase || oldIncrease) {

                const button =
                    increase || oldIncrease;

                const productId =
                    button.getAttribute(
                        "data-cart-increase"
                    );

                changeCartQuantity(
                    productId,
                    1
                );

                return;
            }

            if (decrease) {

                const productId =
                    decrease.getAttribute(
                        "data-cart-decrease"
                    );

                changeCartQuantity(
                    productId,
                    -1
                );

            }

        }
    );


    /* =========================================
       REMOVE CART ITEM
    ========================================= */

    document.addEventListener(
        "click",
        function (event) {

            const button =
                event.target.closest(
                    "[data-remove-cart]"
                );

            if (!button) {
                return;
            }

            const productId =
                button.getAttribute(
                    "data-remove-cart"
                );

            removeFromCart(productId);

        }
    );


    /* =========================================
       CART QUANTITY INPUT
    ========================================= */

    document.addEventListener(
        "change",
        function (event) {

            const input =
                event.target.closest(
                    "[data-cart-quantity-input]"
                );

            if (!input) {
                return;
            }

            const productId =
                input.getAttribute(
                    "data-cart-quantity-input"
                );

            let quantity =
                parseInt(input.value, 10);

            if (
                Number.isNaN(quantity) ||
                quantity < 1
            ) {
                quantity = 1;
            }

            setCartQuantity(
                productId,
                quantity
            );

        }
    );


    /* =========================================
       CHECKOUT
    ========================================= */

    const checkoutButton =
        document.getElementById("checkoutBtn");

    if (checkoutButton) {

        checkoutButton.addEventListener(
            "click",
            function () {

                const cart =
                    loadCart();

                if (!cart.length) {

                    showMenuToast(
                        "السلة فارغة",
                        "error"
                    );

                    return;
                }

                const checkoutUrl =
                    checkoutButton.getAttribute(
                        "data-checkout-url"
                    );

                if (checkoutUrl) {

                    window.location.href =
                        checkoutUrl;

                } else {

                    window.location.href =
                        "/checkout";

                }

            }
        );

    }


    /* =========================================
       CHECKOUT FORM
    ========================================= */

    const checkoutForm =
        document.querySelector(
            "[data-checkout-form]"
        );

    if (checkoutForm) {

        checkoutForm.addEventListener(
            "submit",
            function () {

                const hidden =
                    checkoutForm.querySelector(
                        "[data-cart-json]"
                    );

                if (hidden) {

                    hidden.value =
                        JSON.stringify(
                            loadCart()
                        );

                }

            }
        );

    }


    /* =========================================
       CLEAR CART
    ========================================= */

    document.querySelectorAll(
        "[data-clear-cart]"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const confirmed =
                    window.confirm(
                        "هل تريد إفراغ السلة بالكامل؟"
                    );

                if (!confirmed) {
                    return;
                }

                clearCart();

            }
        );

    });


    /* =========================================
       SHARE MENU
    ========================================= */

    document.querySelectorAll(
        "[data-share-menu]"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            async function () {

                const url =
                    button.getAttribute(
                        "data-share-menu"
                    ) ||
                    window.location.href;

                const title =
                    document.title ||
                    "Menu Smart";

                if (navigator.share) {

                    try {

                        await navigator.share({
                            title: title,
                            url: url
                        });

                    } catch (error) {

                        /* المستخدم أغلق المشاركة */

                    }

                } else {

                    try {

                        await navigator.clipboard.writeText(
                            url
                        );

                        showMenuToast(
                            "تم نسخ رابط المنيو"
                        );

                    } catch (error) {

                        showMenuToast(
                            "تعذر نسخ الرابط",
                            "error"
                        );

                    }

                }

            }
        );

    });


    /* =========================================
       QR PRINT
    ========================================= */

    document.querySelectorAll(
        "[data-print-qr]"
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                window.print();

            }
        );

    });


});


/* =========================================
   LOAD CART
========================================= */

function loadCart() {

    try {

        const saved =
            localStorage.getItem(
                "menusmart_cart"
            );

        if (!saved) {
            return [];
        }

        const cart =
            JSON.parse(saved);

        if (!Array.isArray(cart)) {
            return [];
        }

        return cart.map(function (item) {

            return {

                id:
                    String(item.id),

                name:
                    item.name || "منتج",

                price:
                    Number(item.price) || 0,

                image:
                    item.image || "",

                quantity:
                    Math.max(
                        1,
                        Number(item.quantity) || 1
                    )

            };

        });

    } catch (error) {

        return [];

    }

}


/* =========================================
   SAVE CART
========================================= */

function saveCart(cart) {

    localStorage.setItem(
        "menusmart_cart",
        JSON.stringify(cart)
    );

}


/* =========================================
   GET PRODUCT
========================================= */

function getProductFromButton(button) {

    if (!button) {
        return null;
    }

    const card =
        button.closest(
            ".public-product-card, .menu-product-card, [data-product-container]"
        );


    const id =
        button.getAttribute(
            "data-product-id"
        ) ||
        button.getAttribute(
            "data-add-to-cart"
        ) ||
        button.getAttribute(
            "data-add-product"
        ) ||
        card?.getAttribute(
            "data-product-id"
        );


    if (!id) {
        return null;
    }


    const name =
        button.getAttribute(
            "data-product-name"
        ) ||
        card?.getAttribute(
            "data-product-name"
        ) ||
        card?.querySelector(
            ".public-product-title-row h2, h2, h3"
        )?.textContent?.trim() ||
        "منتج";


    const price =
        parseFloat(
            button.getAttribute(
                "data-product-price"
            )
        ) ||
        parseFloat(
            card?.getAttribute(
                "data-product-price"
            )
        ) ||
        0;


    const image =
        button.getAttribute(
            "data-product-image"
        ) ||
        card?.getAttribute(
            "data-product-image"
        ) ||
        card?.querySelector(
            ".public-product-image img, img"
        )?.getAttribute("src") ||
        "";


    let quantity = 1;


    const quantityInput =
        card?.querySelector(
            "[data-product-quantity-input], [data-product-quantity] input"
        );


    if (quantityInput) {

        quantity =
            parseInt(
                quantityInput.value,
                10
            ) || 1;

    }


    return {

        id: String(id),

        name: name,

        price: Number(price) || 0,

        image: image,

        quantity:
            Math.max(
                1,
                quantity
            )

    };

}


/* =========================================
   ADD TO CART
========================================= */

function addToCart(product) {

    if (
        !product ||
        !product.id
    ) {
        return;
    }


    const cart =
        loadCart();


    const existing =
        cart.find(function (item) {

            return String(item.id) ===
                String(product.id);

        });


    const quantity =
        Math.max(
            1,
            Number(product.quantity) || 1
        );


    if (existing) {

        existing.quantity +=
            quantity;

    } else {

        cart.push({

            id:
                String(product.id),

            name:
                product.name ||
                "منتج",

            price:
                Number(product.price) || 0,

            image:
                product.image || "",

            quantity:
                quantity

        });

    }


    saveCart(cart);

    updateCartInterface();

    renderCartPage();

    showMenuToast(
        "تمت إضافة المنتج إلى السلة"
    );

}


/* =========================================
   REMOVE FROM CART
========================================= */

function removeFromCart(productId) {

    let cart =
        loadCart();


    cart =
        cart.filter(function (item) {

            return String(item.id) !==
                String(productId);

        });


    saveCart(cart);

    updateCartInterface();

    renderCartPage();

    showMenuToast(
        "تم حذف المنتج من السلة"
    );

}


/* =========================================
   CHANGE QUANTITY
========================================= */

function changeCartQuantity(
    productId,
    amount
) {

    let cart =
        loadCart();


    const item =
        cart.find(function (product) {

            return String(product.id) ===
                String(productId);

        });


    if (!item) {
        return;
    }


    item.quantity =
        (
            Number(item.quantity) || 1
        ) +
        Number(amount);


    if (item.quantity <= 0) {

        cart =
            cart.filter(function (product) {

                return String(product.id) !==
                    String(productId);

            });

    }


    saveCart(cart);

    updateCartInterface();

    renderCartPage();

}


/* =========================================
   SET QUANTITY
========================================= */

function setCartQuantity(
    productId,
    quantity
) {

    const cart =
        loadCart();


    const item =
        cart.find(function (product) {

            return String(product.id) ===
                String(productId);

        });


    if (!item) {
        return;
    }


    item.quantity =
        Math.max(
            1,
            Number(quantity) || 1
        );


    saveCart(cart);

    updateCartInterface();

    renderCartPage();

}


/* =========================================
   CLEAR CART
========================================= */

function clearCart() {

    saveCart([]);

    updateCartInterface();

    renderCartPage();

    closeCart();

    showMenuToast(
        "تم إفراغ السلة"
    );

}


/* =========================================
   CART COUNT
========================================= */

function getCartCount() {

    const cart =
        loadCart();


    return cart.reduce(
        function (total, item) {

            return total +
                (
                    Number(item.quantity) || 0
                );

        },
        0
    );

}


/* =========================================
   CART TOTAL
========================================= */

function getCartTotal() {

    const cart =
        loadCart();


    return cart.reduce(
        function (total, item) {

            return total +
                (
                    (
                        Number(item.price) || 0
                    ) *
                    (
                        Number(item.quantity) || 0
                    )
                );

        },
        0
    );

}


/* =========================================
   UPDATE CART INTERFACE
========================================= */

function updateCartInterface() {

    const cart =
        loadCart();

    const count =
        getCartCount();

    const total =
        getCartTotal();


    /* عدد المنتجات */

    document.querySelectorAll(
        ".menu-cart-count, [data-cart-count], #cartCount"
    ).forEach(function (element) {

        element.textContent =
            count;

    });


    /* الإجمالي */

    document.querySelectorAll(
        "[data-cart-total]"
    ).forEach(function (element) {

        element.textContent =
            formatMenuPrice(total) +
            " جنيه";

    });


    const cartTotalElement =
        document.getElementById(
            "cartTotal"
        );

    if (cartTotalElement) {

        cartTotalElement.textContent =
            formatMenuPrice(total) +
            " جنيه";

    }


    /* زر متابعة الطلب */

    const checkoutButton =
        document.getElementById(
            "checkoutBtn"
        );

    if (checkoutButton) {

        checkoutButton.disabled =
            cart.length === 0;

    }


    /* إظهار/إخفاء حالة السلة */

    document.querySelectorAll(
        "[data-cart-empty]"
    ).forEach(function (element) {

        element.style.display =
            count === 0 ? "" : "none";

    });


    document.querySelectorAll(
        "[data-cart-has-items]"
    ).forEach(function (element) {

        element.style.display =
            count > 0 ? "" : "none";

    });

}


/* =========================================
   RENDER CART DRAWER + CART PAGE
========================================= */

function renderCartPage() {

    const cart =
        loadCart();


    /* -----------------------------------------
       السلة الجانبية الموجودة في menu.html
    ----------------------------------------- */

    const drawerItems =
        document.getElementById(
            "cartItems"
        );


    if (drawerItems) {

        if (!cart.length) {

            drawerItems.innerHTML = `

                <div class="cart-empty">

                    <div>🛒</div>

                    <h3>
                        السلة فارغة
                    </h3>

                    <p>
                        أضف المنتجات التي تريد طلبها.
                    </p>

                </div>

            `;

        } else {

            drawerItems.innerHTML =
                cart.map(function (item) {

                    const id =
                        escapeMenuHtml(
                            item.id
                        );

                    const name =
                        escapeMenuHtml(
                            item.name
                        );

                    const quantity =
                        Number(item.quantity) || 1;

                    const price =
                        Number(item.price) || 0;

                    const itemTotal =
                        price * quantity;


                    return `

                        <div class="cart-item">

                            <div class="cart-item-info">

                                <strong>
                                    ${name}
                                </strong>

                                <span>
                                    ${formatMenuPrice(price)}
                                    جنيه
                                </span>

                            </div>


                            <div class="cart-item-actions">

                                <button
                                    type="button"
                                    data-cart-decrease="${id}">
                                    −
                                </button>

                                <b>
                                    ${quantity}
                                </b>

                                <button
                                    type="button"
                                    data-cart-increase="${id}">
                                    +
                                </button>

                            </div>


                            <strong class="cart-item-total">

                                ${formatMenuPrice(itemTotal)}
                                جنيه

                            </strong>


                            <button
                                type="button"
                                class="cart-remove"
                                data-remove-cart="${id}">
                                ×
                            </button>

                        </div>

                    `;

                }).join("");

        }

    }


    /* -----------------------------------------
       صفحة السلة المستقلة
    ----------------------------------------- */

    const cartPageContainer =
        document.querySelector(
            "[data-cart-items]"
        );


    if (cartPageContainer) {

        if (!cart.length) {

            cartPageContainer.innerHTML = `

                <div class="menu-empty">

                    <div class="menu-empty-icon">
                        🛒
                    </div>

                    <h2>
                        السلة فارغة
                    </h2>

                    <p>
                        لم تقم بإضافة أي منتجات إلى السلة بعد.
                    </p>

                </div>

            `;

        } else {

            cartPageContainer.innerHTML =
                cart.map(function (item) {

                    const id =
                        escapeMenuHtml(
                            item.id
                        );

                    const name =
                        escapeMenuHtml(
                            item.name
                        );

                    const image =
                        escapeMenuHtml(
                            item.image || ""
                        );

                    const quantity =
                        Number(item.quantity) || 1;

                    const price =
                        Number(item.price) || 0;

                    const itemTotal =
                        price * quantity;


                    return `

                        <div class="cart-item">

                            <div class="cart-item-image">

                                ${
                                    image
                                    ?
                                    `<img
                                        src="${image}"
                                        alt="${name}"
                                    >`
                                    :
                                    `<div class="menu-product-image-placeholder">
                                        🍽️
                                    </div>`
                                }

                            </div>


                            <div class="cart-item-info">

                                <h3>
                                    ${name}
                                </h3>

                                <p>
                                    ${formatMenuPrice(price)}
                                    جنيه
                                </p>

                                <div class="cart-item-price">

                                    ${formatMenuPrice(itemTotal)}
                                    جنيه

                                </div>

                            </div>


                            <div class="cart-item-actions">

                                <div class="cart-quantity">

                                    <button
                                        type="button"
                                        data-cart-decrease="${id}">
                                        −
                                    </button>

                                    <input
                                        type="number"
                                        min="1"
                                        value="${quantity}"
                                        data-cart-quantity-input="${id}"
                                    >

                                    <button
                                        type="button"
                                        data-cart-increase="${id}">
                                        +
                                    </button>

                                </div>


                                <button
                                    type="button"
                                    class="cart-remove"
                                    data-remove-cart="${id}">
                                    ×
                                </button>

                            </div>

                        </div>

                    `;

                }).join("");

        }

    }


    updateCartInterface();

}


/* =========================================
   OPEN CART
========================================= */

function openCart() {

    const drawer =
        document.getElementById(
            "cartDrawer"
        );

    const overlay =
        document.getElementById(
            "cartOverlay"
        );


    if (drawer) {

        drawer.classList.add(
            "open"
        );

        drawer.setAttribute(
            "aria-hidden",
            "false"
        );

    }


    if (overlay) {

        overlay.classList.add(
            "active"
        );

    }


    document.body.classList.add(
        "cart-open"
    );

}


/* =========================================
   CLOSE CART
========================================= */

function closeCart() {

    const drawer =
        document.getElementById(
            "cartDrawer"
        );

    const overlay =
        document.getElementById(
            "cartOverlay"
        );


    if (drawer) {

        drawer.classList.remove(
            "open"
        );

        drawer.setAttribute(
            "aria-hidden",
            "true"
        );

    }


    if (overlay) {

        overlay.classList.remove(
            "active"
        );

    }


    document.body.classList.remove(
        "cart-open"
    );

}


/* =========================================
   FORMAT PRICE
========================================= */

function formatMenuPrice(value) {

    return new Intl.NumberFormat(
        "ar-EG",
        {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }
    ).format(
        Number(value) || 0
    );

}


/* =========================================
   ESCAPE HTML
========================================= */

function escapeMenuHtml(value) {

    const div =
        document.createElement(
            "div"
        );

    div.textContent =
        value == null
            ? ""
            : String(value);

    return div.innerHTML;

}


/* =========================================
   TOAST
========================================= */

function showMenuToast(
    message,
    type = "success"
) {

    let container =
        document.querySelector(
            ".menusmart-menu-toast-container"
        );


    if (!container) {

        container =
            document.createElement(
                "div"
            );

        container.className =
            "menusmart-menu-toast-container";

        Object.assign(
            container.style,
            {
                position: "fixed",
                bottom: "25px",
                left: "20px",
                right: "20px",
                zIndex: "5000",
                display: "flex",
                justifyContent: "center",
                pointerEvents: "none"
            }
        );

        document.body.appendChild(
            container
        );

    }


    const toast =
        document.createElement(
            "div"
        );


    toast.textContent =
        message;


    Object.assign(
        toast.style,
        {
            padding: "13px 20px",
            borderRadius: "14px",
            background:
                type === "error"
                    ? "#c62828"
                    : "#111",
            color: "#fff",
            fontSize: "13px",
            fontWeight: "700",
            boxShadow:
                "0 10px 30px rgba(0,0,0,.2)",
            transition: ".3s",
            pointerEvents: "auto"
        }
    );


    container.appendChild(
        toast
    );


    setTimeout(function () {

        toast.style.opacity = "0";
        toast.style.transform =
            "translateY(8px)";

        setTimeout(function () {

            toast.remove();

        }, 300);

    }, 2200);

}