from datetime import date, timedelta

from model.database import get_connection


WARNING_RATIO = 0.10
BLOCK_RATIO = 0.30
INCIDENT_WARNING_RATIO = 0.10
INCIDENT_BLOCK_RATIO = 0.20


def _close(cursor, connection):
    cursor.close()
    connection.close()


def _ratio(value, total):
    return round(float(value or 0) / total, 4) if total else 0.0


def _rule_for_status(late_ratio, incident_ratio):
    if late_ratio >= BLOCK_RATIO or incident_ratio >= INCIDENT_BLOCK_RATIO:
        return "ES_SUPPLIER_LATE_BLOCK" if late_ratio >= BLOCK_RATIO else "ES_SUPPLIER_INCIDENT_BLOCK", "tidak_layak_sementara"
    if late_ratio >= WARNING_RATIO or incident_ratio >= INCIDENT_WARNING_RATIO:
        return "ES_SUPPLIER_LATE_WARNING" if late_ratio >= WARNING_RATIO else "ES_SUPPLIER_INCIDENT_WARNING", "dalam_pengawasan"
    return None, "baik"


def _supplier_product_name(cursor, supplier_id, product_id):
    cursor.execute("""
        SELECT s.nama_perusahaan AS supplier, p.nama AS produk
        FROM supplier s CROSS JOIN produk p
        WHERE s.id = %s AND p.id = %s
    """, (supplier_id, product_id))
    return cursor.fetchone() or {"supplier": "Supplier", "produk": "Produk"}


