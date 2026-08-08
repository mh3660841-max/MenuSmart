import os
import pg8000.dbapi

from flask import g

from config import DATABASE_URL

PASSWORD = os.environ.get("DATABASE_PASSWORD")


# =========================================================
# الاتصال بقاعدة البيانات
# =========================================================

def get_db():

    if "db" not in g:

        from urllib.parse import urlparse

        u = urlparse(DATABASE_URL)

        g.db = pg8000.dbapi.connect(
            host=u.hostname,
            port=u.port or 5432,
            user=u.username,
            password=u.password,
            database=u.path.lstrip("/"),
            ssl_context=True,
            timeout=30
        )

    return g.db

# =========================================================
# إغلاق الاتصال
# =========================================================

def close_db(exception=None):

    db = g.pop("db", None)

    if db is not None:
        db.close()

# =========================================================
# SELECT
# =========================================================

def query_db(
    query,
    args=(),
    one=False
):

    db = get_db()

    cursor = db.cursor()

    try:

        cursor.execute(
            query,
            args
        )

        rows = cursor.fetchall()

        columns = [
            column[0]
            for column in cursor.description
        ]

        result = [
            dict(zip(columns, row))
            for row in rows
        ]

        if one:
            return result[0] if result else None

        return result

    finally:

        cursor.close()


# =========================================================
# INSERT / UPDATE / DELETE
# =========================================================

def execute_db(
    query,
    args=()
):

    db = get_db()

    cursor = db.cursor()

    try:

        cursor.execute(
            query,
            args
        )

        db.commit()

        last_id = None

        if cursor.description:

            row = cursor.fetchone()

            if row:
                last_id = row[0]

        return last_id

    except Exception:

        db.rollback()

        raise

    finally:

        cursor.close()



# =========================================================
# تنفيذ أكثر من استعلام
# =========================================================

def execute_many(
    query,
    data
):

    db = get_db()

    cursor = db.cursor()

    try:

        cursor.executemany(
            query,
            data
        )

        db.commit()

    except Exception:

        db.rollback()

        raise

    finally:

        cursor.close()


# =========================================================
# إضافة عمود إذا لم يكن موجودًا
# =========================================================

