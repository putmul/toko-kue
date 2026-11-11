import re
import unicodedata
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

from model.database import get_connection, get_knowledge_connection


def make_slug(text):
    value = unicodedata.normalize("NFKD", text).encode(
        "ascii", "ignore"
    ).decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "artikel-knowledge"


def _close(cursor, connection):
    cursor.close()
    connection.close()


def get_categories():
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, nama, deskripsi
            FROM km_category
            ORDER BY nama
        """)
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def add_category(nama, deskripsi=None):
    connection = get_knowledge_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO km_category (nama, deskripsi) VALUES (%s, %s)",
            (nama, deskripsi)
        )
        connection.commit()
        return True, "Kategori berhasil ditambahkan."
    except Exception as error:
        connection.rollback()
        print("Error tambah kategori knowledge:", error)
        return False, "Nama kategori sudah digunakan atau data tidak valid."
    finally:
        _close(cursor, connection)


def get_tags():
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, nama FROM km_tag ORDER BY nama")
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def _article_query():
    return """
        SELECT a.*, c.nama AS kategori_nama
        FROM km_article a
        JOIN km_category c ON c.id = a.category_id
    """


def list_articles(
    search=None, status=None, category_id=None,
    visibility=None
):
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = _article_query() + " WHERE 1 = 1"
        params = []
        if search:
            query += " AND (a.judul LIKE %s OR a.ringkasan LIKE %s OR a.isi LIKE %s)"
            term = f"%{search}%"
            params.extend((term, term, term))
        if status:
            query += " AND a.status = %s"
            params.append(status)
        if category_id:
            query += " AND a.category_id = %s"
            params.append(category_id)
        if visibility:
            query += " AND a.visibility = %s"
            params.append(visibility)
        query += " ORDER BY a.updated_at DESC, a.id DESC"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def list_published_articles(role, cabang_id=None, search=None, category_id=None):
    articles = list_articles(search, "published", category_id)
    return [
        item for item in articles
        if can_view_published_article(item, role, cabang_id)
    ]


def can_view_published_article(article, role, cabang_id=None):
    """Apply KMS permissions without creating foreign keys to the main DB."""
    if role == "pelanggan":
        return article["visibility"] == "publik"
    if article["visibility"] == "cabang" and article["related_branch_id"] != cabang_id:
        return False
    if role == "kasir":
        return article["kategori_nama"] in (
            "SOP Operasional", "FAQ dan Troubleshooting"
        )
    if role == "pegawai_produksi":
        return article["kategori_nama"] in (
            "Resep Produksi", "Pelatihan Employee", "SOP Operasional"
        )
    return True


def get_article(article_id=None, slug=None):
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = _article_query()
        if article_id is not None:
            query += " WHERE a.id = %s"
            params = (article_id,)
        else:
            query += " WHERE a.slug = %s"
            params = (slug,)
        cursor.execute(query, params)
        article = cursor.fetchone()
        if not article:
            return None

        main_connection = get_connection()
        main_cursor = main_connection.cursor(dictionary=True)
        try:
            main_cursor.execute("""
                SELECT nama, username, role
                FROM users
                WHERE id = %s
                LIMIT 1
            """, (article["author_user_id"],))
            author = main_cursor.fetchone()
        finally:
            _close(main_cursor, main_connection)

        article["author_name"] = author["nama"] if author else None
        article["author_username"] = author["username"] if author else None
        article["author_role"] = author["role"] if author else None

        cursor.execute("""
            SELECT t.id, t.nama
            FROM km_tag t
            JOIN km_article_tag at ON at.tag_id = t.id
            WHERE at.article_id = %s
            ORDER BY t.nama
        """, (article["id"],))
        article["tags"] = cursor.fetchall()

        cursor.execute("""
            SELECT article_id, hasil_jumlah, hasil_satuan, suhu_oven_celsius,
                   durasi_menit, peralatan, penyimpanan, informasi_alergen
            FROM km_recipe
            WHERE article_id = %s
        """, (article["id"],))
        article["recipe"] = cursor.fetchone()
        if article["recipe"]:
            cursor.execute("""
                SELECT id, nama_bahan, jumlah, satuan, urutan
                FROM km_recipe_ingredient
                WHERE article_id = %s
                ORDER BY urutan, id
            """, (article["id"],))
            article["recipe"]["ingredients"] = cursor.fetchall()

        article["attachments"] = get_attachments(article["id"])
        return article
    finally:
        _close(cursor, connection)


def create_article(data, author_user_id):
    connection = get_knowledge_connection()
    cursor = connection.cursor()
    try:
        slug = make_slug(data["judul"])
        cursor.execute("SELECT id FROM km_article WHERE slug = %s", (slug,))
        if cursor.fetchone():
            slug = f"{slug}-{author_user_id}"

        cursor.execute("""
            INSERT INTO km_article
                (judul, slug, ringkasan, isi, category_id, author_user_id,
                 related_product_id, related_branch_id, visibility, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft')
        """, (
            data["judul"], slug, data["ringkasan"], data["isi"],
            data["category_id"], author_user_id, data["related_product_id"],
            data["related_branch_id"], data["visibility"]
        ))
        article_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO km_article_version
                (article_id, version_number, judul, ringkasan, isi, changed_by_user_id)
            VALUES (%s, 1, %s, %s, %s, %s)
        """, (
            article_id, data["judul"], data["ringkasan"], data["isi"],
            author_user_id
        ))
        _save_tags(cursor, article_id, data.get("tag_ids", []))
        connection.commit()
        return article_id
    except Exception as error:
        connection.rollback()
        print("Error tambah artikel knowledge:", error)
        return None
    finally:
        _close(cursor, connection)


