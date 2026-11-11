from flask import render_template, request, redirect, url_for, session

from model.user import login_user, register_user


def register(app):
    @app.route("/")
    def index():
        return redirect(url_for("login"))


    # =========================
    # LOGIN
    # =========================

    @app.route("/login", methods=["GET", "POST"])
    def login():

        if request.method == "POST":

            username = request.form["username"]
            password = request.form["password"]

            user = login_user(username, password)

            if user:
                session["user"] = user

                if user["role"] == "admin":
                    return redirect(url_for("admin"))

                elif user["role"] == "kasir":
                    return redirect(url_for("kasir"))

                elif user["role"] == "manajer_cabang":
                    return redirect(url_for("manajer"))

                elif user["role"] == "pegawai_produksi":
                    return redirect(url_for("knowledge_index"))

                else:
                    return redirect(url_for("katalog"))

            return render_template(
                "login.html",
                error="Username atau password salah."
            )

        return render_template("login.html")


    # =========================
    # REGISTER
    # =========================

    @app.route("/register", methods=["GET", "POST"])
    def register():

        if request.method == "POST":

            nama = request.form["nama"]
            username = request.form["username"]
            password = request.form["password"]

            berhasil, pesan = register_user(
                nama,
                username,
                password
            )

            if berhasil:
                return redirect(url_for("login"))

            return render_template(
                "register.html",
                error=pesan
            )

        return render_template("register.html")


    # =========================
    # KATALOG
    # =========================
