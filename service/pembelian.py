from model.database import get_connection
from service.expert_system import detect_duplicate_purchase, supplier_is_eligible


def get_semua_pembelian():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.id AS pembelian_id, p.tanggal, p.total_harga, p.status,
                   p.tanggal_diterima, p.catatan,
                   s.nama_perusahaan AS supplier, c.nama AS cabang,
                   u.nama AS employee,
                   COUNT(dp.id) AS jumlah_detail
            FROM pembelian p
            JOIN supplier s ON p.supplier_id = s.id
            JOIN employee e ON p.employee_id = e.id
            JOIN users u ON e.user_id = u.id
            LEFT JOIN cabang c ON p.cabang_id = c.id
            LEFT JOIN detail_pembelian dp ON dp.pembelian_id = p.id
            GROUP BY p.id, s.nama_perusahaan, c.nama, u.nama
            ORDER BY p.id DESC
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_supplier_produk(supplier_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT sp.id, sp.supplier_id, sp.produk_id, sp.harga_beli,
                   sp.waktu_pengiriman_hari, sp.minimum_order,
                   sp.tingkat_keandalan, s.nama_perusahaan AS supplier,
                   p.nama AS produk, p.stok
            FROM supplier_produk sp
            JOIN supplier s ON s.id = sp.supplier_id
            JOIN produk p ON p.id = sp.produk_id
            WHERE sp.status = 'aktif' AND s.status = 'aktif'
        """
        params = ()
        if supplier_id is not None:
            query += " AND sp.supplier_id = %s"
            params = (supplier_id,)
        query += " ORDER BY s.nama_perusahaan, p.nama"
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def buat_pembelian_supplier(supplier_id, employee_id, items, catatan=None):
    """Create a supplier purchase destined for the central warehouse."""
    if not items:
        return None, "Minimal satu produk harus dipilih."

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id FROM supplier WHERE id = %s AND status = 'aktif'
        """, (supplier_id,))
        if not cursor.fetchone():
            raise ValueError("Supplier tidak ditemukan atau nonaktif.")

        cursor.execute("""
            SELECT id FROM employee
            WHERE id = %s AND status = 'aktif' AND jabatan = 'admin'
        """, (employee_id,))
        if not cursor.fetchone():
            raise ValueError("Employee admin tidak valid.")

        normalized = []
        total = 0
        for item in items:
            produk_id = int(item["produk_id"])
            jumlah = int(item["jumlah"])
            if jumlah <= 0:
                raise ValueError("Jumlah produk harus lebih dari 0.")
            cursor.execute("""
                SELECT produk_id, harga_beli, minimum_order
                FROM supplier_produk
                WHERE supplier_id = %s AND produk_id = %s AND status = 'aktif'
                FOR UPDATE
            """, (supplier_id, produk_id))
            supplier_product = cursor.fetchone()
            if not supplier_product:
                raise ValueError("Produk tidak tersedia dari supplier tersebut.")
            if not supplier_is_eligible(supplier_id, produk_id):
                raise ValueError(
                    f"Supplier tidak layak sementara untuk produk {produk_id}."
                )
            if jumlah < supplier_product["minimum_order"]:
                raise ValueError(
                    f"Jumlah produk {produk_id} di bawah minimum order."
                )
            subtotal = supplier_product["harga_beli"] * jumlah
            total += subtotal
            normalized.append((produk_id, jumlah, supplier_product["harga_beli"], subtotal))

        duplicates = detect_duplicate_purchase(supplier_id, normalized)
        if duplicates:
            duplicate = duplicates[0]
            raise ValueError(
                f"Pembelian ganda terdeteksi: {duplicate['produk']} masih memiliki "
                f"{duplicate['jumlah_dipesan']} unit dalam pesanan aktif."
            )

        cursor.execute("""
            INSERT INTO pembelian
                (supplier_id, employee_id, cabang_id, total_harga, status, catatan)
            VALUES (%s, %s, NULL, %s, 'dipesan', %s)
        """, (supplier_id, employee_id, total, catatan))
        pembelian_id = cursor.lastrowid

        for produk_id, jumlah, harga_beli, subtotal in normalized:
            cursor.execute("""
                INSERT INTO detail_pembelian
                    (pembelian_id, produk_id, jumlah, harga_beli, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (pembelian_id, produk_id, jumlah, harga_beli, subtotal))

        connection.commit()
        return pembelian_id, None
    except Exception as error:
        connection.rollback()
        return None, str(error)
    finally:
        cursor.close()
        connection.close()


def update_status_pembelian(pembelian_id, status_baru, user_id=None):
    if status_baru == "selesai":
        status_baru = "diterima"
    if status_baru not in ("diterima", "dibatalkan"):
        return False, "Status pembelian tidak valid."

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, status FROM pembelian WHERE id = %s FOR UPDATE
        """, (pembelian_id,))
        purchase = cursor.fetchone()
        if not purchase:
            return False, "Pembelian tidak ditemukan."
        if purchase["status"] not in ("dipesan", "diproses"):
            return False, "Pembelian sudah diproses sebelumnya."

        if status_baru == "diterima":
            cursor.execute("""
                SELECT produk_id, jumlah FROM detail_pembelian
                WHERE pembelian_id = %s
            """, (pembelian_id,))
            details = cursor.fetchall()
            for detail in details:
                cursor.execute("""
                    SELECT stok FROM produk WHERE id = %s FOR UPDATE
                """, (detail["produk_id"],))
                product = cursor.fetchone()
                before = product["stok"]
                after = before + detail["jumlah"]
                cursor.execute("""
                    UPDATE produk SET stok = %s WHERE id = %s
                """, (after, detail["produk_id"]))
                cursor.execute("""
                    INSERT INTO stok_mutasi
                        (produk_id, tipe, referensi_id, jumlah,
                         stok_sebelum, stok_sesudah, dibuat_oleh)
                    VALUES (%s, 'pembelian_supplier', %s, %s, %s, %s, %s)
                """, (detail["produk_id"], pembelian_id, detail["jumlah"],
                      before, after, user_id))

        cursor.execute("""
            UPDATE pembelian
            SET status = %s,
                tanggal_diterima = CASE WHEN %s = 'diterima' THEN NOW() ELSE tanggal_diterima END
            WHERE id = %s
        """, (status_baru, status_baru, pembelian_id))
        connection.commit()
        return True, "Status pembelian berhasil diperbarui."
    except Exception as error:
        connection.rollback()
        return False, str(error)
    finally:
        cursor.close()
        connection.close()