def update_article(article_id, data, editor_user_id):
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT status FROM km_article WHERE id = %s", (article_id,))
        article = cursor.fetchone()
        if not article or article["status"] not in ("draft", "menunggu_review"):
            return False

        cursor.execute("""
            UPDATE km_article
            SET judul = %s, ringkasan = %s, isi = %s, category_id = %s,
                related_product_id = %s, related_branch_id = %s,
                visibility = %s, status = 'draft'
            WHERE id = %s
        """, (
            data["judul"], data["ringkasan"], data["isi"], data["category_id"],
            data["related_product_id"], data["related_branch_id"],
            data["visibility"], article_id
        ))
        cursor.execute("""
            SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version
            FROM km_article_version WHERE article_id = %s
        """, (article_id,))
        next_version = cursor.fetchone()["next_version"]
        cursor.execute("""
            INSERT INTO km_article_version
                (article_id, version_number, judul, ringkasan, isi, changed_by_user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            article_id, next_version, data["judul"], data["ringkasan"],
            data["isi"], editor_user_id
        ))
        _save_tags(cursor, article_id, data.get("tag_ids", []))
        connection.commit()
        return True
    except Exception as error:
        connection.rollback()
        print("Error ubah artikel knowledge:", error)
        return False
    finally:
        _close(cursor, connection)


def _save_tags(cursor, article_id, tag_ids):
    cursor.execute("DELETE FROM km_article_tag WHERE article_id = %s", (article_id,))
    for tag_id in tag_ids:
        try:
            cursor.execute(
                "INSERT INTO km_article_tag (article_id, tag_id) VALUES (%s, %s)",
                (article_id, int(tag_id))
            )
        except (TypeError, ValueError):
            continue


def submit_article(article_id, user_id):
    return _change_status(article_id, "menunggu_review", user_id)


def review_article(article_id, status, reviewer_user_id):
    if status not in ("published", "draft"):
        return False
    return _change_status(article_id, status, reviewer_user_id)


def archive_article(article_id, user_id):
    return _change_status(article_id, "archived", user_id)


def _change_status(article_id, status, user_id):
    connection = get_knowledge_connection()
    cursor = connection.cursor()
    try:
        if status == "published":
            cursor.execute("""
                UPDATE km_article
                SET status = %s, published_by_user_id = %s, published_at = NOW()
                WHERE id = %s AND status = 'menunggu_review'
            """, (status, user_id, article_id))
        elif status == "draft":
            cursor.execute("""
                UPDATE km_article
                SET status = 'draft', published_by_user_id = NULL, published_at = NULL
                WHERE id = %s AND status = 'menunggu_review'
            """, (article_id,))
        else:
            cursor.execute(
                "UPDATE km_article SET status = %s WHERE id = %s",
                (status, article_id)
            )
        if cursor.rowcount == 0:
            return False
        connection.commit()
        return True
    except Exception as error:
        connection.rollback()
        print("Error status artikel knowledge:", error)
        return False
    finally:
        _close(cursor, connection)


def get_versions(article_id):
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, article_id, version_number, judul, ringkasan, isi,
                   changed_by_user_id, created_at
            FROM km_article_version
            WHERE article_id = %s
            ORDER BY version_number DESC
        """, (article_id,))
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def save_recipe(article_id, data):
    connection = get_knowledge_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO km_recipe
                (article_id, hasil_jumlah, hasil_satuan, suhu_oven_celsius,
                 durasi_menit, peralatan, penyimpanan, informasi_alergen)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                hasil_jumlah = VALUES(hasil_jumlah),
                hasil_satuan = VALUES(hasil_satuan),
                suhu_oven_celsius = VALUES(suhu_oven_celsius),
                durasi_menit = VALUES(durasi_menit),
                peralatan = VALUES(peralatan),
                penyimpanan = VALUES(penyimpanan),
                informasi_alergen = VALUES(informasi_alergen)
        """, (
            article_id, data.get("hasil_jumlah") or None,
            data.get("hasil_satuan") or None, data.get("suhu_oven_celsius") or None,
            data.get("durasi_menit") or None, data.get("peralatan") or None,
            data.get("penyimpanan") or None, data.get("informasi_alergen") or None
        ))
        cursor.execute("DELETE FROM km_recipe_ingredient WHERE article_id = %s", (article_id,))
        for index, ingredient in enumerate(data.get("ingredients", []), start=1):
            if not ingredient.get("nama_bahan"):
                continue
            cursor.execute("""
                INSERT INTO km_recipe_ingredient
                    (article_id, nama_bahan, jumlah, satuan, urutan)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                article_id, ingredient["nama_bahan"], ingredient.get("jumlah") or None,
                ingredient.get("satuan") or None, index
            ))
        connection.commit()
        return True
    except Exception as error:
        connection.rollback()
        print("Error simpan resep knowledge:", error)
        return False
    finally:
        _close(cursor, connection)


