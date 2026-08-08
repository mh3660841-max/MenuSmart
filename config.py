import os

=========================================================

مسار المشروع

=========================================================

BASE_DIR = os.path.dirname(
os.path.abspath(file)
)

=========================================================

إعدادات التطبيق

=========================================================

APP_NAME = "Menu Smart"

APP_DESCRIPTION = (
"منصة ذكية لإنشاء وإدارة "
"المنيو الإلكتروني للمطاعم والكافيهات"
)

=========================================================

وضع التشغيل

=========================================================

DEBUG = True

TESTING = False

=========================================================

قاعدة البيانات - Neon PostgreSQL

=========================================================

DATABASE_URL_FILE = os.path.join(
BASE_DIR,
"database_url.txt"
)

DATABASE_URL = None

if os.path.exists(DATABASE_URL_FILE):

with open(
    DATABASE_URL_FILE,
    "r",
    encoding="utf-8"
) as file:

    DATABASE_URL = file.read().strip()

محاولة القراءة من متغير البيئة إذا لم يوجد الملف

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
database_url_file = os.path.join(
BASE_DIR,
"database_url.txt"
)

if os.path.exists(database_url_file):
    with open(
        database_url_file,
        "r",
        encoding="utf-8"
    ) as f:
        DATABASE_URL = f.read().strip()

DATABASE_PASSWORD = os.environ.get(
"DATABASE_PASSWORD"
)

if not DATABASE_URL:
raise RuntimeError(
"DATABASE_URL غير موجود. "
"ضع Connection String الخاصة بقاعدة Neon "
"داخل ملف database_url.txt"
)

=========================================================

مفتاح الجلسات

=========================================================

SECRET_KEY = os.environ.get(
"MENUSMART_SECRET_KEY",
"change-this-secret-key-in-production"
)

=========================================================

إعدادات الجلسة

=========================================================

SESSION_COOKIE_NAME = "menusmart_session"

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = "Lax"

يصبح True عند تشغيل الموقع عبر HTTPS

SESSION_COOKIE_SECURE = False

PERMANENT_SESSION_LIFETIME = (
60 * 60 * 24 * 7
)

=========================================================

مجلد رفع الصور

=========================================================

UPLOAD_FOLDER = os.environ.get(
"UPLOAD_FOLDER",
os.path.join(
BASE_DIR,
"static",
"images",
"uploads"
)
)

=========================================================

أنواع الصور المسموح بها

=========================================================

ALLOWED_EXTENSIONS = {
"png",
"jpg",
"jpeg",
"webp",
"gif"
}

=========================================================

الحد الأقصى لحجم الملفات

=========================================================

MAX_UPLOAD_SIZE = (
10 * 1024 * 1024
)

=========================================================

العملة الافتراضية

=========================================================

DEFAULT_CURRENCY = "EGP"

=========================================================

إعدادات الطلبات

=========================================================

DEFAULT_DELIVERY_FEE = 0

DEFAULT_ORDER_STATUS = "pending"

DEFAULT_PAYMENT_STATUS = "pending"

=========================================================

حالات الحساب

=========================================================

ACCOUNT_STATUS_PENDING = "pending"

ACCOUNT_STATUS_APPROVED = "approved"

ACCOUNT_STATUS_REJECTED = "rejected"

ACCOUNT_STATUS_SUSPENDED = "suspended"

=========================================================

حالات اعتماد المطعم

=========================================================

RESTAURANT_STATUS_PENDING = "pending"

RESTAURANT_STATUS_APPROVED = "approved"

RESTAURANT_STATUS_REJECTED = "rejected"

RESTAURANT_STATUS_SUSPENDED = "suspended"

=========================================================

صلاحيات المستخدمين

=========================================================

ROLE_ADMIN = "admin"

ROLE_RESTAURANT_OWNER = "restaurant_owner"

=========================================================

إعدادات المنيو

=========================================================

DEFAULT_MENU_ACTIVE = 1

DEFAULT_CATEGORY_ACTIVE = 1

DEFAULT_PRODUCT_AVAILABLE = 1

DEFAULT_PRODUCT_FEATURED = 0

=========================================================

إنشاء المجلدات المطلوبة

=========================================================

os.makedirs(
UPLOAD_FOLDER,
exist_ok=True
)