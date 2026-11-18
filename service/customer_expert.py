"""Rule-based expert system for helping customers choose a cake.

This module is deliberately separate from ``expert_system.py`` which evaluates
suppliers. It uses customer facts and IF/THEN rules, not DSS criteria weights.
"""

from model.database import get_connection


ALLOWED_TEXTURES = {"lembut", "renyah", "creamy"}
ALLOWED_CATEGORIES = {"cake", "brownies", "donat", "cookies", "pastry", "lainnya"}
ALLOWED_TASTES = {
    "coklat": "intensitas_coklat",
    "manis": "tingkat_kemanisan",
    "pahit": "tingkat_kepahitan",
}
ALLOWED_ALLERGENS = {
    "susu": "mengandung_susu",
    "telur": "mengandung_telur",
    "kacang": "mengandung_kacang",
    "gluten": "mengandung_gluten",
}


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_product_profiles():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.id AS produk_id, p.nama, p.harga,
                   COALESCE(cp.intensitas_coklat, 0) AS intensitas_coklat,
                   COALESCE(cp.tingkat_kemanisan, 0) AS tingkat_kemanisan,
                   COALESCE(cp.tingkat_kepahitan, 0) AS tingkat_kepahitan,
                   COALESCE(cp.tekstur, '') AS tekstur,
                   COALESCE(cp.kategori, 'lainnya') AS kategori,
                   COALESCE(cp.mengandung_susu, 0) AS mengandung_susu,
                   COALESCE(cp.mengandung_telur, 0) AS mengandung_telur,
                   COALESCE(cp.mengandung_kacang, 0) AS mengandung_kacang,
                   COALESCE(cp.mengandung_gluten, 0) AS mengandung_gluten,
                   CASE WHEN cp.produk_id IS NULL THEN 0 ELSE 1 END AS punya_profil
            FROM produk p
            LEFT JOIN customer_es_product_profile cp
                ON cp.produk_id = p.id
            ORDER BY p.nama
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def save_product_profile(produk_id, data):
    produk_id = _int(produk_id, -1)
    coklat = _int(data.get("intensitas_coklat"), -1)
    manis = _int(data.get("tingkat_kemanisan"), -1)
    pahit = _int(data.get("tingkat_kepahitan"), -1)
    tekstur = data.get("tekstur", "")
    kategori = data.get("kategori", "")

    if produk_id <= 0 or any(value < 0 or value > 100 for value in (coklat, manis, pahit)):
        return False, "Nilai intensitas rasa harus berada di antara 0 dan 100."
    if tekstur not in ALLOWED_TEXTURES:
        return False, "Tekstur produk tidak valid."
    if kategori not in ALLOWED_CATEGORIES:
        return False, "Kategori produk tidak valid."

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO customer_es_product_profile
                (produk_id, intensitas_coklat, tingkat_kemanisan,
                 tingkat_kepahitan, tekstur, kategori,
                 mengandung_susu, mengandung_telur,
                 mengandung_kacang, mengandung_gluten, diperbarui_oleh)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                intensitas_coklat = VALUES(intensitas_coklat),
                tingkat_kemanisan = VALUES(tingkat_kemanisan),
                tingkat_kepahitan = VALUES(tingkat_kepahitan),
                tekstur = VALUES(tekstur),
                kategori = VALUES(kategori),
                mengandung_susu = VALUES(mengandung_susu),
                mengandung_telur = VALUES(mengandung_telur),
                mengandung_kacang = VALUES(mengandung_kacang),
                mengandung_gluten = VALUES(mengandung_gluten),
                diperbarui_oleh = VALUES(diperbarui_oleh)
        """, (
            produk_id, coklat, manis, pahit, tekstur, kategori,
            int(data.get("mengandung_susu")),
            int(data.get("mengandung_telur")),
            int(data.get("mengandung_kacang")),
            int(data.get("mengandung_gluten")),
            data.get("diperbarui_oleh"),
        ))
        connection.commit()
        return True, "Profil produk berhasil disimpan."
    except Exception as error:
        connection.rollback()
        print("Error simpan profil ES customer:", error)
        return False, "Profil produk gagal disimpan."
    finally:
        cursor.close()
        connection.close()


def _intensity_range(level):
    return {
        "ringan": (0, 40),
        "sedang": (30, 70),
        "kuat": (60, 100),
    }.get(level, (0, 100))


def _taste_label(taste):
    return {"coklat": "coklat", "manis": "manis", "pahit": "pahit"}[taste]


def recommend_cakes(branch_id, budget, tastes, intensity, texture=None,
                    category=None, allergens=None):
    """Run customer facts through the cake recommendation rule base."""
    branch_id = _int(branch_id, -1)
    budget = _int(budget, 0)
    tastes = [taste for taste in tastes if taste in ALLOWED_TASTES]
    allergens = [allergen for allergen in (allergens or []) if allergen in ALLOWED_ALLERGENS]
    if branch_id <= 0 or budget <= 0:
        return [], "Cabang dan budget wajib dipilih."
    if intensity not in ("ringan", "sedang", "kuat"):
        intensity = "sedang"
    if texture not in ALLOWED_TEXTURES:
        texture = None
    if category not in ALLOWED_CATEGORIES:
        category = None

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.id AS produk_id, p.nama, p.harga,
                   COALESCE(sc.stok, 0) AS stok,
                   cp.intensitas_coklat, cp.tingkat_kemanisan,
                   cp.tingkat_kepahitan, cp.tekstur, cp.kategori,
                   cp.mengandung_susu, cp.mengandung_telur,
                   cp.mengandung_kacang, cp.mengandung_gluten
            FROM produk p
            JOIN customer_es_product_profile cp ON cp.produk_id = p.id
            LEFT JOIN stok_cabang sc
                ON sc.produk_id = p.id AND sc.cabang_id = %s
            ORDER BY p.nama
        """, (branch_id,))
        products = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    results = []
    min_intensity, max_intensity = _intensity_range(intensity)
    total_preference_rules = len(tastes) + bool(texture) + bool(category)

    for product in products:
        # Rule ES-01: a product above the budget is not eligible.
        if product["harga"] > budget:
            continue
        # Rule ES-02: a product unavailable at the selected branch is not eligible.
        if _int(product["stok"]) <= 0:
            continue

        excluded = False
        for allergen in allergens:
            if product[ALLOWED_ALLERGENS[allergen]]:
                excluded = True
                break
        # Rule ES-03: an allergen conflict is a hard exclusion.
        if excluded:
            continue

        matched_rules = [
            f"Harga Rp {product['harga']:,.0f} sesuai budget maksimal Rp {budget:,.0f}",
            f"Stok tersedia {product['stok']} unit di cabang pilihan",
        ]
        explanations = []
        preference_matches = 0

        for taste in tastes:
            value = _int(product[ALLOWED_TASTES[taste]])
            if min_intensity <= value <= max_intensity:
                preference_matches += 1
                matched_rules.append(
                    f"Rasa {_taste_label(taste)} berada pada intensitas {intensity}"
                )
                explanations.append(
                    f"profil {_taste_label(taste)} {value}/100"
                )

        # Rule ES-04: at least one selected taste must match.
        if tastes and preference_matches == 0:
            continue

        if texture:
            if product["tekstur"] != texture:
                continue
            preference_matches += 1
            matched_rules.append(f"Tekstur {texture} sesuai pilihan")
            explanations.append(f"tekstur {texture}")

        if category:
            if product["kategori"] != category:
                continue
            preference_matches += 1
            matched_rules.append(f"Kategori {category} sesuai pilihan")
            explanations.append(f"kategori {category}")

        # The value is a rule-match confidence, not a DSS criterion weight.
        confidence = 100
        if total_preference_rules:
            confidence = round(preference_matches / total_preference_rules * 100)
        results.append({
            "produk_id": product["produk_id"],
            "nama": product["nama"],
            "harga": product["harga"],
            "stok": product["stok"],
            "confidence": confidence,
            "matched_rules": matched_rules,
            "explanation": ", ".join(explanations) or "memenuhi aturan harga dan stok",
        })

    results.sort(key=lambda item: (-item["confidence"], item["harga"], item["nama"]))
    if not results:
        return [], (
            "Belum ada kue yang memenuhi semua aturan. "
            "Coba naikkan budget atau kurangi filter rasa/tekstur."
        )
    return results[:5], None
