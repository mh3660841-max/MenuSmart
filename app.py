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
            AND is_active = 1
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
# موظف المنتجات مطلوب
# =========================================================

def employee_products_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "يجب تسجيل الدخول أولاً.",
                "warning"
            )

            return redirect(
                url_for("employee_login")
            )

        if not session.get("employee"):

            flash(
                "هذه الصفحة مخصصة للموظفين.",
                "danger"
            )

            return redirect(
                url_for("employee_login")
            )

        staff = query_db(
            """
            SELECT
                restaurant_staff.restaurant_id,
                restaurant_staff.role,
                restaurant_staff.is_active
            FROM restaurant_staff
            INNER JOIN restaurants
                ON restaurants.id = restaurant_staff.restaurant_id
            WHERE restaurant_staff.user_id = %s
            AND restaurant_staff.is_active = 1
            AND restaurants.is_active = 1
            LIMIT 1
            """,
            [
                session["user_id"]
            ],
            one=True
        )

        if staff is None:

            session.clear()

            flash(
                "حساب الموظف غير صالح.",
                "danger"
            )

            return redirect(
                url_for("employee_login")
            )

        if staff["role"] not in (
            "products",
            "manager"
        ):

            flash(
                "ليس لديك صلاحية لإدارة المنتجات.",
                "danger"
            )

            return redirect(
                url_for("employee_dashboard")
            )

        session["restaurant_id"] = staff["restaurant_id"]

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
        AND is_active = 1
        LIMIT 1
        """,
        (
            session["user_id"],
        ),
        one=True
    )


# =========================================================
# لغة النشاط الحالية
# =========================================================

def current_language():
    return "ar"

# =========================================================
# نظام اللغات
# =========================================================

TRANSLATIONS = {
    "ar": {
        "home": "الرئيسية",
        "share_with_business": "شارك Menu Smart مع نشاط تجاري آخر",
        "invite_business": "دعوة نشاط تجاري",
        "no_orders_yet": "لا توجد طلبات حتى الآن",
        "shown_to_customers": "وسيتم عرضها تلقائيًا للعملاء.",
        "add_menu_items": "أضف الأقسام والمنتجات والأسعار،",
        "professional_menu": "منيو إلكتروني احترافي لنشاطك التجاري",
        "open_menu": "فتح المنيو ←",
        "digital_menu": "المنيو الإلكتروني",
        "customize_menu": "تخصيص إعدادات المنيو",
        "share_qr": "مشاركة المنيو عبر QR Code",
        "analytics_description": "متابعة أداء النشاط والمبيعات",
        "organize_categories": "إنشاء وتنظيم أقسام المنيو",
        "all_tools": "جميع الأدوات في مكان واحد",
        "menu_products": "منتجات المنيو",
        "menu_categories": "أقسام المنيو",
        "account": "حسابي",
        "no_notifications": "لا توجد إشعارات جديدة",
        "read_all": "قراءة الكل",
        "back": "رجوع",
        "categories": "الأقسام",
        "dashboard": "لوحة التحكم",
        "business_tools": "كل أدوات نشاطك في مكان واحد، بإدارة أبسط وأذكى.",
        "view_menu": "مشاهدة المنيو",
        "business_settings": "إعدادات النشاط",
        "ready_management": "جاهز للإدارة",
        "create_business": "إنشاء النشاط",
        "business": "النشاط",
        "products": "المنتجات",
        "orders": "الطلبات",
        "customers": "العملاء",
        "total_orders": "إجمالي الطلبات",
        "business_customers": "عملاء النشاط",
        "quick_management": "الإدارة السريعة",
        "manage_business": "إدارة النشاط",
        "add_products": "إضافة المنتجات والأسعار والصور",
        "manage_orders": "متابعة وإدارة طلبات العملاء",
        "manage_customers": "إدارة بيانات العملاء",
        "settings": "الإعدادات",
        "management_data": "بيانات الإدارة",
        "manage_business_data": "إدارة بيانات النشاط الأساسية",
        "last_orders": "آخر الطلبات",
        "all_orders": "كل الطلبات ←",
        "no_orders": "ستظهر طلبات العملاء هنا بمجرد بدء استقبال الطلبات.",
        "smart_platform": "منصتك الذكية لإنشاء وإدارة المنيو الإلكتروني.",
        "logout_confirm": "هل أنت متأكد أنك تريد تسجيل الخروج؟",
        "logout": "تسجيل الخروج",
        "orders": "الطلبات",
        "customers": "العملاء",
        "products": "المنتجات",
        "settings": "الإعدادات",
        "profile": "الملف الشخصي",
        "menu": "المنيو",
        "view_menu": "مشاهدة المنيو",
        "save": "حفظ",
        "activity": "النشاط",
        "language": "لغة المنصة",
        "notifications": "الإشعارات",
        "profile_title": "الملف الشخصي",
        "profile_description": "إدارة بيانات النشاط في Menu Smart.",
        "profile_account": "الحساب",
        "business_data": "بيانات النشاط",
        "business_data_description": "تحكم في بيانات نشاطك الأساسية وظهورها داخل المنيو الإلكتروني.",
        "back_dashboard": "← العودة للوحة التحكم",
        "customer_visible_data": "هذه البيانات ستظهر للعملاء داخل المنيو.",
        "business_name": "اسم النشاط",
        "business_name_placeholder": "مثال: نشاط الذوق",
        "business_phone": "رقم هاتف النشاط",
        "business_address": "عنوان النشاط",
        "business_address_placeholder": "مثال: الجيزة - شارع...",
        "business_description": "وصف النشاط",
        "business_description_placeholder": "اكتب وصفًا مختصرًا عن النشاط...",
        "business_description_example": "مثال: نشاط متخصص في البرجر والمشروبات والحلويات.",
        "platform_language": "لغة المنصة",
        "choose_platform_language": "اختر اللغة الأساسية التي تريد استخدامها في المنصة.",
        "business_logo": "شعار النشاط",
        "logo_formats": "PNG أو JPG أو WEBP — اختياري.",
        "current_logo": "الشعار الحالي",
        "save_business_data": "حفظ بيانات النشاط",
        "business_preview": "معاينة النشاط",
        "default_business_preview": "أنشئ بيانات نشاطك وابدأ في بناء منيو إلكتروني احترافي.",
        "menu_status": "حالة المنيو",
        "ready_for_work": "جاهز للعمل"
    },

    "en": {
        "dashboard": "Dashboard",
        "business_tools": "All your business tools in one place, with simpler and smarter management.",
        "view_menu": "View Menu",
        "business_settings": "Business Settings",
        "ready_management": "Ready to manage",
        "create_business": "Create Business",
        "business": "Business",
        "products": "Products",
        "orders": "Orders",
        "customers": "Customers",
        "total_orders": "Total Orders",
        "business_customers": "Business Customers",
        "quick_management": "Quick Management",
        "manage_business": "Manage Business",
        "add_products": "Add products, prices and images",
        "manage_orders": "Track and manage customer orders",
        "manage_customers": "Manage customer data",
        "settings": "Settings",
        "management_data": "Management Data",
        "manage_business_data": "Manage basic business information",
        "last_orders": "Latest Orders",
        "all_orders": "All Orders →",
        "no_orders": "Customer orders will appear here once you start receiving orders.",
        "smart_platform": "Your smart platform for creating and managing your digital menu.",
        "logout_confirm": "Are you sure you want to log out?",
        "logout": "Logout",
        "orders": "Orders",
        "customers": "Customers",
        "products": "Products",
        "settings": "Settings",
        "profile": "Profile",
        "menu": "Menu",
        "view_menu": "View Menu",
        "save": "Save",
        "activity": "Business",
        "language": "Platform Language",
        "notifications": "Notifications",
        "account": "My Account",
        "all_tools": "All tools in one place",
        "analytics_description": "Track business performance and sales",
        "back": "Back",
        "categories": "Categories",
        "home": "Home",
        "invite_business": "Invite a Business",
        "no_notifications": "No new notifications",
        "no_orders_yet": "No orders yet",
        "professional_menu": "Professional digital menu for your business",
        "read_all": "Mark all as read",
        "share_with_business": "Share Menu Smart with another business",
        "shown_to_customers": "and it will be displayed automatically to customers.",
        "profile_title": "Profile",
        "profile_description": "Manage your business information in Menu Smart.",
        "profile_account": "Account",
        "business_data": "Business Information",
        "business_data_description": "Manage your basic business information and how it appears in your digital menu.",
        "back_dashboard": "← Back to Dashboard",
        "customer_visible_data": "This information will be shown to customers in the menu.",
        "business_name": "Business Name",
        "business_name_placeholder": "Example: Taste Business",
        "business_phone": "Business Phone",
        "business_address": "Business Address",
        "business_address_placeholder": "Example: Giza - Street...",
        "business_description": "Business Description",
        "business_description_placeholder": "Write a short description about your business...",
        "business_description_example": "Example: A business specializing in burgers, drinks and desserts.",
        "platform_language": "Platform Language",
        "choose_platform_language": "Choose the primary language you want to use on the platform.",
        "business_logo": "Business Logo",
        "logo_formats": "PNG, JPG or WEBP — optional.",
        "current_logo": "Current Logo",
        "save_business_data": "Save Business Information",
        "business_preview": "Business Preview",
        "default_business_preview": "Add your business information and start building a professional digital menu.",
        "menu_status": "Menu Status",
        "ready_for_work": "Ready to use"
    },

    "fr": {
        "dashboard": "Tableau de bord",
        "business_tools": "Tous vos outils professionnels au même endroit, avec une gestion plus simple et plus intelligente.",
        "view_menu": "Voir le menu",
        "business_settings": "Paramètres de l'activité",
        "ready_management": "Prêt à gérer",
        "create_business": "Créer l'activité",
        "business": "Activité",
        "products": "Produits",
        "orders": "Commandes",
        "customers": "Clients",
        "total_orders": "Total des commandes",
        "business_customers": "Clients de l'activité",
        "quick_management": "Gestion rapide",
        "manage_business": "Gérer l'activité",
        "add_products": "Ajouter les produits, prix et images",
        "manage_orders": "Suivre et gérer les commandes clients",
        "manage_customers": "Gérer les données des clients",
        "settings": "Paramètres",
        "management_data": "Données de gestion",
        "manage_business_data": "Gérer les informations principales de l'activité",
        "last_orders": "Dernières commandes",
        "all_orders": "Toutes les commandes →",
        "no_orders": "Les commandes des clients apparaîtront ici dès que vous commencerez à les recevoir.",
        "smart_platform": "Votre plateforme intelligente pour créer et gérer votre menu numérique.",
        "logout_confirm": "Êtes-vous sûr de vouloir vous déconnecter ?",
        "logout": "Déconnexion",
        "orders": "Commandes",
        "customers": "Clients",
        "products": "Produits",
        "settings": "Paramètres",
        "profile": "Profil",
        "menu": "Menu",
        "view_menu": "Voir le menu",
        "save": "Enregistrer",
        "activity": "Activité",
        "language": "Langue de la plateforme",
        "notifications": "Notifications",
        "account": "Mon compte",
        "all_tools": "Tous les outils au même endroit",
        "analytics_description": "Suivre les performances et les ventes de l'activité",
        "back": "Retour",
        "categories": "Catégories",
        "home": "Accueil",
        "invite_business": "Inviter une activité",
        "no_notifications": "Aucune nouvelle notification",
        "no_orders_yet": "Aucune commande pour le moment",
        "professional_menu": "Menu numérique professionnel pour votre activité",
        "read_all": "Tout marquer comme lu",
        "share_with_business": "Partager Menu Smart avec une autre activité",
        "shown_to_customers": "et il sera automatiquement affiché aux clients.",
        "profile_title": "Profil",
        "profile_description": "Gérer les informations de votre activité dans Menu Smart.",
        "profile_account": "Compte",
        "business_data": "Informations de l'activité",
        "business_data_description": "Gérez les informations principales de votre activité et leur affichage dans le menu numérique.",
        "back_dashboard": "← Retour au tableau de bord",
        "customer_visible_data": "Ces informations seront affichées aux clients dans le menu.",
        "business_name": "Nom de l'activité",
        "business_name_placeholder": "Exemple : Activité Saveur",
        "business_phone": "Téléphone de l'activité",
        "business_address": "Adresse de l'activité",
        "business_address_placeholder": "Exemple : Gizeh - Rue...",
        "business_description": "Description de l'activité",
        "business_description_placeholder": "Écrivez une courte description de votre activité...",
        "business_description_example": "Exemple : Une activité spécialisée dans les burgers, boissons et desserts.",
        "platform_language": "Langue de la plateforme",
        "choose_platform_language": "Choisissez la langue principale que vous souhaitez utiliser sur la plateforme.",
        "business_logo": "Logo de l'activité",
        "logo_formats": "PNG, JPG ou WEBP — facultatif.",
        "current_logo": "Logo actuel",
        "save_business_data": "Enregistrer les informations",
        "business_preview": "Aperçu de l'activité",
        "default_business_preview": "Ajoutez les informations de votre activité et commencez à créer un menu numérique professionnel.",
        "menu_status": "État du menu",
        "ready_for_work": "Prêt à l'emploi",
    },
}



# =========================================================
# ترجمات Dashboard الإضافية
# =========================================================
TRANSLATIONS["ar"].update({
    "menu_sections": "أقسام المنيو",
    "menu_products": "منتجات المنيو",
    "total_orders_label": "إجمالي الطلبات",
    "create_menu_sections": "إنشاء وتنظيم أقسام المنيو",
    "analytics": "التحليلات",
    "share_menu_qr": "مشاركة المنيو عبر QR Code",
    "customize_menu": "تخصيص إعدادات المنيو",
    "open_menu_arrow": "فتح المنيو ←",
    "add_menu_items": "أضف الأقسام والمنتجات والأسعار،",
    "order": "طلب",
    "currency_egp": "جنيه",
    "completed": "مكتمل",
    "cancelled": "ملغي",
    "pending": "قيد الانتظار",
    "confirmed": "مؤكد",
    "preparing": "قيد التجهيز",
    "ready": "جاهز",
})

TRANSLATIONS["en"].update({
    "menu_sections": "Menu Sections",
    "menu_products": "Menu Products",
    "total_orders_label": "Total Orders",
    "create_menu_sections": "Create and organize menu sections",
    "analytics": "Analytics",
    "share_menu_qr": "Share Menu via QR Code",
    "customize_menu": "Customize Menu Settings",
    "open_menu_arrow": "Open Menu →",
    "add_menu_items": "Add sections, products and prices,",
    "order": "Order",
    "currency_egp": "EGP",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "pending": "Pending",
    "confirmed": "Confirmed",
    "preparing": "Preparing",
    "ready": "Ready",
})

TRANSLATIONS["fr"].update({
    "menu_sections": "Sections du menu",
    "menu_products": "Produits du menu",
    "total_orders_label": "Total des commandes",
    "create_menu_sections": "Créer et organiser les sections du menu",
    "analytics": "Analyses",
    "share_menu_qr": "Partager le menu via QR Code",
    "customize_menu": "Personnaliser les paramètres du menu",
    "open_menu_arrow": "Ouvrir le menu →",
    "add_menu_items": "Ajoutez les sections, produits et prix,",
    "order": "Commande",
    "currency_egp": "EGP",
    "completed": "Terminée",
    "cancelled": "Annulée",
    "pending": "En attente",
    "confirmed": "Confirmée",
    "preparing": "En préparation",
    "ready": "Prête",
})
TRANSLATIONS["ar"].update({
    "edit_category": "تعديل القسم",
    "add_category": "إضافة قسم",
    "category_page_description": "إضافة وتعديل أقسام المنيو في Menu Smart.",
})

TRANSLATIONS["en"].update({
    "edit_category": "Edit Category",
    "add_category": "Add Category",
    "category_page_description": "Add and edit menu categories in Menu Smart.",
})

TRANSLATIONS["fr"].update({
    "edit_category": "Modifier la catégorie",
    "add_category": "Ajouter une catégorie",
    "category_page_description": "Ajouter et modifier les catégories du menu dans Menu Smart.",
})

TRANSLATIONS["ar"].update({
    "analytics": "التحليلات",
    "login": "تسجيل الدخول",
    "smarter": "بشكل أذكى",
    "manage_categories": "إدارة الأقسام",
    "add_product": "إضافة منتج",
    "create_account": "إنشاء حساب",
    "checkout": "إتمام الطلب",
    "employee_dashboard": "لوحة الموظف",
    "employee_login": "دخول الموظف",
})

TRANSLATIONS["en"].update({
    "analytics": "Analytics",
    "login": "Login",
    "smarter": "Smarter.",
    "manage_categories": "Manage Categories",
    "add_product": "Add Product",
    "create_account": "Create Account",
    "checkout": "Checkout",
    "employee_dashboard": "Employee Dashboard",
    "employee_login": "Employee Login",
})

TRANSLATIONS["fr"].update({
    "analytics": "Analyses",
    "login": "Connexion",
    "smarter": "Plus intelligemment.",
    "manage_categories": "Gestion des catégories",
    "add_product": "Ajouter un produit",
    "create_account": "Créer un compte",
    "checkout": "Finaliser la commande",
    "employee_dashboard": "Tableau de bord employé",
    "employee_login": "Connexion employé",
})


def translate(key):
    language = current_language()

    return (
        TRANSLATIONS
        .get(language, TRANSLATIONS["ar"])
        .get(key, key)
    )


@app.context_processor
def inject_language():
    return {
        "current_language": current_language(),
        "t": translate,
    }


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
        SELECT
            r.*,
            owner.name AS owner_name,
            owner.email AS owner_email,

            (
                SELECT COUNT(*)
                FROM restaurant_staff rs
                WHERE rs.restaurant_id = r.id
                AND rs.is_active = 1
            ) AS employee_count,

            (
                SELECT COUNT(*)
                FROM products p
                WHERE p.restaurant_id = r.id
            ) AS product_count,

            (
                SELECT COUNT(*)
                FROM orders o
                WHERE o.restaurant_id = r.id
            ) AS order_count

        FROM restaurants r

        LEFT JOIN users owner
            ON owner.id = r.owner_id

        ORDER BY r.id DESC
        """
    )

    user = current_user()

    new_contact_messages = query_db(
        """
        SELECT COUNT(*) AS count
        FROM contact_messages
        WHERE status = 'new'
        """,
        one=True
    )

    new_contact_messages = (
        new_contact_messages["count"]
        if new_contact_messages
        else 0
    )

    return render_template(
        "admin.html",
        user=user,
        users=users,
        restaurants=restaurants,
        new_contact_messages=new_contact_messages
    )


