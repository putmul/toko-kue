from flask import render_template, request, session, redirect, url_for

from service.cabang import get_semua_cabang
from service.customer_expert import recommend_cakes


def register(app):
    @app.route("/rekomendasi-kue", methods=["GET", "POST"])
    def customer_expert():
        if "user" not in session:
            return redirect(url_for("login"))
        if session["user"]["role"] != "pelanggan":
            return "Akses ditolak", 403

        branches = get_semua_cabang(aktif_saja=True)
        selected_branch = request.form.get(
            "cabang_id", session.get("cabang_id", "")
        )
        try:
            selected_branch = int(selected_branch) if selected_branch else None
        except ValueError:
            selected_branch = None
        valid_branches = {branch["id"] for branch in branches}
        if selected_branch not in valid_branches:
            selected_branch = None

        form = {
            "cabang_id": selected_branch,
            "budget": request.form.get("budget", ""),
            "tastes": request.form.getlist("rasa"),
            "intensity": request.form.get("intensitas", "sedang"),
            "texture": request.form.get("tekstur", ""),
            "category": request.form.get("kategori", ""),
            "allergens": request.form.getlist("alergi"),
        }
        results = []
        error = None
        cart_reset = False

        if request.method == "POST":
            if selected_branch is None:
                error = "Pilih cabang terlebih dahulu."
            else:
                previous_branch = session.get("cabang_id")
                if (
                    previous_branch is not None
                    and previous_branch != selected_branch
                    and session.get("keranjang")
                ):
                    session["keranjang"] = []
                    cart_reset = True
                session["cabang_id"] = selected_branch
                if not error:
                    results, error = recommend_cakes(
                        selected_branch,
                        form["budget"],
                        form["tastes"],
                        form["intensity"],
                        form["texture"],
                        form["category"],
                        form["allergens"],
                    )

        return render_template(
            "customer_expert.html",
            branches=branches,
            form=form,
            results=results,
            error=error,
            cart_reset=cart_reset,
            user=session["user"],
        )
