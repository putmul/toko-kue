from model.database import get_connection

def ambil_pesanan(transaksi_id, user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT e.id AS employee_id, e.cabang_id
            FROM employee e
            JOIN users u ON e.user_id = u.id
            WHERE u.id = %s
              AND u.role = 'kasir'
              AND e.status = 'aktif'
        """, (user_id,))

        kasir = cursor.fetchone()

        if not kasir:
            print("User bukan kasir.")
            return False

        employee_id = kasir["employee_id"]

        cursor.execute("""
            SELECT id, status, kasir_id, cabang_id
            FROM transaksi
            WHERE id = %s
            FOR UPDATE
        """, (transaksi_id,))

        transaksi = cursor.fetchone()

        if not transaksi:
            print("Transaksi tidak ditemukan.")
            return False

        if transaksi["status"] != "diproses":
            print("Pesanan tidak dapat diambil.")
            return False

        if transaksi["kasir_id"] is not None:
            print("Pesanan sudah ditangani kasir lain.")
            return False

        if (
            kasir["cabang_id"] is None
            or transaksi["cabang_id"] != kasir["cabang_id"]
        ):
            print("Pesanan bukan untuk cabang kasir ini.")
            return False

        cursor.execute("""
            UPDATE transaksi
            SET kasir_id = %s
            WHERE id = %s
        """, (employee_id, transaksi_id))

        connection.commit()
        return True

    except Exception as e:
        connection.rollback()
        print("Error mengambil pesanan:", e)
        return False

    finally:
        cursor.close()
        connection.close()


def update_status_pesanan(transaksi_id, status_baru, employee_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    status_valid = [
        "diproses",
        "dikirim",
        "selesai",
        "dibatalkan"
    ]

    try:

        # -------------------------------------------------
        # Validasi status
        # -------------------------------------------------
        if status_baru not in status_valid:
            print("Status tidak valid.")
            return False

        # -------------------------------------------------
        # Ambil transaksi dan lock
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                id,
                status,
                kasir_id,
                cabang_id
            FROM transaksi
            WHERE id = %s
            FOR UPDATE
        """, (transaksi_id,))

        transaksi = cursor.fetchone()

        if not transaksi:
            print("Transaksi tidak ditemukan.")
            return False

        status_lama = transaksi["status"]

        if employee_id is not None:
            cursor.execute("""
                SELECT cabang_id
                FROM employee
                WHERE id = %s AND status = 'aktif'
            """, (employee_id,))
            employee = cursor.fetchone()
            if (
                not employee
                or employee["cabang_id"] is None
                or transaksi["cabang_id"] != employee["cabang_id"]
                or (
                    transaksi["kasir_id"] is not None
                    and transaksi["kasir_id"] != employee_id
                )
            ):
                print("Transaksi bukan tanggung jawab kasir ini.")
                return False

            if transaksi["kasir_id"] is None:
                cursor.execute("""
                    UPDATE transaksi
                    SET kasir_id = %s
                    WHERE id = %s
                """, (employee_id, transaksi_id))

        # -------------------------------------------------
        # Tidak boleh mengubah transaksi yang sudah batal
        # -------------------------------------------------
        if status_lama == "dibatalkan":
            print("Pesanan sudah dibatalkan.")
            return False

        # -------------------------------------------------
        # Tidak boleh mengubah pesanan selesai
        # -------------------------------------------------
        if status_lama == "selesai":
            print("Pesanan sudah selesai.")
            return False

        # -------------------------------------------------
        # Validasi alur status
        # -------------------------------------------------
        status_diizinkan = {
            "diproses": ["dikirim", "dibatalkan"],
            "dikirim": ["selesai"],
            "selesai": [],
            "dibatalkan": []
        }

        if status_baru not in status_diizinkan[status_lama]:
            print(
                f"Status tidak dapat diubah dari "
                f"{status_lama} menjadi {status_baru}."
            )
            return False

        # -------------------------------------------------
        # Jika dibatalkan,
        # kembalikan stok
        # -------------------------------------------------
        if status_baru == "dibatalkan":

            cursor.execute("""
                SELECT
                    produk_id,
                    jumlah
                FROM detail_transaksi
                WHERE transaksi_id = %s
            """, (transaksi_id,))

            details = cursor.fetchall()

            for detail in details:
                if transaksi["cabang_id"] is None:
                    raise Exception("Transaksi lama belum memiliki cabang.")

                cursor.execute("""
                    INSERT INTO stok_cabang (cabang_id, produk_id, stok)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE stok = stok + VALUES(stok)
                """, (
                    transaksi["cabang_id"],
                    detail["produk_id"],
                    detail["jumlah"]
                ))

        # -------------------------------------------------
        # Update status
        # -------------------------------------------------
        cursor.execute("""
            UPDATE transaksi
            SET status = %s
            WHERE id = %s
        """, (
            status_baru,
            transaksi_id
        ))

        connection.commit()

        return True

    except Exception as e:

        connection.rollback()

        print("Error update status:", e)

        return False

    finally:
        cursor.close()
        connection.close()
