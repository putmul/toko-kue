from cli.customer import menu_login, menu_register, menu_pelanggan
from cli.admin import menu_admin
from cli.cashier import menu_kasir


def main():

    while True:

        print("\n========================================")
        print("       SISTEM TRANSAKSI TOKO KUE")
        print("========================================")

        print("\n1. Login")
        print("2. Register Pembeli")
        print("3. Keluar")

        pilihan = input("\nPilih: ").strip()

        # =========================================
        # LOGIN
        # =========================================

        if pilihan == "1":

            user = menu_login()

            if not user:
                continue

            # -------------------------------------
            # ADMIN
            # -------------------------------------

            if user["role"] == "admin":

                menu_admin(user)

            # -------------------------------------
            # KASIR
            # -------------------------------------

            elif user["role"] == "kasir":

                menu_kasir(user)

            # -------------------------------------
            # PELANGGAN
            # -------------------------------------

            elif user["role"] == "pelanggan":

                menu_pelanggan(user)

            else:

                print("Role tidak dikenali.")

        # =========================================
        # REGISTER
        # =========================================

        elif pilihan == "2":

            menu_register()

        # =========================================
        # KELUAR
        # =========================================

        elif pilihan == "3":

            print("\nProgram selesai.")
            break

        else:

            print("Pilihan tidak valid.")


if __name__ == "__main__":
    main()