# =========================================================
# المطعم الحالي لصاحب المطعم أو الموظف
# =========================================================

def accessible_restaurant():

    if "user_id" not in session:
        return None

    # =====================================================
    # صاحب المطعم
    # =====================================================

    restaurant = query_db(
        """
        SELECT *
        FROM restaurants
        WHERE owner_id = %s
        AND is_active = 1
        LIMIT 1
        """,
        [
            session["user_id"]
        ],
        one=True
    )

    if restaurant is not None:
        return restaurant

    # =====================================================
    # الموظف
    # =====================================================

    if session.get("employee"):

        restaurant = query_db(
            """
            SELECT restaurants.*
            FROM restaurants
            INNER JOIN restaurant_staff
                ON restaurant_staff.restaurant_id = restaurants.id
            WHERE restaurant_staff.user_id = %s
            AND restaurant_staff.is_active = 1
            AND restaurants.is_active = 1
            LIMIT 1
            """,
            [
                session["user_id"]
            ],
            one=True
        )

        return restaurant

    return None


# =========================================================
# صاحب المطعم أو موظف المنتجات
# =========================================================

def restaurant_or_products_required(function):

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

        restaurant = accessible_restaurant()

        if restaurant is None:

            flash(
                "لا يوجد مطعم مرتبط بهذا الحساب.",
                "danger"
            )

            if session.get("employee"):

                return redirect(
                    url_for("employee_login")
                )

            return redirect(
                url_for("profile")
            )

        # =================================================
        # التحقق من صلاحية الموظف
        # =================================================

        if session.get("employee"):

            staff = query_db(
                """
                SELECT
                    role,
                    is_active
                FROM restaurant_staff
                WHERE user_id = %s
                AND restaurant_id = %s
                LIMIT 1
                """,
                [
                    session["user_id"],
                    restaurant["id"]
                ],
                one=True
            )

            if staff is None:

                session.clear()

                flash(
                    "حساب الموظف غير صالح.",
                    "danger"
                )

                return redirect(
                    url_for("employee_login")
                )

            if staff["is_active"] != 1:

                session.clear()

                flash(
                    "حساب الموظف غير نشط.",
                    "danger"
                )

                return redirect(
                    url_for("employee_login")
                )

            if staff["role"] not in (
                "products",
                "manager"
            ):

                flash(
                    "ليس لديك صلاحية لإدارة المنتجات.",
                    "danger"
                )

                return redirect(
                    url_for("employee_dashboard")
                )

            # حفظ المطعم الخاص بالموظف في الجلسة
            session["restaurant_id"] = restaurant["id"]

        return function(*args, **kwargs)

    return decorated_function
