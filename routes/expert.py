from flask import redirect, render_template, request, session, url_for

from service.expert_system import (
    approve_supplier_action,
    evaluate_supplier_product,
    generate_purchase_notifications,
    get_notifications,
    get_supplier_actions,
    get_supplier_evaluations,
    record_supplier_incident,
    run_all_supplier_evaluations,
)
from service.pembelian import get_supplier_produk


def register(app):
    def is_admin():
        return "user" in session and session["user"]["role"] == "admin"

    @app.route("/expert-system")
    def expert_dashboard():
        if not is_admin():
            return "Akses ditolak", 403
        error = None
        try:
            generate_purchase_notifications(session["user"]["id"])
            evaluations = get_supplier_evaluations()
            actions = get_supplier_actions()
            notifications = get_notifications()
            supplier_products = get_supplier_produk()
        except Exception as exception:
            evaluations, actions, notifications, supplier_products = [], [], [], []
            error = str(exception)
        return render_template(
            "expert_dashboard.html", evaluations=evaluations, actions=actions,
            notifications=notifications, supplier_products=supplier_products,
            error=error, user=session["user"]
        )

    @app.route("/expert-system/evaluate", methods=["POST"])
    def expert_evaluate():
        if not is_admin():
            return "Akses ditolak", 403
        try:
            supplier_id = request.form.get("supplier_id")
            produk_id = request.form.get("produk_id")
            if supplier_id and produk_id:
                evaluate_supplier_product(
                    int(supplier_id), int(produk_id), session["user"]["id"]
                )
            else:
                run_all_supplier_evaluations(session["user"]["id"])
        except (TypeError, ValueError) as exception:
            return str(exception), 400
        return redirect(url_for("expert_dashboard"))

    @app.route("/expert-system/action/<int:action_id>/decision", methods=["POST"])
    def expert_action_decision(action_id):
        if not is_admin():
            return "Akses ditolak", 403
        approved = request.form.get("decision") == "disetujui"
        approve_supplier_action(action_id, session["user"]["id"], approved)
        return redirect(url_for("expert_dashboard"))

    @app.route("/expert-system/incident", methods=["POST"])
    def expert_incident():
        if not is_admin():
            return "Akses ditolak", 403
        try:
            pair = request.form.get("supplier_product", "").split("|", 1)
            if len(pair) != 2:
                raise ValueError("Supplier dan produk harus dipilih.")
            record_supplier_incident(
                int(pair[0]), int(pair[1]),
                request.form["jenis"], int(request.form.get("jumlah", 1)),
                request.form.get("keterangan", ""),
                int(request.form["pembelian_id"]) if request.form.get("pembelian_id") else None,
                session["user"]["id"]
            )
            evaluate_supplier_product(
                int(pair[0]), int(pair[1]),
                session["user"]["id"]
            )
        except (KeyError, TypeError, ValueError) as exception:
            return str(exception), 400
        return redirect(url_for("expert_dashboard"))

    @app.route("/expert-system/notification/<int:notification_id>/read", methods=["POST"])
    def expert_notification_read(notification_id):
        if not is_admin():
            return "Akses ditolak", 403
        from model.database import get_connection
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                UPDATE expert_notification
                SET status = 'dibaca', dibaca_pada = NOW()
                WHERE id = %s
            """, (notification_id,))
            connection.commit()
        finally:
            cursor.close()
            connection.close()
        return redirect(url_for("expert_dashboard"))