def delete_recipe(article_id):
    connection = get_knowledge_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM km_recipe WHERE article_id = %s", (article_id,))
        connection.commit()
        return True
    except Exception as error:
        connection.rollback()
        print("Error hapus resep knowledge:", error)
        return False
    finally:
        _close(cursor, connection)


ALLOWED_ATTACHMENT_EXTENSIONS = {
    "jpg", "jpeg", "png", "webp", "gif",
    "mp4", "webm", "mov",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"
}
MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024


def _attachment_directory():
    directory = Path(__file__).resolve().parent.parent / "static" / "uploads" / "knowledge"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_attachments(article_id):
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, article_id, nama_file, path_file, tipe_file,
                   uploaded_by_user_id, created_at
            FROM km_attachment
            WHERE article_id = %s
            ORDER BY created_at DESC, id DESC
        """, (article_id,))
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def get_attachment(attachment_id):
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, article_id, nama_file, path_file, tipe_file,
                   uploaded_by_user_id, created_at
            FROM km_attachment WHERE id = %s
        """, (attachment_id,))
        return cursor.fetchone()
    finally:
        _close(cursor, connection)


def save_attachment(article_id, uploaded_file, user_id):
    if not uploaded_file or not uploaded_file.filename:
        return False, "Pilih file terlebih dahulu."
    original_name = secure_filename(uploaded_file.filename)
    if not original_name or "." not in original_name:
        return False, "Nama atau tipe file tidak valid."
    extension = original_name.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        return False, "Tipe file belum didukung."

    stream = uploaded_file.stream
    stream.seek(0, 2)
    file_size = stream.tell()
    stream.seek(0)
    if file_size > MAX_ATTACHMENT_SIZE:
        return False, "Ukuran file maksimal 25 MB."

    stored_name = f"{uuid.uuid4().hex}.{extension}"
    directory = _attachment_directory()
    destination = directory / stored_name
    uploaded_file.save(destination)
    connection = get_knowledge_connection()
    cursor = connection.cursor()
    try:
        relative_path = f"uploads/knowledge/{stored_name}"
        cursor.execute("""
            INSERT INTO km_attachment
                (article_id, nama_file, path_file, tipe_file, uploaded_by_user_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            article_id, original_name, relative_path,
            uploaded_file.mimetype or extension, user_id
        ))
        connection.commit()
        return True, "File berhasil diunggah."
    except Exception as error:
        connection.rollback()
        destination.unlink(missing_ok=True)
        print("Error upload attachment knowledge:", error)
        return False, "File gagal disimpan."
    finally:
        _close(cursor, connection)


def remove_attachment(attachment_id):
    attachment = get_attachment(attachment_id)
    if not attachment:
        return False
    connection = get_knowledge_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM km_attachment WHERE id = %s", (attachment_id,))
        connection.commit()
        file_path = Path(__file__).resolve().parent.parent / "static" / attachment["path_file"]
        try:
            file_path.unlink(missing_ok=True)
        except PermissionError:
            # Windows can briefly keep a downloaded response open. The
            # database record is already removed and the file can be cleaned
            # by the next maintenance run without exposing it in the UI.
            print("File attachment masih digunakan dan akan dibersihkan kemudian.")
        return True
    except Exception as error:
        connection.rollback()
        print("Error hapus attachment knowledge:", error)
        return False
    finally:
        _close(cursor, connection)


def save_feedback(article_id, user_id, membantu, komentar):
    connection = get_knowledge_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO km_feedback (article_id, user_id, membantu, komentar)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE membantu = VALUES(membantu), komentar = VALUES(komentar)
        """, (article_id, user_id, membantu, komentar or None))
        connection.commit()
        return True
    except Exception as error:
        connection.rollback()
        print("Error feedback knowledge:", error)
        return False
    finally:
        _close(cursor, connection)


def get_feedback(article_id):
    connection = get_knowledge_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT membantu, komentar, user_id, created_at
            FROM km_feedback WHERE article_id = %s
            ORDER BY created_at DESC
        """, (article_id,))
        return cursor.fetchall()
    finally:
        _close(cursor, connection)


def get_branch_id_for_user(user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT cabang_id FROM employee
            WHERE user_id = %s AND status = 'aktif'
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        return row["cabang_id"] if row else None
    finally:
        _close(cursor, connection)
