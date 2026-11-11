from flask import render_template, request, redirect, url_for, session

from service.riwayat_transaksi import lihat_detail_transaksi, lihat_semua_transaksi
from service.kasir import update_status_pesanan, ambil_pesanan
from service.employee import get_employee_for_user


def register(app):
    # =========================
    # KASIR
    # =========================

    @app.route("/kasir")
    def kasir():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "kasir":
            return "Akses ditolak", 403

        employee = get_employee_for_user(session["user"]["id"])
        if not employee or employee["cabang_id"] is None:
            return "Akun kasir belum memiliki employee aktif.", 403

        transaksi = lihat_semua_transaksi(employee["cabang_id"])

        return render_template(
            "kasir.html",
            user=session["user"],
            transaksi=transaksi
        )

    @app.route("/kasir/transaksi/<int:transaksi_id>")
    def kasir_detail_transaksi(transaksi_id):

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "kasir":
            return "Akses ditolak", 403

        employee = get_employee_for_user(session["user"]["id"])
        if not employee or employee["cabang_id"] is None:
            return "Akun kasir belum memiliki employee aktif.", 403

        transaksi = lihat_detail_transaksi(
            transaksi_id,
            cabang_id=employee["cabang_id"]
        )

        if not transaksi:
            return "Transaksi tidak ditemukan.", 404

        return render_template(
            "kasir_detail.html",
            transaksi=transaksi,
            user=session["user"]
        )

    @app.route(
        "/kasir/transaksi/<int:transaksi_id>/status",
        methods=["POST"]
    )
    def kasir_update_status(transaksi_id):

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "kasir":
            return "Akses ditolak", 403

        status_baru = request.form.get("status")

        status_valid = [
            "dikirim",
            "selesai",
            "dibatalkan"
        ]

        if status_baru not in status_valid:
            return "Status tidak valid.", 400

        employee = get_employee_for_user(session["user"]["id"])
        if not employee or employee["cabang_id"] is None:
            return "Akun kasir belum memiliki employee aktif.", 403

        berhasil = update_status_pesanan(
            transaksi_id,
            status_baru,
            employee["id"]
        )

        if not berhasil:
            return (
                "Status tidak dapat diperbarui. "
                "Pastikan status berikutnya valid dan kasir berada di cabang transaksi.",
                400
            )

        return redirect(
            url_for(
                "kasir_detail_transaksi",
                transaksi_id=transaksi_id
            )
        )

    @app.route(
        "/kasir/transaksi/<int:transaksi_id>/ambil",
        methods=["POST"]
    )
    def kasir_ambil_pesanan(transaksi_id):

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "kasir":
            return "Akses ditolak", 403

        berhasil = ambil_pesanan(
            transaksi_id,
            session["user"]["id"]
        )

        if not berhasil:
            return (
                "Pesanan gagal diambil. "
                "Kemungkinan sudah ditangani kasir lain.",
                400
            )

        return redirect(
            url_for(
                "kasir_detail_transaksi",
                transaksi_id=transaksi_id
            )
        )
