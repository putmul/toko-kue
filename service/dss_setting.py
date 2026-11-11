from model.database import get_connection


DEFAULT_CRITERIA = (
    ("harga_beli", "Harga beli", "cost", "harga_beli"),
    ("waktu_pengiriman", "Waktu pengiriman", "cost", "waktu_pengiriman_hari"),
    ("minimum_order", "Minimum order", "cost", "minimum_order"),
    ("keandalan", "Tingkat keandalan", "benefit", "tingkat_keandalan"),
)


def get_dss_criteria(include_inactive=True):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT id, kode_kriteria, nama_kriteria, tipe, bobot,
                   aktif, sumber_data
            FROM dss_kriteria_supplier
        """
        if not include_inactive:
            query += " WHERE aktif = 1"
        query += " ORDER BY id"
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
            return rows
        return [
            {
                "id": None,
                "kode_kriteria": code,
                "nama_kriteria": name,
                "tipe": criterion_type,
                "bobot": 0,
                "aktif": 1,
                "sumber_data": source,
            }
            for code, name, criterion_type, source in DEFAULT_CRITERIA
        ]
    finally:
        cursor.close()
        connection.close()


def save_dss_criteria(values, user_id):
    allowed_codes = {item[0] for item in DEFAULT_CRITERIA}
    if set(values) != allowed_codes:
        raise ValueError("Kriteria DSS tidak lengkap atau tidak valid.")

    total_weight = 0
    normalized = []
    for code, value in values.items():
        try:
            weight = float(value.get("bobot", 0))
        except (TypeError, ValueError):
            raise ValueError("Bobot kriteria harus berupa angka.") from None
        if weight < 0 or weight > 100:
            raise ValueError("Bobot kriteria harus berada di antara 0 dan 100.")
        active = bool(value.get("aktif", True))
        if active:
            total_weight += weight
        normalized.append((code, weight, active))

    if not any(item[2] for item in normalized):
        raise ValueError("Minimal satu kriteria harus aktif.")
    if abs(total_weight - 100) > 0.001:
        raise ValueError("Total bobot kriteria aktif harus tepat 100%.")

    connection = get_connection()
    cursor = connection.cursor()
    try:
        for code, weight, active in normalized:
            cursor.execute("""
                INSERT INTO dss_kriteria_supplier
                    (kode_kriteria, nama_kriteria, tipe, bobot, aktif,
                     sumber_data, diperbarui_oleh)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    bobot = VALUES(bobot),
                    aktif = VALUES(aktif),
                    diperbarui_oleh = VALUES(diperbarui_oleh)
            """, (
                code,
                next(item[1] for item in DEFAULT_CRITERIA if item[0] == code),
                next(item[2] for item in DEFAULT_CRITERIA if item[0] == code),
                weight,
                int(active),
                next(item[3] for item in DEFAULT_CRITERIA if item[0] == code),
                user_id,
            ))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
