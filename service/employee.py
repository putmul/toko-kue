from model.database import get_connection

def get_employee_for_user(user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT e.id, e.user_id, e.cabang_id, e.jabatan, e.status,
                   c.nama AS cabang
            FROM employee e
            LEFT JOIN cabang c ON e.cabang_id = c.id
            WHERE e.user_id = %s
              AND e.status = 'aktif'
        """, (user_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def get_semua_employee():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                e.id,
                u.nama,
                u.username,
                e.jabatan,
                c.nama AS cabang,
                e.no_telepon,
                e.status
            FROM employee e
            JOIN users u ON e.user_id = u.id
            LEFT JOIN cabang c ON e.cabang_id = c.id
            ORDER BY u.nama
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def tambah_employee(nama, username, password, jabatan, cabang_id,
                    no_telepon, alamat):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT id FROM users WHERE username = %s
        """, (username,))
        if cursor.fetchone():
            raise ValueError("Username sudah digunakan.")

        cursor.execute("""
            INSERT INTO users (nama, username, password, role)
            VALUES (%s, %s, %s, %s)
        """, (nama, username, password, jabatan))
        user_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO employee
                (user_id, jabatan, cabang_id, no_telepon, alamat)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, jabatan, cabang_id, no_telepon, alamat))

        connection.commit()
        return True, "Employee berhasil ditambahkan."
    except Exception as e:
        connection.rollback()
        print("Error tambah employee:", e)
        return False, str(e)
    finally:
        cursor.close()
        connection.close()


def get_employee(employee_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT e.id, e.user_id, e.jabatan, e.cabang_id,
                   e.no_telepon, e.alamat, e.status,
                   u.nama, u.username
            FROM employee e
            JOIN users u ON e.user_id = u.id
            WHERE e.id = %s
        """, (employee_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def update_employee(employee_id, nama, username, password, jabatan,
                    cabang_id, no_telepon, alamat, status):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT user_id FROM employee WHERE id = %s", (employee_id,))
        employee = cursor.fetchone()
        if not employee:
            return False, "Employee tidak ditemukan."

        user_id = employee[0]
        cursor.execute("""
            SELECT id FROM users
            WHERE username = %s AND id <> %s
        """, (username, user_id))
        if cursor.fetchone():
            return False, "Username sudah digunakan."

        if password:
            cursor.execute("""
                UPDATE users
                SET nama = %s, username = %s, password = %s, role = %s
                WHERE id = %s
            """, (nama, username, password, jabatan, user_id))
        else:
            cursor.execute("""
                UPDATE users
                SET nama = %s, username = %s, role = %s
                WHERE id = %s
            """, (nama, username, jabatan, user_id))

        cursor.execute("""
            UPDATE employee
            SET jabatan = %s, cabang_id = %s, no_telepon = %s,
                alamat = %s, status = %s
            WHERE id = %s
        """, (jabatan, cabang_id, no_telepon, alamat, status, employee_id))

        connection.commit()
        return True, "Employee berhasil diperbarui."
    except Exception as e:
        connection.rollback()
        print("Error update employee:", e)
        return False, str(e)
    finally:
        cursor.close()
        connection.close()