# =========================================================
# صاحب المطعم أو موظف الطلبات
# =========================================================

def restaurant_or_orders_required(function):

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

        restaurant = accessible_restaurant()

        if restaurant is None:

            flash(
                "لا يوجد مطعم مرتبط بهذا الحساب.",
                "danger"
            )

            if session.get("employee"):
                return redirect(
                    url_for("employee_login")
                )

            return redirect(
                url_for("profile")
            )

        if session.get("employee"):

            staff = query_db(
                """
                SELECT
                    role,
                    is_active
                FROM restaurant_staff
                WHERE user_id = %s
                AND restaurant_id = %s
                LIMIT 1
                """,
                [
                    session["user_id"],
                    restaurant["id"]
                ],
                one=True
            )

            if staff is None:

                session.clear()

                flash(
                    "حساب الموظف غير صالح.",
                    "danger"
                )

                return redirect(
                    url_for("employee_login")
                )

            if staff["is_active"] != 1:

                session.clear()

                flash(
                    "حساب الموظف غير نشط.",
                    "danger"
                )

                return redirect(
                    url_for("employee_login")
                )

            if staff["role"] not in (
                "orders",
                "manager"
            ):

                flash(
                    "ليس لديك صلاحية للوصول إلى الطلبات.",
                    "danger"
                )

                return redirect(
                    url_for("employee_dashboard")
                )

            session["restaurant_id"] = restaurant["id"]

        return function(*args, **kwargs)

    return decorated_function
