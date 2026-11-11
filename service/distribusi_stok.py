from model.database import get_connection


def get_semua_distribusi(cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT ds.id AS distribusi_id, ds.permintaan_id, ds.tanggal,
                   ds.status, ds.catatan, c.nama AS cabang,
                   u.nama AS employee,
                   GROUP_CONCAT(CONCAT(p.nama, ' (', dds.jumlah, ')')
                                ORDER BY p.nama SEPARATOR ', ') AS detail
            FROM distribusi_stok ds
            JOIN cabang c ON c.id = ds.cabang_id
            JOIN employee e ON e.id = ds.employee_id
            JOIN users u ON u.id = e.user_id
            JOIN detail_distribusi_stok dds ON dds.distribusi_id = ds.id
            JOIN produk p ON p.id = dds.produk_id
        """
        params = []
        if cabang_id is not None:
            query += " WHERE ds.cabang_id = %s"
            params.append(cabang_id)
        query += " GROUP BY ds.id, c.nama, u.nama ORDER BY ds.id DESC"
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_distribusi_detail(distribusi_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT ds.*, c.nama AS cabang,
                   dds.produk_id, dds.jumlah, p.nama AS produk,
                   p.stok AS stok_gudang
            FROM distribusi_stok ds
            JOIN cabang c ON c.id = ds.cabang_id
            JOIN detail_distribusi_stok dds ON dds.distribusi_id = ds.id
            JOIN produk p ON p.id = dds.produk_id
            WHERE ds.id = %s
        """, (distribusi_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def buat_distribusi_stok(employee_id, cabang_id, items, permintaan_id=None, catatan=None):
    if not items:
        return None, "Minimal satu produk harus dipilih."
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id FROM employee WHERE id = %s AND status = 'aktif'
        """, (employee_id,))
        if not cursor.fetchone():
            raise ValueError("Employee tidak aktif.")
        cursor.execute("""
            SELECT id FROM cabang WHERE id = %s AND status = 'aktif'
        """, (cabang_id,))
        if not cursor.fetchone():
            raise ValueError("Cabang tidak aktif.")

        cursor.execute("""
            INSERT INTO distribusi_stok
                (permintaan_id, employee_id, cabang_id, catatan)
            VALUES (%s, %s, %s, %s)
        """, (permintaan_id, employee_id, cabang_id, catatan))
        distribution_id = cursor.lastrowid
        for item in items:
            product_id = int(item["produk_id"])
            quantity = int(item["jumlah"])
            if quantity <= 0:
                raise ValueError("Jumlah distribusi harus lebih dari 0.")
            cursor.execute("""
                INSERT INTO detail_distribusi_stok
                    (distribusi_id, produk_id, jumlah)
                VALUES (%s, %s, %s)
            """, (distribution_id, product_id, quantity))
        connection.commit()
        return distribution_id, None
    except Exception as error:
        connection.rollback()
        return None, str(error)
    finally:
        cursor.close()
        connection.close()


def update_status_distribusi(distribusi_id, status_baru, user_id=None):
    if status_baru not in ("dikirim", "diterima", "dibatalkan"):
        return False, "Status distribusi tidak valid."
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, cabang_id, status, permintaan_id
            FROM distribusi_stok WHERE id = %s FOR UPDATE
        """, (distribusi_id,))
        distribution = cursor.fetchone()
        if not distribution:
            return False, "Distribusi tidak ditemukan."
        if distribution["status"] != "diproses":
            return False, "Distribusi sudah diproses sebelumnya."

        cursor.execute("""
            SELECT produk_id, jumlah FROM detail_distribusi_stok
            WHERE distribusi_id = %s
        """, (distribusi_id,))
        details = cursor.fetchall()
        if status_baru in ("dikirim", "diterima"):
            for detail in details:
                cursor.execute("""
                    SELECT stok FROM produk WHERE id = %s FOR UPDATE
                """, (detail["produk_id"],))
                product = cursor.fetchone()
                if product["stok"] < detail["jumlah"]:
                    return False, "Stok gudang tidak mencukupi."

            for detail in details:
                cursor.execute("SELECT stok FROM produk WHERE id = %s", (detail["produk_id"],))
                before = cursor.fetchone()["stok"]
                after = before - detail["jumlah"]
                cursor.execute("UPDATE produk SET stok = %s WHERE id = %s", (after, detail["produk_id"]))
                cursor.execute("""
                    INSERT INTO stok_cabang (cabang_id, produk_id, stok)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE stok = stok + VALUES(stok)
                """, (distribution["cabang_id"], detail["produk_id"], detail["jumlah"]))
                cursor.execute("""
                    INSERT INTO stok_mutasi
                        (produk_id, cabang_id, tipe, referensi_id, jumlah,
                         stok_sebelum, stok_sesudah, dibuat_oleh)
                    VALUES (%s, %s, 'distribusi_keluar', %s, %s, %s, %s, %s)
                """, (detail["produk_id"], distribution["cabang_id"], distribusi_id,
                      detail["jumlah"], before, after, user_id))

        cursor.execute("UPDATE distribusi_stok SET status = %s WHERE id = %s", (status_baru, distribusi_id))
        if distribution["permintaan_id"] and status_baru in ("dikirim", "diterima"):
            cursor.execute("UPDATE permintaan_stok SET status = 'selesai' WHERE id = %s", (distribution["permintaan_id"],))
        connection.commit()
        return True, "Status distribusi berhasil diperbarui."
    except Exception as error:
        connection.rollback()
        return False, str(error)
    finally:
        cursor.close()
        connection.close()
