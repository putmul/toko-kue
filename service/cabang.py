from model.database import get_connection

def tambah_cabang(nama, alamat, telepon):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO cabang (nama, alamat, telepon)
            VALUES (%s, %s, %s)
        """, (nama, alamat, telepon))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print("Error tambah cabang:", e)
        return False
    finally:
        cursor.close()
        connection.close()


def get_semua_cabang(aktif_saja=False):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, nama, alamat, telepon, status
            FROM cabang
        """
        if aktif_saja:
            query += " WHERE status = 'aktif'"
        query += " ORDER BY nama"
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def update_cabang(cabang_id, nama, alamat, telepon, status):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE cabang
            SET nama = %s, alamat = %s, telepon = %s, status = %s
            WHERE id = %s
        """, (nama, alamat, telepon, status, cabang_id))
        if cursor.rowcount == 0:
            cursor.execute("SELECT id FROM cabang WHERE id = %s", (cabang_id,))
            if not cursor.fetchone():
                return False
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print("Error update cabang:", e)
        return False
    finally:
        cursor.close()
        connection.close()
