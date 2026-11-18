from model.database import get_connection
from service.inventory import record_mutation


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
            SELECT id, user_id FROM employee
            WHERE id = %s AND status = 'aktif' AND jabatan = 'admin'
        """, (employee_id,))
        employee = cursor.fetchone()
        if not employee:
            raise ValueError("Employee tidak aktif.")
        cursor.execute("""
            SELECT id FROM cabang WHERE id = %s AND status = 'aktif'
        """, (cabang_id,))
        if not cursor.fetchone():
            raise ValueError("Cabang tidak aktif.")

        request_data = None
        if permintaan_id is not None:
            cursor.execute("""
                SELECT id, cabang_id, status
                FROM permintaan_stok
                WHERE id = %s
                FOR UPDATE
            """, (permintaan_id,))
            request_data = cursor.fetchone()
            if not request_data:
                raise ValueError("Permintaan stok tidak ditemukan.")
            if request_data["cabang_id"] != cabang_id:
                raise ValueError("Cabang distribusi tidak sesuai dengan request.")
            if request_data["status"] != "diproses":
                raise ValueError("Request stok sudah tidak dapat didistribusikan.")

        cursor.execute("""
            INSERT INTO distribusi_stok
                (permintaan_id, employee_id, cabang_id, catatan)
            VALUES (%s, %s, %s, %s)
        """, (permintaan_id, employee_id, cabang_id, catatan))
        distribution_id = cursor.lastrowid
        requested = {}
        if request_data:
            cursor.execute("""
                SELECT produk_id, jumlah
                FROM detail_permintaan_stok
                WHERE permintaan_id = %s
            """, (permintaan_id,))
            requested = {
                row["produk_id"]: row["jumlah"]
                for row in cursor.fetchall()
            }

        normalized = {}
        for item in items:
            product_id = int(item["produk_id"])
            quantity = int(item["jumlah"])
            if quantity <= 0:
                continue
            normalized[product_id] = normalized.get(product_id, 0) + quantity

        if not normalized:
            raise ValueError("Minimal satu jumlah distribusi harus lebih dari 0.")

        for product_id, quantity in normalized.items():
            if requested and product_id not in requested:
                raise ValueError("Produk distribusi tidak ada dalam request.")
            if requested:
                cursor.execute("""
                    SELECT COALESCE(SUM(dds.jumlah), 0) AS sudah_dibuat
                    FROM distribusi_stok ds
                    JOIN detail_distribusi_stok dds
                        ON dds.distribusi_id = ds.id
                    WHERE ds.permintaan_id = %s
                      AND ds.status <> 'dibatalkan'
                      AND dds.produk_id = %s
                """, (permintaan_id, product_id))
                already_created = cursor.fetchone()["sudah_dibuat"]
                remaining = requested[product_id] - already_created
                if quantity > remaining:
                    raise ValueError(
                        f"Distribusi produk {product_id} melebihi sisa request "
                        f"({remaining} unit)."
                    )
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
        allowed_next = {
            "diproses": ("dikirim", "dibatalkan"),
            "dikirim": ("diterima",),
        }
        if status_baru not in allowed_next.get(distribution["status"], ()):
            return False, "Perubahan status distribusi tidak valid."

        cursor.execute("""
            SELECT produk_id, jumlah FROM detail_distribusi_stok
            WHERE distribusi_id = %s
        """, (distribusi_id,))
        details = cursor.fetchall()
        if status_baru == "dikirim":
            for detail in details:
                cursor.execute("""
                    SELECT stok
                    FROM produk
                    WHERE id = %s
                    FOR UPDATE
                """, (detail["produk_id"],))
                product = cursor.fetchone()
                if not product or product["stok"] < detail["jumlah"]:
                    return False, "Stok gudang tidak mencukupi untuk dikirim."

            for detail in details:
                cursor.execute("""
                    SELECT stok FROM produk WHERE id = %s FOR UPDATE
                """, (detail["produk_id"],))
                before = cursor.fetchone()["stok"]
                after = before - detail["jumlah"]
                cursor.execute(
                    "UPDATE produk SET stok = %s WHERE id = %s",
                    (after, detail["produk_id"])
                )
                record_mutation(
                    cursor, detail["produk_id"], distribution["cabang_id"],
                    "distribusi_keluar", distribusi_id, detail["jumlah"],
                    before, after, user_id
                )

        if status_baru == "diterima":
            for detail in details:
                cursor.execute("""
                    INSERT INTO stok_cabang (cabang_id, produk_id, stok)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE stok = stok + VALUES(stok)
                """, (distribution["cabang_id"], detail["produk_id"], detail["jumlah"]))
                cursor.execute("""
                    SELECT stok
                    FROM stok_cabang
                    WHERE cabang_id = %s AND produk_id = %s
                """, (distribution["cabang_id"], detail["produk_id"]))
                branch_after = cursor.fetchone()["stok"]
                record_mutation(
                    cursor, detail["produk_id"], distribution["cabang_id"],
                    "distribusi_masuk", distribusi_id, detail["jumlah"],
                    branch_after - detail["jumlah"], branch_after, user_id
                )

        cursor.execute("UPDATE distribusi_stok SET status = %s WHERE id = %s", (status_baru, distribusi_id))
        if distribution["permintaan_id"] and status_baru == "diterima":
            cursor.execute("""
                SELECT dps.produk_id, dps.jumlah AS diminta,
                       COALESCE((
                           SELECT SUM(dds.jumlah)
                           FROM distribusi_stok ds2
                           JOIN detail_distribusi_stok dds
                               ON dds.distribusi_id = ds2.id
                           WHERE ds2.permintaan_id = %s
                             AND ds2.status = 'diterima'
                             AND dds.produk_id = dps.produk_id
                       ), 0) AS diterima
                FROM detail_permintaan_stok dps
                WHERE dps.permintaan_id = %s
            """, (distribution["permintaan_id"], distribution["permintaan_id"]))
            request_lines = cursor.fetchall()
            if request_lines and all(
                line["diterima"] >= line["diminta"]
                for line in request_lines
            ):
                cursor.execute(
                    "UPDATE permintaan_stok SET status = 'selesai' WHERE id = %s",
                    (distribution["permintaan_id"],)
                )
        connection.commit()
        return True, "Status distribusi berhasil diperbarui."
    except Exception as error:
        connection.rollback()
        return False, str(error)
    finally:
        cursor.close()
        connection.close()
