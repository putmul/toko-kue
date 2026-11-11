from model.database import get_connection
from model.user import login_user, register_user
from service.checkout import buat_transaksi
from service.riwayat_transaksi import (
    lihat_riwayat_transaksi, lihat_detail_transaksi
)
from service.produk import tambah_produk, update_stok
from service.cabang import get_semua_cabang


def lihat_katalog():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                id,
                nama,
                harga,
                stok
            FROM produk
            ORDER BY id
        """)

        produk = cursor.fetchall()

        print("\n========================================")
        print("              KATALOG KUE")
        print("========================================")

        if not produk:
            print("Belum ada produk.")
            return

        print(
            f"{'ID':<5}"
            f"{'Nama':<25}"
            f"{'Harga':<15}"
            f"{'Stok':<8}"
        )

        print("-" * 53)

        for p in produk:

            status = "HABIS" if p["stok"] <= 0 else str(p["stok"])

            print(
                f'{p["id"]:<5}'
                f'{p["nama"]:<25}'
                f'Rp{p["harga"]:,.0f}{"":<4}'
                f'{status:<8}'
            )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# REGISTER
# =========================================================

def menu_register():

    print("\n================================")
    print("          REGISTER PEMBELI")
    print("================================")

    nama = input("Nama     : ").strip()
    username = input("Username : ").strip()
    password = input("Password : ").strip()

    if not nama or not username or not password:
        print("\nSemua data wajib diisi.")
        return

    success, message = register_user(
        nama,
        username,
        password
    )

    print(f"\n{message}")


# =========================================================
# LOGIN
# =========================================================

def menu_login():

    print("\n================================")
    print("              LOGIN")
    print("================================")

    username = input("Username : ").strip()
    password = input("Password : ").strip()

    user = login_user(
        username,
        password
    )

    if user:
        print("\nLogin berhasil!")
        print(f"Selamat datang, {user['nama']}.")
        print(f"Role: {user['role']}")

        return user

    print("\nUsername atau password salah.")

    return None


# =========================================================
# AMBIL PRODUK
# =========================================================

def get_produk(produk_id):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                id,
                nama,
                harga,
                stok
            FROM produk
            WHERE id = %s
        """, (produk_id,))

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


# =========================================================
# TAMPILKAN KERANJANG
# =========================================================

def tampilkan_keranjang(keranjang):

    print("\n================================")
    print("            KERANJANG")
    print("================================")

    if not keranjang:
        print("Keranjang kosong.")
        return 0

    total = 0

    for i, item in enumerate(keranjang, start=1):

        subtotal = item["harga"] * item["jumlah"]

        total += subtotal

        print(
            f'{i}. {item["nama"]}'
        )

        print(
            f'   {item["jumlah"]} x '
            f'Rp{item["harga"]:,.0f} '
            f'= Rp{subtotal:,.0f}'
        )

    print("--------------------------------")
    print(f"TOTAL: Rp{total:,.0f}")

    return total


# =========================================================
# KERANJANG & CHECKOUT
# =========================================================

def menu_keranjang(user):

    keranjang = []

    while True:

        tampilkan_keranjang(keranjang)

        print("\n1. Tambah kue")
        print("2. Hapus kue")
        print("3. Checkout COD")
        print("4. Kembali")

        pilihan = input("\nPilih: ").strip()

        # -------------------------------------------------
        # TAMBAH
        # -------------------------------------------------

        if pilihan == "1":

            lihat_katalog()

            try:
                produk_id = int(
                    input("\nMasukkan ID kue: ")
                )

                jumlah = int(
                    input("Jumlah: ")
                )

            except ValueError:
                print("ID dan jumlah harus berupa angka.")
                continue

            if jumlah <= 0:
                print("Jumlah harus lebih dari 0.")
                continue

            produk = get_produk(produk_id)

            if not produk:
                print("Produk tidak ditemukan.")
                continue

            if produk["stok"] <= 0:
                print("Produk sedang habis.")
                continue

            # Cari apakah sudah ada di keranjang
            existing = None

            for item in keranjang:

                if item["produk_id"] == produk_id:
                    existing = item
                    break

            jumlah_lama = (
                existing["jumlah"]
                if existing
                else 0
            )

            if jumlah_lama + jumlah > produk["stok"]:

                print(
                    f"Stok tidak mencukupi. "
                    f"Stok tersedia: {produk['stok']}"
                )

                continue

            if existing:

                existing["jumlah"] += jumlah

            else:

                keranjang.append({
                    "produk_id": produk["id"],
                    "nama": produk["nama"],
                    "harga": float(produk["harga"]),
                    "jumlah": jumlah
                })

            print("Produk berhasil ditambahkan.")

        # -------------------------------------------------
        # HAPUS
        # -------------------------------------------------

        elif pilihan == "2":

            if not keranjang:
                print("Keranjang kosong.")
                continue

            try:

                nomor = int(
                    input("Nomor produk yang dihapus: ")
                )

            except ValueError:

                print("Input harus berupa angka.")
                continue

            if nomor < 1 or nomor > len(keranjang):

                print("Nomor tidak valid.")
                continue

            produk = keranjang.pop(nomor - 1)

            print(
                f'{produk["nama"]} berhasil dihapus.'
            )

        # -------------------------------------------------
        # CHECKOUT
        # -------------------------------------------------

        elif pilihan == "3":

            if not keranjang:

                print("Keranjang kosong.")
                continue

            total = tampilkan_keranjang(
                keranjang
            )

            print("\nMetode pembayaran: COD")

            cabang = get_semua_cabang(aktif_saja=True)
            if not cabang:
                print("Belum ada cabang aktif.")
                continue

            print("\nPilih cabang:")
            for item in cabang:
                print(f'{item["id"]}. {item["nama"]}')

            try:
                cabang_id = int(input("ID cabang: "))
            except ValueError:
                print("ID cabang harus berupa angka.")
                continue

            if not any(item["id"] == cabang_id for item in cabang):
                print("Cabang tidak valid.")
                continue

            konfirmasi = input(
                "Lanjut checkout? (y/n): "
            ).lower()

            if konfirmasi != "y":

                print("Checkout dibatalkan.")
                continue

            transaksi_id = buat_transaksi(
                user["id"],
                keranjang,
                cabang_id
            )

            if transaksi_id:

                print("\n================================")
                print("       CHECKOUT BERHASIL")
                print("================================")

                print(
                    f"Nomor transaksi : #{transaksi_id}"
                )

                print(
                    f"Total           : Rp{total:,.0f}"
                )

                print(
                    "Pembayaran      : COD"
                )

                keranjang.clear()

                tampilkan_invoice(
                    transaksi_id,
                    user["id"]
                )

        # -------------------------------------------------
        # KEMBALI
        # -------------------------------------------------

        elif pilihan == "4":

            break

        else:

            print("Pilihan tidak valid.")


