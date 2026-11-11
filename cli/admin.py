from service.produk import tambah_produk, update_stok
from service.transaksi import lihat_semua_transaksi, update_status_pesanan
from cli.customer import lihat_katalog, tampilkan_invoice


def menu_tambah_produk():

        print("\n================================")
        print("          TAMBAH KUE")
        print("================================")

        nama = input("Nama kue : ").strip()

        if not nama:
            print("Nama kue wajib diisi.")
            return

        try:
            harga = float(
                input("Harga    : ")
            )

            stok = int(
                input("Stok     : ")
            )

        except ValueError:
            print("Harga dan stok harus berupa angka.")
            return

        if harga <= 0:
            print("Harga harus lebih dari 0.")
            return

        if stok < 0:
            print("Stok tidak boleh negatif.")
            return

        berhasil = tambah_produk(
            nama,
            harga,
            stok
        )

        if berhasil:
            print("\nKue berhasil ditambahkan.")
        else:
            print("\nGagal menambahkan kue.")

def menu_update_stok():

        lihat_katalog()

        print("\n================================")
        print("          UBAH STOK")
        print("================================")

        try:

            produk_id = int(
                input("ID kue       : ")
            )

            stok_baru = int(
                input("Stok baru    : ")
            )

        except ValueError:

            print("ID dan stok harus berupa angka.")
            return

        if stok_baru < 0:

            print("Stok tidak boleh negatif.")
            return

        berhasil = update_stok(
            produk_id,
            stok_baru
        )

        if berhasil:

            print("\nStok berhasil diperbarui.")

        else:

            print("\nProduk tidak ditemukan.")

def menu_histori_admin():

    transaksi = lihat_semua_transaksi()

    print("\n========================================")
    print("          HISTORI TRANSAKSI")
    print("========================================")

    if not transaksi:

        print("Belum ada transaksi.")
        return

    for t in transaksi:

        print(
            f'#{t["transaksi_id"]} | '
            f'{t["pelanggan"]} | '
            f'{t["tanggal"]} | '
            f'Status: {t["status"]} | '
            f'Rp{t["total"]:,.0f}'
        )

    while True:

        print("\n1. Lihat detail")
        print("2. Kembali")

        pilihan = input("Pilih: ").strip()

        if pilihan == "1":

            try:

                transaksi_id = int(
                    input("ID transaksi: ")
                )

            except ValueError:

                print("ID harus berupa angka.")
                continue

            tampilkan_invoice(
                transaksi_id
            )

        elif pilihan == "2":

            break

        else:

            print("Pilihan tidak valid.")

# =========================================================
# MENU ADMIN
# =========================================================

def menu_admin(user):

    while True:

        print("\n================================")
        print("           MENU ADMIN")
        print("================================")

        print(
            f"Login sebagai: {user['nama']}"
        )

        print("\n1. Lihat katalog & stok")
        print("2. Tambah kue")
        print("3. Ubah stok kue")
        print("4. Histori transaksi")
        print("5. Logout")

        pilihan = input("\nPilih: ").strip()

        if pilihan == "1":

            lihat_katalog()

        elif pilihan == "2":

            menu_tambah_produk()

        elif pilihan == "3":

            menu_update_stok()

        elif pilihan == "4":

            menu_histori_admin()

        elif pilihan == "5":

            print("Logout berhasil.")
            break

        else:

            print("Pilihan tidak valid.")

# =========================================================
# UPDATE STATUS PESANAN
# =========================================================