def evaluate_supplier_product(supplier_id, product_id, user_id=None, days=90):
    """Evaluate one supplier/product pair using purchase and incident history."""
    supplier_id = int(supplier_id)
    product_id = int(product_id)
    period_start = date.today() - timedelta(days=days)
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT COUNT(DISTINCT pb.id) AS jumlah_pembelian,
                   SUM(CASE WHEN pb.status = 'diterima' THEN 1 ELSE 0 END) AS jumlah_diterima,
                   SUM(CASE WHEN pb.status = 'diterima'
                              AND pb.tanggal_diterima IS NOT NULL
                              AND DATEDIFF(pb.tanggal_diterima, pb.tanggal) <= COALESCE(sp.waktu_pengiriman_hari, 1)
                            THEN 1 ELSE 0 END) AS jumlah_tepat_waktu,
                   SUM(CASE WHEN pb.status = 'diterima'
                              AND (pb.tanggal_diterima IS NULL
                                   OR DATEDIFF(pb.tanggal_diterima, pb.tanggal) > COALESCE(sp.waktu_pengiriman_hari, 1))
                            THEN 1 ELSE 0 END) AS jumlah_terlambat
            FROM pembelian pb
            JOIN detail_pembelian dp ON dp.pembelian_id = pb.id
            LEFT JOIN supplier_produk sp
                ON sp.supplier_id = pb.supplier_id AND sp.produk_id = dp.produk_id
            WHERE pb.supplier_id = %s AND dp.produk_id = %s
              AND pb.tanggal >= %s
        """, (supplier_id, product_id, period_start))
        metrics = cursor.fetchone() or {}
        cursor.execute("""
            SELECT COALESCE(SUM(jumlah), 0) AS jumlah_insiden
            FROM expert_supplier_incident
            WHERE supplier_id = %s AND produk_id = %s AND terjadi_pada >= %s
        """, (supplier_id, product_id, period_start))
        incident = cursor.fetchone() or {}
        names = _supplier_product_name(cursor, supplier_id, product_id)
        purchases = int(metrics.get("jumlah_pembelian") or 0)
        received = int(metrics.get("jumlah_diterima") or 0)
        on_time = int(metrics.get("jumlah_tepat_waktu") or 0)
        late = int(metrics.get("jumlah_terlambat") or 0)
        incidents = int(incident.get("jumlah_insiden") or 0)
        late_ratio = _ratio(late, received)
        incident_ratio = _ratio(incidents, received or purchases)
        rule_code, status = _rule_for_status(late_ratio, incident_ratio)

        previous = None
        cursor.execute("""
            SELECT status_evaluasi FROM expert_supplier_evaluation
            WHERE supplier_id = %s AND produk_id = %s
            ORDER BY id DESC LIMIT 1
        """, (supplier_id, product_id))
        previous = cursor.fetchone()
        recovering = previous and previous["status_evaluasi"] == "tidak_layak_sementara" and status == "baik"
        if recovering:
            status = "layak_kembali"

        if status == "baik":
            diagnosis = "Performa supplier masih berada dalam batas yang dapat diterima."
            action = "Tetap gunakan dan pantau pada periode evaluasi berikutnya."
        elif status == "dalam_pengawasan":
            diagnosis = f"Ditemukan tingkat keterlambatan {late_ratio:.1%} dan tingkat insiden {incident_ratio:.1%}."
            action = "Beri peringatan, minta klarifikasi, dan batasi pemesanan bila masalah berulang."
        elif status == "tidak_layak_sementara":
            diagnosis = f"Performa kritis: keterlambatan {late_ratio:.1%} atau insiden {incident_ratio:.1%}."
            action = "Jangan gunakan untuk produk ini sementara; evaluasi supplier dan gunakan alternatif lain."
        else:
            diagnosis = "Performa supplier membaik setelah evaluasi sebelumnya."
            action = "Ajukan pemulihan supplier untuk disetujui manajer."

        cursor.execute("""
            INSERT INTO expert_supplier_evaluation
                (supplier_id, produk_id, periode_mulai, periode_selesai,
                 jumlah_pembelian, jumlah_diterima, jumlah_tepat_waktu,
                 jumlah_terlambat, jumlah_insiden, tingkat_keterlambatan,
                 tingkat_insiden, status_evaluasi, diagnosis,
                 rekomendasi_tindakan, dibuat_oleh)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (supplier_id, product_id, period_start, date.today(), purchases,
              received, on_time, late, incidents, late_ratio, incident_ratio,
              status, diagnosis, action, user_id))
        evaluation_id = cursor.lastrowid

        if status in ("dalam_pengawasan", "tidak_layak_sementara", "layak_kembali"):
            action_type = "pemulihan_supplier" if status == "layak_kembali" else (
                "blokir_sementara" if status == "tidak_layak_sementara" else "peringatan_supplier"
            )
            cursor.execute("""
                SELECT id FROM expert_supplier_action
                WHERE supplier_id = %s AND produk_id = %s
                  AND jenis_tindakan = %s AND status = 'terbuka'
                LIMIT 1
            """, (supplier_id, product_id, action_type))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO expert_supplier_action
                        (supplier_id, produk_id, evaluation_id, jenis_tindakan,
                         alasan, tanggal_evaluasi_ulang, dibuat_oleh)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (supplier_id, product_id, evaluation_id, action_type,
                      diagnosis, date.today() + timedelta(days=30), user_id))
        connection.commit()
        return {
            "id": evaluation_id, "supplier_id": supplier_id, "produk_id": product_id,
            "supplier": names["supplier"], "produk": names["produk"],
            "jumlah_pembelian": purchases, "jumlah_diterima": received,
            "jumlah_tepat_waktu": on_time, "jumlah_terlambat": late,
            "jumlah_insiden": incidents, "tingkat_keterlambatan": late_ratio,
            "tingkat_insiden": incident_ratio, "status_evaluasi": status,
            "diagnosis": diagnosis, "rekomendasi_tindakan": action,
            "rule_code": rule_code,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(cursor, connection)


def get_latest_evaluation(supplier_id, product_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.*, s.nama_perusahaan AS supplier, p.nama AS produk
            FROM expert_supplier_evaluation e
            JOIN supplier s ON s.id = e.supplier_id
            JOIN produk p ON p.id = e.produk_id
            WHERE e.supplier_id = %s AND e.produk_id = %s
            ORDER BY e.id DESC LIMIT 1
        """, (supplier_id, product_id))
        return cursor.fetchone()
    finally:
        _close(cursor, connection)


def explain_decision(supplier_id, product_id):
    """Return the latest explainable conclusion for a supplier/product pair."""
    evaluation = get_latest_evaluation(supplier_id, product_id)
    if not evaluation:
        return {
            "status": "belum_dievaluasi",
            "kesimpulan": "Belum ada histori evaluasi untuk supplier dan produk ini.",
            "tindakan": "Lakukan evaluasi supplier sebelum membuat keputusan pembelian.",
        }
    return {
        "status": evaluation["status_evaluasi"],
        "kesimpulan": evaluation["diagnosis"],
        "tindakan": evaluation["rekomendasi_tindakan"],
        "periode_mulai": evaluation["periode_mulai"],
        "periode_selesai": evaluation["periode_selesai"],
        "tingkat_keterlambatan": evaluation["tingkat_keterlambatan"],
        "tingkat_insiden": evaluation["tingkat_insiden"],
    }


def supplier_is_eligible(supplier_id, product_id):
    latest = get_latest_evaluation(supplier_id, product_id)
    if not latest or latest["status_evaluasi"] in ("baik", "dalam_pengawasan"):
        return True
    if latest["status_evaluasi"] in ("tidak_layak_sementara", "dibatasi"):
        return False
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT status FROM expert_supplier_action
            WHERE supplier_id = %s AND produk_id = %s
              AND jenis_tindakan = 'pemulihan_supplier'
            ORDER BY id DESC LIMIT 1
        """, (supplier_id, product_id))
        action = cursor.fetchone()
        return bool(action and action["status"] == "disetujui")
    finally:
        _close(cursor, connection)


def record_supplier_incident(supplier_id, product_id, incident_type,
                             quantity, description, purchase_id=None,
                             user_id=None):
    if incident_type not in ("terlambat", "rusak", "kurang", "masa_simpan", "retur"):
        raise ValueError("Jenis insiden supplier tidak valid.")
    quantity = int(quantity or 1)
    if quantity <= 0:
        raise ValueError("Jumlah insiden harus lebih dari 0.")
    if not description.strip():
        raise ValueError("Keterangan insiden wajib diisi.")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO expert_supplier_incident
                (supplier_id, produk_id, pembelian_id, jenis, jumlah,
                 keterangan, dibuat_oleh)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (supplier_id, product_id, purchase_id, incident_type,
              quantity, description.strip(), user_id))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(cursor, connection)


