from model.database import get_connection


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
        """, (nama, username, password))

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
                u.role
            FROM users u
            LEFT JOIN employee e ON e.user_id = u.id
            WHERE u.username = %s
              AND u.password = %s
              AND (e.id IS NULL OR e.status = 'aktif')
            LIMIT 1
        """, (username, password))

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()
