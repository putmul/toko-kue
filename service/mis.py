from datetime import date, datetime, timedelta

from model.database import get_connection


def _as_int(value):
    return int(value or 0)


def _as_float(value):
    return float(value or 0)


def _date_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def refresh_mis_data():
    """Refresh the MIS read model from TPS/OAS data.

    MIS tables are deliberately populated from the operational tables. This
    function never changes transactions, stock, requests, or master data.
    """
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO mis_penjualan_harian (
                tanggal, cabang_id, jumlah_transaksi, transaksi_berhasil,
                transaksi_diproses, transaksi_dikirim, transaksi_selesai,
                transaksi_dibatalkan, pendapatan_berhasil,
                rata_rata_transaksi
            )
            SELECT
                DATE(t.tanggal),
                t.cabang_id,
                COUNT(*),
                SUM(CASE WHEN r.status_rekap = 'berhasil' THEN 1 ELSE 0 END),
                SUM(CASE WHEN t.status = 'diproses' THEN 1 ELSE 0 END),
                SUM(CASE WHEN t.status = 'dikirim' THEN 1 ELSE 0 END),
                SUM(CASE WHEN t.status = 'selesai' THEN 1 ELSE 0 END),
                SUM(CASE WHEN t.status = 'dibatalkan' THEN 1 ELSE 0 END),
                COALESCE(SUM(
                    CASE WHEN r.status_rekap = 'berhasil'
                         THEN t.total_harga ELSE 0 END
                ), 0),
                COALESCE(AVG(
                    CASE WHEN r.status_rekap = 'berhasil'
                         THEN t.total_harga ELSE NULL END
                ), 0)
            FROM transaksi t
            LEFT JOIN rekap_transaksi r ON r.transaksi_id = t.id
            WHERE t.cabang_id IS NOT NULL
            GROUP BY DATE(t.tanggal), t.cabang_id
            ON DUPLICATE KEY UPDATE
                jumlah_transaksi = VALUES(jumlah_transaksi),
                transaksi_berhasil = VALUES(transaksi_berhasil),
                transaksi_diproses = VALUES(transaksi_diproses),
                transaksi_dikirim = VALUES(transaksi_dikirim),
                transaksi_selesai = VALUES(transaksi_selesai),
                transaksi_dibatalkan = VALUES(transaksi_dibatalkan),
                pendapatan_berhasil = VALUES(pendapatan_berhasil),
                rata_rata_transaksi = VALUES(rata_rata_transaksi)
        """)

        cursor.execute("""
            INSERT INTO mis_penjualan_produk_harian (
                tanggal, cabang_id, produk_id, jumlah_terjual, pendapatan
            )
            SELECT
                DATE(t.tanggal),
                t.cabang_id,
                dt.produk_id,
                SUM(dt.jumlah),
                SUM(dt.subtotal)
            FROM transaksi t
            JOIN rekap_transaksi r
                ON r.transaksi_id = t.id
               AND r.status_rekap = 'berhasil'
            JOIN detail_transaksi dt ON dt.transaksi_id = t.id
            WHERE t.cabang_id IS NOT NULL
            GROUP BY DATE(t.tanggal), t.cabang_id, dt.produk_id
            ON DUPLICATE KEY UPDATE
                jumlah_terjual = VALUES(jumlah_terjual),
                pendapatan = VALUES(pendapatan)
        """)

        cursor.execute("""
            INSERT INTO mis_stok_snapshot (
                tanggal_snapshot, cabang_id, produk_id, stok_gudang,
                stok_cabang, stok_minimum, status_stok
            )
            SELECT
                CURRENT_DATE(),
                c.id,
                p.id,
                p.stok,
                COALESCE(sc.stok, 0),
                p.stok_minimum,
                CASE
                    WHEN COALESCE(sc.stok, 0) <= 0 THEN 'habis'
                    WHEN COALESCE(sc.stok, 0) <= p.stok_minimum THEN 'menipis'
                    ELSE 'normal'
                END
            FROM cabang c
            CROSS JOIN produk p
            LEFT JOIN stok_cabang sc
                ON sc.cabang_id = c.id
               AND sc.produk_id = p.id
            WHERE c.status = 'aktif'
            ON DUPLICATE KEY UPDATE
                stok_gudang = VALUES(stok_gudang),
                stok_cabang = VALUES(stok_cabang),
                stok_minimum = VALUES(stok_minimum),
                status_stok = VALUES(status_stok)
        """)

        cursor.execute("""
            INSERT INTO mis_permintaan_stok_harian (
                tanggal, cabang_id, jumlah_request, request_diproses,
                request_selesai, request_dibatalkan, total_item_diminta,
                total_item_selesai
            )
            SELECT
                DATE(ps.tanggal),
                ps.cabang_id,
                COUNT(DISTINCT ps.id),
                COUNT(DISTINCT CASE WHEN ps.status = 'diproses' THEN ps.id END),
                COUNT(DISTINCT CASE WHEN ps.status = 'selesai' THEN ps.id END),
                COUNT(DISTINCT CASE WHEN ps.status = 'dibatalkan' THEN ps.id END),
                COALESCE(SUM(dps.jumlah), 0),
                COALESCE(SUM(
                    CASE WHEN ps.status = 'selesai' THEN dps.jumlah ELSE 0 END
                ), 0)
            FROM permintaan_stok ps
            JOIN detail_permintaan_stok dps ON dps.permintaan_id = ps.id
            GROUP BY DATE(ps.tanggal), ps.cabang_id
            ON DUPLICATE KEY UPDATE
                jumlah_request = VALUES(jumlah_request),
                request_diproses = VALUES(request_diproses),
                request_selesai = VALUES(request_selesai),
                request_dibatalkan = VALUES(request_dibatalkan),
                total_item_diminta = VALUES(total_item_diminta),
                total_item_selesai = VALUES(total_item_selesai)
        """)

        # Create alerts for low stock, pending requests, and old pending orders.
        cursor.execute("""
            INSERT INTO mis_monitoring_alert (
                fingerprint, tipe_sumber, sumber_id, cabang_id, produk_id,
                tingkat, judul, pesan, status
            )
            SELECT
                CONCAT('stok:', sc.cabang_id, ':', sc.produk_id),
                'stok', NULL, sc.cabang_id, sc.produk_id,
                CASE WHEN sc.stok <= 0 THEN 'critical' ELSE 'warning' END,
                CASE WHEN sc.stok <= 0
                     THEN 'Stok produk habis'
                     ELSE 'Stok produk menipis' END,
                CONCAT(
                    'Stok ', p.nama, ' di ', c.nama, ' saat ini ', sc.stok,
                    ' unit. Batas minimum: ', p.stok_minimum, ' unit.'
                ),
                'terbuka'
            FROM stok_cabang sc
            JOIN produk p ON p.id = sc.produk_id
            JOIN cabang c ON c.id = sc.cabang_id
            WHERE c.status = 'aktif' AND sc.stok <= p.stok_minimum
            ON DUPLICATE KEY UPDATE
                tingkat = VALUES(tingkat),
                judul = VALUES(judul),
                pesan = VALUES(pesan),
                status = 'terbuka',
                ditangani_pada = NULL
        """)

        cursor.execute("""
            INSERT INTO mis_monitoring_alert (
                fingerprint, tipe_sumber, sumber_id, cabang_id,
                tingkat, judul, pesan, status
            )
            SELECT
                CONCAT('permintaan_stok:', ps.id),
                'permintaan_stok', ps.id, ps.cabang_id,
                'warning',
                'Permintaan stok menunggu proses',
                CONCAT(
                    'Permintaan stok #', ps.id, ' masih berstatus diproses.'
                ),
                'terbuka'
            FROM permintaan_stok ps
            WHERE ps.status = 'diproses'
            ON DUPLICATE KEY UPDATE
                cabang_id = VALUES(cabang_id),
                tingkat = VALUES(tingkat),
                judul = VALUES(judul),
                pesan = VALUES(pesan),
                status = 'terbuka',
                ditangani_pada = NULL
        """)

        cursor.execute("""
            INSERT INTO mis_monitoring_alert (
                fingerprint, tipe_sumber, sumber_id, cabang_id,
                tingkat, judul, pesan, status
            )
            SELECT
                CONCAT('transaksi:', t.id),
                'transaksi', t.id, t.cabang_id,
                'warning',
                'Transaksi belum selesai',
                CONCAT(
                    'Transaksi #', t.id,
                    ' masih berstatus ', t.status,
                    ' lebih dari 24 jam.'
                ),
                'terbuka'
            FROM transaksi t
            WHERE t.status IN ('diproses', 'dikirim')
              AND t.tanggal < (NOW() - INTERVAL 1 DAY)
            ON DUPLICATE KEY UPDATE
                cabang_id = VALUES(cabang_id),
                tingkat = VALUES(tingkat),
                judul = VALUES(judul),
                pesan = VALUES(pesan),
                status = 'terbuka',
                ditangani_pada = NULL
        """)

        # Close alerts whose underlying condition no longer exists.
        cursor.execute("""
            UPDATE mis_monitoring_alert a
            LEFT JOIN stok_cabang sc
                ON a.tipe_sumber = 'stok'
               AND a.cabang_id = sc.cabang_id
               AND a.produk_id = sc.produk_id
            LEFT JOIN produk p ON p.id = a.produk_id
            SET a.status = 'ditangani', a.ditangani_pada = COALESCE(
                a.ditangani_pada, NOW()
            )
            WHERE a.tipe_sumber = 'stok'
              AND a.status = 'terbuka'
              AND (sc.produk_id IS NULL OR sc.stok > p.stok_minimum)
        """)

        cursor.execute("""
            UPDATE mis_monitoring_alert a
            LEFT JOIN permintaan_stok ps ON ps.id = a.sumber_id
            SET a.status = 'ditangani', a.ditangani_pada = COALESCE(
                a.ditangani_pada, NOW()
            )
            WHERE a.tipe_sumber = 'permintaan_stok'
              AND a.status = 'terbuka'
              AND (ps.id IS NULL OR ps.status <> 'diproses')
        """)

        cursor.execute("""
            UPDATE mis_monitoring_alert a
            LEFT JOIN transaksi t ON t.id = a.sumber_id
            SET a.status = 'ditangani', a.ditangani_pada = COALESCE(
                a.ditangani_pada, NOW()
            )
            WHERE a.tipe_sumber = 'transaksi'
              AND a.status = 'terbuka'
              AND (t.id IS NULL OR t.status NOT IN ('diproses', 'dikirim')
                   OR t.tanggal >= (NOW() - INTERVAL 1 DAY))
        """)

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_kpi(start_date, end_date, cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        branch_filter = "AND cabang_id = %s" if cabang_id is not None else ""
        params = [start_date, end_date]
        if cabang_id is not None:
            params.append(cabang_id)

        cursor.execute(f"""
            SELECT
                COALESCE(SUM(pendapatan_berhasil), 0) AS total_pendapatan,
                COALESCE(SUM(transaksi_berhasil), 0) AS transaksi_berhasil,
                COALESCE(SUM(jumlah_transaksi), 0) AS total_transaksi,
                COALESCE(SUM(transaksi_selesai), 0) AS transaksi_selesai,
                COALESCE(SUM(transaksi_dibatalkan), 0) AS transaksi_dibatalkan,
                COALESCE(SUM(transaksi_diproses), 0) AS transaksi_diproses,
                COALESCE(SUM(transaksi_dikirim), 0) AS transaksi_dikirim,
                COALESCE(AVG(rata_rata_transaksi), 0) AS rata_rata_transaksi
            FROM mis_penjualan_harian
            WHERE tanggal BETWEEN %s AND %s {branch_filter}
        """, params)
        kpi = cursor.fetchone()

        stock_params = []
        stock_filter = ""
        if cabang_id is not None:
            stock_filter = "AND cabang_id = %s"
            stock_params.append(cabang_id)
        cursor.execute(f"""
            SELECT
                COUNT(*) AS total_produk_cabang,
                SUM(status_stok = 'normal') AS stok_normal,
                SUM(status_stok = 'menipis') AS stok_menipis,
                SUM(status_stok = 'habis') AS stok_habis
            FROM mis_stok_snapshot
            WHERE tanggal_snapshot = (
                SELECT MAX(tanggal_snapshot) FROM mis_stok_snapshot
            ) {stock_filter}
        """, stock_params)
        stock = cursor.fetchone()

        alert_params = []
        alert_filter = ""
        if cabang_id is not None:
            alert_filter = "AND cabang_id = %s"
            alert_params.append(cabang_id)
        cursor.execute(f"""
            SELECT COUNT(*) AS alert_terbuka
            FROM mis_monitoring_alert
            WHERE status = 'terbuka' {alert_filter}
        """, alert_params)
        alerts = cursor.fetchone()

        request_params = [start_date, end_date]
        request_filter = ""
        if cabang_id is not None:
            request_filter = "AND cabang_id = %s"
            request_params.append(cabang_id)
        cursor.execute(f"""
            SELECT COALESCE(SUM(request_diproses), 0) AS request_menunggu
            FROM mis_permintaan_stok_harian
            WHERE tanggal BETWEEN %s AND %s {request_filter}
        """, request_params)
        requests = cursor.fetchone()

        total_pendapatan = _as_float(kpi["total_pendapatan"])
        transaksi_berhasil = _as_int(kpi["transaksi_berhasil"])
        rata_rata_transaksi = (
            total_pendapatan / transaksi_berhasil
            if transaksi_berhasil else 0
        )

        return {
            "total_pendapatan": total_pendapatan,
            "transaksi_berhasil": transaksi_berhasil,
            "total_transaksi": _as_int(kpi["total_transaksi"]),
            "transaksi_selesai": _as_int(kpi["transaksi_selesai"]),
            "transaksi_dibatalkan": _as_int(kpi["transaksi_dibatalkan"]),
            "transaksi_diproses": _as_int(kpi["transaksi_diproses"]),
            "transaksi_dikirim": _as_int(kpi["transaksi_dikirim"]),
            "rata_rata_transaksi": rata_rata_transaksi,
            "stok_normal": _as_int(stock["stok_normal"]),
            "stok_menipis": _as_int(stock["stok_menipis"]),
            "stok_habis": _as_int(stock["stok_habis"]),
            "alert_terbuka": _as_int(alerts["alert_terbuka"]),
            "request_menunggu": _as_int(requests["request_menunggu"]),
        }
    finally:
        cursor.close()
        connection.close()


def get_sales_trend(start_date, end_date, cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        branch_filter = "AND cabang_id = %s" if cabang_id is not None else ""
        params = [start_date, end_date]
        if cabang_id is not None:
            params.append(cabang_id)
        cursor.execute(f"""
            SELECT
                tanggal,
                SUM(pendapatan_berhasil) AS pendapatan,
                SUM(transaksi_berhasil) AS transaksi_berhasil,
                SUM(transaksi_selesai) AS transaksi_selesai,
                SUM(transaksi_dibatalkan) AS transaksi_dibatalkan
            FROM mis_penjualan_harian
            WHERE tanggal BETWEEN %s AND %s {branch_filter}
            GROUP BY tanggal
            ORDER BY tanggal
        """, params)
        source = {row["tanggal"]: row for row in cursor.fetchall()}

        result = []
        current = start_date
        while current <= end_date:
            row = source.get(current, {})
            result.append({
                "tanggal": current.isoformat(),
                "pendapatan": _as_float(row.get("pendapatan")),
                "transaksi_berhasil": _as_int(row.get("transaksi_berhasil")),
                "transaksi_selesai": _as_int(row.get("transaksi_selesai")),
                "transaksi_dibatalkan": _as_int(
                    row.get("transaksi_dibatalkan")
                ),
            })
            current += timedelta(days=1)
        return result
    finally:
        cursor.close()
        connection.close()


def get_top_products(start_date, end_date, cabang_id=None, limit=10):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        branch_filter = "AND m.cabang_id = %s" if cabang_id is not None else ""
        params = [start_date, end_date]
        if cabang_id is not None:
            params.append(cabang_id)
        params.append(limit)
        cursor.execute(f"""
            SELECT
                m.produk_id,
                p.nama,
                SUM(m.jumlah_terjual) AS jumlah_terjual,
                SUM(m.pendapatan) AS pendapatan
            FROM mis_penjualan_produk_harian m
            JOIN produk p ON p.id = m.produk_id
            WHERE m.tanggal BETWEEN %s AND %s {branch_filter}
            GROUP BY m.produk_id, p.nama
            ORDER BY jumlah_terjual DESC, pendapatan DESC
            LIMIT %s
        """, params)
        return [{
            "produk_id": row["produk_id"],
            "nama": row["nama"],
            "jumlah_terjual": _as_int(row["jumlah_terjual"]),
            "pendapatan": _as_float(row["pendapatan"]),
        } for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()


def get_branch_comparison(start_date, end_date, cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        branch_filter = "AND m.cabang_id = %s" if cabang_id is not None else ""
        params = [start_date, end_date]
        if cabang_id is not None:
            params.append(cabang_id)
        cursor.execute(f"""
            SELECT
                m.cabang_id,
                c.nama AS cabang,
                SUM(m.pendapatan_berhasil) AS pendapatan,
                SUM(m.transaksi_berhasil) AS transaksi_berhasil,
                SUM(m.transaksi_selesai) AS transaksi_selesai,
                SUM(m.transaksi_dibatalkan) AS transaksi_dibatalkan
            FROM mis_penjualan_harian m
            JOIN cabang c ON c.id = m.cabang_id
            WHERE m.tanggal BETWEEN %s AND %s {branch_filter}
            GROUP BY m.cabang_id, c.nama
            ORDER BY pendapatan DESC, transaksi_berhasil DESC
        """, params)
        return [{
            "cabang_id": row["cabang_id"],
            "cabang": row["cabang"],
            "pendapatan": _as_float(row["pendapatan"]),
            "transaksi_berhasil": _as_int(row["transaksi_berhasil"]),
            "transaksi_selesai": _as_int(row["transaksi_selesai"]),
            "transaksi_dibatalkan": _as_int(row["transaksi_dibatalkan"]),
        } for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()


def get_stock_monitoring(cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        branch_filter = "AND s.cabang_id = %s" if cabang_id is not None else ""
        params = []
        if cabang_id is not None:
            params.append(cabang_id)
        cursor.execute(f"""
            SELECT
                s.cabang_id,
                c.nama AS cabang,
                s.produk_id,
                p.nama AS produk,
                s.stok_gudang,
                s.stok_cabang,
                s.stok_minimum,
                s.status_stok
            FROM mis_stok_snapshot s
            JOIN cabang c ON c.id = s.cabang_id
            JOIN produk p ON p.id = s.produk_id
            WHERE s.tanggal_snapshot = (
                SELECT MAX(tanggal_snapshot) FROM mis_stok_snapshot
            ) {branch_filter}
            ORDER BY
                CASE s.status_stok
                    WHEN 'habis' THEN 1
                    WHEN 'menipis' THEN 2
                    ELSE 3
                END,
                s.stok_cabang,
                c.nama,
                p.nama
        """, params)
        rows = cursor.fetchall()
        summary = {"normal": 0, "menipis": 0, "habis": 0}
        items = []
        for row in rows:
            status = row["status_stok"]
            summary[status] = summary.get(status, 0) + 1
            items.append({
                "cabang_id": row["cabang_id"],
                "cabang": row["cabang"],
                "produk_id": row["produk_id"],
                "produk": row["produk"],
                "stok_gudang": _as_int(row["stok_gudang"]),
                "stok_cabang": _as_int(row["stok_cabang"]),
                "stok_minimum": _as_int(row["stok_minimum"]),
                "status_stok": status,
            })
        return {"summary": summary, "items": items}
    finally:
        cursor.close()
        connection.close()


def get_alerts(cabang_id=None, limit=50):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        branch_filter = "AND a.cabang_id = %s" if cabang_id is not None else ""
        params = [limit]
        if cabang_id is not None:
            params.insert(0, cabang_id)
        cursor.execute(f"""
            SELECT
                a.id,
                a.tipe_sumber,
                a.sumber_id,
                a.cabang_id,
                c.nama AS cabang,
                a.produk_id,
                p.nama AS produk,
                a.tingkat,
                a.judul,
                a.pesan,
                a.status,
                a.terdeteksi_pada,
                a.ditangani_pada
            FROM mis_monitoring_alert a
            LEFT JOIN cabang c ON c.id = a.cabang_id
            LEFT JOIN produk p ON p.id = a.produk_id
            WHERE a.status = 'terbuka' {branch_filter}
            ORDER BY
                CASE a.tingkat
                    WHEN 'critical' THEN 1
                    WHEN 'warning' THEN 2
                    ELSE 3
                END,
                a.terdeteksi_pada DESC
            LIMIT %s
        """, params)
        result = []
        for row in cursor.fetchall():
            result.append({
                "id": row["id"],
                "tipe_sumber": row["tipe_sumber"],
                "sumber_id": row["sumber_id"],
                "cabang_id": row["cabang_id"],
                "cabang": row["cabang"],
                "produk_id": row["produk_id"],
                "produk": row["produk"],
                "tingkat": row["tingkat"],
                "judul": row["judul"],
                "pesan": row["pesan"],
                "status": row["status"],
                "terdeteksi_pada": row["terdeteksi_pada"].isoformat(),
                "ditangani_pada": (
                    row["ditangani_pada"].isoformat()
                    if row["ditangani_pada"] else None
                ),
            })
        return result
    finally:
        cursor.close()
        connection.close()


def get_last_refresh():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT GREATEST(
                COALESCE(MAX(diperbarui_pada), '1000-01-01'),
                COALESCE((SELECT MAX(dibuat_pada) FROM mis_stok_snapshot), '1000-01-01')
            ) AS terakhir_diperbarui
            FROM mis_penjualan_harian
        """)
        value = cursor.fetchone()["terakhir_diperbarui"]
        if not value:
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    finally:
        cursor.close()
        connection.close()
