from model.database import get_connection

def lihat_riwayat_transaksi(user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                t.id AS transaksi_id,
                t.tanggal,
                t.status,
                t.metode_pembayaran,
                c.nama AS cabang,
                CASE
                    WHEN t.total_harga > 0 THEN t.total_harga
                    ELSE COALESCE(SUM(dt.subtotal), 0)
                END AS total
            FROM transaksi t
            LEFT JOIN detail_transaksi dt
                ON t.id = dt.transaksi_id
            LEFT JOIN cabang c
                ON t.cabang_id = c.id
            WHERE t.user_id = %s
            GROUP BY
                t.id,
                t.tanggal,
                t.status,
                t.metode_pembayaran,
                c.nama,
                t.total_harga
            ORDER BY t.id DESC
        """, (user_id,))

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def lihat_detail_transaksi(transaksi_id, user_id=None, cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Jika user_id diberikan,
        # pastikan transaksi memang milik user tersebut
        cabang_filter = ""
        query_params = [transaksi_id]
        if cabang_id is not None:
            cabang_filter = " AND t.cabang_id = %s"
            query_params.append(cabang_id)

        if user_id is not None:

            cursor.execute("""
                    SELECT
                        t.id AS transaksi_id,
                        t.tanggal,
                        t.status,
                        t.metode_pembayaran,

                        pelanggan.nama AS pelanggan,

                        kasir.nama AS kasir,
                        c.nama AS cabang,
                        t.total_harga

                    FROM transaksi t

                    JOIN users pelanggan
                        ON t.user_id = pelanggan.id

                    LEFT JOIN employee e
                        ON t.kasir_id = e.id

                    LEFT JOIN users kasir
                        ON e.user_id = kasir.id

                    LEFT JOIN cabang c
                        ON t.cabang_id = c.id

                    WHERE t.id = %s
                    AND t.user_id = %s
                """ + cabang_filter, [transaksi_id, user_id] + ([cabang_id] if cabang_id is not None else []))
        else:

            cursor.execute("""
                SELECT
                    t.id AS transaksi_id,
                    t.tanggal,
                    t.status,
                    t.metode_pembayaran,
                    t.total_harga,
                    u.nama AS pelanggan,
                    kasir.nama AS kasir,
                    c.nama AS cabang
                FROM transaksi t
                JOIN users u
                    ON t.user_id = u.id
                LEFT JOIN employee e
                    ON t.kasir_id = e.id
                LEFT JOIN users kasir
                    ON e.user_id = kasir.id
                LEFT JOIN cabang c
                    ON t.cabang_id = c.id
                WHERE t.id = %s
            """ + cabang_filter, query_params)

        transaksi = cursor.fetchone()

        if not transaksi:
            return None

        cursor.execute("""
            SELECT
                p.id AS produk_id,
                p.nama,
                CASE
                    WHEN dt.harga_satuan > 0 THEN dt.harga_satuan
                    ELSE p.harga
                END AS harga,
                dt.jumlah,
                dt.subtotal
            FROM detail_transaksi dt
            JOIN produk p
                ON dt.produk_id = p.id
            WHERE dt.transaksi_id = %s
            ORDER BY dt.id
        """, (transaksi_id,))

        transaksi["items"] = cursor.fetchall()

        return transaksi

    finally:
        cursor.close()
        connection.close()


def lihat_semua_transaksi(cabang_id=None):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT
                t.id AS transaksi_id,

                pelanggan.nama AS pelanggan,

                kasir.nama AS kasir,

                t.tanggal,
                t.status,
                t.metode_pembayaran,
                c.nama AS cabang,

                CASE
                    WHEN t.total_harga > 0 THEN t.total_harga
                    ELSE COALESCE(SUM(dt.subtotal), 0)
                END AS total

            FROM transaksi t

            JOIN users pelanggan
                ON t.user_id = pelanggan.id

            LEFT JOIN employee e
                ON t.kasir_id = e.id

            LEFT JOIN users kasir
                ON e.user_id = kasir.id

            LEFT JOIN detail_transaksi dt
                ON t.id = dt.transaksi_id
            LEFT JOIN cabang c
                ON t.cabang_id = c.id

            {cabang_filter}

            GROUP BY
                t.id,
                pelanggan.nama,
                kasir.nama,
                t.tanggal,
                t.status,
                t.metode_pembayaran,
                c.nama,
                t.total_harga

            ORDER BY t.id DESC
        """.format(
            cabang_filter="WHERE t.cabang_id = %s" if cabang_id is not None else ""
        )

        cursor.execute(query, (cabang_id,) if cabang_id is not None else ())

        return cursor.fetchall()

    finally:

        cursor.close()
        connection.close()
