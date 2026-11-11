from flask import render_template, request, redirect, url_for, session

from service.produk import (
    tambah_produk, update_stok, get_semua_produk, update_produk,
    hapus_produk, get_stok_produk_per_cabang, distribusikan_stok_bulk
)
from service.riwayat_transaksi import lihat_detail_transaksi, lihat_semua_transaksi
from service.employee import get_employee_for_user


def register(app):
    # =========================
    # ADMIN
    # =========================

    @app.route("/admin")
    def admin():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        return render_template(
            "admin.html",
            user=session["user"]
        )

    @app.route("/admin/produk")
    def admin_produk():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] not in ("admin", "manajer_cabang"):
            return "Akses ditolak", 403

        branch_filter = None
        if session["user"]["role"] == "manajer_cabang":
            employee = get_employee_for_user(session["user"]["id"])
            if not employee or employee["cabang_id"] is None:
                return "Akun manager belum memiliki cabang aktif.", 403
            branch_filter = employee["cabang_id"]

        produk = get_stok_produk_per_cabang(branch_filter)

        return render_template(
            "admin_produk.html",
            produk=produk,
            user=session["user"]
        )


    @app.route("/admin/stok/distribusi", methods=["POST"])
    def admin_distribusi_stok():
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        return "Distribusi stok harus dibuat dari permintaan stok cabang.", 410

        distributions = []
        for field, value in request.form.items():
            if not field.startswith("jumlah_") or not value.strip():
                continue
            try:
                _, produk_id, cabang_id = field.split("_")
                jumlah = int(value)
                distributions.append((int(produk_id), int(cabang_id), jumlah))
            except (ValueError, TypeError):
                return render_template(
                    "admin_produk.html",
                    produk=get_stok_produk_per_cabang(),
                    error="Data distribusi stok tidak valid.",
                    user=session["user"]
                )

        if not distributions:
            return render_template(
                "admin_produk.html",
                produk=get_stok_produk_per_cabang(),
                error="Masukkan minimal satu jumlah distribusi.",
                user=session["user"]
            )

        berhasil, pesan = distribusikan_stok_bulk(distributions)
        if not berhasil:
            return render_template(
                "admin_produk.html",
                produk=get_stok_produk_per_cabang(),
                error=pesan,
                user=session["user"]
            )

        return redirect(url_for("admin_produk"))


    @app.route("/admin/produk/<int:produk_id>/edit", methods=["GET", "POST"])
    def admin_edit_produk(produk_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        produk = next(
            (item for item in get_semua_produk() if item["id"] == produk_id),
            None
        )
        if not produk:
            return "Produk tidak ditemukan.", 404

        if request.method == "POST":
            nama = request.form.get("nama", "").strip()
            try:
                harga = float(request.form["harga"])
            except (KeyError, ValueError):
                harga = -1

            if not nama or harga <= 0:
                return render_template(
                    "admin_edit_produk.html",
                    produk=produk,
                    error="Nama dan harga harus diisi dengan benar.",
                    user=session["user"]
                )

            if update_produk(produk_id, nama, harga):
                return redirect(url_for("admin_produk"))

            return render_template(
                "admin_edit_produk.html",
                produk=produk,
                error="Produk gagal diperbarui.",
                user=session["user"]
            )

        return render_template(
            "admin_edit_produk.html",
            produk=produk,
            user=session["user"]
        )


    @app.route("/admin/produk/<int:produk_id>/hapus", methods=["POST"])
    def admin_hapus_produk(produk_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        berhasil, pesan = hapus_produk(produk_id)
        if not berhasil:
            return render_template(
                "admin_produk.html",
                produk=get_semua_produk(),
                error=pesan,
                user=session["user"]
            )

        return redirect(url_for("admin_produk"))

    @app.route("/admin/produk/tambah", methods=["GET", "POST"])
    def admin_tambah_produk():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        if request.method == "POST":

            nama = request.form["nama"].strip()

            try:
                harga = float(request.form["harga"])
                stok = int(request.form["stok"])
            except ValueError:
                return render_template(
                    "admin_tambah_produk.html",
                    error="Harga dan stok harus berupa angka.",
                    user=session["user"]
                )

            if not nama:
                return render_template(
                    "admin_tambah_produk.html",
                    error="Nama kue wajib diisi.",
                    user=session["user"]
                )

            if harga <= 0:
                return render_template(
                    "admin_tambah_produk.html",
                    error="Harga harus lebih dari 0.",
                    user=session["user"]
                )

            if stok < 0:
                return render_template(
                    "admin_tambah_produk.html",
                    error="Stok tidak boleh negatif.",
                    user=session["user"]
                )

            berhasil = tambah_produk(
                nama,
                harga,
                stok
            )

            if berhasil:
                return redirect(url_for("admin_produk"))

            return render_template(
                "admin_tambah_produk.html",
                error="Gagal menambahkan kue.",
                user=session["user"]
            )

        return render_template(
            "admin_tambah_produk.html",
            user=session["user"]
        )

    @app.route("/admin/stok", methods=["GET", "POST"])
    def admin_stok():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        if request.method == "POST":

            try:
                produk_id = int(request.form["produk_id"])
                stok_baru = int(request.form["stok"])
            except ValueError:
                return render_template(
                    "admin_stok.html",
                    produk=get_semua_produk(),
                    error="ID produk dan stok harus berupa angka.",
                    user=session["user"]
                )

            if stok_baru < 0:
                return render_template(
                    "admin_stok.html",
                    produk=get_semua_produk(),
                    error="Stok tidak boleh negatif.",
                    user=session["user"]
                )

            berhasil = update_stok(
                produk_id,
                stok_baru
            )

            if berhasil:
                return redirect(url_for("admin_stok"))

            return render_template(
                "admin_stok.html",
                produk=get_semua_produk(),
                error="Produk tidak ditemukan.",
                user=session["user"]
            )

        return render_template(
            "admin_stok.html",
            produk=get_semua_produk(),
            user=session["user"]
        )

    @app.route("/admin/transaksi")
    def admin_transaksi():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "manajer_cabang":
            return "Akses ditolak", 403

        cabang_id = None
        if session["user"]["role"] == "manajer_cabang":
            employee = get_employee_for_user(session["user"]["id"])
            if not employee or employee["cabang_id"] is None:
                return "Akun manager belum memiliki employee aktif.", 403
            cabang_id = employee["cabang_id"]

        transaksi = lihat_semua_transaksi(cabang_id)

        return render_template(
            "admin_transaksi.html",
            transaksi=transaksi,
            user=session["user"]
        )

    @app.route("/admin/transaksi/<int:transaksi_id>")
    def admin_detail_transaksi(transaksi_id):

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "manajer_cabang":
            return "Akses ditolak", 403

        cabang_id = None
        if session["user"]["role"] == "manajer_cabang":
            employee = get_employee_for_user(session["user"]["id"])
            if not employee or employee["cabang_id"] is None:
                return "Akun manager belum memiliki employee aktif.", 403
            cabang_id = employee["cabang_id"]

        transaksi = lihat_detail_transaksi(transaksi_id, cabang_id=cabang_id)

        if not transaksi:
            return "Transaksi tidak ditemukan.", 404

        return render_template(
            "admin_detail.html",
            transaksi=transaksi,
            user=session["user"]
        )
