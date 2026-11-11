from model.database import get_connection

def get_semua_supplier():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, nama_perusahaan, nama_kontak, telepon, email,
                   alamat, status
            FROM supplier
            ORDER BY nama_perusahaan
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def update_supplier(supplier_id, nama_perusahaan, nama_kontak,
                    telepon, email, alamat, status):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE supplier
            SET nama_perusahaan = %s,
                nama_kontak = %s,
                telepon = %s,
                email = %s,
                alamat = %s,
                status = %s
            WHERE id = %s
        """, (
            nama_perusahaan, nama_kontak, telepon, email,
            alamat, status, supplier_id
        ))
        if cursor.rowcount == 0:
            cursor.execute("SELECT id FROM supplier WHERE id = %s", (supplier_id,))
            if not cursor.fetchone():
                return False
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print("Error update supplier:", e)
        return False
    finally:
        cursor.close()
        connection.close()


def tambah_supplier(nama_perusahaan, nama_kontak, telepon, email, alamat):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO supplier
                (nama_perusahaan, nama_kontak, telepon, email, alamat)
            VALUES (%s, %s, %s, %s, %s)
        """, (nama_perusahaan, nama_kontak, telepon, email, alamat))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print("Error tambah supplier:", e)
        return False
    finally:
        cursor.close()
        connection.close()
