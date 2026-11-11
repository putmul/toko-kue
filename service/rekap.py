from model.database import get_connection

def get_transaksi_untuk_rekap(cabang_id, hanya_belum=False, hanya_sudah=False):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                t.id AS transaksi_id,
                t.tanggal,
                t.total_harga,
                t.status,
                u.nama AS pelanggan,
                c.nama AS cabang,
                COALESCE(r.status_rekap, 'belum') AS status_rekap,
                r.catatan
            FROM transaksi t
            JOIN users u ON t.user_id = u.id
            JOIN cabang c ON t.cabang_id = c.id
            LEFT JOIN rekap_transaksi r ON r.transaksi_id = t.id
            WHERE t.cabang_id = %s
            {filter_rekap}
            ORDER BY t.tanggal DESC, t.id DESC
        """.format(
            filter_rekap=(
                "AND r.id IS NULL" if hanya_belum
                else "AND r.id IS NOT NULL" if hanya_sudah
                else ""
            )
        )
        cursor.execute(query, (cabang_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def simpan_rekap_transaksi(employee_id, cabang_id, entries):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id
            FROM employee
            WHERE id = %s AND cabang_id = %s AND status = 'aktif'
        """, (employee_id, cabang_id))
        if not cursor.fetchone():
            return False, "Employee tidak memiliki akses ke cabang ini."

        for transaksi_id, status_rekap, catatan in entries:
            if status_rekap not in ("berhasil", "dibatalkan"):
                return False, "Status rekap tidak valid."

            cursor.execute("""
                SELECT id
                FROM transaksi
                WHERE id = %s AND cabang_id = %s
                FOR UPDATE
            """, (transaksi_id, cabang_id))
            if not cursor.fetchone():
                return False, "Transaksi bukan milik cabang manager."

            cursor.execute("""
                INSERT INTO rekap_transaksi
                    (transaksi_id, employee_id, cabang_id, status_rekap, catatan)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    employee_id = VALUES(employee_id),
                    cabang_id = VALUES(cabang_id),
                    status_rekap = VALUES(status_rekap),
                    catatan = VALUES(catatan)
            """, (
                transaksi_id, employee_id, cabang_id, status_rekap, catatan
            ))

        connection.commit()
        return True, "Rekap transaksi berhasil disimpan."
    except Exception as e:
        connection.rollback()
        print("Error simpan rekap:", e)
        return False, "Rekap transaksi gagal disimpan."
    finally:
        cursor.close()
        connection.close()


def get_semua_rekap():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                r.id AS rekap_id,
                r.transaksi_id,
                r.tanggal_rekap,
                r.status_rekap,
                r.catatan,
                t.tanggal AS tanggal_transaksi,
                t.total_harga,
                pelanggan.nama AS pelanggan,
                c.nama AS cabang,
                manager.nama AS direkap_oleh
            FROM rekap_transaksi r
            JOIN transaksi t ON r.transaksi_id = t.id
            JOIN users pelanggan ON t.user_id = pelanggan.id
            JOIN cabang c ON r.cabang_id = c.id
            JOIN employee e ON r.employee_id = e.id
            JOIN users manager ON e.user_id = manager.id
            ORDER BY r.tanggal_rekap DESC, r.id DESC
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_detail_rekap(rekap_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                r.id AS rekap_id,
                r.transaksi_id,
                r.tanggal_rekap,
                r.status_rekap,
                r.catatan,
                t.tanggal AS tanggal_transaksi,
                t.total_harga,
                pelanggan.nama AS pelanggan,
                c.nama AS cabang,
                manager.nama AS direkap_oleh
            FROM rekap_transaksi r
            JOIN transaksi t ON r.transaksi_id = t.id
            JOIN users pelanggan ON t.user_id = pelanggan.id
            JOIN cabang c ON r.cabang_id = c.id
            JOIN employee e ON r.employee_id = e.id
            JOIN users manager ON e.user_id = manager.id
            WHERE r.id = %s
        """, (rekap_id,))
        rekap = cursor.fetchone()
        if not rekap:
            return None

        cursor.execute("""
            SELECT p.nama, dt.jumlah, dt.harga_satuan, dt.subtotal
            FROM detail_transaksi dt
            JOIN produk p ON dt.produk_id = p.id
            WHERE dt.transaksi_id = %s
            ORDER BY dt.id
        """, (rekap["transaksi_id"],))
        rekap["items"] = cursor.fetchall()
        return rekap
    finally:
        cursor.close()
        connection.close()


def laporan_pendapatan_harian(cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                DATE(t.tanggal) AS tanggal,
                c.id AS cabang_id,
                c.nama AS cabang,
                COALESCE(SUM(
                    CASE WHEN r.status_rekap = 'berhasil'
                         THEN t.total_harga ELSE 0 END
                ), 0) AS pendapatan,
                COUNT(CASE WHEN r.status_rekap = 'berhasil' THEN 1 END) AS jumlah_transaksi
            FROM transaksi t
            JOIN cabang c ON t.cabang_id = c.id
            JOIN rekap_transaksi r ON r.transaksi_id = t.id
                AND r.status_rekap = 'berhasil'
            {filter_cabang}
            GROUP BY DATE(t.tanggal), c.id, c.nama
            ORDER BY DATE(t.tanggal) DESC, c.nama
        """.format(
            filter_cabang="WHERE t.cabang_id = %s" if cabang_id is not None else ""
        )
        cursor.execute(query, (cabang_id,) if cabang_id is not None else ())
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def detail_pendapatan_harian(cabang_id, tanggal):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                t.id AS transaksi_id,
                t.tanggal,
                t.total_harga,
                t.metode_pembayaran,
                u.nama AS pelanggan,
                c.nama AS cabang,
                r.status_rekap,
                r.catatan
            FROM transaksi t
            JOIN rekap_transaksi r
                ON r.transaksi_id = t.id
               AND r.status_rekap = 'berhasil'
            JOIN users u ON t.user_id = u.id
            JOIN cabang c ON t.cabang_id = c.id
            WHERE t.cabang_id = %s
              AND DATE(t.tanggal) = %s
            ORDER BY t.id DESC
        """, (cabang_id, tanggal))
        transaksi = cursor.fetchall()

        for item in transaksi:
            cursor.execute("""
                SELECT p.nama, dt.jumlah, dt.harga_satuan, dt.subtotal
                FROM detail_transaksi dt
                JOIN produk p ON dt.produk_id = p.id
                WHERE dt.transaksi_id = %s
                ORDER BY dt.id
            """, (item["transaksi_id"],))
            item["items"] = cursor.fetchall()

        return transaksi
    finally:
        cursor.close()
        connection.close()