# =========================================================
# صاحب المطعم أو موظف العملاء / الكاشير
# =========================================================

def restaurant_or_customers_required(function):

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

        restaurant = accessible_restaurant()

        if restaurant is None:

            flash(
                "لا يوجد مطعم مرتبط بهذا الحساب.",
                "danger"
            )

            if session.get("employee"):
                return redirect(
                    url_for("employee_login")
                )

            return redirect(
                url_for("profile")
            )

        if session.get("employee"):

            staff = query_db(
                """
                SELECT
                    role,
                    is_active
                FROM restaurant_staff
                WHERE user_id = %s
                AND restaurant_id = %s
                LIMIT 1
                """,
                [
                    session["user_id"],
                    restaurant["id"]
                ],
                one=True
            )

            if staff is None:

                session.clear()

                flash(
                    "حساب الموظف غير صالح.",
                    "danger"
                )

                return redirect(
                    url_for("employee_login")
                )

            if staff["is_active"] != 1:

                session.clear()

                flash(
                    "حساب الموظف غير نشط.",
                    "danger"
                )

                return redirect(
                    url_for("employee_login")
                )

            if staff["role"] not in (
                "customers",
                "manager"
            ):

                flash(
                    "ليس لديك صلاحية للوصول إلى العملاء.",
                    "danger"
                )

                return redirect(
                    url_for("employee_dashboard")
                )

            session["restaurant_id"] = restaurant["id"]

        return function(*args, **kwargs)

    return decorated_function
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
        [
            user_id
        ]
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
        [
            user_id
        ]
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
        [
            user_id
        ]
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
        [
            user_id
        ]
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
# تسجيل الخروج
# =========================================================
@app.route("/logout")
def logout():
    session.clear()
    flash("تم تسجيل الخروج بنجاح.", "success")
    return redirect(url_for("home"))


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

#=========================================================

#التسجيل