def get_supplier_evaluations(limit=50):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.*, s.nama_perusahaan AS supplier, p.nama AS produk
            FROM expert_supplier_evaluation e
            JOIN supplier s ON s.id = e.supplier_id
            JOIN produk p ON p.id = e.produk_id
            JOIN (SELECT supplier_id, produk_id, MAX(id) id
                  FROM expert_supplier_evaluation GROUP BY supplier_id, produk_id) latest
              ON latest.id = e.id
            ORDER BY e.id DESC LIMIT %s
        """, (limit,))
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def get_supplier_actions(limit=50):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.*, s.nama_perusahaan AS supplier, p.nama AS produk
            FROM expert_supplier_action a
            JOIN supplier s ON s.id = a.supplier_id
            JOIN produk p ON p.id = a.produk_id
            ORDER BY a.status = 'terbuka' DESC, a.id DESC LIMIT %s
        """, (limit,))
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def get_notifications(limit=50):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT n.*, p.nama AS produk, s.nama_perusahaan AS supplier,
                   c.nama AS cabang
            FROM expert_notification n
            LEFT JOIN produk p ON p.id = n.produk_id
            LEFT JOIN supplier s ON s.id = n.supplier_id
            LEFT JOIN cabang c ON c.id = n.cabang_id
            WHERE n.status = 'terbuka'
            ORDER BY FIELD(n.prioritas, 'kritis', 'tinggi', 'normal'), n.id DESC
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def generate_purchase_notifications(user_id=None):
    """Create one notification per product when stock needs replenishment."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    created = []
    try:
        cursor.execute("""
            SELECT n.id, p.stok, p.stok_minimum,
                   COALESCE((SELECT SUM(dp.jumlah)
                     FROM pembelian pb JOIN detail_pembelian dp ON dp.pembelian_id = pb.id
                     WHERE dp.produk_id = p.id AND pb.status IN ('dipesan', 'diproses')), 0) AS stok_dipesan
            FROM expert_notification n
            JOIN produk p ON p.id = n.produk_id
            WHERE n.jenis = 'kebutuhan_pembelian' AND n.status = 'terbuka'
        """)
        for notification in cursor.fetchall():
            available = int(notification["stok"] or 0) + int(notification["stok_dipesan"] or 0)
            if available > int(notification["stok_minimum"] or 0):
                cursor.execute("""
                    UPDATE expert_notification SET status = 'selesai'
                    WHERE id = %s
                """, (notification["id"],))
        cursor.execute("""
            SELECT p.id, p.nama, p.stok, p.stok_minimum,
                   COALESCE((SELECT SUM(dp.jumlah)
                     FROM pembelian pb JOIN detail_pembelian dp ON dp.pembelian_id = pb.id
                     WHERE dp.produk_id = p.id AND pb.status IN ('dipesan', 'diproses')), 0) AS stok_dipesan
            FROM produk p
            WHERE p.stok <= p.stok_minimum
        """)
        for item in cursor.fetchall():
            if int(item["stok"] or 0) + int(item["stok_dipesan"] or 0) > int(item["stok_minimum"] or 0):
                continue
            fingerprint = f"purchase:{item['id']}"
            priority = "kritis" if int(item["stok"] or 0) <= 0 else "tinggi"
            cursor.execute("""
                INSERT INTO expert_notification
                    (fingerprint, jenis, produk_id, prioritas, judul, pesan,
                     rule_code, source_article_slug, status)
                VALUES (%s, 'kebutuhan_pembelian', %s, %s, %s, %s,
                        'ES_PURCHASE_REORDER',
                        'sop-pengadaan-ulang-dan-notifikasi-stok', 'terbuka')
                ON DUPLICATE KEY UPDATE
                    prioritas = VALUES(prioritas), pesan = VALUES(pesan),
                    status = 'terbuka'
            """, (fingerprint, item["id"], priority,
                  f"Stok {item['nama']} perlu dibeli",
                  f"Stok saat ini {item['stok']} unit, stok dipesan {item['stok_dipesan']} unit, batas minimum {item['stok_minimum']} unit."))
            created.append(item)
        connection.commit()
        return created
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(cursor, connection)


def detect_duplicate_purchase(supplier_id, items):
    product_ids = [int(item["produk_id"]) for item in items]
    if not product_ids:
        return []
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        placeholders = ",".join(["%s"] * len(product_ids))
        cursor.execute(f"""
            SELECT dp.produk_id, p.nama AS produk, SUM(dp.jumlah) AS jumlah_dipesan,
                   COUNT(DISTINCT pb.id) AS jumlah_pembelian
            FROM pembelian pb
            JOIN detail_pembelian dp ON dp.pembelian_id = pb.id
            JOIN produk p ON p.id = dp.produk_id
            WHERE pb.status IN ('dipesan', 'diproses')
              AND dp.produk_id IN ({placeholders})
            GROUP BY dp.produk_id, p.nama
        """, tuple(product_ids))
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def approve_supplier_action(action_id, user_id, approved=True):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            UPDATE expert_supplier_action
            SET status = %s, disetujui_oleh = %s,
                diselesaikan_pada = NOW()
            WHERE id = %s AND status = 'terbuka'
        """, ("disetujui" if approved else "ditolak", user_id, action_id))
        if cursor.rowcount == 0:
            return False
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(cursor, connection)


def run_all_supplier_evaluations(user_id=None):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT supplier_id, produk_id FROM supplier_produk
            WHERE status = 'aktif'
        """)
        pairs = cursor.fetchall()
    finally:
        _close(cursor, connection)
    return [evaluate_supplier_product(row[0], row[1], user_id) for row in pairs]
