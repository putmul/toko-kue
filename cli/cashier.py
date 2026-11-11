from service.transaksi import lihat_semua_transaksi, update_status_pesanan
from cli.customer import tampilkan_invoice


def menu_update_status():

        try:
            transaksi_id = int(
                input("ID transaksi: ")
            )

        except ValueError:
            print("ID harus berupa angka.")
            return

        print("\nStatus baru:")
        print("1. Diproses")
        print("2. Dikirim")
        print("3. Selesai")
        print("4. Dibatalkan")

        pilihan = input("Pilih: ").strip()

        status_map = {
            "1": "diproses",
            "2": "dikirim",
            "3": "selesai",
            "4": "dibatalkan"
        }

        if pilihan not in status_map:
            print("Pilihan status tidak valid.")
            return

        status_baru = status_map[pilihan]

        berhasil = update_status_pesanan(
            transaksi_id,
            status_baru
        )

        if berhasil:
            print(
                "\nStatus pesanan berhasil diperbarui."
            )
        else:
            print(
                "\nStatus pesanan gagal diperbarui."
            )

def menu_kasir(user):

    while True:

        print("\n================================")
        print("           MENU KASIR")
        print("================================")

        print(
            f"Login sebagai: {user['nama']}"
        )

        print("\n1. Lihat semua pesanan")
        print("2. Lihat detail pesanan")
        print("3. Update status pesanan")
        print("4. Logout")

        pilihan = input("\nPilih: ").strip()

        # -----------------------------------------
        # SEMUA PESANAN
        # -----------------------------------------

        if pilihan == "1":

            transaksi = lihat_semua_transaksi()

            print("\n========================================")
            print("             SEMUA PESANAN")
            print("========================================")

            if not transaksi:

                print("Belum ada pesanan.")
                continue

            for t in transaksi:

                print(
                    f'#{t["transaksi_id"]} | '
                    f'{t["pelanggan"]} | '
                    f'{t["tanggal"]} | '
                    f'{t["status"]} | '
                    f'Rp{t["total"]:,.0f}'
                )

        # -----------------------------------------
        # DETAIL PESANAN
        # -----------------------------------------

        elif pilihan == "2":

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

        # -----------------------------------------
        # UPDATE STATUS
        # -----------------------------------------

        elif pilihan == "3":

            menu_update_status()

        # -----------------------------------------
        # LOGOUT
        # -----------------------------------------

        elif pilihan == "4":

            print("Logout berhasil.")
            break

        else:

            print("Pilihan tidak valid.")

# =========================================================
# MAIN
# =========================================================