#=========================================================

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

        language = request.form.get(
            "language",
            "ar"
        ).strip()

        if language not in ("ar", "en", "fr"):
            language = "ar"

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        terms = request.form.get(
            "terms"
        )

        if not name or not email or not password:

            flash(
                "يرجى ملء جميع الحقول المطلوبة.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        if not terms:

            flash(
                "يجب الموافقة على الشروط والأحكام.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 6:

            flash(
                "كلمة المرور يجب أن تكون 6 أحرف أو أكثر.",
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

        password_hash = generate_password_hash(
            password
        )

        execute_db(
            """
            INSERT INTO users (
                name,
                email,
                phone,
                password,
                role,
                is_active,
                account_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                name,
                email,
                phone,
                password_hash,
                "restaurant_owner",
                1,
                "pending"
            ]
        )

        flash(
            "تم إنشاء الحساب بنجاح. حسابك قيد مراجعة الإدارة.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )

#=========================================================

#تسجيل الدخول

#=========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # =================================================
        # البحث عن المستخدم بالبريد الإلكتروني
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
        # إذا لم يوجد بالبريد، نبحث عن موظف بالاسم
        # =================================================

        if user is None:

            user = query_db(
                """
                SELECT users.*
                FROM users
                INNER JOIN restaurant_staff
                    ON restaurant_staff.user_id = users.id
                WHERE LOWER(users.name) = %s
                    AND restaurant_staff.is_active = 1
                    AND users.is_active = 1
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
                "البريد الإلكتروني أو اسم الموظف أو كلمة المرور غير صحيحة.",
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
        # التحقق من حالة النشاط لصاحب النشاط
        # =================================================
        if user["role"] != "admin":

            restaurant = query_db(
                """
                SELECT id, is_active
                FROM restaurants
                WHERE owner_id = %s
                LIMIT 1
                """,
                [user["id"]],
                one=True
            )

            if restaurant is not None and restaurant["is_active"] != 1:
                session.clear()

                flash(
                    "تم إيقاف النشاط من الإدارة.",
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
        # توجيه الموظف
        # =================================================

        if user["role"] == "employee":

            return redirect(
                url_for("employee_dashboard")
            )

        # =================================================
        # توجيه صاحب المطعم
        # =================================================

        return redirect(
        url_for("dashboard")
    )

    return render_template("login.html")



# =========================================================
# نظام الموظفين
# =========================================================

@app.route("/employee")
@login_required
def employee_dashboard():

    if not session.get("employee"):

        flash(
            "هذه الصفحة مخصصة للموظفين فقط.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    user_id = session.get("user_id")

    staff = query_db(
        """
        SELECT
            restaurant_staff.id,
            restaurant_staff.role,
            restaurant_staff.is_active,
            restaurants.name AS restaurant_name
        FROM restaurant_staff
        INNER JOIN restaurants
            ON restaurants.id = restaurant_staff.restaurant_id
        WHERE restaurant_staff.user_id = %s
        AND restaurant_staff.is_active = 1
        LIMIT 1
        """,
        [
            user_id
        ],
        one=True
    )

    if staff is None:

        session.clear()

        flash(
            "لا يوجد حساب موظف نشط مرتبط بهذا المستخدم.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    user = current_user()

    return render_template(
        "employee.html",
        user=user,
        staff=staff
    )

@app.route("/employee/login", methods=["GET", "POST"])
def employee_login():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")

        if not name or not password:
            flash(
                "يرجى إدخال اسم الموظف وكلمة المرور.",
                "danger"
            )
            return render_template("employee_login.html")

        # البحث عن الموظف
        staff = query_db(
            """
            SELECT
                users.id,
                users.name,
                users.password,
                users.is_active,
                users.account_status,
                restaurant_staff.restaurant_id,
                restaurant_staff.role,
                restaurant_staff.is_active AS staff_active,
                restaurants.name AS restaurant_name,
                restaurants.is_active AS restaurant_active
            FROM users
            INNER JOIN restaurant_staff
                ON restaurant_staff.user_id = users.id
            INNER JOIN restaurants
                ON restaurants.id = restaurant_staff.restaurant_id
            WHERE LOWER(users.name) = %s
            AND users.role = 'employee'
            LIMIT 1
            """,
            [name.lower()],
            one=True
        )

        # الموظف غير موجود
        if staff is None:
            flash(
                "اسم الموظف أو كلمة المرور غير صحيحة.",
                "danger"
            )
            return render_template("employee_login.html")

        # حساب الموظف موقوف
        if staff["is_active"] != 1:
            flash(
                "حساب الموظف غير نشط.",
                "danger"
            )
            return render_template("employee_login.html")

        # النشاط موقوف
        if staff["restaurant_active"] != 1:
            flash(
                "هذا النشاط موقوف حاليًا من الإدارة.",
                "danger"
            )
            return render_template("employee_login.html")

        # الموظف نفسه موقوف داخل النشاط
        if staff["staff_active"] != 1:
            flash(
                "تم إيقاف حساب الموظف داخل هذا النشاط.",
                "danger"
            )
            return render_template("employee_login.html")

        # التحقق من كلمة المرور
        if not check_password_hash(
            staff["password"],
            password
        ):
            flash(
                "اسم الموظف أو كلمة المرور غير صحيحة.",
                "danger"
            )
            return render_template("employee_login.html")

        # إنهاء أي جلسة قديمة
        session.clear()

        # إنشاء جلسة الموظف
        session["user_id"] = staff["id"]
        session["user_name"] = staff["name"]
        session["employee"] = True
        session["restaurant_id"] = staff["restaurant_id"]

        flash(
            "تم تسجيل الدخول بنجاح.",
            "success"
        )

        # التوجيه حسب الصلاحية
        if staff["role"] == "products":
            return redirect(url_for("products"))

        elif staff["role"] == "orders":
            return redirect(url_for("orders"))

        elif staff["role"] == "customers":
            return redirect(url_for("customers"))

        elif staff["role"] == "manager":
            return redirect(url_for("employee_dashboard"))

        else:
            session.clear()
            flash(
                "ليس لديك صلاحية للوصول إلى أي منصة.",
                "danger"
            )
            return redirect(url_for("employee_login"))

    return render_template("employee_login.html")


@app.route("/staff/add", methods=["POST"])
@restaurant_required
def add_staff():

    restaurant = current_restaurant()

    name = request.form.get(
        "name",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    role = request.form.get(
        "role",
        "orders"
    ).strip()

    if not name or not password:

        flash(
            "اسم الموظف وكلمة المرور مطلوبان.",
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )

    allowed_roles = {
        "orders",
        "products",
        "cashier",
        "manager"
    }

    if role not in allowed_roles:

        role = "orders"

    existing_staff = query_db(
        """
        SELECT users.id
        FROM users
        INNER JOIN restaurant_staff
            ON restaurant_staff.user_id = users.id
        WHERE restaurant_staff.restaurant_id = %s
        AND LOWER(users.name) = %s
        AND restaurant_staff.is_active = 1
        LIMIT 1
        """,
        [
            restaurant["id"],
            name.lower()
        ],
        one=True
    )

    if existing_staff:

        flash(
            "يوجد موظف بهذا الاسم بالفعل.",
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )

    employee_email = (
        "employee_"
        + uuid.uuid4().hex
        + "@menusmart.local"
    )

    hashed_password = generate_password_hash(
        password
    )

    execute_db(
        """
        INSERT INTO users (
            name,
            email,
            password,
            role,
            is_active,
            account_status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        [
            name,
            employee_email,
            hashed_password,
            "employee",
            1,
            "approved"
        ]
    )

    user = query_db(
        """
        SELECT id
        FROM users
        WHERE email = %s
        LIMIT 1
        """,
        [
            employee_email
        ],
        one=True
    )

    user_id = user["id"]

    execute_db(
        """
        INSERT INTO restaurant_staff (
            restaurant_id,
            user_id,
            role,
            is_active
        )
        VALUES (%s, %s, %s, %s)
        """,
        [
            restaurant["id"],
            user_id,
            role,
            1
        ]
    )

    flash(
        "تم إنشاء حساب الموظف بنجاح.",
        "success"
    )

    return redirect(
        url_for("dashboard")
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

        language = request.form.get("language", "ar").strip().lower()

        print("=== LANGUAGE DEBUG ===")
        print("FORM:", request.form)
        print("LANGUAGE:", repr(language))

        if language not in ("ar", "en", "fr"):
            language = "ar"

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
                    language = %s,
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
                    language,
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
                    language,
                    allow_orders,
                    allow_delivery,
                    delivery_fee
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
            url_for("dashboard")
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
@restaurant_or_products_required
def categories():

    restaurant = accessible_restaurant()

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
@restaurant_or_products_required
def category_add():

    restaurant = accessible_restaurant()
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
@restaurant_or_products_required
def category_edit(category_id):

    restaurant = accessible_restaurant()

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
@restaurant_or_products_required
def category_delete(category_id):

    restaurant = accessible_restaurant()

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
@employee_products_required
def products():

    restaurant = accessible_restaurant()

    print("PRODUCTS RESTAURANT:", restaurant)

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
@employee_products_required
def product_add():

    restaurant = accessible_restaurant()

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
@employee_products_required
def product_edit(product_id):

    restaurant = accessible_restaurant()

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
@employee_products_required
def product_delete(product_id):

    restaurant = accessible_restaurant()

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
# لوحة التحكم
# =========================================================
@app.route("/dashboard")
@restaurant_required
def dashboard():
    restaurant = current_restaurant()

    stats = query_db(
        """
        SELECT
            (SELECT COUNT(*) FROM categories WHERE restaurant_id = %s) AS categories_count,
            (SELECT COUNT(*) FROM products WHERE restaurant_id = %s) AS products_count,
            (SELECT COUNT(*) FROM orders WHERE restaurant_id = %s) AS orders_count,
            (SELECT COUNT(*) FROM customers WHERE restaurant_id = %s) AS customers_count
        """,
        [
            restaurant["id"],
            restaurant["id"],
            restaurant["id"],
            restaurant["id"]
        ],
        one=True
    )

    categories_count = stats["categories_count"]
    products_count = stats["products_count"]
    orders_count = stats["orders_count"]
    customers_count = stats["customers_count"]

    recent_orders = query_db(
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
        LIMIT 5
        """,
        [restaurant["id"]]
    )

    return render_template(
        "dashboard.html",
        restaurant=restaurant,
        categories_count=categories_count,
        products_count=products_count,
        orders_count=orders_count,
        customers_count=customers_count,
        recent_orders=recent_orders
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
@restaurant_or_orders_required
def orders():

    restaurant = accessible_restaurant()

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
@restaurant_or_orders_required
def latest_orders():

    restaurant = accessible_restaurant()

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
@restaurant_or_orders_required
def order_details(order_id):

    restaurant = accessible_restaurant()

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
@restaurant_or_orders_required
def order_invoice(order_id):

    restaurant = accessible_restaurant()
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
@restaurant_or_orders_required
def update_order_status(order_id):

    restaurant = accessible_restaurant()

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
@restaurant_or_customers_required
def customers():

    restaurant = accessible_restaurant()

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
    restaurant_id = restaurant["id"]

    # =====================================================
    # الإحصائيات الأساسية
    # =====================================================

    total_orders = query_db(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE restaurant_id = %s
        """,
        [restaurant_id],
        one=True
    )["count"]

    total_sales = query_db(
        """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM orders
        WHERE restaurant_id = %s
        AND status = 'completed'
        """,
        [restaurant_id],
        one=True
    )["total"]

    total_customers = query_db(
        """
        SELECT COUNT(DISTINCT customer_id) AS count
        FROM orders
        WHERE restaurant_id = %s
        AND customer_id IS NOT NULL
        """,
        [restaurant_id],
        one=True
    )["count"]

    average_order = query_db(
        """
        SELECT COALESCE(AVG(total), 0) AS average
        FROM orders
        WHERE restaurant_id = %s
        AND status = 'completed'
        """,
        [restaurant_id],
        one=True
    )["average"]

    # =====================================================
    # حالات الطلبات
    # =====================================================

    completed_orders = query_db(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE restaurant_id = %s
        AND status = 'completed'
        """,
        [restaurant_id],
        one=True
    )["count"]

    confirmed_orders = query_db(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE restaurant_id = %s
        AND status = 'confirmed'
        """,
        [restaurant_id],
        one=True
    )["count"]

    pending_orders = query_db(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE restaurant_id = %s
        AND status = 'pending'
        """,
        [restaurant_id],
        one=True
    )["count"]

    cancelled_orders = query_db(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE restaurant_id = %s
        AND status = 'cancelled'
        """,
        [restaurant_id],
        one=True
    )["count"]

    # =====================================================
    # نسب حالات الطلبات
    # =====================================================

    if total_orders > 0:

        completed_percentage = round(
            (completed_orders / total_orders) * 100,
            1
        )

        confirmed_percentage = round(
            (confirmed_orders / total_orders) * 100,
            1
        )

        pending_percentage = round(
            (pending_orders / total_orders) * 100,
            1
        )

        cancelled_percentage = round(
            (cancelled_orders / total_orders) * 100,
            1
        )

    else:

        completed_percentage = 0
        confirmed_percentage = 0
        pending_percentage = 0
        cancelled_percentage = 0

    # =====================================================
    # الرسم البياني - آخر 7 أيام
    # =====================================================

    daily_analytics = query_db(
        """
        SELECT
            d::date AS day,
            COUNT(o.id) AS orders_count,
            COALESCE(
                SUM(
                    CASE
                        WHEN o.status = 'completed'
                        THEN o.total
                        ELSE 0
                    END
                ),
                0
            ) AS sales
        FROM generate_series(
            CURRENT_DATE - INTERVAL '6 days',
            CURRENT_DATE,
            INTERVAL '1 day'
        ) AS d
        LEFT JOIN orders o
            ON o.restaurant_id = %s
            AND o.created_at::date = d::date
        GROUP BY d
        ORDER BY d
        """,
        [restaurant_id]
    )

    # =====================================================
    # تجهيز بيانات الرسم للـ HTML
    # =====================================================

    daily_labels = []
    daily_orders = []
    daily_sales = []

    arabic_days = {
        0: "الإثنين",
        1: "الثلاثاء",
        2: "الأربعاء",
        3: "الخميس",
        4: "الجمعة",
        5: "السبت",
        6: "الأحد"
    }

    for row in daily_analytics:

        day = row["day"]

        daily_labels.append(
            arabic_days.get(day.weekday(), "")
        )

        daily_orders.append(
            int(row["orders_count"] or 0)
        )

        daily_sales.append(
            float(row["sales"] or 0)
        )

    # =====================================================
    # أكثر المنتجات طلبًا
    # =====================================================

    top_products = query_db(
        """
        SELECT
            product_name AS name,
            SUM(quantity) AS orders_count,
            COALESCE(SUM(total), 0) AS total_sales
        FROM order_items
        WHERE order_id IN (
            SELECT id
            FROM orders
            WHERE restaurant_id = %s
            AND status = 'completed'
        )
        GROUP BY product_name
        ORDER BY orders_count DESC
        LIMIT 5
        """,
        [restaurant_id]
    )

    # =====================================================
    # عدد المنتجات
    # =====================================================

    total_products = query_db(
        """
        SELECT COUNT(*) AS count
        FROM products
        WHERE restaurant_id = %s
        """,
        [restaurant_id],
        one=True
    )["count"]

    # =====================================================
    # مشاهدات المنيو
    # =====================================================

    menu_views = query_db(
        """
        SELECT COUNT(*) AS count
        FROM menu_views
        WHERE restaurant_id = %s
        """,
        [restaurant_id],
        one=True
    )["count"]

    # =====================================================
    # معدل التحويل
    # الطلبات ÷ مشاهدات المنيو
    # =====================================================

    if menu_views > 0:

        conversion_rate = round(
            (total_orders / menu_views) * 100,
            1
        )

    else:

        conversion_rate = 0

    # =====================================================
    # إرسال البيانات للصفحة
    # =====================================================

    return render_template(
        "analytics.html",

        restaurant=restaurant,

        total_sales=float(total_sales or 0),
        total_orders=total_orders,
        total_customers=total_customers,
        average_order=float(average_order or 0),
        total_products=total_products,

        completed_orders=completed_orders,
        confirmed_orders=confirmed_orders,
        pending_orders=pending_orders,
        cancelled_orders=cancelled_orders,

        completed_percentage=completed_percentage,
        confirmed_percentage=confirmed_percentage,
        pending_percentage=pending_percentage,
        cancelled_percentage=cancelled_percentage,

        top_products=top_products,

        menu_views=menu_views,
        conversion_rate=conversion_rate,

        daily_labels=daily_labels,
        daily_orders=daily_orders,
        daily_sales=daily_sales
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
# الإشعارات
# =========================================================

@app.route("/api/notifications")
@login_required
def api_notifications():

    user_id = session["user_id"]

    notifications = query_db(
        """
        SELECT
            id,
            title,
            message,
            notification_type,
            is_read,
            created_at
        FROM notifications
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 20
        """,
        [
            user_id
        ]
    )

    unread = query_db(
        """
        SELECT COUNT(*) AS count
        FROM notifications
        WHERE user_id = %s
          AND is_read = 0
        """,
        [
            user_id
        ],
        one=True
    )

    return jsonify(
        {
            "unread_count": unread["count"],
            "notifications": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "message": item["message"],
                    "type": item["notification_type"],
                    "is_read": bool(item["is_read"]),
                    "created_at": str(item["created_at"])
                }
                for item in notifications
            ]
        }
    )
# =========================================================
# تحديد إشعار كمقروء
# =========================================================

@app.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):

    execute_db(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE id = %s
          AND user_id = %s
        """,
        [
            notification_id,
            session["user_id"]
        ]
    )

    return jsonify({
        "success": True
    })
    # =========================================================
# تحديد جميع الإشعارات كمقروءة
# =========================================================

@app.route("/api/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():

    execute_db(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = %s
          AND is_read = 0
        """,
        [
            session["user_id"]
        ]
    )

    return jsonify({
        "success": True
    })
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


@app.route("/admin/contact-messages/count")
@admin_required
def admin_contact_messages_count():
    result = query_db(
        """
        SELECT COUNT(*) AS count
        FROM contact_messages
        WHERE status = 'new'
        """,
        one=True
    )

    return {"count": result["count"] if result else 0}

@app.route("/admin/contact-messages")
@admin_required
def admin_contact_messages():
    messages = query_db(
        """
        SELECT
            id,
            name,
            email,
            subject,
            message,
            status,
            created_at
        FROM contact_messages
        ORDER BY created_at DESC
        """
    )

    return render_template(
        "admin_contact_messages.html",
        messages=messages,
        user=current_user()
    )

@app.route("/admin/contact-messages/<int:message_id>/status", methods=["POST"])
@admin_required
def admin_contact_message_status(message_id):
    status = request.form.get("status", "").strip()

    if status not in ("new", "read", "replied"):
        flash("حالة الرسالة غير صحيحة.", "danger")
        return redirect(url_for("admin_contact_messages"))

    execute_db(
        """
        UPDATE contact_messages
        SET status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        [status, message_id]
    )

    flash("تم تحديث حالة الرسالة بنجاح.", "success")

    return redirect(url_for("admin_contact_messages"))

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not phone or not subject or not message:
            flash("يرجى ملء جميع الحقول المطلوبة.", "danger")
            return redirect(url_for("contact"))

        execute_db(
            """
            INSERT INTO contact_messages
                (name, phone, subject, message)
            VALUES
                (%s, %s, %s, %s)
            """,
            [name, phone, subject, message]
        )

        flash(
            "تم إرسال رسالتك بنجاح. شكرًا لتواصلك معنا.",
            "success"
        )

        return redirect(url_for("contact"))

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



# =========================================================
# ملف نشاط مستقل للأدمن
# =========================================================

@app.route("/admin/restaurant/<int:restaurant_id>")
@admin_required
def admin_restaurant(restaurant_id):

    restaurant = query_db(
        """
        SELECT
            r.*,
            owner.name AS owner_name,
            owner.email AS owner_email
        FROM restaurants r
        LEFT JOIN users owner
            ON owner.id = r.owner_id
        WHERE r.id = %s
        LIMIT 1
        """,
        [restaurant_id],
        one=True
    )

    if restaurant is None:
        flash("النشاط غير موجود.", "danger")
        return redirect(url_for("admin"))

    employees = query_db(
        """
        SELECT
            rs.id AS staff_id,
            rs.restaurant_id,
            rs.user_id,
            rs.role AS staff_role,
            rs.is_active AS staff_active,
            rs.created_at AS staff_created_at,
            u.name,
            u.email,
            u.is_active AS user_active
        FROM restaurant_staff rs
        LEFT JOIN users u
            ON u.id = rs.user_id
        WHERE rs.restaurant_id = %s
        ORDER BY rs.id DESC
        """,
        [restaurant_id]
    )

    return render_template(
        "admin_restaurant.html",
        restaurant=restaurant,
        employees=employees
    )


# =========================================================
# تعديل بيانات النشاط من لوحة الأدمن
# =========================================================

@app.route(
    "/admin/restaurant/<int:restaurant_id>/edit",
    methods=["GET", "POST"]
)
@admin_required
def admin_edit_restaurant(restaurant_id):

    restaurant = query_db(
        """
        SELECT
            r.*,
            owner.name AS owner_name,
            owner.email AS owner_email
        FROM restaurants r
        LEFT JOIN users owner
            ON owner.id = r.owner_id
        WHERE r.id = %s
        LIMIT 1
        """,
        [restaurant_id],
        one=True
    )

    if restaurant is None:
        flash("النشاط غير موجود.", "danger")
        return redirect(url_for("admin"))

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

        if not restaurant_name:
            flash("اسم النشاط مطلوب.", "danger")

            return render_template(
                "admin_restaurant_edit.html",
                restaurant=restaurant
            )

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
                restaurant_id
            ]
        )

        flash(
            "تم تحديث بيانات النشاط بنجاح.",
            "success"
        )

        return redirect(
            url_for(
                "admin_restaurant",
                restaurant_id=restaurant_id
            )
        )

    return render_template(
        "admin_restaurant_edit.html",
        restaurant=restaurant
    )



# =========================================================
# إدارة النشاط من داخل ملف النشاط بواسطة الأدمن
# =========================================================

@app.route(
    "/admin/restaurant/<int:restaurant_id>/toggle",
    methods=["POST"]
)
@admin_required
def admin_toggle_restaurant(restaurant_id):

    restaurant = query_db(
        """
        SELECT id, is_active, name
        FROM restaurants
        WHERE id = %s
        LIMIT 1
        """,
        [restaurant_id],
        one=True
    )

    if restaurant is None:
        flash("النشاط غير موجود.", "danger")
        return redirect(url_for("admin"))

    new_status = 0 if restaurant["is_active"] else 1

    execute_db(
        """
        UPDATE restaurants
        SET is_active = %s
        WHERE id = %s
        """,
        [new_status, restaurant_id]
    )

    if new_status:
        flash("تم تفعيل النشاط بنجاح.", "success")
    else:
        flash("تم إيقاف النشاط بنجاح.", "warning")

    return redirect(
        url_for(
            "admin_restaurant",
            restaurant_id=restaurant_id
        )
    )


@app.route(
    "/admin/restaurant/<int:restaurant_id>/owner/toggle",
    methods=["POST"]
)
@admin_required
def admin_toggle_restaurant_owner(restaurant_id):

    restaurant = query_db(
        """
        SELECT
            r.id,
            r.owner_id,
            u.name
        FROM restaurants r
        LEFT JOIN users u
            ON u.id = r.owner_id
        WHERE r.id = %s
        LIMIT 1
        """,
        [restaurant_id],
        one=True
    )

    if restaurant is None or restaurant["owner_id"] is None:
        flash("صاحب النشاط غير موجود.", "danger")
        return redirect(
            url_for(
                "admin_restaurant",
                restaurant_id=restaurant_id
            )
        )

    owner = query_db(
        """
        SELECT id, is_active, role
        FROM users
        WHERE id = %s
        AND role != 'admin'
        LIMIT 1
        """,
        [restaurant["owner_id"]],
        one=True
    )

    if owner is None:
        flash("حساب صاحب النشاط غير موجود.", "danger")
        return redirect(
            url_for(
                "admin_restaurant",
                restaurant_id=restaurant_id
            )
        )

    new_status = 0 if owner["is_active"] else 1

    execute_db(
        """
        UPDATE users
        SET
            is_active = %s,
            account_status = %s
        WHERE id = %s
        AND role != 'admin'
        """,
        [
            new_status,
            "approved" if new_status else "suspended",
            owner["id"]
        ]
    )

    if new_status:
        flash("تم تفعيل حساب صاحب النشاط.", "success")
    else:
        flash("تم إيقاف حساب صاحب النشاط.", "warning")

    return redirect(
        url_for(
            "admin_restaurant",
            restaurant_id=restaurant_id
        )
    )


@app.route(
    "/admin/restaurant/<int:restaurant_id>/owner/reset-password",
    methods=["POST"]
)
@admin_required
def admin_restaurant_owner_reset_password(restaurant_id):

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
            url_for(
                "admin_restaurant",
                restaurant_id=restaurant_id
            )
        )

    restaurant = query_db(
        """
        SELECT owner_id
        FROM restaurants
        WHERE id = %s
        LIMIT 1
        """,
        [restaurant_id],
        one=True
    )

    if restaurant is None or restaurant["owner_id"] is None:
        flash("صاحب النشاط غير موجود.", "danger")
        return redirect(
            url_for(
                "admin_restaurant",
                restaurant_id=restaurant_id
            )
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
            restaurant["owner_id"]
        ]
    )

    flash(
        "تم تغيير كلمة مرور صاحب النشاط بنجاح.",
        "success"
    )

    return redirect(
        url_for(
            "admin_restaurant",
            restaurant_id=restaurant_id
        )
    )


@app.route(
    "/admin/restaurant/<int:restaurant_id>/employee/<int:user_id>/toggle",
    methods=["POST"]
)
@admin_required
def admin_toggle_restaurant_employee(
    restaurant_id,
    user_id
):

    staff = query_db(
        """
        SELECT
            rs.user_id,
            rs.is_active
        FROM restaurant_staff rs
        WHERE rs.restaurant_id = %s
        AND rs.user_id = %s
        LIMIT 1
        """,
        [
            restaurant_id,
            user_id
        ],
        one=True
    )

    if staff is None:
        flash("الموظف غير مرتبط بهذا النشاط.", "danger")
        return redirect(
            url_for(
                "admin_restaurant",
                restaurant_id=restaurant_id
            )
        )

    new_status = 0 if staff["is_active"] else 1

    execute_db(
        """
        UPDATE restaurant_staff
        SET is_active = %s
        WHERE restaurant_id = %s
        AND user_id = %s
        """,
        [
            new_status,
            restaurant_id,
            user_id
        ]
    )

    execute_db(
        """
        UPDATE users
        SET is_active = %s
        WHERE id = %s
        AND role != 'admin'
        """,
        [
            new_status,
            user_id
        ]
    )

    if new_status:
        flash("تم تفعيل الموظف.", "success")
    else:
        flash("تم إيقاف الموظف.", "warning")

    return redirect(
        url_for(
            "admin_restaurant",
            restaurant_id=restaurant_id
        )
    )


@app.route(
    "/admin/restaurant/<int:restaurant_id>/employee/<int:user_id>/reset-password",
    methods=["POST"]
)
@admin_required
def admin_restaurant_employee_reset_password(
    restaurant_id,
    user_id
):

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
            url_for(
                "admin_restaurant",
                restaurant_id=restaurant_id
            )
        )

    staff = query_db(
        """
        SELECT user_id
        FROM restaurant_staff
        WHERE restaurant_id = %s
        AND user_id = %s
        LIMIT 1
        """,
        [
            restaurant_id,
            user_id
        ],
        one=True
    )

    if staff is None:
        flash("الموظف غير مرتبط بهذا النشاط.", "danger")
        return redirect(
            url_for(
                "admin_restaurant",
                restaurant_id=restaurant_id
            )
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
        "تم تغيير كلمة مرور الموظف بنجاح.",
        "success"
    )

    return redirect(
        url_for(
            "admin_restaurant",
            restaurant_id=restaurant_id
        )
    )


# =========================================================
# إعدادات حساب الأدمن الحالي
# =========================================================

@app.route(
    "/admin/settings",
    methods=["GET", "POST"]
)
@admin_required
def admin_settings():

    user = query_db(
        """
        SELECT id, name, email, phone
        FROM users
        WHERE id = %s
        AND role = 'admin'
        LIMIT 1
        """,
        [session["user_id"]],
        one=True
    )

    if user is None:
        flash("حساب الأدمن غير موجود.", "danger")
        return redirect(url_for("admin"))

    if request.method == "POST":

        action = request.form.get(
            "action",
            "profile"
        )

        # -------------------------------------------------
        # تحديث بيانات الأدمن
        # -------------------------------------------------

        if action == "profile":

            name = request.form.get(
                "name",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip()

            phone = request.form.get(
                "phone",
                ""
            ).strip()

            if not name:
                flash(
                    "اسم الأدمن مطلوب.",
                    "danger"
                )
                return redirect(
                    url_for("admin_settings")
                )

            if not email:
                flash(
                    "البريد الإلكتروني مطلوب.",
                    "danger"
                )
                return redirect(
                    url_for("admin_settings")
                )

            existing = query_db(
                """
                SELECT id
                FROM users
                WHERE email = %s
                AND id != %s
                LIMIT 1
                """,
                [
                    email,
                    user["id"]
                ],
                one=True
            )

            if existing:
                flash(
                    "البريد الإلكتروني مستخدم بالفعل.",
                    "danger"
                )
                return redirect(
                    url_for("admin_settings")
                )

            execute_db(
                """
                UPDATE users
                SET
                    name = %s,
                    email = %s,
                    phone = %s
                WHERE id = %s
                AND role = 'admin'
                """,
                [
                    name,
                    email,
                    phone,
                    user["id"]
                ]
            )

            flash(
                "تم تحديث بيانات حساب الأدمن.",
                "success"
            )

            return redirect(
                url_for("admin_settings")
            )

        # -------------------------------------------------
        # تغيير كلمة المرور
        # -------------------------------------------------

        if action == "password":

            current_password = request.form.get(
                "current_password",
                ""
            )

            new_password = request.form.get(
                "new_password",
                ""
            )

            confirm_password = request.form.get(
                "confirm_password",
                ""
            )

            if not check_password_hash(
                user["password"],
                current_password
            ):
                flash(
                    "كلمة المرور الحالية غير صحيحة.",
                    "danger"
                )
                return redirect(
                    url_for("admin_settings")
                )

            if len(new_password) < 6:
                flash(
                    "كلمة المرور الجديدة يجب أن تكون 6 أحرف أو أكثر.",
                    "danger"
                )
                return redirect(
                    url_for("admin_settings")
                )

            if new_password != confirm_password:
                flash(
                    "تأكيد كلمة المرور غير مطابق.",
                    "danger"
                )
                return redirect(
                    url_for("admin_settings")
                )

            password_hash = generate_password_hash(
                new_password
            )

            execute_db(
                """
                UPDATE users
                SET password = %s
                WHERE id = %s
                AND role = 'admin'
                """,
                [
                    password_hash,
                    user["id"]
                ]
            )

            flash(
                "تم تغيير كلمة مرور الأدمن بنجاح.",
                "success"
            )

            return redirect(
                url_for("admin_settings")
            )

    return render_template(
        "admin_settings.html",
        user=user
    )

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