# =========================================================
# INVOICE
# =========================================================

def tampilkan_invoice(
    transaksi_id,
    user_id=None
):

    transaksi = lihat_detail_transaksi(
        transaksi_id,
        user_id
    )

    if not transaksi:

        print("Transaksi tidak ditemukan.")
        return

    print("\n========================================")
    print("                 INVOICE")
    print("========================================")

    print(
        f"Nomor transaksi : #{transaksi['transaksi_id']}"
    )

    print(
        f"Pelanggan       : {transaksi['pelanggan']}"
    )

    print(
        f"Tanggal         : {transaksi['tanggal']}"
    )

    print(
        f"Status          : {transaksi['status']}"
    )

    print(
        f"Pembayaran      : {transaksi['metode_pembayaran']}"
    )

    print("----------------------------------------")

    total = 0

    for item in transaksi["items"]:

        print(
            f'{item["nama"]}'
        )

        print(
            f'  {item["jumlah"]} x '
            f'Rp{item["harga"]:,.0f} '
            f'= Rp{item["subtotal"]:,.0f}'
        )

        total += float(item["subtotal"])

    print("----------------------------------------")

    print(
        f"TOTAL: Rp{total:,.0f}"
    )

    print("========================================")


# =========================================================
# RIWAYAT PELANGGAN
# =========================================================

def menu_riwayat(user):

    while True:

        transaksi = lihat_riwayat_transaksi(
            user["id"]
        )

        print("\n========================================")
        print("          RIWAYAT TRANSAKSI")
        print("========================================")

        if not transaksi:

            print("Belum ada transaksi.")

        else:

            for t in transaksi:

                print(
                    f'#{t["transaksi_id"]} | '
                    f'{t["tanggal"]} | '
                    f'{t["status"]} | '
                    f'Rp{t["total"]:,.0f}'
                )

        print("\n1. Lihat invoice")
        print("2. Kembali")

        pilihan = input("\nPilih: ").strip()

        if pilihan == "1":

            try:

                transaksi_id = int(
                    input("ID transaksi: ")
                )

            except ValueError:

                print("ID harus berupa angka.")
                continue

            tampilkan_invoice(
                transaksi_id,
                user["id"]
            )

        elif pilihan == "2":

            break

        else:

            print("Pilihan tidak valid.")


# =========================================================
# MENU PELANGGAN
# =========================================================

def menu_pelanggan(user):

    while True:

        print("\n================================")
        print("          MENU PEMBELI")
        print("================================")

        print(
            f"Login sebagai: {user['nama']}"
        )

        print("\n1. Lihat katalog kue")
        print("2. Keranjang & checkout COD")
        print("3. Riwayat transaksi")
        print("4. Logout")

        pilihan = input("\nPilih: ").strip()

        if pilihan == "1":

            lihat_katalog()

        elif pilihan == "2":

            menu_keranjang(user)

        elif pilihan == "3":

            menu_riwayat(user)

        elif pilihan == "4":

            print("Logout berhasil.")
            break

        else:

            print("Pilihan tidak valid.")
