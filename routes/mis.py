from datetime import date, timedelta

from flask import jsonify, request, session

from model.database import get_connection
from service.employee import get_employee_for_user
from service.mis import (
    get_alerts,
    get_branch_comparison,
    get_kpi,
    get_last_refresh,
    get_sales_trend,
    get_stock_monitoring,
    get_top_products,
    refresh_mis_data,
)


def register(app):
    def parse_period():
        today = date.today()
        default_start = today - timedelta(days=29)
        raw_start = request.args.get("start_date")
        raw_end = request.args.get("end_date")

        try:
            start_date = (
                date.fromisoformat(raw_start) if raw_start else default_start
            )
            end_date = date.fromisoformat(raw_end) if raw_end else today
        except ValueError:
            raise ValueError(
                "Format tanggal harus YYYY-MM-DD."
            ) from None

        if start_date > end_date:
            raise ValueError("start_date tidak boleh lebih besar dari end_date.")
        if (end_date - start_date).days > 366:
            raise ValueError("Rentang laporan maksimal 367 hari.")
        return start_date, end_date

    def resolve_scope():
        if "user" not in session:
            return None, (jsonify(error="Anda harus login terlebih dahulu."), 401)

        current_user = session["user"]
        if current_user["role"] not in ("admin", "manajer_cabang"):
            return None, (jsonify(error="Akses MIS hanya untuk admin dan manajer cabang."), 403)

        requested_branch = request.args.get("cabang_id")
        try:
            requested_branch = int(requested_branch) if requested_branch else None
        except ValueError:
            return None, (jsonify(error="cabang_id harus berupa angka."), 400)

        if current_user["role"] == "manajer_cabang":
            employee = get_employee_for_user(current_user["id"])
            if not employee or employee["cabang_id"] is None:
                return None, (jsonify(error="Akun manager belum memiliki cabang aktif."), 403)
            branch_id = employee["cabang_id"]
            if requested_branch is not None and requested_branch != branch_id:
                return None, (jsonify(error="Manager hanya dapat melihat cabangnya sendiri."), 403)
            return branch_id, None

        if requested_branch is not None:
            connection = get_connection()
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT id FROM cabang WHERE id = %s", (requested_branch,))
                if not cursor.fetchone():
                    return None, (jsonify(error="Cabang tidak ditemukan."), 404)
            finally:
                cursor.close()
                connection.close()
        return requested_branch, None

    def dashboard_payload():
        try:
            start_date, end_date = parse_period()
        except ValueError as error:
            return None, (jsonify(error=str(error)), 400)

        branch_id, error_response = resolve_scope()
        if error_response:
            return None, error_response

        # Keep the reporting data current for the frontend.
        refresh_mis_data()
        payload = {
            "filters": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "cabang_id": branch_id,
            },
            "kpi": get_kpi(start_date, end_date, branch_id),
            "sales_trend": get_sales_trend(start_date, end_date, branch_id),
            "top_products": get_top_products(start_date, end_date, branch_id),
            "branch_comparison": get_branch_comparison(
                start_date, end_date, branch_id
            ),
            "stock": get_stock_monitoring(branch_id),
            "alerts": get_alerts(branch_id),
            "meta": {"last_refresh": get_last_refresh()},
        }
        return payload, None

    @app.route("/api/mis/dashboard")
    def mis_dashboard_api():
        try:
            payload, error_response = dashboard_payload()
            if error_response:
                return error_response
            return jsonify(payload)
        except Exception:
            app.logger.exception("Gagal memuat dashboard MIS")
            return jsonify(error="Data dashboard MIS gagal dimuat."), 500

    @app.route("/api/mis/kpi")
    def mis_kpi_api():
        try:
            payload, error_response = dashboard_payload()
            if error_response:
                return error_response
            return jsonify({
                "filters": payload["filters"],
                "kpi": payload["kpi"],
                "meta": payload["meta"],
            })
        except Exception:
            app.logger.exception("Gagal memuat KPI MIS")
            return jsonify(error="KPI MIS gagal dimuat."), 500

    @app.route("/api/mis/grafik-penjualan")
    def mis_sales_chart_api():
        try:
            payload, error_response = dashboard_payload()
            if error_response:
                return error_response
            return jsonify({
                "filters": payload["filters"],
                "data": payload["sales_trend"],
                "meta": payload["meta"],
            })
        except Exception:
            app.logger.exception("Gagal memuat grafik penjualan MIS")
            return jsonify(error="Grafik penjualan gagal dimuat."), 500

    @app.route("/api/mis/produk-terlaris")
    def mis_top_products_api():
        try:
            payload, error_response = dashboard_payload()
            if error_response:
                return error_response
            return jsonify({
                "filters": payload["filters"],
                "data": payload["top_products"],
                "meta": payload["meta"],
            })
        except Exception:
            app.logger.exception("Gagal memuat produk terlaris MIS")
            return jsonify(error="Produk terlaris gagal dimuat."), 500

    @app.route("/api/mis/perbandingan-cabang")
    def mis_branch_comparison_api():
        try:
            payload, error_response = dashboard_payload()
            if error_response:
                return error_response
            return jsonify({
                "filters": payload["filters"],
                "data": payload["branch_comparison"],
                "meta": payload["meta"],
            })
        except Exception:
            app.logger.exception("Gagal memuat perbandingan cabang MIS")
            return jsonify(error="Perbandingan cabang gagal dimuat."), 500

    @app.route("/api/mis/stok")
    def mis_stock_api():
        try:
            payload, error_response = dashboard_payload()
            if error_response:
                return error_response
            return jsonify({
                "filters": payload["filters"],
                "data": payload["stock"],
                "meta": payload["meta"],
            })
        except Exception:
            app.logger.exception("Gagal memuat monitoring stok MIS")
            return jsonify(error="Monitoring stok gagal dimuat."), 500

    @app.route("/api/mis/alerts")
    def mis_alerts_api():
        try:
            payload, error_response = dashboard_payload()
            if error_response:
                return error_response
            return jsonify({
                "filters": payload["filters"],
                "data": payload["alerts"],
                "meta": payload["meta"],
            })
        except Exception:
            app.logger.exception("Gagal memuat alert monitoring MIS")
            return jsonify(error="Alert monitoring gagal dimuat."), 500

    @app.route("/api/mis/alerts/<int:alert_id>/tangani", methods=["POST"])
    def mis_handle_alert_api(alert_id):
        branch_id, error_response = resolve_scope()
        if error_response:
            return error_response

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT id, cabang_id, status
                FROM mis_monitoring_alert
                WHERE id = %s
            """, (alert_id,))
            alert = cursor.fetchone()
            if not alert:
                return jsonify(error="Alert tidak ditemukan."), 404

            if branch_id is not None and alert["cabang_id"] != branch_id:
                return jsonify(error="Alert bukan milik cabang Anda."), 403

            cursor.execute("""
                UPDATE mis_monitoring_alert
                SET status = 'ditangani', ditangani_pada = NOW()
                WHERE id = %s
            """, (alert_id,))
            connection.commit()
            return jsonify(
                message="Alert berhasil ditandai sebagai ditangani.",
                alert_id=alert_id,
                status="ditangani",
            )
        except Exception:
            connection.rollback()
            app.logger.exception("Gagal menangani alert MIS")
            return jsonify(error="Alert gagal diperbarui."), 500
        finally:
            cursor.close()
            connection.close()
