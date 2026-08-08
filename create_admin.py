from werkzeug.security import generate_password_hash

from database import (
    init_db,
    get_db,
)

from config import DATABASE_PATH


ADMIN_EMAIL = "admin@menusmart.com"
ADMIN_PASSWORD = "Admin@123456"


init_db()


import sqlite3

db = sqlite3.connect(DATABASE_PATH)
db.row_factory = sqlite3.Row

existing_admin = db.execute(
    """
    SELECT id
    FROM users
    WHERE email = ?
    """,
    (ADMIN_EMAIL,)
).fetchone()


if existing_admin:

    db.execute(
        """
        UPDATE users
        SET
            role = 'admin',
            is_active = 1,
            account_status = 'active'
        WHERE email = ?
        """,
        (ADMIN_EMAIL,)
    )

    db.commit()

    print("Admin account already exists.")
    print("Admin permissions have been updated.")

else:

    password_hash = generate_password_hash(
        ADMIN_PASSWORD
    )

    db.execute(
        """
        INSERT INTO users (
            name,
            email,
            password,
            role,
            is_active,
            account_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "Menu Smart Admin",
            ADMIN_EMAIL,
            password_hash,
            "admin",
            1,
            "active"
        )
    )

    db.commit()

    print("Admin account created successfully.")


db.close()

print()
print("Email:", ADMIN_EMAIL)
print("Password:", ADMIN_PASSWORD)
print("Database:", DATABASE_PATH)