from flask import (
    render_template, request, redirect, url_for, session,
    send_from_directory
)

from service.cabang import get_semua_cabang
from service.knowledge import (
    add_category, archive_article, can_view_published_article,
    create_article, delete_recipe, get_article, get_attachment,
    get_branch_id_for_user, get_categories, get_feedback, get_tags,
    get_versions, list_articles, list_published_articles, remove_attachment,
    review_article, save_attachment, save_feedback, save_recipe,
    submit_article, update_article
)
from service.produk import get_semua_produk


def register(app):
    def logged_in():
        return "user" in session

    def user():
        return session.get("user")

    def is_admin():
        return logged_in() and user()["role"] == "admin"

    def can_manage():
        return logged_in() and user()["role"] in (
            "admin", "manajer_cabang", "pegawai_produksi"
        )

    def manager_branch_id():
        if user()["role"] not in ("manajer_cabang", "pegawai_produksi"):
            return None
        return get_branch_id_for_user(user()["id"])

    def can_read(article):
        if not article:
            return False
        current = user()
        if current["role"] == "admin":
            return True
        if article["status"] != "published":
            return (
                article["author_user_id"] == current["id"]
                and current["role"] in ("manajer_cabang", "pegawai_produksi")
            )
        return can_view_published_article(
            article, current["role"], manager_branch_id()
        )

    def can_modify_article(article):
        return (
            article
            and can_manage()
            and (is_admin() or article["author_user_id"] == user()["id"])
        )

    def can_author_category(category_id):
        if is_admin():
            return True
        category = next(
            (item for item in get_categories() if item["id"] == category_id),
            None
        )
        if not category:
            return False
        if user()["role"] == "pegawai_produksi":
            return category["nama"] in (
                "Resep Produksi", "Pelatihan Employee", "SOP Operasional"
            )
        return True

    def article_form_data():
        try:
            category_id = int(request.form["category_id"])
        except (KeyError, TypeError, ValueError):
            category_id = None
        try:
            product_id = int(request.form["related_product_id"])
        except (KeyError, TypeError, ValueError):
            product_id = None
        try:
            branch_id = int(request.form["related_branch_id"])
        except (KeyError, TypeError, ValueError):
            branch_id = None
        if user()["role"] in ("manajer_cabang", "pegawai_produksi"):
            branch_id = manager_branch_id()
        visibility = request.form.get("visibility", "internal")
        ingredients = []
        names = request.form.getlist("bahan_nama")
        quantities = request.form.getlist("bahan_jumlah")
        units = request.form.getlist("bahan_satuan")
        for index, name in enumerate(names):
            ingredients.append({
                "nama_bahan": name.strip(),
                "jumlah": quantities[index].strip() if index < len(quantities) else "",
                "satuan": units[index].strip() if index < len(units) else ""
            })
        return {
            "judul": request.form.get("judul", "").strip(),
            "ringkasan": request.form.get("ringkasan", "").strip() or None,
            "isi": request.form.get("isi", "").strip(),
            "category_id": category_id,
            "related_product_id": product_id,
            "related_branch_id": branch_id,
            "visibility": visibility,
            "tag_ids": request.form.getlist("tag_ids"),
            "tags": [],
            "recipe_enabled": request.form.get("is_recipe") == "1" or category_id == 1,
            "recipe": {
                "hasil_jumlah": request.form.get("hasil_jumlah", "").strip(),
                "hasil_satuan": request.form.get("hasil_satuan", "").strip(),
                "suhu_oven_celsius": request.form.get("suhu_oven_celsius", "").strip(),
                "durasi_menit": request.form.get("durasi_menit", "").strip(),
                "peralatan": request.form.get("peralatan", "").strip(),
                "penyimpanan": request.form.get("penyimpanan", "").strip(),
                "informasi_alergen": request.form.get("informasi_alergen", "").strip(),
                "ingredients": ingredients
            }
        }

    def render_form(article=None, error=None):
        return render_template(
            "knowledge_form.html",
            article=article,
            categories=get_categories(),
            tags=get_tags(),
            produk=get_semua_produk(),
            cabang=get_semua_cabang(aktif_saja=True),
            error=error,
            user=user()
        )

    @app.route("/knowledge")
    def knowledge_index():
        if not logged_in():
            return redirect(url_for("login"))

        search = request.args.get("q", "").strip() or None
        status = request.args.get("status") or None
        category_id = request.args.get("category_id", type=int)
        visibility = request.args.get("visibility") or None
        current = user()
        if current["role"] == "admin":
            articles = list_articles(
                search, status, category_id, visibility
            )
        else:
            articles = list_published_articles(
                current["role"], manager_branch_id(), search, category_id
            )
            if current["role"] in ("manajer_cabang", "pegawai_produksi"):
                own = list_articles(search, None, category_id)
                articles += [
                    item for item in own
                    if item["author_user_id"] == current["id"]
                    and item["status"] in ("draft", "menunggu_review")
                ]

        unique = {item["id"]: item for item in articles}
        return render_template(
            "knowledge.html",
            articles=list(unique.values()),
            categories=get_categories(),
            search=search or "",
            selected_category=category_id,
            selected_status=status,
            selected_visibility=visibility,
            can_manage=can_manage(),
            user=current
        )

    @app.route("/knowledge/<slug>")
    def knowledge_detail(slug):
        if not logged_in():
            return redirect(url_for("login"))
        article = get_article(slug=slug)
        if not article:
            return "Artikel tidak ditemukan.", 404
        if not can_read(article):
            return "Akses ditolak", 403
        return render_template(
            "knowledge_detail.html",
            article=article,
            versions=get_versions(article["id"]),
            feedback=get_feedback(article["id"]),
            user=user(),
            can_review=is_admin() and article["status"] == "menunggu_review",
            can_edit=can_modify_article(article)
        )

    @app.route("/knowledge/tambah", methods=["GET", "POST"])
    def knowledge_add():
        if not can_manage():
            return "Akses ditolak", 403
        if request.method == "POST":
            data = article_form_data()
            if not data["judul"] or not data["isi"] or not data["category_id"]:
                return render_form(data, "Judul, isi, dan kategori wajib diisi.")
            if not can_author_category(data["category_id"]):
                return render_form(data, "Role Anda tidak memiliki akses membuat artikel pada kategori ini.")
            if user()["role"] in ("manajer_cabang", "pegawai_produksi") and not data["related_branch_id"]:
                return render_form(data, "Akun belum memiliki cabang aktif.")
            article_id = create_article(data, user()["id"])
            if article_id:
                if data["recipe_enabled"]:
                    save_recipe(article_id, data["recipe"])
                for uploaded_file in request.files.getlist("attachments"):
                    if uploaded_file and uploaded_file.filename:
                        save_attachment(article_id, uploaded_file, user()["id"])
                return redirect(url_for("knowledge_detail", slug=get_article(article_id=article_id)["slug"]))
            return render_form(data, "Artikel gagal disimpan.")
        return render_form()

    @app.route("/knowledge/<int:article_id>/edit", methods=["GET", "POST"])
    def knowledge_edit(article_id):
        if not can_manage():
            return "Akses ditolak", 403
        article = get_article(article_id=article_id)
        if not article:
            return "Artikel tidak ditemukan.", 404
        if not can_modify_article(article):
            return "Akses ditolak", 403
        if request.method == "POST":
            data = article_form_data()
            if not data["judul"] or not data["isi"] or not data["category_id"]:
                return render_form(data, "Judul, isi, dan kategori wajib diisi.")
            if not can_author_category(data["category_id"]):
                return render_form(data, "Role Anda tidak memiliki akses membuat artikel pada kategori ini.")
            if update_article(article_id, data, user()["id"]):
                if data["recipe_enabled"]:
                    save_recipe(article_id, data["recipe"])
                else:
                    delete_recipe(article_id)
                for uploaded_file in request.files.getlist("attachments"):
                    if uploaded_file and uploaded_file.filename:
                        save_attachment(article_id, uploaded_file, user()["id"])
                return redirect(url_for("knowledge_detail", slug=get_article(article_id=article_id)["slug"]))
            return render_form(data, "Artikel hanya dapat diubah saat draft atau menunggu review.")
        return render_form(article)

    @app.route("/knowledge/<int:article_id>/submit", methods=["POST"])
    def knowledge_submit(article_id):
        if not can_manage():
            return "Akses ditolak", 403
        article = get_article(article_id=article_id)
        if not article or not can_modify_article(article):
            return "Akses ditolak", 403
        if not submit_article(article_id, user()["id"]):
            return "Artikel hanya dapat diajukan dari status draft.", 400
        return redirect(url_for("knowledge_detail", slug=article["slug"]))

    @app.route("/knowledge/<int:article_id>/review", methods=["POST"])
    def knowledge_review(article_id):
        if not is_admin():
            return "Akses ditolak", 403
        status = request.form.get("status")
        if not review_article(article_id, status, user()["id"]):
            return "Review artikel gagal.", 400
        return redirect(url_for("knowledge_index", status="menunggu_review"))

    @app.route("/knowledge/<int:article_id>/archive", methods=["POST"])
    def knowledge_archive(article_id):
        if not is_admin():
            return "Akses ditolak", 403
        if not archive_article(article_id, user()["id"]):
            return "Artikel tidak dapat diarsipkan.", 400
        return redirect(url_for("knowledge_index"))

    @app.route("/knowledge/<int:article_id>/feedback", methods=["POST"])
    def knowledge_feedback(article_id):
        if not logged_in():
            return redirect(url_for("login"))
        article = get_article(article_id=article_id)
        if not can_read(article) or article["status"] != "published":
            return "Akses ditolak", 403
        membantu = request.form.get("membantu") == "1"
        save_feedback(
            article_id, user()["id"], membantu,
            request.form.get("komentar", "").strip()
        )
        return redirect(url_for("knowledge_detail", slug=article["slug"]))

    @app.route("/knowledge/<int:article_id>/attachment", methods=["POST"])
    def knowledge_upload_attachment(article_id):
        article = get_article(article_id=article_id)
        if not can_modify_article(article) or article["status"] == "archived":
            return "Akses ditolak", 403
        berhasil, pesan = save_attachment(
            article_id, request.files.get("attachment"), user()["id"]
        )
        if not berhasil:
            return render_template(
                "knowledge_detail.html", article=article,
                versions=get_versions(article_id), feedback=get_feedback(article_id),
                user=user(), can_review=False, can_edit=True, error=pesan
            ), 400
        return redirect(url_for("knowledge_detail", slug=article["slug"]))

    @app.route("/knowledge/attachment/<int:attachment_id>")
    def knowledge_attachment(attachment_id):
        if not logged_in():
            return redirect(url_for("login"))
        attachment = get_attachment(attachment_id)
        if not attachment:
            return "File tidak ditemukan.", 404
        article = get_article(article_id=attachment["article_id"])
        if not can_read(article):
            return "Akses ditolak", 403
        return send_from_directory(
            app.static_folder,
            attachment["path_file"],
            download_name=attachment["nama_file"]
        )

    @app.route("/knowledge/attachment/<int:attachment_id>/hapus", methods=["POST"])
    def knowledge_delete_attachment(attachment_id):
        if not logged_in():
            return redirect(url_for("login"))
        attachment = get_attachment(attachment_id)
        article = get_article(article_id=attachment["article_id"]) if attachment else None
        if not can_modify_article(article):
            return "Akses ditolak", 403
        slug = article["slug"]
        if not remove_attachment(attachment_id):
            return "File gagal dihapus.", 400
        return redirect(url_for("knowledge_detail", slug=slug))

    @app.route("/knowledge/kategori", methods=["GET", "POST"])
    def knowledge_categories():
        if not is_admin():
            return "Akses ditolak", 403
        error = None
        if request.method == "POST":
            nama = request.form.get("nama", "").strip()
            deskripsi = request.form.get("deskripsi", "").strip() or None
            if not nama:
                error = "Nama kategori wajib diisi."
            else:
                berhasil, pesan = add_category(nama, deskripsi)
                if berhasil:
                    return redirect(url_for("knowledge_categories"))
                error = pesan
        return render_template(
            "knowledge_categories.html",
            categories=get_categories(),
            error=error,
            user=user()
        )
