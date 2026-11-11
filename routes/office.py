from flask import render_template, request, redirect, url_for, session

from service.produk import get_semua_produk
from service.rekap import (
    laporan_pendapatan_harian, detail_pendapatan_harian,
    get_transaksi_untuk_rekap, simpan_rekap_transaksi,
    get_detail_rekap
)
from service.supplier import get_semua_supplier, update_supplier, tambah_supplier
from service.cabang import tambah_cabang, get_semua_cabang, update_cabang
from service.employee import (
    get_semua_employee, get_employee, update_employee, tambah_employee,
    get_employee_for_user
)
from service.permintaan_stok import (
    get_semua_permintaan_stok, buat_permintaan_stok,
    update_status_permintaan_stok
)
from service.pembelian import (
    get_semua_pembelian, get_supplier_produk,
    buat_pembelian_supplier, update_status_pembelian
)
from service.distribusi_stok import (
    get_semua_distribusi, get_distribusi_detail,
    buat_distribusi_stok, update_status_distribusi
)


def register(app):
    # =========================
    # OFFICE OPERATIONS
    # =========================

    def is_office_staff():
        return (
            "user" in session
            and session["user"]["role"] in ("admin", "manajer_cabang")
        )


    @app.route("/manajer")
    def manajer():
        if not is_office_staff() or session["user"]["role"] != "manajer_cabang":
            return "Akses ditolak", 403

        return render_template(
            "manajer.html",
            user=session["user"]
        )


    @app.route("/laporan/pendapatan")
    def laporan_pendapatan():
        if not is_office_staff():
            return redirect(url_for("login"))

        cabang_id = None
        if session["user"]["role"] == "manajer_cabang":
            employee = get_employee_for_user(session["user"]["id"])
            if not employee or employee["cabang_id"] is None:
                return "Akun manager belum memiliki employee aktif.", 403
            cabang_id = employee["cabang_id"]

            return render_template(
                "laporan_pendapatan.html",
                transaksi=get_transaksi_untuk_rekap(cabang_id, hanya_belum=True),
                laporan=laporan_pendapatan_harian(cabang_id),
                user=session["user"]
            )

        return render_template(
            "laporan_pendapatan.html",
            laporan=laporan_pendapatan_harian(cabang_id),
            user=session["user"]
        )


    @app.route("/laporan/pendapatan/<int:cabang_id>/<tanggal>")
    def detail_laporan_pendapatan(cabang_id, tanggal):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        transaksi = detail_pendapatan_harian(cabang_id, tanggal)
        return render_template(
            "detail_laporan_pendapatan.html",
            transaksi=transaksi,
            tanggal=tanggal,
            user=session["user"]
        )


    @app.route("/rekap-transaksi")
    def rekap_transaksi():
        if "user" not in session or session["user"]["role"] != "manajer_cabang":
            return "Akses ditolak", 403

        employee = get_employee_for_user(session["user"]["id"])
        if not employee or employee["cabang_id"] is None:
            return "Akun manager belum memiliki cabang aktif.", 403

        return render_template(
            "rekap_transaksi.html",
            transaksi=get_transaksi_untuk_rekap(
                employee["cabang_id"],
                hanya_sudah=True
            ),
            user=session["user"]
        )


    @app.route("/rekap-transaksi/simpan", methods=["POST"])
    def simpan_rekap_transaksi_route():
        if "user" not in session or session["user"]["role"] != "manajer_cabang":
            return "Akses ditolak", 403

        employee = get_employee_for_user(session["user"]["id"])
        if not employee or employee["cabang_id"] is None:
            return "Akun manager belum memiliki cabang aktif.", 403

        transaction_ids = request.form.getlist("selected_ids")
        if not transaction_ids:
            transaction_ids = request.form.getlist("transaksi_ids")
        failed_ids = set(request.form.getlist("dibatalkan_ids"))
        entries = []

        try:
            for transaction_id in transaction_ids:
                transaction_id = int(transaction_id)
                status_rekap = (
                    "dibatalkan"
                    if str(transaction_id) in failed_ids
                    else "berhasil"
                )
                entries.append((
                    transaction_id,
                    status_rekap,
                    request.form.get(f"catatan_{transaction_id}", "").strip() or None
                ))
        except ValueError:
            return "Data rekap tidak valid.", 400

        if not entries:
            return "Pilih minimal satu transaksi untuk direkap.", 400

        berhasil, pesan = simpan_rekap_transaksi(
            employee["id"],
            employee["cabang_id"],
            entries
        )
        if not berhasil:
            return pesan, 400

        return redirect(url_for("rekap_transaksi"))


    @app.route("/admin/rekap-pendapatan")
    def admin_rekap_pendapatan():
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        return redirect(url_for("laporan_pendapatan"))


    @app.route("/admin/rekap-pendapatan/<int:rekap_id>")
    def admin_detail_rekap(rekap_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        rekap = get_detail_rekap(rekap_id)
        if not rekap:
            return "Rekap tidak ditemukan.", 404

        return render_template(
            "admin_detail_rekap.html",
            rekap=rekap,
            user=session["user"]
        )


    @app.route("/supplier")
    def supplier():
        if not is_office_staff():
            return redirect(url_for("login"))

        return render_template(
            "supplier.html",
            supplier=get_semua_supplier(),
            user=session["user"]
        )


    @app.route("/supplier/tambah", methods=["GET", "POST"])
    def tambah_supplier_route():
        if "user" not in session:
            return redirect(url_for("login"))
        if session["user"]["role"] != "admin":
            return "Hanya admin yang dapat menambah supplier.", 403

        if request.method == "POST":
            nama_perusahaan = request.form.get("nama_perusahaan", "").strip()
            nama_kontak = request.form.get("nama_kontak", "").strip() or None
            telepon = request.form.get("telepon", "").strip() or None
            email = request.form.get("email", "").strip() or None
            alamat = request.form.get("alamat", "").strip() or None

            if not nama_perusahaan:
                return render_template(
                    "supplier_tambah.html",
                    error="Nama perusahaan wajib diisi.",
                    user=session["user"]
                )

            if tambah_supplier(
                nama_perusahaan,
                nama_kontak,
                telepon,
                email,
                alamat
            ):
                return redirect(url_for("supplier"))

            return render_template(
                "supplier_tambah.html",
                error="Supplier gagal ditambahkan.",
                user=session["user"]
            )

        return render_template(
            "supplier_tambah.html",
            user=session["user"]
        )


    @app.route("/supplier/<int:supplier_id>/edit", methods=["GET", "POST"])
    def edit_supplier_route(supplier_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        supplier_data = next(
            (item for item in get_semua_supplier() if item["id"] == supplier_id),
            None
        )
        if not supplier_data:
            return "Supplier tidak ditemukan.", 404

        if request.method == "POST":
            nama_perusahaan = request.form.get("nama_perusahaan", "").strip()
            status = request.form.get("status")
            if not nama_perusahaan or status not in ("aktif", "nonaktif"):
                return render_template(
                    "supplier_edit.html",
                    supplier=supplier_data,
                    error="Nama perusahaan dan status wajib valid.",
                    user=session["user"]
                )

            berhasil = update_supplier(
                supplier_id,
                nama_perusahaan,
                request.form.get("nama_kontak", "").strip() or None,
                request.form.get("telepon", "").strip() or None,
                request.form.get("email", "").strip() or None,
                request.form.get("alamat", "").strip() or None,
                status
            )
            if berhasil:
                return redirect(url_for("supplier"))

            return render_template(
                "supplier_edit.html",
                supplier=supplier_data,
                error="Supplier gagal diperbarui.",
                user=session["user"]
            )

        return render_template(
            "supplier_edit.html",
            supplier=supplier_data,
            user=session["user"]
        )


    @app.route("/cabang")
    def daftar_cabang():
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        return render_template(
            "cabang.html",
            cabang=get_semua_cabang(),
            user=session["user"]
        )


    @app.route("/cabang/tambah", methods=["GET", "POST"])
    def tambah_cabang_route():
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        if request.method == "POST":
            nama = request.form.get("nama", "").strip()
            alamat = request.form.get("alamat", "").strip()
            telepon = request.form.get("telepon", "").strip() or None

            if not nama or not alamat:
                return render_template(
                    "cabang_tambah.html",
                    error="Nama dan alamat cabang wajib diisi.",
                    user=session["user"]
                )

            if tambah_cabang(nama, alamat, telepon):
                return redirect(url_for("daftar_cabang"))

            return render_template(
                "cabang_tambah.html",
                error="Cabang gagal ditambahkan.",
                user=session["user"]
            )

        return render_template("cabang_tambah.html", user=session["user"])


    @app.route("/cabang/<int:cabang_id>/edit", methods=["GET", "POST"])
    def edit_cabang_route(cabang_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        cabang = next(
            (item for item in get_semua_cabang() if item["id"] == cabang_id),
            None
        )
        if not cabang:
            return "Cabang tidak ditemukan.", 404

        if request.method == "POST":
            nama = request.form.get("nama", "").strip()
            alamat = request.form.get("alamat", "").strip()
            telepon = request.form.get("telepon", "").strip() or None
            status = request.form.get("status")

            if not nama or not alamat or status not in ("aktif", "nonaktif"):
                return render_template(
                    "cabang_edit.html",
                    cabang=cabang,
                    error="Data cabang tidak valid.",
                    user=session["user"]
                )

            if update_cabang(cabang_id, nama, alamat, telepon, status):
                return redirect(url_for("daftar_cabang"))

            return render_template(
                "cabang_edit.html",
                cabang=cabang,
                error="Cabang gagal diperbarui.",
                user=session["user"]
            )

        return render_template(
            "cabang_edit.html",
            cabang=cabang,
            user=session["user"]
        )


    @app.route("/employee")
    def daftar_employee():
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        return render_template(
            "employee.html",
            employee=get_semua_employee(),
            user=session["user"]
        )


    @app.route("/employee/tambah", methods=["GET", "POST"])
    def tambah_employee_route():
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        cabang = get_semua_cabang(aktif_saja=True)

        if request.method == "POST":
            nama = request.form.get("nama", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            jabatan = request.form.get("jabatan")
            no_telepon = request.form.get("no_telepon", "").strip() or None
            alamat = request.form.get("alamat", "").strip() or None

            try:
                cabang_id = int(request.form["cabang_id"])
            except (KeyError, ValueError):
                cabang_id = None

            if not nama or not username or not password or jabatan not in (
                "admin", "manajer_cabang", "kasir", "pegawai_produksi"
            ) or cabang_id is None:
                return render_template(
                    "employee_tambah.html",
                    cabang=cabang,
                    error="Semua data employee wajib diisi dengan benar.",
                    user=session["user"]
                )

            berhasil, pesan = tambah_employee(
                nama,
                username,
                password,
                jabatan,
                cabang_id,
                no_telepon,
                alamat
            )

            if berhasil:
                return redirect(url_for("daftar_employee"))

            return render_template(
                "employee_tambah.html",
                cabang=cabang,
                error=pesan,
                user=session["user"]
            )

        return render_template(
            "employee_tambah.html",
            cabang=cabang,
            user=session["user"]
        )


    @app.route("/employee/<int:employee_id>/edit", methods=["GET", "POST"])
    def edit_employee_route(employee_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        employee = get_employee(employee_id)
        if not employee:
            return "Employee tidak ditemukan.", 404

        cabang = get_semua_cabang(aktif_saja=True)

        if request.method == "POST":
            nama = request.form.get("nama", "").strip()
            username = request.form.get("username", "").strip()
            jabatan = request.form.get("jabatan")
            status = request.form.get("status")
            no_telepon = request.form.get("no_telepon", "").strip() or None
            alamat = request.form.get("alamat", "").strip() or None

            try:
                cabang_id = int(request.form["cabang_id"])
            except (KeyError, ValueError):
                cabang_id = None

            if (
                not nama or not username
                or jabatan not in (
                    "admin", "manajer_cabang", "kasir", "pegawai_produksi"
                )
                or status not in ("aktif", "nonaktif")
                or cabang_id is None
            ):
                return render_template(
                    "employee_edit.html",
                    employee=employee,
                    cabang=cabang,
                    error="Data employee tidak valid.",
                    user=session["user"]
                )

            berhasil, pesan = update_employee(
                employee_id,
                nama,
                username,
                request.form.get("password", ""),
                jabatan,
                cabang_id,
                no_telepon,
                alamat,
                status
            )

            if berhasil:
                return redirect(url_for("daftar_employee"))

            return render_template(
                "employee_edit.html",
                employee=employee,
                cabang=cabang,
                error=pesan,
                user=session["user"]
            )

        return render_template(
            "employee_edit.html",
            employee=employee,
            cabang=cabang,
            user=session["user"]
        )


    @app.route("/permintaan-stok")
    def daftar_permintaan_stok():
        if not is_office_staff():
            return redirect(url_for("login"))

        cabang_id = None
        if session["user"]["role"] == "manajer_cabang":
            employee = get_employee_for_user(session["user"]["id"])
            if not employee:
                return "Akun manager belum memiliki employee aktif.", 403
            cabang_id = employee["cabang_id"]

        return render_template(
            "permintaan_stok.html",
            permintaan=get_semua_permintaan_stok(cabang_id),
            user=session["user"]
        )


    @app.route("/permintaan-stok/tambah", methods=["GET", "POST"])
    def tambah_permintaan_stok():
        if "user" not in session:
            return redirect(url_for("login"))
        if session["user"]["role"] != "manajer_cabang":
            return "Hanya manager cabang yang dapat membuat request stok.", 403

        user = session["user"]
        employee = get_employee_for_user(user["id"])
        produk = get_semua_produk()

        if not employee or employee["cabang_id"] is None:
            return "Manager belum memiliki cabang aktif.", 403

        if request.method == "POST":
            try:
                produk_id = int(request.form["produk_id"])
                jumlah = int(request.form["jumlah"])
                catatan = request.form.get("catatan", "").strip() or None
            except (KeyError, TypeError, ValueError):
                return render_template(
                    "permintaan_stok_tambah.html",
                    produk=produk,
                    error="Data request stok tidak valid.",
                    user=user
                )

            permintaan_id = buat_permintaan_stok(
                employee["id"],
                employee["cabang_id"],
                produk_id,
                jumlah,
                catatan
            )

            if permintaan_id:
                return redirect(url_for("daftar_permintaan_stok"))

            return render_template(
                "permintaan_stok_tambah.html",
                produk=produk,
                error="Request stok gagal disimpan.",
                user=user
            )

        return render_template(
            "permintaan_stok_tambah.html",
            produk=produk,
            employee=employee,
            user=user
        )


    @app.route("/permintaan-stok/<int:permintaan_id>/status", methods=["POST"])
    def admin_update_status_permintaan(permintaan_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403

        status_baru = request.form.get("status")
        if status_baru == "selesai":
            return "Gunakan proses distribusi stok untuk menyelesaikan request.", 400
        berhasil, pesan = update_status_permintaan_stok(permintaan_id, status_baru)
        if not berhasil:
            return pesan, 400

        return redirect(url_for("daftar_permintaan_stok"))


    @app.route("/pembelian")
    def daftar_pembelian():
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403
        return render_template(
            "pembelian.html",
            pembelian=get_semua_pembelian(),
            user=session["user"]
        )


    @app.route("/pembelian/tambah", methods=["GET", "POST"])
    def tambah_pembelian_route():
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403
        suppliers = get_semua_supplier()
        recommendation_prefill = session.pop("dss_prefill", None)
        supplier_id = request.form.get(
            "supplier_id",
            request.args.get(
                "supplier_id",
                recommendation_prefill["supplier_id"]
                if recommendation_prefill else None
            )
        )
        try:
            supplier_id = int(supplier_id) if supplier_id else None
        except ValueError:
            supplier_id = None
        supplier_products = get_supplier_produk(supplier_id)
        prefill_quantities = {}
        if recommendation_prefill:
            prefill_quantities[recommendation_prefill["produk_id"]] = recommendation_prefill["jumlah"]
        error = None
        if request.method == "POST":
            for key, value in request.form.items():
                if key.startswith("jumlah_") and value:
                    try:
                        prefill_quantities[int(key.split("_", 1)[1])] = value
                    except ValueError:
                        continue
            try:
                items = []
                for key, value in request.form.items():
                    if key.startswith("jumlah_") and value:
                        items.append({"produk_id": int(key.split("_", 1)[1]), "jumlah": int(value)})
                employee = get_employee_for_user(session["user"]["id"])
                if not employee:
                    raise ValueError("Akun admin belum memiliki employee aktif.")
                purchase_id, error = buat_pembelian_supplier(
                    supplier_id,
                    employee["id"],
                    items,
                    catatan=request.form.get("catatan", "").strip() or None,
                )
                if purchase_id:
                    return redirect(url_for("daftar_pembelian"))
            except ValueError as exception:
                error = str(exception)
            except TypeError:
                error = "Data pembelian tidak valid."
        return render_template(
            "pembelian_tambah.html",
            suppliers=suppliers,
            supplier_products=supplier_products,
            selected_supplier_id=supplier_id,
            prefill_quantities=prefill_quantities,
            error=error,
            user=session["user"]
        )


    @app.route("/pembelian/<int:pembelian_id>/status", methods=["POST"])
    def admin_update_status_pembelian(pembelian_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403
        employee = get_employee_for_user(session["user"]["id"])
        status = request.form.get("status")
        berhasil, pesan = update_status_pembelian(
            pembelian_id, status, session["user"]["id"] if employee else None
        )
        if not berhasil:
            return pesan, 400
        return redirect(url_for("daftar_pembelian"))


    @app.route("/distribusi-stok")
    def daftar_distribusi_stok():
        if not is_office_staff():
            return redirect(url_for("login"))
        cabang_id = None
        if session["user"]["role"] == "manajer_cabang":
            employee = get_employee_for_user(session["user"]["id"])
            cabang_id = employee["cabang_id"] if employee else None
        return render_template(
            "distribusi_stok.html",
            distribusi=get_semua_distribusi(cabang_id),
            user=session["user"]
        )


    @app.route("/distribusi-stok/tambah/<int:permintaan_id>", methods=["GET", "POST"])
    def tambah_distribusi_stok_route(permintaan_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403
        requests = get_semua_permintaan_stok()
        selected = [item for item in requests if item["permintaan_id"] == permintaan_id]
        if not selected:
            return "Permintaan stok tidak ditemukan.", 404
        error = None
        if request.method == "POST":
            try:
                items = [{"produk_id": int(key.split("_", 1)[1]), "jumlah": int(value)}
                         for key, value in request.form.items()
                         if key.startswith("jumlah_") and value]
                employee = get_employee_for_user(session["user"]["id"])
                distribution_id, error = buat_distribusi_stok(
                    employee["id"], selected[0]["cabang_id"], items,
                    permintaan_id, request.form.get("catatan", "").strip() or None
                )
                if distribution_id:
                    return redirect(url_for("daftar_distribusi_stok"))
            except (TypeError, ValueError, AttributeError):
                error = "Data distribusi tidak valid."
        return render_template(
            "distribusi_stok_tambah.html",
            permintaan=selected,
            error=error,
            user=session["user"]
        )


    @app.route("/distribusi-stok/<int:distribusi_id>/status", methods=["POST"])
    def admin_update_status_distribusi(distribusi_id):
        if "user" not in session or session["user"]["role"] != "admin":
            return "Akses ditolak", 403
        status = request.form.get("status")
        berhasil, pesan = update_status_distribusi(
            distribusi_id, status, session["user"]["id"]
        )
        if not berhasil:
            return pesan, 400
        return redirect(url_for("daftar_distribusi_stok"))
