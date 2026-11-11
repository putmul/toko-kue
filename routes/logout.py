from flask import redirect, url_for, session


def register(app):
    # =========================
    # LOGOUT
    # =========================

    @app.route("/logout")
    def logout():

        session.clear()

        return redirect(url_for("login"))