def add_column_if_missing(
    cursor,
    table_name,
    column_name,
    column_definition
):

    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        """,
        (
            table_name,
            column_name
        )
    )

    exists = cursor.fetchone()

    if not exists:

        cursor.execute(
            f"""
            ALTER TABLE "{table_name}"
            ADD COLUMN "{column_name}"
            {column_definition}
            """
        )


# =========================================================
# إنشاء Trigger لتحديث updated_at
# =========================================================

def create_updated_at_trigger(
    cursor,
    table_name
):

    function_name = (
        f"update_{table_name}_updated_at"
    )

    trigger_name = (
        f"trg_{table_name}_updated_at"
    )

    # إنشاء دالة التحديث
    cursor.execute(
        f"""
        CREATE OR REPLACE FUNCTION
        {function_name}()
        RETURNS TRIGGER
        AS $$
        BEGIN

            NEW.updated_at = CURRENT_TIMESTAMP;

            RETURN NEW;

        END;
        $$
        LANGUAGE plpgsql;
        """
    )

    # حذف الـ Trigger القديم إن وجد
    cursor.execute(
        f"""
        DROP TRIGGER IF EXISTS
        {trigger_name}
        ON "{table_name}";
        """
    )

    # إنشاء Trigger جديد
    cursor.execute(
        f"""
        CREATE TRIGGER
        {trigger_name}

        BEFORE UPDATE
        ON "{table_name}"

        FOR EACH ROW

        EXECUTE FUNCTION
        {function_name}();
        """
    )


# =========================================================
# إنشاء قاعدة البيانات والجداول
# =========================================================

def init_db():

    db = get_db()

    cursor = db.cursor()

    try:

        # =====================================================
        # المستخدمون
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                id BIGSERIAL PRIMARY KEY,

                name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,

                phone TEXT,

                password TEXT NOT NULL,

                role TEXT
                    NOT NULL DEFAULT 'restaurant_owner',

                is_active INTEGER
                    NOT NULL DEFAULT 1,

                account_status TEXT
                    NOT NULL DEFAULT 'pending',

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        add_column_if_missing(
            cursor,
            "users",
            "role",
            "TEXT NOT NULL DEFAULT 'restaurant_owner'"
        )

        add_column_if_missing(
            cursor,
            "users",
            "is_active",
            "INTEGER NOT NULL DEFAULT 1"
        )

        add_column_if_missing(
            cursor,
            "users",
            "account_status",
            "TEXT NOT NULL DEFAULT 'pending'"
        )


        # =====================================================
        # المطاعم
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurants (

                id BIGSERIAL PRIMARY KEY,

                owner_id BIGINT NOT NULL,

                name TEXT NOT NULL,

                slug TEXT NOT NULL UNIQUE,

                description TEXT,

                address TEXT,

                phone TEXT,

                logo TEXT,

                is_active INTEGER
                    NOT NULL DEFAULT 0,

                approval_status TEXT
                    NOT NULL DEFAULT 'pending',

                approved_at TIMESTAMP,

                approved_by BIGINT,

                rejection_reason TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    owner_id
                )
                REFERENCES users(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    approved_by
                )
                REFERENCES users(id)
                ON DELETE SET NULL
            )
            """
        )


        add_column_if_missing(
            cursor,
            "restaurants",
            "approval_status",
            "TEXT NOT NULL DEFAULT 'pending'"
        )

        add_column_if_missing(
            cursor,
            "restaurants",
            "approved_at",
            "TIMESTAMP"
        )

        add_column_if_missing(
            cursor,
            "restaurants",
            "approved_by",
            "BIGINT"
        )

        add_column_if_missing(
            cursor,
            "restaurants",
            "rejection_reason",
            "TEXT"
        )

        add_column_if_missing(
            cursor,
            "restaurants",
            "updated_at",
            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )


        # =====================================================
        # إعدادات المطعم
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurant_settings (

                id BIGSERIAL PRIMARY KEY,

                restaurant_id BIGINT NOT NULL UNIQUE,

                primary_color TEXT
                    DEFAULT '#111111',

                secondary_color TEXT
                    DEFAULT '#D4AF37',

                currency TEXT
                    DEFAULT 'EGP',

                allow_orders INTEGER
                    DEFAULT 1,

                allow_delivery INTEGER
                    DEFAULT 1,

                delivery_fee NUMERIC(12,2)
                    DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE
            )
            """
        )


        add_column_if_missing(
            cursor,
            "restaurant_settings",
            "allow_orders",
            "INTEGER DEFAULT 1"
        )

        add_column_if_missing(
            cursor,
            "restaurant_settings",
            "allow_delivery",
            "INTEGER DEFAULT 1"
        )

        add_column_if_missing(
            cursor,
            "restaurant_settings",
            "delivery_fee",
            "NUMERIC(12,2) DEFAULT 0"
        )

        add_column_if_missing(
            cursor,
            "restaurant_settings",
            "updated_at",
            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )


        # =====================================================
        # المنيو
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS menus (

                id BIGSERIAL PRIMARY KEY,

                restaurant_id BIGINT NOT NULL,

                name TEXT NOT NULL,

                description TEXT,

                is_active INTEGER
                    DEFAULT 1,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE
            )
            """
        )


        # =====================================================
        # الأقسام
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (

                id BIGSERIAL PRIMARY KEY,

                restaurant_id BIGINT NOT NULL,

                menu_id BIGINT,

                name TEXT NOT NULL,

                description TEXT,

                icon TEXT
                    DEFAULT '🍽️',

                image TEXT,

                sort_order INTEGER
                    DEFAULT 0,

                is_active INTEGER
                    DEFAULT 1,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    menu_id
                )
                REFERENCES menus(id)
                ON DELETE SET NULL
            )
            """
        )


        add_column_if_missing(
            cursor,
            "categories",
            "menu_id",
            "BIGINT"
        )

        add_column_if_missing(
            cursor,
            "categories",
            "description",
            "TEXT"
        )

        add_column_if_missing(
            cursor,
            "categories",
            "icon",
            "TEXT DEFAULT '🍽️'"
        )

        add_column_if_missing(
            cursor,
            "categories",
            "image",
            "TEXT"
        )

        add_column_if_missing(
            cursor,
            "categories",
            "sort_order",
            "INTEGER DEFAULT 0"
        )

        add_column_if_missing(
            cursor,
            "categories",
            "is_active",
            "INTEGER DEFAULT 1"
        )

        add_column_if_missing(
            cursor,
            "categories",
            "created_at",
            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )

        add_column_if_missing(
            cursor,
            "categories",
            "updated_at",
            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )


        # =====================================================
        # المنتجات
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (

                id BIGSERIAL PRIMARY KEY,

                restaurant_id BIGINT NOT NULL,

                category_id BIGINT,

                menu_id BIGINT,

                name TEXT NOT NULL,

                description TEXT,

                price NUMERIC(12,2)
                    NOT NULL DEFAULT 0,

                old_price NUMERIC(12,2),

                image TEXT,

                available INTEGER
                    DEFAULT 1,

                featured INTEGER
                    DEFAULT 0,

                sort_order INTEGER
                    DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    category_id
                )
                REFERENCES categories(id)
                ON DELETE SET NULL,

                FOREIGN KEY (
                    menu_id
                )
                REFERENCES menus(id)
                ON DELETE SET NULL
            )
            """
        )


        add_column_if_missing(
            cursor,
            "products",
            "category_id",
            "BIGINT"
        )

        add_column_if_missing(
            cursor,
            "products",
            "menu_id",
            "BIGINT"
        )

        add_column_if_missing(
            cursor,
            "products",
            "description",
            "TEXT"
        )

        add_column_if_missing(
            cursor,
            "products",
            "price",
            "NUMERIC(12,2) DEFAULT 0"
        )

        add_column_if_missing(
            cursor,
            "products",
            "old_price",
            "NUMERIC(12,2)"
        )

        add_column_if_missing(
            cursor,
            "products",
            "image",
            "TEXT"
        )

        add_column_if_missing(
            cursor,
            "products",
            "available",
            "INTEGER DEFAULT 1"
        )

        add_column_if_missing(
            cursor,
            "products",
            "featured",
            "INTEGER DEFAULT 0"
        )

        add_column_if_missing(
            cursor,
            "products",
            "sort_order",
            "INTEGER DEFAULT 0"
        )

        add_column_if_missing(
            cursor,
            "products",
            "created_at",
            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )

        add_column_if_missing(
            cursor,
            "products",
            "updated_at",
            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )


        # =====================================================
        # خيارات المنتجات
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS product_options (

                id BIGSERIAL PRIMARY KEY,

                product_id BIGINT NOT NULL,

                name TEXT NOT NULL,

                price NUMERIC(12,2)
                    DEFAULT 0,

                is_required INTEGER
                    DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    product_id
                )
                REFERENCES products(id)
                ON DELETE CASCADE
            )
            """
        )


        # =====================================================
        # العملاء
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (

                id BIGSERIAL PRIMARY KEY,

                restaurant_id BIGINT NOT NULL,

                name TEXT NOT NULL,

                phone TEXT,

                address TEXT,

                notes TEXT,

                total_orders INTEGER
                    DEFAULT 0,

                total_spent NUMERIC(12,2)
                    DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE
            )
            """
        )


        # =====================================================
        # الطلبات
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (

                id BIGSERIAL PRIMARY KEY,

                restaurant_id BIGINT NOT NULL,

                customer_id BIGINT,

                customer_name TEXT NOT NULL,

                customer_phone TEXT,

                customer_address TEXT,

                notes TEXT,

                subtotal NUMERIC(12,2)
                    DEFAULT 0,

                delivery_fee NUMERIC(12,2)
                    DEFAULT 0,

                discount NUMERIC(12,2)
                    DEFAULT 0,

                total NUMERIC(12,2)
                    DEFAULT 0,

                status TEXT
                    DEFAULT 'pending',

                payment_method TEXT,

                payment_status TEXT
                    DEFAULT 'pending',

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    customer_id
                )
                REFERENCES customers(id)
                ON DELETE SET NULL
            )
            """
        )


        # =====================================================
        # تفاصيل الطلب
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (

                id BIGSERIAL PRIMARY KEY,

                order_id BIGINT NOT NULL,

                product_id BIGINT,

                product_name TEXT NOT NULL,

                quantity INTEGER
                    DEFAULT 1,

                price NUMERIC(12,2)
                    DEFAULT 0,

                total NUMERIC(12,2)
                    DEFAULT 0,

                options TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    order_id
                )
                REFERENCES orders(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    product_id
                )
                REFERENCES products(id)
                ON DELETE SET NULL
            )
            """
        )


        # =====================================================
        # QR Codes
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS qr_codes (

                id BIGSERIAL PRIMARY KEY,

                restaurant_id BIGINT NOT NULL,

                menu_id BIGINT,

                code TEXT NOT NULL UNIQUE,

                url TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    menu_id
                )
                REFERENCES menus(id)
                ON DELETE SET NULL
            )
            """
        )


        # =====================================================
        # مشاهدات المنيو
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS menu_views (

                id BIGSERIAL PRIMARY KEY,

                restaurant_id BIGINT NOT NULL,

                menu_id BIGINT,

                ip_address TEXT,

                user_agent TEXT,

                viewed_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    menu_id
                )
                REFERENCES menus(id)
                ON DELETE SET NULL
            )
            """
        )


        # =====================================================
        # الإشعارات
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (

                id BIGSERIAL PRIMARY KEY,

                user_id BIGINT NOT NULL,

                restaurant_id BIGINT,

                title TEXT NOT NULL,

                message TEXT,

                notification_type TEXT,

                is_read INTEGER
                    DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    user_id
                )
                REFERENCES users(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    restaurant_id
                )
                REFERENCES restaurants(id)
                ON DELETE CASCADE
            )
            """
        )


        # =====================================================
        # الفهارس
        # =====================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_role
            ON users(role)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_status
            ON users(account_status)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_active
            ON users(is_active)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_restaurants_approval
            ON restaurants(approval_status)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_restaurants_owner
            ON restaurants(owner_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_restaurants_active
            ON restaurants(is_active)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_menus_restaurant
            ON menus(restaurant_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_categories_restaurant
            ON categories(restaurant_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_categories_menu
            ON categories(menu_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_products_restaurant
            ON products(restaurant_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_products_category
            ON products(category_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_products_menu
            ON products(menu_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_customers_restaurant
            ON customers(restaurant_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_customers_phone
            ON customers(phone)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_orders_restaurant
            ON orders(restaurant_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_orders_customer
            ON orders(customer_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_orders_status
            ON orders(status)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_orders_payment_status
            ON orders(payment_status)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_orders_created
            ON orders(created_at)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_order_items_order
            ON order_items(order_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_order_items_product
            ON order_items(product_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_qr_restaurant
            ON qr_codes(restaurant_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_qr_menu
            ON qr_codes(menu_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_menu_views_restaurant
            ON menu_views(restaurant_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_menu_views_menu
            ON menu_views(menu_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_menu_views_date
            ON menu_views(viewed_at)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_notifications_user
            ON notifications(user_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_notifications_restaurant
            ON notifications(restaurant_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_notifications_read
            ON notifications(is_read)
            """
        )


        # =====================================================
        # Triggers
        # =====================================================

        create_updated_at_trigger(
            cursor,
            "restaurants"
        )

        create_updated_at_trigger(
            cursor,
            "restaurant_settings"
        )

        create_updated_at_trigger(
            cursor,
            "menus"
        )

        create_updated_at_trigger(
            cursor,
            "categories"
        )

        create_updated_at_trigger(
            cursor,
            "products"
        )

        create_updated_at_trigger(
            cursor,
            "customers"
        )

        create_updated_at_trigger(
            cursor,
            "orders"
        )


        # =====================================================
        # تنظيف القيم القديمة
        # =====================================================

        cursor.execute(
            """
            UPDATE users
            SET role = 'restaurant_owner'
            WHERE role IS NULL
               OR TRIM(role) = ''
            """
        )

        cursor.execute(
            """
            UPDATE users
            SET is_active = 1
            WHERE is_active IS NULL
            """
        )

        cursor.execute(
            """
            UPDATE users
            SET account_status = 'pending'
            WHERE account_status IS NULL
               OR TRIM(account_status) = ''
            """
        )

        cursor.execute(
            """
            UPDATE restaurants
            SET approval_status = 'pending'
            WHERE approval_status IS NULL
               OR TRIM(approval_status) = ''
            """
        )

        cursor.execute(
            """
            UPDATE restaurants
            SET is_active = 0
            WHERE is_active IS NULL
            """
        )


        # =====================================================
        # الحفظ
        # =====================================================

        db.commit()

    except Exception:

        db.rollback()

        raise

    finally:

        cursor.close()


# =========================================================
# ربط قاعدة البيانات بتطبيق Flask
# =========================================================

def register_db(app):

    app.teardown_appcontext(
        close_db
    )