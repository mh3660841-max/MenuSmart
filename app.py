from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

from functools import wraps

import os
import sqlite3
import uuid
import qrcode
import base64
import cloudinary
import cloudinary.uploader
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)
from io import BytesIO

from database import (
    init_db,
    get_db,
    query_db,
    execute_db
)

from config import (
    SECRET_KEY,
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS
)


# =========================================================
# التطبيق
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = SECRET_KEY

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER




# =========================================================
# إعدادات الجلسة والأمان
# =========================================================

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

# =========================================================
# مجلد رفع الصور العام
# =========================================================

os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)


# =========================================================
# مجلد صور المنتجات والأقسام
# =========================================================

CATEGORY_PRODUCT_UPLOAD_FOLDER = UPLOAD_FOLDER

os.makedirs(
    CATEGORY_PRODUCT_UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# تهيئة قاعدة البيانات
# =========================================================

with app.app_context():
    init_db()

# =========================================================
# الملفات المسموح بها
# =========================================================

ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


# =========================================================
# فحص امتداد الملف
# =========================================================

def allowed_file(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return (
        extension in ALLOWED_IMAGE_EXTENSIONS
        or extension in ALLOWED_EXTENSIONS
    )


# =========================================================
# تسجيل الدخول
# =========================================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        user_id = session.get("user_id")

        if not user_id:

            session.clear()

            flash(
                "يجب تسجيل الدخول أولاً.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        user = query_db(
            """
            SELECT *
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            [user_id],
            one=True
        )

        if user is None:

            session.clear()

            flash(
                "الحساب غير موجود.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return decorated_function


# =========================================================
# المطعم مطلوب
# =========================================================

def restaurant_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "يجب تسجيل الدخول أولاً.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        restaurant = query_db(
            """
            SELECT *
            FROM restaurants
            WHERE owner_id = %s
            LIMIT 1
            """,
            [
                session["user_id"]
            ],
            one=True
        )

        if restaurant is None:

            flash(
                "يجب إنشاء المطعم أولاً.",
                "warning"
            )

            return redirect(
                url_for("profile")
            )

        return function(*args, **kwargs)

    return decorated_function
# =========================================================
# الأدمن مطلوب
# =========================================================

def admin_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        # -------------------------------------------------
        # التأكد من تسجيل الدخول
        # -------------------------------------------------

        if "user_id" not in session:

            flash(
                "يجب تسجيل الدخول أولاً.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        # -------------------------------------------------
        # جلب المستخدم الحالي
        # -------------------------------------------------

        user = query_db(
            """
            SELECT *
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (
                session["user_id"],
            ),
            one=True
        )

        # -------------------------------------------------
        # التأكد من وجود المستخدم
        # -------------------------------------------------

        if user is None:

            session.clear()

            flash(
                "الحساب غير موجود.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        # -------------------------------------------------
        # التأكد أن الحساب نشط
        # -------------------------------------------------

        if not user["is_active"]:

            session.clear()

            flash(
                "هذا الحساب غير نشط.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        # -------------------------------------------------
        # التأكد أن المستخدم أدمن
        # -------------------------------------------------

        if user["role"] != "admin":

            flash(
                "ليس لديك صلاحية للوصول إلى لوحة الإدارة.",
                "danger"
            )

            return redirect(
                url_for("dashboard")
            )

        # -------------------------------------------------
        # السماح للأدمن
        # -------------------------------------------------

        return function(
            *args,
            **kwargs
        )

    return decorated_function

# =========================================================
# إعادة تعيين كلمة مرور صاحب المطعم بواسطة الأدمن
# =========================================================

@app.route(
    "/admin/users/<int:user_id>/reset-password",
    methods=["POST"]
)
@admin_required
def admin_reset_password(user_id):

    new_password = request.form.get(
        "new_password",
        ""
    ).strip()

    if len(new_password) < 6:

        flash(
            "كلمة المرور يجب أن تكون 6 أحرف أو أكثر.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    user = query_db(
        """
        SELECT *
        FROM users
        WHERE id = %s
        AND role != 'admin'
        LIMIT 1
        """,
        [
            user_id
        ],
        one=True
    )

    if user is None:

        flash(
            "المستخدم غير موجود.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    password_hash = generate_password_hash(
        new_password
    )

    execute_db(
        """
        UPDATE users
        SET password = %s
        WHERE id = %s
        AND role != 'admin'
        """,
        [
            password_hash,
            user_id
        ]
    )

    flash(
        f"تم تغيير كلمة مرور {user['name']} بنجاح.",
        "success"
    )

    return redirect(
        url_for("admin")
    )
# =========================================================
# المستخدم الحالي
# =========================================================

def current_user():

    if "user_id" not in session:
        return None

    return query_db(
        """
        SELECT
            id,
            name,
            email,
            phone,
            created_at
        FROM users
        WHERE id = %s
        """,
        (
            session["user_id"],
        ),
        one=True
    )


# =========================================================
# المطعم الحالي
# =========================================================

def current_restaurant():

    if "user_id" not in session:
        return None

    return query_db(
        """
        SELECT *
        FROM restaurants
        WHERE owner_id = %s
        LIMIT 1
        """,
        (
            session["user_id"],
        ),
        one=True
    )


# =========================================================
# لوحة الإدارة
# =========================================================

@app.route("/admin")
@admin_required
def admin():

    users = query_db(
        """
        SELECT *
        FROM users
        ORDER BY id DESC
        """
    )

    restaurants = query_db(
        """
        SELECT *
        FROM restaurants
        ORDER BY id DESC
        """
    )

    user = current_user()

    return render_template(
        "admin.html",
        user=user,
        users=users,
        restaurants=restaurants
    )


# =========================================================
# الموافقة على حساب صاحب المطعم
# =========================================================

@app.route(
    "/admin/users/<int:user_id>/approve",
    methods=["POST"]
)
@admin_required
def approve_user(user_id):

    execute_db(
        """
        UPDATE users
        SET account_status = 'approved',
            is_active = 1
        WHERE id = %s
          AND role != 'admin'
        """,
        [user_id]
    )

    flash(
        "تمت الموافقة على الحساب بنجاح.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# رفض حساب صاحب المطعم
# =========================================================

@app.route(
    "/admin/users/<int:user_id>/reject",
    methods=["POST"]
)
@admin_required
def reject_user(user_id):

    execute_db(
        """
        UPDATE users
        SET account_status = 'rejected',
            is_active = 0
        WHERE id = %s
          AND role != 'admin'
        """,
        [user_id]
    )

    flash(
        "تم رفض الحساب.",
        "warning"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# إيقاف حساب صاحب المطعم
# =========================================================

@app.route(
    "/admin/users/<int:user_id>/suspend",
    methods=["POST"]
)
@admin_required
def suspend_user(user_id):

    execute_db(
        """
        UPDATE users
        SET account_status = 'suspended',
            is_active = 0
        WHERE id = %s
          AND role != 'admin'
        """,
        [user_id]
    )

    flash(
        "تم إيقاف الحساب.",
        "warning"
    )

    return redirect(
        url_for("admin")
    )
    # =========================================================
# إعادة تفعيل حساب صاحب المطعم
# =========================================================

@app.route(
    "/admin/users/<int:user_id>/activate",
    methods=["POST"]
)
@admin_required
def activate_user(user_id):

    execute_db(
        """
        UPDATE users
        SET account_status = 'approved',
            is_active = 1
        WHERE id = %s
          AND role != 'admin'
        """,
        [user_id]
    )

    flash(
        "تمت إعادة تفعيل الحساب بنجاح.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# منع المتصفح من حفظ الصفحات الحساسة في الكاش
# =========================================================

@app.after_request
def add_no_cache_headers(response):

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, "
        "max-age=0, private"
    )

    response.headers["Pragma"] = "no-cache"

    response.headers["Expires"] = "0"

    return response
# =========================================================
# حفظ صورة
# =========================================================

def save_uploaded_image(image):

    original_name = secure_filename(
        image.filename
    )

    if not original_name:
        return None

    if "." not in original_name:
        return None

    extension = original_name.rsplit(
        ".",
        1
    )[1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    try:

        result = cloudinary.uploader.upload(
            image,
            folder="menusmart"
        )

        return result.get("secure_url")

    except Exception as e:

        print(
            "CLOUDINARY UPLOAD ERROR:",
            e
        )

        return None


# =========================================================
# الصفحة الرئيسية
# =========================================================

@app.route("/")
def home():

    restaurants = query_db(
        """
        SELECT
            id,
            name,
            slug,
            description,
            address,
            phone,
            logo,
            is_active
        FROM restaurants
        WHERE is_active = 1
        ORDER BY id DESC
        """
    )

    return render_template(
        "home.html",
        user=current_user(),
        restaurant=current_restaurant(),
        restaurants=restaurants
    )


# =========================================================
# التسجيل
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # =================================================
        # التحقق من البيانات
        # =================================================

        if not name or not email or not password:

            flash(
                "من فضلك أكمل البيانات المطلوبة.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        if password != confirm_password:

            flash(
                "كلمتا المرور غير متطابقتين.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        # =================================================
        # التأكد أن البريد غير مستخدم
        # =================================================

        existing_user = query_db(
            """
            SELECT id
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            [
                email
            ],
            one=True
        )

        if existing_user:

            flash(
                "البريد الإلكتروني مستخدم بالفعل.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        # =================================================
        # تشفير كلمة المرور
        # =================================================

        password_hash = generate_password_hash(
            password
        )

        # =================================================
        # إنشاء الحساب
        #
        # role:
        # restaurant = صاحب مطعم
        #
        # account_status:
        # pending = في انتظار موافقة الأدمن
        # =================================================

        user_id = execute_db(
            """
            INSERT INTO users
            (
                name,
                email,
                phone,
                password,
                role,
                account_status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            [
                name,
                email,
                phone,
                password_hash,
                "restaurant",
                "pending"
            ]
        )

        # =================================================
        # لا نسجل دخول المستخدم تلقائيًا
        # =================================================

        flash(
            "تم إنشاء حسابك بنجاح، والحساب الآن قيد مراجعة الإدارة.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# =========================================================
# تسجيل الدخول
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    # =====================================================
    # إذا كان المستخدم مسجل الدخول بالفعل
    # =====================================================

    if "user_id" in session:

        user = query_db(
            """
            SELECT *
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            [
                session["user_id"]
            ],
            one=True
        )

        if user is not None:

            if user["role"] == "admin":

                return redirect(
                    url_for("admin")
                )

            return redirect(
                url_for("dashboard")
            )

        session.clear()

    # =====================================================
    # معالجة تسجيل الدخول
    # =====================================================

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # =================================================
        # البحث عن المستخدم
        # =================================================

        user = query_db(
            """
            SELECT *
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            [
                email
            ],
            one=True
        )

        # =================================================
        # المستخدم غير موجود
        # =================================================

        if user is None:

            flash(
                "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        # =================================================
        # التحقق من كلمة المرور
        # =================================================

        if not check_password_hash(
            user["password"],
            password
        ):

            flash(
                "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        # =================================================
        # حالة الحساب
        # =================================================

        account_status = user["account_status"]

        # =================================================
        # السماح للأدمن
        # =================================================

        if user["role"] == "admin":

            pass

        # =================================================
        # التحقق من حالة المستخدم العادي
        # =================================================

        elif account_status != "approved":

            session.clear()

            if account_status == "pending":

                flash(
                    "حسابك قيد مراجعة الإدارة ولم تتم الموافقة عليه بعد.",
                    "warning"
                )

            elif account_status == "rejected":

                flash(
                    "تم رفض الحساب من الإدارة.",
                    "danger"
                )

            elif account_status == "suspended":

                flash(
                    "تم إيقاف حسابك. يرجى التواصل مع الإدارة.",
                    "danger"
                )

            else:

                flash(
                    "حسابك غير نشط حاليًا.",
                    "danger"
                )

            return render_template(
                "login.html"
            )

        # =================================================
        # مسح أي جلسة قديمة
        # =================================================

        session.clear()

        # =================================================
        # إنشاء جلسة جديدة
        # =================================================

        session["user_id"] = user["id"]

        session["user_name"] = user["name"]

        # =================================================
        # نجاح تسجيل الدخول
        # =================================================

        flash(
            "تم تسجيل الدخول بنجاح.",
            "success"
        )

        # =================================================
        # توجيه الأدمن
        # =================================================

        if user["role"] == "admin":

            return redirect(
                url_for("admin")
            )

        # =================================================
        # توجيه صاحب المطعم
        # =================================================

        return redirect(
            url_for("dashboard")
        )

    # =====================================================
    # عرض صفحة تسجيل الدخول
    # =====================================================

    return render_template(
        "login.html"
    )
# =========================================================
# تسجيل الخروج
# =========================================================

@app.route("/logout")
def logout():

    # =====================================================
    # إنهاء الجلسة بالكامل
    # =====================================================

    session.clear()

    # =====================================================
    # رسالة تسجيل الخروج
    # =====================================================

    flash(
        "تم تسجيل الخروج بنجاح.",
        "success"
    )

    # =====================================================
    # العودة للصفحة الرئيسية
    # =====================================================

    response = redirect(
        url_for("home")
    )

    # =====================================================
    # منع المتصفح من حفظ الصفحات الحساسة
    # =====================================================

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, "
        "max-age=0, private"
    )

    response.headers["Pragma"] = "no-cache"

    response.headers["Expires"] = "0"

    return response

# =========================================================
# لوحة التحكم
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    restaurant = current_restaurant()

    if restaurant is None:

        return redirect(
            url_for("profile")
        )

    categories_count = query_db(
        """
        SELECT COUNT(*) AS count
        FROM categories
        WHERE restaurant_id = %s
        """,
        [
            restaurant["id"]
        ],
        one=True
    )

    products_count = query_db(
        """
        SELECT COUNT(*) AS count
        FROM products
        WHERE restaurant_id = %s
        """,
        [
            restaurant["id"]
        ],
        one=True
    )

    orders_count = query_db(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE restaurant_id = %s
        """,
        [
            restaurant["id"]
        ],
        one=True
    )

    customers_count = query_db(
        """
        SELECT COUNT(*) AS count
        FROM customers
        WHERE restaurant_id = %s
        """,
        [
            restaurant["id"]
        ],
        one=True
    )

    recent_orders = query_db(
        """
        SELECT *
        FROM orders
        WHERE restaurant_id = %s
        ORDER BY id DESC
        LIMIT 10
        """,
        [
            restaurant["id"]
        ]
    )

    return render_template(
        "dashboard.html",
        user=current_user(),
        restaurant=restaurant,
        categories_count=categories_count["count"],
        products_count=products_count["count"],
        orders_count=orders_count["count"],
        customers_count=customers_count["count"],
        recent_orders=recent_orders
    )
@app.route("/invite")
@login_required
def invite_restaurant():

    restaurant = current_restaurant()

    return render_template(
        "invite.html",
        restaurant=restaurant
    )

# =========================================================
# الملف الشخصي
# =========================================================

@app.route(
    "/profile",
    methods=["GET", "POST"]
)
@login_required
def profile():

    restaurant = current_restaurant()

    if request.method == "POST":

        restaurant_name = request.form.get(
            "restaurant_name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        logo = request.files.get(
            "logo"
        )

        if not restaurant_name:

            flash(
                "اسم المطعم مطلوب.",
                "danger"
            )

            return render_template(
                "profile.html",
                user=current_user(),
                restaurant=restaurant
            )

        logo_name = None

        if logo and logo.filename:

            logo_name = save_uploaded_image(
                logo
            )

            if logo_name is None:

                flash(
                    "نوع صورة الشعار غير مسموح به.",
                    "danger"
                )

                return render_template(
                    "profile.html",
                    user=current_user(),
                    restaurant=restaurant
                )

        # =====================================================
        # إنشاء مطعم جديد
        # =====================================================

        if restaurant is None:

            slug = "ms-" + uuid.uuid4().hex[:10]

            while query_db(
                """
                SELECT id
                FROM restaurants
                WHERE slug = %s
                """,
                [
                    slug
                ],
                one=True
            ):

                slug = "ms-" + uuid.uuid4().hex[:10]

            restaurant_id = execute_db(
                """
                INSERT INTO restaurants
                (
                    owner_id,
                    name,
                    slug,
                    description,
                    address,
                    phone,
                    logo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    session["user_id"],
                    restaurant_name,
                    slug,
                    description,
                    address,
                    phone,
                    logo_name
                ]
            )

            flash(
                "تم إنشاء المطعم بنجاح.",
                "success"
            )

        # =====================================================
        # تحديث المطعم الحالي
        # =====================================================

        else:

            if logo_name:

                execute_db(
                    """
                    UPDATE restaurants
                    SET
                        name = %s,
                        description = %s,
                        address = %s,
                        phone = %s,
                        logo = %s
                    WHERE id = %s
                    """,
                    [
                        restaurant_name,
                        description,
                        address,
                        phone,
                        logo_name,
                        restaurant["id"]
                    ]
                )

            else:

                execute_db(
                    """
                    UPDATE restaurants
                    SET
                        name = %s,
                        description = %s,
                        address = %s,
                        phone = %s
                    WHERE id = %s
                    """,
                    [
                        restaurant_name,
                        description,
                        address,
                        phone,
                        restaurant["id"]
                    ]
                )

            flash(
                "تم تحديث بيانات المطعم.",
                "success"
            )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "profile.html",
        user=current_user(),
        restaurant=restaurant
    )

# =========================================================
# إعدادات المطعم
# =========================================================

@app.route(
    "/settings",
    methods=["GET", "POST"]
)
@restaurant_required
def settings():

    restaurant = current_restaurant()

    settings_data = query_db(
        """
        SELECT *
        FROM restaurant_settings
        WHERE restaurant_id = %s
        LIMIT 1
        """,
        [
            restaurant["id"]
        ],
        one=True
    )

    if request.method == "POST":

        primary_color = request.form.get(
            "primary_color",
            "#111111"
        )

        secondary_color = request.form.get(
            "secondary_color",
            "#D4AF37"
        )

        currency = request.form.get(
            "currency",
            "EGP"
        )

        allow_orders = (
            1
            if request.form.get("allow_orders")
            else 0
        )

        allow_delivery = (
            1
            if request.form.get("allow_delivery")
            else 0
        )

        delivery_fee_text = request.form.get(
            "delivery_fee",
            "0"
        ).strip()

        try:

            delivery_fee = float(
                delivery_fee_text or 0
            )

            if delivery_fee < 0:
                delivery_fee = 0

        except ValueError:

            delivery_fee = 0

        if settings_data:

            execute_db(
                """
                UPDATE restaurant_settings
                SET
                    primary_color = %s,
                    secondary_color = %s,
                    currency = %s,
                    allow_orders = %s,
                    allow_delivery = %s,
                    delivery_fee = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE restaurant_id = %s
                """,
                [
                    primary_color,
                    secondary_color,
                    currency,
                    allow_orders,
                    allow_delivery,
                    delivery_fee,
                    restaurant["id"]
                ]
            )

        else:

            execute_db(
                """
                INSERT INTO restaurant_settings
                (
                    restaurant_id,
                    primary_color,
                    secondary_color,
                    currency,
                    allow_orders,
                    allow_delivery,
                    delivery_fee
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    restaurant["id"],
                    primary_color,
                    secondary_color,
                    currency,
                    allow_orders,
                    allow_delivery,
                    delivery_fee
                ]
            )

        flash(
            "تم حفظ الإعدادات بنجاح.",
            "success"
        )

        return redirect(
            url_for("settings")
        )

    settings_data = query_db(
        """
        SELECT *
        FROM restaurant_settings
        WHERE restaurant_id = %s
        LIMIT 1
        """,
        [
            restaurant["id"]
        ],
        one=True
    )

    return render_template(
        "settings.html",
        restaurant=restaurant,
        settings=settings_data
    )


# =========================================================
# إدارة الأقسام
# =========================================================

@app.route("/categories")
@restaurant_required
def categories():

    restaurant = current_restaurant()

    categories_list = query_db(
        """
        SELECT *
        FROM categories
        WHERE restaurant_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        [
            restaurant["id"]
        ]
    )

    return render_template(
        "categories.html",
        restaurant=restaurant,
        categories=categories_list
    )

# =========================================================
# إضافة قسم
# =========================================================

@app.route(
    "/categories/add",
    methods=["POST"]
)
@restaurant_required
def category_add():

    restaurant = current_restaurant()

    name = request.form.get(
        "name",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    icon = request.form.get(
        "icon",
        "🍽️"
    ).strip()

    image = request.files.get(
        "image"
    )

    if not name:

        flash(
            "اسم القسم مطلوب.",
            "danger"
        )

        return redirect(
            url_for("categories")
        )

    image_name = None

    if image and image.filename:

        image_name = save_uploaded_image(
            image
        )

        if image_name is None:

            flash(
                "نوع صورة القسم غير مسموح به.",
                "danger"
            )

            return redirect(
                url_for("categories")
            )

    execute_db(
        """
        INSERT INTO categories
        (
            restaurant_id,
            name,
            description,
            icon,
            image
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        [
            restaurant["id"],
            name,
            description,
            icon,
            image_name
        ]
    )

    flash(
        "تم إضافة القسم بنجاح.",
        "success"
    )

    return redirect(
        url_for("categories")
    )


# =========================================================
# تعديل القسم
# =========================================================

@app.route(
    "/categories/<int:category_id>/edit",
    methods=["GET", "POST"]
)
@restaurant_required
def category_edit(category_id):

    restaurant = current_restaurant()

    category = query_db(
        """
        SELECT *
        FROM categories
        WHERE id = %s
        AND restaurant_id = %s
        """,
        [
            category_id,
            restaurant["id"]
        ],
        one=True
    )

    if category is None:

        flash(
            "القسم غير موجود.",
            "danger"
        )

        return redirect(
            url_for("categories")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        icon = request.form.get(
            "icon",
            "🍽️"
        ).strip()

        sort_order = request.form.get(
            "sort_order",
            "0"
        ).strip()

        status = request.form.get(
            "status",
            "active"
        )

        image = request.files.get(
            "image"
        )

        try:

            sort_order = int(
                sort_order
            )

        except (ValueError, TypeError):

            sort_order = 0

        is_active = (
            1
            if status == "active"
            else 0
        )

        if not name:

            flash(
                "اسم القسم مطلوب.",
                "danger"
            )

            return render_template(
                "category_edit.html",
                restaurant=restaurant,
                category=category
            )

        image_name = category["image"]

        if image and image.filename:

            new_image = save_uploaded_image(
                image
            )

            if new_image is None:

                flash(
                    "نوع صورة القسم غير مسموح به.",
                    "danger"
                )

                return render_template(
                    "category_edit.html",
                    restaurant=restaurant,
                    category=category
                )

            image_name = new_image

        execute_db(
            """
            UPDATE categories
            SET
                name = %s,
                description = %s,
                icon = %s,
                image = %s,
                sort_order = %s,
                is_active = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            AND restaurant_id = %s
            """,
            [
                name,
                description,
                icon,
                image_name,
                sort_order,
                is_active,
                category_id,
                restaurant["id"]
            ]
        )

        flash(
            "تم تعديل القسم بنجاح.",
            "success"
        )

        return redirect(
            url_for("categories")
        )

    return render_template(
        "category_edit.html",
        restaurant=restaurant,
        category=category
    )

# =========================================================
# حذف القسم
# =========================================================

@app.route(
    "/categories/<int:category_id>/delete",
    methods=["POST"]
)
@restaurant_required
def category_delete(category_id):

    restaurant = current_restaurant()

    category = query_db(
        """
        SELECT *
        FROM categories
        WHERE id = %s
        AND restaurant_id = %s
        """,
        [
            category_id,
            restaurant["id"]
        ],
        one=True
    )

    if category is None:

        flash(
            "القسم غير موجود.",
            "danger"
        )

        return redirect(
            url_for("categories")
        )

    execute_db(
        """
        DELETE FROM categories
        WHERE id = %s
        AND restaurant_id = %s
        """,
        [
            category_id,
            restaurant["id"]
        ]
    )

    flash(
        "تم حذف القسم.",
        "success"
    )

    return redirect(
        url_for("categories")
    )


# =========================================================
# المنتجات
# =========================================================

@app.route("/products")
@restaurant_required
def products():

    restaurant = current_restaurant()

    products_list = query_db(
        """
        SELECT
            products.*,
            categories.name AS category_name
        FROM products
        LEFT JOIN categories
            ON categories.id = products.category_id
        WHERE products.restaurant_id = %s
        ORDER BY products.id DESC
        """,
        [
            restaurant["id"]
        ]
    )

    categories_list = query_db(
        """
        SELECT *
        FROM categories
        WHERE restaurant_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        [
            restaurant["id"]
        ]
    )

    return render_template(
        "products.html",
        restaurant=restaurant,
        products=products_list,
        categories=categories_list
    )


# =========================================================
# إضافة منتج
# =========================================================

@app.route(
    "/products/add",
    methods=["GET", "POST"]
)
@restaurant_required
def product_add():

    restaurant = current_restaurant()

    categories_list = query_db(
        """
        SELECT *
        FROM categories
        WHERE restaurant_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        [
            restaurant["id"]
        ]
    )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        price = request.form.get(
            "price",
            "0"
        ).strip()

        category_id = request.form.get(
            "category_id"
        )

        available = (
            1
            if request.form.get("available")
            else 0
        )

        image = request.files.get(
            "image"
        )

        if not name:

            flash(
                "اسم المنتج مطلوب.",
                "danger"
            )

            return render_template(
                "product_add.html",
                restaurant=restaurant,
                categories=categories_list
            )

        image_name = None

        if image and image.filename:

            image_name = save_uploaded_image(
                image
            )

            if image_name is None:

                flash(
                    "نوع صورة المنتج غير مسموح به.",
                    "danger"
                )

                return render_template(
                    "product_add.html",
                    restaurant=restaurant,
                    categories=categories_list
                )

        try:

            price_value = float(
                price
            )

        except (
            ValueError,
            TypeError
        ):

            flash(
                "السعر غير صحيح.",
                "danger"
            )

            return render_template(
                "product_add.html",
                restaurant=restaurant,
                categories=categories_list
            )

        execute_db(
            """
            INSERT INTO products
            (
                restaurant_id,
                category_id,
                name,
                description,
                price,
                image,
                available
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                restaurant["id"],
                category_id
                if category_id
                else None,
                name,
                description,
                price_value,
                image_name,
                available
            ]
        )

        flash(
            "تم إضافة المنتج.",
            "success"
        )

        return redirect(
            url_for("products")
        )

    return render_template(
        "product_add.html",
        restaurant=restaurant,
        categories=categories_list
    )

# =========================================================
# تعديل المنتج
# =========================================================

@app.route(
    "/products/<int:product_id>/edit",
    methods=["GET", "POST"]
)
@restaurant_required
def product_edit(product_id):

    restaurant = current_restaurant()

    product = query_db(
        """
        SELECT
            products.*,
            categories.name AS category_name
        FROM products
        LEFT JOIN categories
            ON categories.id = products.category_id
        WHERE products.id = %s
        AND products.restaurant_id = %s
        """,
        [
            product_id,
            restaurant["id"]
        ],
        one=True
    )

    if product is None:

        flash(
            "المنتج غير موجود.",
            "danger"
        )

        return redirect(
            url_for("products")
        )

    categories_list = query_db(
        """
        SELECT *
        FROM categories
        WHERE restaurant_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        [
            restaurant["id"]
        ]
    )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        price = request.form.get(
            "price",
            "0"
        ).strip()

        old_price = request.form.get(
            "old_price",
            ""
        ).strip()

        category_id = request.form.get(
            "category_id"
        )

        status = request.form.get(
            "status",
            "active"
        )

        available = (
            1
            if status == "active"
            else 0
        )

        image = request.files.get(
            "image"
        )

        if not name:

            flash(
                "اسم المنتج مطلوب.",
                "danger"
            )

            return render_template(
                "product_edit.html",
                restaurant=restaurant,
                product=product,
                categories=categories_list
            )

        try:

            price_value = float(
                price
            )

        except (
            ValueError,
            TypeError
        ):

            flash(
                "السعر غير صحيح.",
                "danger"
            )

            return render_template(
                "product_edit.html",
                restaurant=restaurant,
                product=product,
                categories=categories_list
            )

        old_price_value = None

        if old_price:

            try:

                old_price_value = float(
                    old_price
                )

            except (
                ValueError,
                TypeError
            ):

                flash(
                    "السعر القديم غير صحيح.",
                    "danger"
                )

                return render_template(
                    "product_edit.html",
                    restaurant=restaurant,
                    product=product,
                    categories=categories_list
                )

        image_name = product["image"]

        if image and image.filename:

            new_image = save_uploaded_image(
                image
            )

            if new_image is None:

                flash(
                    "نوع الصورة غير مسموح به.",
                    "danger"
                )

                return render_template(
                    "product_edit.html",
                    restaurant=restaurant,
                    product=product,
                    categories=categories_list
                )

            image_name = new_image

        execute_db(
            """
            UPDATE products
            SET
                category_id = %s,
                name = %s,
                description = %s,
                price = %s,
                old_price = %s,
                image = %s,
                available = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            AND restaurant_id = %s
            """,
            [
                category_id
                if category_id
                else None,
                name,
                description,
                price_value,
                old_price_value,
                image_name,
                available,
                product_id,
                restaurant["id"]
            ]
        )

        flash(
            "تم تعديل المنتج.",
            "success"
        )

        return redirect(
            url_for("products")
        )

    return render_template(
        "product_edit.html",
        restaurant=restaurant,
        product=product,
        categories=categories_list
    )


# =========================================================
# حذف المنتج
# =========================================================

@app.route(
    "/products/<int:product_id>/delete",
    methods=["POST"]
)
@restaurant_required
def product_delete(product_id):

    restaurant = current_restaurant()

    product = query_db(
        """
        SELECT *
        FROM products
        WHERE id = %s
        AND restaurant_id = %s
        """,
        [
            product_id,
            restaurant["id"]
        ],
        one=True
    )

    if product is None:

        flash(
            "المنتج غير موجود.",
            "danger"
        )

        return redirect(
            url_for("products")
        )

    execute_db(
        """
        DELETE FROM products
        WHERE id = %s
        AND restaurant_id = %s
        """,
        [
            product_id,
            restaurant["id"]
        ]
    )

    flash(
        "تم حذف المنتج بنجاح.",
        "success"
    )

    return redirect(
        url_for("products")
    )


# =========================================================
# إدارة المنيو
# =========================================================

@app.route("/menu")
@restaurant_required
def menu():

    restaurant = current_restaurant()

    categories_count = query_db(
        """
        SELECT COUNT(*) AS count
        FROM categories
        WHERE restaurant_id = %s
        """,
        [
            restaurant["id"]
        ],
        one=True
    )["count"]

    products_count = query_db(
        """
        SELECT COUNT(*) AS count
        FROM products
        WHERE restaurant_id = %s
        """,
        [
            restaurant["id"]
        ],
        one=True
    )["count"]

    return render_template(
        "menu.html",
        restaurant=restaurant,
        categories_count=categories_count,
        products_count=products_count
    )


# =========================================================
# المنيو العامة
# =========================================================

@app.route("/menu/<slug>")
def public_menu(slug):

    restaurant = query_db(
        """
        SELECT *
        FROM restaurants
        WHERE slug = %s
        LIMIT 1
        """,
        [
            slug
        ],
        one=True
    )

    if restaurant is None:

        return render_template(
            "public_menu.html",
            restaurant=None,
            categories=[],
            products=[]
        ), 404

    categories_list = query_db(
        """
        SELECT *
        FROM categories
        WHERE restaurant_id = %s
        AND is_active = 1
        ORDER BY sort_order ASC, id ASC
        """,
        [
            restaurant["id"]
        ]
    )

    products_list = query_db(
        """
        SELECT
            products.*,
            categories.name AS category_name
        FROM products
        LEFT JOIN categories
            ON categories.id = products.category_id
        WHERE products.restaurant_id = %s
        AND products.available = 1
        ORDER BY products.id ASC
        """,
        [
            restaurant["id"]
        ]
    )

    settings_data = query_db(
        """
        SELECT *
        FROM restaurant_settings
        WHERE restaurant_id = %s
        LIMIT 1
        """,
        [
            restaurant["id"]
        ],
        one=True
    )

    return render_template(
        "public_menu.html",
        restaurant=restaurant,
        categories=categories_list,
        products=products_list,
        settings=settings_data
    )

# =========================================================
# تفاصيل المنتج
# =========================================================

@app.route(
    "/menu/<slug>/product/<int:product_id>"
)
def public_product(
    slug,
    product_id
):

    restaurant = query_db(
        """
        SELECT *
        FROM restaurants
        WHERE slug = %s
        LIMIT 1
        """,
        [
            slug
        ],
        one=True
    )

    if restaurant is None:

        return "المطعم غير موجود", 404

    product = query_db(
        """
        SELECT
            products.*,
            categories.name AS category_name
        FROM products
        LEFT JOIN categories
            ON categories.id = products.category_id
        WHERE products.id = %s
AND products.restaurant_id = %s
        """,
        [
            product_id,
            restaurant["id"]
        ],
        one=True
    )

    if product is None:

        return "المنتج غير موجود", 404

    return render_template(
        "product_details.html",
        restaurant=restaurant,
        product=product
    )

# =========================================================
# السلة
# =========================================================

@app.route("/cart")
def cart():

    return render_template(
        "cart.html",
        user=current_user(),
        restaurant=current_restaurant()
    )
# =========================================================
# إتمام الطلب
# =========================================================

# =========================================================
# إنشاء الطلب
# =========================================================

@app.route(
    "/checkout",
    methods=["GET", "POST"]
)
def checkout():

    if request.method == "GET":

        return render_template(
            "checkout.html",
            user=current_user()
        )

    customer_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    customer_phone = request.form.get(
        "customer_phone",
        ""
    ).strip()

    customer_address = request.form.get(
        "customer_address",
        ""
    ).strip()

    order_notes = request.form.get(
        "order_notes",
        ""
    ).strip()

    payment_method = request.form.get(
        "payment_method",
        "cash"
    ).strip()

    cart_data = request.form.get(
        "cart_data",
        ""
    ).strip()

    # =====================================================
    # التحقق من بيانات العميل
    # =====================================================

    if not customer_name:

        flash(
            "من فضلك أدخل اسمك.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not customer_phone:

        flash(
            "من فضلك أدخل رقم الهاتف.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    if not customer_address:

        flash(
            "من فضلك أدخل العنوان.",
            "danger"
        )

        return redirect(
            url_for("checkout")
        )

    # =====================================================
    # التحقق من طريقة الدفع
    # =====================================================

    allowed_payment_methods = {
        "cash",
        "online"
    }

    if payment_method not in allowed_payment_methods:

        payment_method = "cash"

    # =====================================================
    # قراءة السلة
    # =====================================================

    try:

        import json

        cart = json.loads(
            cart_data
        )

    except (
        ValueError,
        TypeError
    ):

        cart = []

    if not isinstance(cart, list):

        cart = []

    if not cart:

        flash(
            "السلة فارغة، أضف منتجات أولاً.",
            "warning"
        )

        return redirect(
            url_for("checkout")
        )

    # =====================================================
    # استخراج IDs المنتجات
    # =====================================================

    product_ids = []

    for item in cart:

        try:

            product_id = int(
                item.get("id")
            )

            quantity = int(
                item.get("quantity", 0)
            )

        except (
            ValueError,
            TypeError,
            AttributeError
        ):

            continue

        if product_id <= 0:

            continue

        if quantity <= 0:

            continue

        if quantity > 99:

            quantity = 99

        product_ids.append(
            product_id
        )

    product_ids = list(
        dict.fromkeys(
            product_ids
        )
    )

    if not product_ids:

        flash(
            "السلة لا تحتوي على منتجات صحيحة.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    # =====================================================
    # البحث عن المنتجات
    # =====================================================

    placeholders = ",".join(
        ["%s"] * len(product_ids)
    )

    products = query_db(
        f"""
        SELECT
            id,
            restaurant_id,
            name,
            price,
            available
        FROM products
        WHERE id IN ({placeholders})
        """,
        product_ids
    )

    products_by_id = {
        product["id"]: product
        for product in products
    }

    valid_products = []

    restaurant_id = None

    # =====================================================
    # التحقق من المنتجات
    # =====================================================

    for item in cart:

        try:

            product_id = int(
                item.get("id")
            )

            quantity = int(
                item.get("quantity", 0)
            )

        except (
            ValueError,
            TypeError,
            AttributeError
        ):

            continue

        if product_id <= 0:

            continue

        if quantity <= 0:

            continue

        if quantity > 99:

            quantity = 99

        product = products_by_id.get(
            product_id
        )

        if product is None:

            flash(
                "أحد المنتجات الموجودة في السلة لم يعد متاحًا.",
                "danger"
            )

            return redirect(
                url_for("checkout")
            )

        if not product["available"]:

            flash(
                f'المنتج "{product["name"]}" غير متاح حاليًا.',
                "danger"
            )

            return redirect(
                url_for("checkout")
            )

        if restaurant_id is None:

            restaurant_id = product["restaurant_id"]

        elif restaurant_id != product["restaurant_id"]:

            flash(
                "لا يمكن إنشاء طلب يحتوي على منتجات من مطاعم مختلفة.",
                "danger"
            )

            return redirect(
                url_for("checkout")
            )

        valid_products.append(
            {
                "product": product,
                "quantity": quantity
            }
        )

    # =====================================================
    # التحقق النهائي
    # =====================================================

    if not valid_products or restaurant_id is None:

        flash(
            "لم يتم العثور على منتجات صالحة في السلة.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    # =====================================================
    # التأكد من أن المطعم موجود ومفعّل
    # =====================================================

    restaurant = query_db(
        """
        SELECT *
        FROM restaurants
        WHERE id = %s
        AND is_active = 1
        LIMIT 1
        """,
        [
            restaurant_id
        ],
        one=True
    )

    if restaurant is None:

        flash(
            "المطعم غير متاح حاليًا.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    # =====================================================
    # إعدادات المطعم
    # =====================================================

    restaurant_settings = query_db(
        """
        SELECT *
        FROM restaurant_settings
        WHERE restaurant_id = %s
        LIMIT 1
        """,
        [
            restaurant_id
        ],
        one=True
    )

    if restaurant_settings:

        if not restaurant_settings["allow_orders"]:

            flash(
                "المطعم لا يستقبل الطلبات حاليًا.",
                "warning"
            )

            return redirect(
                url_for(
                    "public_menu",
                    slug=restaurant["slug"]
                )
            )

    # =====================================================
    # حساب الإجمالي
    # =====================================================

    subtotal = 0

    prepared_items = []

    for item in valid_products:

        product = item["product"]

        quantity = item["quantity"]

        price = float(
            product["price"] or 0
        )

        item_total = (
            price * quantity
        )

        subtotal += item_total

        prepared_items.append(
            {
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": quantity,
                "price": price,
                "total": item_total
            }
        )

    # =====================================================
    # حساب رسوم التوصيل
    # =====================================================

    delivery_fee = 0

    if restaurant_settings:

        if restaurant_settings["allow_delivery"]:

            delivery_fee = float(
                restaurant_settings["delivery_fee"] or 0
            )

    discount = 0

    total = (
        subtotal
        + delivery_fee
        - discount
    )

    # =====================================================
    # البحث عن العميل
    # =====================================================

    customer = query_db(
        """
        SELECT *
        FROM customers
        WHERE restaurant_id = %s
        AND phone = %s
        LIMIT 1
        """,
        [
            restaurant_id,
            customer_phone
        ],
        one=True
    )

    # =====================================================
    # إنشاء أو تحديث العميل
    # =====================================================

    if customer is None:

        customer_id = execute_db(
            """
            INSERT INTO customers
            (
                restaurant_id,
                name,
                phone,
                address,
                notes,
                total_orders,
                total_spent
            )
            VALUES (%s, %s, %s, %s, %s, 1, %s)
            """,
            [
                restaurant_id,
                customer_name,
                customer_phone,
                customer_address,
                order_notes,
                total
            ]
        )

    else:

        customer_id = customer["id"]

        execute_db(
            """
            UPDATE customers
            SET
                name = %s,
                address = %s,
                notes = %s,
                total_orders = COALESCE(total_orders, 0) + 1,
                total_spent = COALESCE(total_spent, 0) + %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            AND restaurant_id = %s
            """,
            [
                customer_name,
                customer_address,
                order_notes,
                total,
                customer_id,
                restaurant_id
            ]
        )

    # =====================================================
    # حالة الدفع
    # =====================================================

    payment_status = "pending"

    # =====================================================
    # إنشاء الطلب
    # =====================================================

    order_id = execute_db(
        """
        INSERT INTO orders
        (
            restaurant_id,
            customer_id,
            customer_name,
            customer_phone,
            customer_address,
            notes,
            subtotal,
            delivery_fee,
            discount,
            total,
            status,
            payment_method,
            payment_status
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        [
            restaurant_id,
            customer_id,
            customer_name,
            customer_phone,
            customer_address,
            order_notes,
            subtotal,
            delivery_fee,
            discount,
            total,
            "pending",
            payment_method,
            payment_status
        ]
    )

    # =====================================================
    # حفظ عناصر الطلب
    # =====================================================

    for item in prepared_items:

        execute_db(
            """
            INSERT INTO order_items
            (
                order_id,
                product_id,
                product_name,
                quantity,
                price,
                total
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                order_id,
                item["product_id"],
                item["product_name"],
                item["quantity"],
                item["price"],
                item["total"]
            ]
        )

    # =====================================================
    # حفظ بيانات الطلب في الجلسة
    # =====================================================

    session["last_order_id"] = order_id

    session["last_order_restaurant"] = restaurant["slug"]

    flash(
        "تم إرسال طلبك بنجاح.",
        "success"
    )

    return redirect(
        url_for(
            "order_success",
            order_id=order_id
        )
    )

    # =====================================================
    # إشعار صاحب المطعم
    # =====================================================

    execute_db(
        """
        INSERT INTO notifications
        (
            user_id,
            restaurant_id,
            title,
            message,
            notification_type,
            is_read
        )
        VALUES (%s, %s, %s, %s, %s, 0)
        """,
        [
            restaurant["owner_id"],
            restaurant_id,
            "طلب جديد",
            f"تم استلام طلب جديد رقم #{order_id} بقيمة {total:.2f} جنيه.",
            "new_order"
        ]
    )


           # =====================================================
    # حفظ بيانات الطلب في الجلسة
    # =====================================================

    session["last_order_id"] = order_id

    session["last_order_restaurant"] = restaurant["slug"]

    flash(
        "تم إرسال طلبك بنجاح.",
        "success"
    )

    return redirect(
        url_for(
            "order_success",
            order_id=order_id
        )
    )


# =========================================================
# نجاح الطلب
# =========================================================

@app.route(
    "/order-success/<int:order_id>"
)
def order_success(order_id):

    # =====================================================
    # جلب الطلب
    # =====================================================

    order = query_db(
        """
        SELECT
            orders.*,
            restaurants.name AS restaurant_name,
            restaurants.slug AS restaurant_slug
        FROM orders
        JOIN restaurants
            ON restaurants.id = orders.restaurant_id
        WHERE orders.id = %s
        LIMIT 1
        """,
        [
            order_id
        ],
        one=True
    )

    # =====================================================
    # إذا كان الطلب غير موجود
    # =====================================================

    if order is None:

        flash(
            "الطلب غير موجود.",
            "danger"
        )

        return redirect(
            url_for("home")
        )

    # =====================================================
    # جلب منتجات الطلب
    # =====================================================

    items = query_db(
        """
        SELECT *
        FROM order_items
        WHERE order_id = %s
        ORDER BY id ASC
        """,
        [
            order_id
        ]
    )

    # =====================================================
    # عرض صفحة نجاح الطلب
    # =====================================================

    return render_template(
        "order_success.html",
        order=order,
        items=items,
        restaurant=order
    )


# =========================================================
# الطلبات
# =========================================================

@app.route("/orders")
@restaurant_required
def orders():

    restaurant = current_restaurant()

    orders_list = query_db(
        """
        SELECT *
        FROM orders
        WHERE restaurant_id = %s
        ORDER BY id DESC
        """,
        [
            restaurant["id"]
        ]
    )

    return render_template(
        "orders.html",
        restaurant=restaurant,
        orders=orders_list
    )

# =========================================================
# API - آخر الطلبات
# =========================================================

@app.route("/api/orders/latest")
@restaurant_required
def latest_orders():

    restaurant = current_restaurant()

    orders_list = query_db(
        """
        SELECT
            id,
            customer_name,
            total,
            status,
            created_at
        FROM orders
        WHERE restaurant_id = %s
        ORDER BY id DESC
        LIMIT 10
        """,
        [
            restaurant["id"]
        ]
    )

    return jsonify([
        dict(order)
        for order in orders_list
    ])
# =========================================================
# تفاصيل الطلب
# =========================================================

@app.route("/orders/<int:order_id>")
@restaurant_required
def order_details(order_id):

    restaurant = current_restaurant()

    order = query_db(
        """
        SELECT *
        FROM orders
        WHERE id = %s
        AND restaurant_id = %s
        """,
        [
            order_id,
            restaurant["id"]
        ],
        one=True
    )

    if order is None:

        flash(
            "الطلب غير موجود.",
            "danger"
        )

        return redirect(
            url_for("orders")
        )

    order_items = query_db(
        """
        SELECT *
        FROM order_items
        WHERE order_id = %s
        ORDER BY id ASC
        """,
        [
            order_id
        ]
    )

    return render_template(
        "order_details.html",
        restaurant=restaurant,
        order=order,
        order_items=order_items
    )


# =========================================================
# فاتورة الطلب
# =========================================================

@app.route("/orders/<int:order_id>/invoice")
@restaurant_required
def order_invoice(order_id):

    restaurant = current_restaurant()

    order = query_db(
        """
        SELECT *
        FROM orders
        WHERE id = %s
        AND restaurant_id = %s
        """,
        [
            order_id,
            restaurant["id"]
        ],
        one=True
    )

    if order is None:

        flash(
            "الطلب غير موجود.",
            "danger"
        )

        return redirect(
            url_for("orders")
        )

    order_items = query_db(
        """
        SELECT *
        FROM order_items
        WHERE order_id = %s
        ORDER BY id ASC
        """,
        [
            order_id
        ]
    )

    return render_template(
        "invoice.html",
        restaurant=restaurant,
        order=order,
        order_items=order_items
    )


# =========================================================
# تحديث حالة الطلب
# =========================================================

@app.route(
    "/orders/<int:order_id>/status",
    methods=["POST"]
)
@restaurant_required
def update_order_status(order_id):

    restaurant = current_restaurant()

    status = request.form.get(
        "status",
        ""
    ).strip()

    allowed_statuses = {
        "pending",
        "confirmed",
        "preparing",
        "ready",
        "completed",
        "cancelled"
    }

    if status not in allowed_statuses:

        flash(
            "حالة الطلب غير صحيحة.",
            "danger"
        )

        return redirect(
            url_for(
                "order_details",
                order_id=order_id
            )
        )

    execute_db(
        """
        UPDATE orders
        SET
            status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        AND restaurant_id = %s
        """,
        [
            status,
            order_id,
            restaurant["id"]
        ]
    )

    flash(
        "تم تحديث حالة الطلب.",
        "success"
    )

    return redirect(
        url_for(
            "order_details",
            order_id=order_id
        )
    )


# =========================================================
# العملاء
# =========================================================

@app.route("/customers")
@restaurant_required
def customers():

    restaurant = current_restaurant()

    customers_list = query_db(
        """
        SELECT *
        FROM customers
        WHERE restaurant_id = %s
        ORDER BY id DESC
        """,
        [
            restaurant["id"]
        ]
    )

    return render_template(
        "customers.html",
        restaurant=restaurant,
        customers=customers_list
    )


# =========================================================
# الإحصائيات
# =========================================================

@app.route("/analytics")
@restaurant_required
def analytics():

    restaurant = current_restaurant()

    total_orders = query_db(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE restaurant_id = %s
        """,
        [
            restaurant["id"]
        ],
        one=True
    )["count"]

    completed_orders = query_db(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE restaurant_id = %s
        AND status = 'completed'
        """,
        [
            restaurant["id"]
        ],
        one=True
    )["count"]

    total_revenue = query_db(
        """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM orders
        WHERE restaurant_id = %s
        AND status = 'completed'
        """,
        [
            restaurant["id"]
        ],
        one=True
    )["total"]

    total_products = query_db(
        """
        SELECT COUNT(*) AS count
        FROM products
        WHERE restaurant_id = %s
        """,
        [
            restaurant["id"]
        ],
        one=True
    )["count"]

    return render_template(
        "analytics.html",
        restaurant=restaurant,
        total_orders=total_orders,
        completed_orders=completed_orders,
        total_revenue=total_revenue,
        total_products=total_products
    )

# =========================================================
# QR Code
# =========================================================

@app.route("/qr-code")
@restaurant_required
def qr_code():

    restaurant = current_restaurant()

    menu_url = url_for(
        "public_menu",
        slug=restaurant["slug"],
        _external=True
    )

    # إنشاء QR Code حقيقي
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )

    qr.add_data(menu_url)
    qr.make(fit=True)

    qr_image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    # تحويل صورة QR إلى Base64
    buffer = BytesIO()

    qr_image.save(
        buffer,
        format="PNG"
    )

    qr_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    qr_code_data = (
        "data:image/png;base64,"
        + qr_base64
    )

    return render_template(
        "qr_code.html",
        restaurant=restaurant,
        menu_url=menu_url,
        qr_code=qr_code_data
    )


# =========================================================
# API المنتجات
# =========================================================

@app.route("/api/products")
@restaurant_required
def api_products():

    restaurant = current_restaurant()

    products_list = query_db(
        """
        SELECT
            id,
            category_id,
            name,
            description,
            price,
            old_price,
            image,
            available,
            featured,
            sort_order
        FROM products
        WHERE restaurant_id = %s
        ORDER BY id DESC
        """,
        [
            restaurant["id"]
        ]
    )

    return jsonify([
        dict(product)
        for product in products_list
    ])
# =========================================================
# API الأقسام
# =========================================================

@app.route("/api/categories")
@restaurant_required
def api_categories():

    restaurant = current_restaurant()

    categories_list = query_db(
        """
        SELECT
            id,
            name,
            description,
            icon,
            image,
            sort_order,
            is_active
        FROM categories
        WHERE restaurant_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        [
            restaurant["id"]
        ]
    )

    return jsonify([
        dict(category)
        for category in categories_list
    ])

# =========================================================
# API الطلبات
# =========================================================

@app.route("/api/orders")
@restaurant_required
def api_orders():

    restaurant = current_restaurant()

    orders_list = query_db(
        """
        SELECT *
        FROM orders
        WHERE restaurant_id = %s
        ORDER BY id DESC
        """,
        [
            restaurant["id"]
        ]
    )

    return jsonify([
        dict(order)
        for order in orders_list
    ])

# =========================================================
# الصفحات العامة
# =========================================================

@app.route("/about")
def about():

    return render_template(
        "about.html",
        user=current_user(),
        restaurant=current_restaurant()
    )


@app.route("/contact")
def contact():

    return render_template(
        "contact.html",
        user=current_user(),
        restaurant=current_restaurant()
    )


@app.route("/privacy")
def privacy():

    return render_template(
        "privacy.html",
        user=current_user(),
        restaurant=current_restaurant()
    )


@app.route("/terms")
def terms():

    return render_template(
        "terms.html",
        user=current_user(),
        restaurant=current_restaurant()
    )


# =========================================================
# 404
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "home.html",
        user=current_user(),
        restaurant=current_restaurant(),
        error_message="الصفحة غير موجودة."
    ), 404


# =========================================================
# 500
# =========================================================

@app.errorhandler(500)
def internal_error(error):

    return render_template(
        "home.html",
        user=current_user(),
        restaurant=current_restaurant(),
        error_message="حدث خطأ داخل الموقع."
    ), 500


# =========================================================
# تشغيل التطبيق
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
