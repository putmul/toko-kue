from model.database import get_connection

def get_semua_permintaan_stok(cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                ps.id AS permintaan_id,
                ps.cabang_id,
                ps.tanggal,
                ps.status,
                ps.catatan,
                c.nama AS cabang,
                u.nama AS employee,
                p.nama AS produk,
                d.jumlah
            FROM permintaan_stok ps
            JOIN cabang c ON ps.cabang_id = c.id
            JOIN employee e ON ps.employee_id = e.id
            JOIN users u ON e.user_id = u.id
            JOIN detail_permintaan_stok d ON ps.id = d.permintaan_id
            JOIN produk p ON d.produk_id = p.id
            {filter_cabang}
            ORDER BY ps.id DESC
        """.format(
            filter_cabang="WHERE ps.cabang_id = %s" if cabang_id is not None else ""
        )
        cursor.execute(query, (cabang_id,) if cabang_id is not None else ())
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def buat_permintaan_stok(employee_id, cabang_id, produk_id, jumlah, catatan):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if jumlah <= 0:
            raise ValueError("Jumlah harus lebih dari 0.")

        cursor.execute("""
            SELECT id
            FROM employee
            WHERE id = %s AND cabang_id = %s AND status = 'aktif'
        """, (employee_id, cabang_id))
        if not cursor.fetchone():
            raise ValueError("Employee tidak terdaftar pada cabang tersebut.")

        cursor.execute("""
            SELECT id
            FROM cabang
            WHERE id = %s AND status = 'aktif'
        """, (cabang_id,))
        if not cursor.fetchone():
            raise ValueError("Cabang tidak aktif.")

        cursor.execute("""
            SELECT id FROM produk WHERE id = %s
        """, (produk_id,))
        if not cursor.fetchone():
            raise ValueError("Produk tidak ditemukan.")

        cursor.execute("""
            INSERT INTO permintaan_stok (employee_id, cabang_id, catatan)
            VALUES (%s, %s, %s)
        """, (employee_id, cabang_id, catatan or None))
        permintaan_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO detail_permintaan_stok
                (permintaan_id, produk_id, jumlah)
            VALUES (%s, %s, %s)
        """, (permintaan_id, produk_id, jumlah))

        connection.commit()
        return permintaan_id
    except Exception as e:
        connection.rollback()
        print("Error buat permintaan stok:", e)
        return None
    finally:
        cursor.close()
        connection.close()


def update_status_permintaan_stok(permintaan_id, status_baru):
    if status_baru not in ("selesai", "dibatalkan"):
        return False, "Status request tidak valid."

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, cabang_id, status
            FROM permintaan_stok
            WHERE id = %s
            FOR UPDATE
        """, (permintaan_id,))
        request_data = cursor.fetchone()

        if not request_data:
            return False, "Request stok tidak ditemukan."
        if request_data["status"] != "diproses":
            return False, "Request stok sudah diproses sebelumnya."

        cursor.execute("""
            SELECT produk_id, jumlah
            FROM detail_permintaan_stok
            WHERE permintaan_id = %s
        """, (permintaan_id,))
        details = cursor.fetchall()

        if status_baru == "selesai":
            for detail in details:
                cursor.execute("""
                    SELECT stok
                    FROM produk
                    WHERE id = %s
                    FOR UPDATE
                """, (detail["produk_id"],))
                produk = cursor.fetchone()
                if not produk or produk["stok"] < detail["jumlah"]:
                    return False, "Stok gudang tidak mencukupi."

            for detail in details:
                cursor.execute("""
                    UPDATE produk
                    SET stok = stok - %s
                    WHERE id = %s
                """, (detail["jumlah"], detail["produk_id"]))
                cursor.execute("""
                    INSERT INTO stok_cabang (cabang_id, produk_id, stok)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE stok = stok + VALUES(stok)
                """, (
                    request_data["cabang_id"],
                    detail["produk_id"],
                    detail["jumlah"]
                ))

        cursor.execute("""
            UPDATE permintaan_stok
            SET status = %s
            WHERE id = %s
        """, (status_baru, permintaan_id))

        connection.commit()
        return True, "Status request berhasil diperbarui."
    except Exception as e:
        connection.rollback()
        print("Error update request stok:", e)
        return False, "Request stok gagal diproses."
    finally:
        cursor.close()
        connection.close()
