from model.database import get_connection
from werkzeug.security import check_password_hash, generate_password_hash


def register_user(nama, username, password):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Cek apakah username sudah digunakan
        cursor.execute("""
            SELECT id
            FROM users
            WHERE username = %s
        """, (username,))

        if cursor.fetchone():
            return False, "Username sudah digunakan."

        # Semua user yang register dari aplikasi
        # otomatis menjadi pelanggan
        cursor.execute("""
            INSERT INTO users
                (nama, username, password, role)
            VALUES
                (%s, %s, %s, 'pelanggan')
        """, (nama, username, generate_password_hash(password)))

        user_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO pembeli (user_id)
            VALUES (%s)
        """, (user_id,))

        connection.commit()

        return True, "Registrasi berhasil."

    except Exception as e:
        connection.rollback()
        print("Error register:", e)

        return False, "Registrasi gagal."

    finally:
        cursor.close()
        connection.close()


def login_user(username, password):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                u.id,
                u.nama,
                u.username,
                u.role,
                u.password
            FROM users u
            LEFT JOIN employee e ON e.user_id = u.id
            WHERE u.username = %s
              AND (e.id IS NULL OR e.status = 'aktif')
            LIMIT 1
        """, (username,))

        user = cursor.fetchone()
        if not user:
            return None

        stored_password = user.pop("password", "")
        try:
            valid = check_password_hash(stored_password, password)
        except (ValueError, TypeError):
            valid = False

        # ``check_password_hash`` can return False (instead of raising) for
        # old plaintext accounts. Upgrade such an account after a successful
        # legacy-password login.
        if not valid and stored_password == password:
            valid = True
            cursor.execute("""
                UPDATE users
                SET password = %s
                WHERE id = %s
            """, (generate_password_hash(password), user["id"]))
            connection.commit()

        return user if valid else None

    finally:
        cursor.close()
        connection.close()
