from datetime import date, timedelta
from math import ceil

from model.database import get_connection
from service.dss_setting import get_dss_criteria


CRITERION_KEYS = {
    "harga_beli": "harga_beli",
    "waktu_pengiriman": "waktu_pengiriman_hari",
    "minimum_order": "minimum_order",
    "keandalan": "tingkat_keandalan",
}


def _number(value):
    return float(value or 0)


def get_dss_products():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, nama, stok, stok_minimum
            FROM produk
            ORDER BY nama
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_dss_branches():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, nama
            FROM cabang
            WHERE status = 'aktif'
            ORDER BY nama
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_stock_summary(produk_id, cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if cabang_id is not None:
            cursor.execute("""
                SELECT id
                FROM cabang
                WHERE id = %s AND status = 'aktif'
            """, (cabang_id,))
            if not cursor.fetchone():
                raise ValueError("Cabang tidak ditemukan atau nonaktif.")

        params = [produk_id]
        join_branch = ""
        if cabang_id is not None:
            join_branch = " AND sc.cabang_id = %s"
            params = [cabang_id, produk_id]
        cursor.execute(f"""
            SELECT p.id AS produk_id, p.nama, p.stok AS stok_gudang,
                   p.stok_minimum,
                   COALESCE(SUM(sc.stok), 0) AS stok_cabang
            FROM produk p
            LEFT JOIN stok_cabang sc
                ON sc.produk_id = p.id{join_branch}
            WHERE p.id = %s
            GROUP BY p.id, p.nama, p.stok, p.stok_minimum
        """, params)
        row = cursor.fetchone()
        if not row:
            raise ValueError("Produk tidak ditemukan.")
        row["stok_gudang"] = int(row["stok_gudang"] or 0)
        row["stok_cabang"] = int(row["stok_cabang"] or 0)
        row["stok_minimum"] = int(row["stok_minimum"] or 0)
        return row
    finally:
        cursor.close()
        connection.close()


def get_supplier_alternatives(produk_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT s.id AS supplier_id, s.nama_perusahaan AS supplier,
                   sp.harga_beli, sp.waktu_pengiriman_hari,
                   sp.minimum_order, sp.tingkat_keandalan
            FROM supplier_produk sp
            JOIN supplier s ON s.id = sp.supplier_id
            WHERE sp.produk_id = %s
              AND sp.status = 'aktif'
              AND s.status = 'aktif'
              AND NOT EXISTS (
                  SELECT 1
                  FROM expert_supplier_evaluation ee
                  WHERE ee.supplier_id = sp.supplier_id
                    AND ee.produk_id = sp.produk_id
                    AND ee.id = (
                        SELECT MAX(last_eval.id)
                        FROM expert_supplier_evaluation last_eval
                        WHERE last_eval.supplier_id = sp.supplier_id
                          AND last_eval.produk_id = sp.produk_id
                    )
                    AND (
                        ee.status_evaluasi IN ('tidak_layak_sementara', 'dibatasi')
                        OR (
                            ee.status_evaluasi = 'layak_kembali'
                            AND EXISTS (
                                SELECT 1 FROM expert_supplier_action recovery
                                WHERE recovery.supplier_id = ee.supplier_id
                                  AND recovery.produk_id = ee.produk_id
                                  AND recovery.jenis_tindakan = 'pemulihan_supplier'
                                  AND recovery.status = 'terbuka'
                            )
                        )
                    )
              )
            ORDER BY s.nama_perusahaan
        """, (produk_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def _normalize(value, values, criterion_type):
    value = _number(value)
    numeric_values = [_number(item) for item in values]
    if criterion_type == "benefit":
        maximum = max(numeric_values)
        return 1 if maximum == 0 else value / maximum
    minimum = min(numeric_values)
    return 1 if value == 0 and minimum == 0 else minimum / value if value else 1


def _save_recommendation(product_id, branch_id, requested_qty, stock,
                         ranked, user_id):
    selected = ranked[0]
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO dss_rekomendasi_pengadaan
                (produk_id, cabang_id, jumlah_kebutuhan, stok_gudang,
                 stok_cabang, supplier_terpilih_id, jumlah_pembelian,
                 total_biaya, skor_tertinggi, dibuat_oleh)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            product_id, branch_id, requested_qty, stock["stok_gudang"],
            stock["stok_cabang"], selected["supplier_id"],
            selected["jumlah_pembelian"], selected["total_biaya"],
            selected["skor_akhir"], user_id,
        ))
        recommendation_id = cursor.lastrowid
        for item in ranked:
            cursor.execute("""
                INSERT INTO dss_rekomendasi_detail
                    (rekomendasi_id, supplier_id, harga_beli,
                     waktu_pengiriman_hari, minimum_order,
                     tingkat_keandalan, skor_harga, skor_pengiriman,
                     skor_minimum_order, skor_keandalan, skor_akhir,
                     peringkat)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                recommendation_id, item["supplier_id"], item["harga_beli"],
                item["waktu_pengiriman_hari"], item["minimum_order"],
                item["tingkat_keandalan"], item["skor_harga"],
                item["skor_pengiriman"], item["skor_minimum_order"],
                item["skor_keandalan"], item["skor_akhir"], item["peringkat"],
            ))
        connection.commit()
        return recommendation_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def calculate_recommendation(product_id, requested_qty, branch_id, user_id):
    try:
        product_id = int(product_id)
        requested_qty = int(requested_qty)
        branch_id = int(branch_id) if branch_id else None
    except (TypeError, ValueError):
        raise ValueError("Produk, cabang, dan jumlah kebutuhan harus valid.") from None
    if requested_qty <= 0:
        raise ValueError("Jumlah kebutuhan harus lebih dari 0.")

    criteria = [item for item in get_dss_criteria(False) if item["aktif"]]
    total_weight = sum(_number(item["bobot"]) for item in criteria)
    if not criteria or abs(total_weight - 100) > 0.001:
        raise ValueError("Bobot kriteria DSS belum valid. Total bobot harus 100%.")

    stock = get_stock_summary(product_id, branch_id)
    alternatives = get_supplier_alternatives(product_id)
    if not alternatives:
        raise ValueError("Belum ada supplier aktif dan layak untuk produk tersebut.")

    source_values = {
        key: [item[CRITERION_KEYS[key]] for item in alternatives]
        for key in CRITERION_KEYS
    }
    weights = {item["kode_kriteria"]: _number(item["bobot"]) / 100 for item in criteria}
    types = {item["kode_kriteria"]: item["tipe"] for item in criteria}
    ranked = []
    for item in alternatives:
        scores = {
            key: _normalize(item[CRITERION_KEYS[key]], source_values[key], types[key])
            for key in weights
        }
        final_score = sum(scores[key] * weights[key] for key in weights)
        minimum_order = max(1, int(item["minimum_order"] or 1))
        order_qty = ceil(requested_qty / minimum_order) * minimum_order
        ranked.append({
            "supplier_id": item["supplier_id"],
            "supplier": item["supplier"],
            "harga_beli": _number(item["harga_beli"]),
            "waktu_pengiriman_hari": int(item["waktu_pengiriman_hari"] or 0),
            "minimum_order": minimum_order,
            "tingkat_keandalan": _number(item["tingkat_keandalan"]),
            "skor_harga": scores.get("harga_beli", 0),
            "skor_pengiriman": scores.get("waktu_pengiriman", 0),
            "skor_minimum_order": scores.get("minimum_order", 0),
            "skor_keandalan": scores.get("keandalan", 0),
            "skor_akhir": final_score,
            "jumlah_pembelian": order_qty,
            "total_biaya": order_qty * _number(item["harga_beli"]),
            "estimasi_tiba": (date.today() + timedelta(
                days=int(item["waktu_pengiriman_hari"] or 0)
            )).isoformat(),
        })

    ranked.sort(key=lambda item: (
        -item["skor_akhir"], item["harga_beli"],
        item["waktu_pengiriman_hari"], item["supplier"]
    ))
    for index, item in enumerate(ranked, start=1):
        item["peringkat"] = index

    recommendation_id = _save_recommendation(
        product_id, branch_id, requested_qty, stock, ranked, user_id
    )
    return {
        "recommendation_id": recommendation_id,
        "product": stock,
        "requested_qty": requested_qty,
        "criteria": criteria,
        "ranked": ranked,
        "recommended": ranked[0],
    }


def get_recommendation_for_purchase(recommendation_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.id, r.produk_id, r.supplier_terpilih_id,
                   r.jumlah_pembelian, p.nama AS produk,
                   s.nama_perusahaan AS supplier
            FROM dss_rekomendasi_pengadaan r
            JOIN produk p ON p.id = r.produk_id
            JOIN supplier s ON s.id = r.supplier_terpilih_id
            WHERE r.id = %s
        """, (recommendation_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return row
    finally:
        cursor.close()
        connection.close()
