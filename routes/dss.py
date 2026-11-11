from flask import jsonify, redirect, render_template, request, session, url_for

from service.dss_pengadaan import (
    calculate_recommendation,
    get_dss_branches,
    get_dss_products,
    get_recommendation_for_purchase,
    get_stock_summary,
    get_supplier_alternatives,
)
from service.dss_setting import get_dss_criteria, save_dss_criteria


def _is_admin():
    return "user" in session and session["user"]["role"] == "admin"


def register(app):
    @app.route("/dss/pengadaan", methods=["GET", "POST"])
    def dss_pengadaan():
        if not _is_admin():
            return "Akses ditolak", 403

        products = get_dss_products()
        branches = get_dss_branches()
        criteria = get_dss_criteria()
        result = None
        error = None
        form = {
            "produk_id": request.form.get("produk_id", ""),
            "jumlah_kebutuhan": request.form.get("jumlah_kebutuhan", ""),
            "cabang_id": request.form.get("cabang_id", ""),
        }
        if request.method == "POST":
            try:
                result = calculate_recommendation(
                    form["produk_id"], form["jumlah_kebutuhan"],
                    form["cabang_id"], session["user"]["id"]
                )
            except (ValueError, TypeError) as exception:
                error = str(exception)
        return render_template(
            "dss_pengadaan.html", products=products, branches=branches,
            criteria=criteria, result=result, error=error, form=form,
            user=session["user"]
        )

    @app.route("/dss/pengaturan", methods=["GET", "POST"])
    def dss_pengaturan():
        if not _is_admin():
            return "Akses ditolak", 403
        error = None
        success = None
        criteria = get_dss_criteria()
        if request.method == "POST":
            values = {}
            for item in criteria:
                code = item["kode_kriteria"]
                values[code] = {
                    "bobot": request.form.get(f"bobot_{code}", "0"),
                    "aktif": request.form.get(f"aktif_{code}") == "1",
                }
            try:
                save_dss_criteria(values, session["user"]["id"])
                success = "Pengaturan kriteria berhasil disimpan."
                criteria = get_dss_criteria()
            except (ValueError, TypeError) as exception:
                error = str(exception)
        return render_template(
            "dss_pengaturan.html", criteria=criteria, error=error,
            success=success, user=session["user"]
        )

    @app.route("/api/dss/stok/<int:produk_id>")
    def dss_stock_api(produk_id):
        if not _is_admin():
            return jsonify(error="Akses ditolak."), 403
        raw_branch = request.args.get("cabang_id")
        try:
            branch_id = int(raw_branch) if raw_branch else None
            return jsonify(get_stock_summary(produk_id, branch_id))
        except (ValueError, TypeError) as exception:
            return jsonify(error=str(exception)), 400

    @app.route("/api/dss/supplier/<int:produk_id>")
    def dss_supplier_api(produk_id):
        if not _is_admin():
            return jsonify(error="Akses ditolak."), 403
        return jsonify(get_supplier_alternatives(produk_id))

    @app.route("/dss/pengadaan/<int:recommendation_id>/gunakan")
    def dss_use_recommendation(recommendation_id):
        if not _is_admin():
            return "Akses ditolak", 403
        recommendation = get_recommendation_for_purchase(recommendation_id)
        if not recommendation:
            return "Rekomendasi tidak ditemukan.", 404
        session["dss_prefill"] = {
            "supplier_id": recommendation["supplier_terpilih_id"],
            "produk_id": recommendation["produk_id"],
            "jumlah": recommendation["jumlah_pembelian"],
        }
        return redirect(url_for("tambah_pembelian_route"))
