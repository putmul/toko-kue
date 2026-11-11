from flask import render_template, request, redirect, url_for, session

from service.produk import get_semua_produk
from service.checkout import buat_transaksi
from service.riwayat_transaksi import lihat_riwayat_transaksi, lihat_detail_transaksi
from service.cabang import get_semua_cabang


def register(app):
    @app.route("/katalog")
    def katalog():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "pelanggan":
            return "Akses ditolak", 403

        cabang = get_semua_cabang(aktif_saja=True)
        selected_cabang = request.args.get("cabang_id", session.get("cabang_id"))
        try:
            selected_cabang = int(selected_cabang) if selected_cabang is not None else None
        except ValueError:
            selected_cabang = None

        valid_cabang = {item["id"] for item in cabang}
        if selected_cabang not in valid_cabang:
            selected_cabang = None

        keranjang_dikosongkan = False
        previous_cabang = session.get("cabang_id")
        if (
            selected_cabang is not None
            and previous_cabang is not None
            and previous_cabang != selected_cabang
            and session.get("keranjang")
        ):
            session["keranjang"] = []
            keranjang_dikosongkan = True

        if selected_cabang is not None:
            session["cabang_id"] = selected_cabang

        produk = get_semua_produk(selected_cabang)

        return render_template(
            "katalog.html",
            produk=produk,
            cabang=cabang,
            cabang_id=selected_cabang,
            keranjang_dikosongkan=keranjang_dikosongkan,
            user=session["user"]
        )

    @app.route(
        "/keranjang/tambah/<int:produk_id>",
        methods=["POST"]
    )
    def tambah_keranjang(produk_id):

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "pelanggan":
            return "Akses ditolak", 403

        cabang_id = session.get("cabang_id")
        if cabang_id is None:
            return "Pilih cabang terlebih dahulu dari halaman katalog.", 400

        produk = get_semua_produk(cabang_id)

        produk_dipilih = None

        for item in produk:

            if item["id"] == produk_id:
                produk_dipilih = item
                break

        if not produk_dipilih:
            return "Produk tidak ditemukan.", 404

        keranjang = session.get("keranjang", [])

        # Cek apakah produk sudah ada
        for item in keranjang:

            if item["produk_id"] == produk_id:

                if item["jumlah"] + 1 > produk_dipilih["stok"]:
                    return "Jumlah melebihi stok.", 400

                item["jumlah"] += 1

                session["keranjang"] = keranjang

                return redirect(url_for("keranjang"))

        # Produk baru
        keranjang.append({
            "produk_id": produk_id,
            "nama": produk_dipilih["nama"],
            "harga": float(produk_dipilih["harga"]),
            "jumlah": 1
        })

        session["keranjang"] = keranjang

        return redirect(url_for("keranjang"))

    @app.route("/keranjang")
    def keranjang():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "pelanggan":
            return "Akses ditolak", 403

        keranjang = session.get("keranjang", [])
        cabang_id = session.get("cabang_id")
        cabang = get_semua_cabang(aktif_saja=True)
        cabang_nama = next(
            (item["nama"] for item in cabang if item["id"] == cabang_id),
            "Belum dipilih"
        )

        return render_template(
            "keranjang.html",
            keranjang=keranjang,
            cabang_id=cabang_id,
            cabang_nama=cabang_nama,
            user=session["user"]
        )

    @app.route(
        "/keranjang/hapus/<int:produk_id>",
        methods=["POST"]
    )
    def hapus_keranjang(produk_id):

        if "user" not in session:
            return redirect(url_for("login"))

        keranjang = session.get("keranjang", [])

        keranjang = [
            item
            for item in keranjang
            if item["produk_id"] != produk_id
        ]

        session["keranjang"] = keranjang

        return redirect(url_for("keranjang"))

    @app.route(
        "/checkout",
        methods=["POST"]
    )
    def checkout():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "pelanggan":
            return "Akses ditolak", 403

        keranjang = session.get("keranjang", [])

        if not keranjang:
            return "Keranjang kosong.", 400

        cabang_id = session.get("cabang_id")
        if cabang_id is None:
            return "Cabang transaksi wajib dipilih.", 400

        active_branch_ids = {
            item["id"] for item in get_semua_cabang(aktif_saja=True)
        }
        if cabang_id not in active_branch_ids:
            return "Cabang tidak valid atau sudah nonaktif.", 400

        session["cabang_id"] = cabang_id

        items = []

        for item in keranjang:

            items.append({
                "produk_id": item["produk_id"],
                "jumlah": item["jumlah"]
            })

        transaksi_id = buat_transaksi(
            session["user"]["id"],
            items,
            cabang_id
        )

        if not transaksi_id:
            return (
                "Checkout gagal. "
                "Kemungkinan stok tidak mencukupi.",
                400
            )

        # Keranjang dikosongkan setelah checkout berhasil
        session["keranjang"] = []

        return redirect(
            url_for(
                "invoice",
                transaksi_id=transaksi_id
            )
        )

    @app.route("/invoice/<int:transaksi_id>")
    def invoice(transaksi_id):

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "pelanggan":
            return "Akses ditolak", 403

        transaksi = lihat_detail_transaksi(
            transaksi_id,
            session["user"]["id"]
        )

        if not transaksi:
            return "Transaksi tidak ditemukan.", 404

        return render_template(
            "invoice.html",
            transaksi=transaksi,
            user=session["user"]
        )

    @app.route("/riwayat")
    def riwayat():

        if "user" not in session:
            return redirect(url_for("login"))

        if session["user"]["role"] != "pelanggan":
            return "Akses ditolak", 403

        transaksi = lihat_riwayat_transaksi(
            session["user"]["id"]
        )

        return render_template(
            "riwayat.html",
            transaksi=transaksi,
            user=session["user"]
        )
