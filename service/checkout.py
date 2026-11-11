from model.database import get_connection

def buat_transaksi(user_id, items, cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # -------------------------------------------------
        # 1. Pastikan user adalah pelanggan
        # -------------------------------------------------
        cursor.execute("""
            SELECT id, nama, role
            FROM users
            WHERE id = %s
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            print("User tidak ditemukan.")
            return None

        if user["role"] != "pelanggan":
            print("Hanya pelanggan yang dapat melakukan transaksi.")
            return None

        # -------------------------------------------------
        # 2. Pastikan keranjang tidak kosong
        # -------------------------------------------------
        if not items:
            print("Keranjang kosong.")
            return None

        if cabang_id is None:
            print("Cabang transaksi wajib dipilih.")
            return None

        cursor.execute("""
            SELECT id
            FROM cabang
            WHERE id = %s AND status = 'aktif'
        """, (cabang_id,))
        if not cursor.fetchone():
            print("Cabang tidak ditemukan atau nonaktif.")
            return None

        # -------------------------------------------------
        # 3. Buat transaksi
        # -------------------------------------------------
        cursor.execute("""
            INSERT INTO transaksi
                (user_id, cabang_id, status, metode_pembayaran)
            VALUES
                (%s, %s, 'diproses', 'COD')
        """, (user_id, cabang_id))

        transaksi_id = cursor.lastrowid

        total_harga = 0

        # -------------------------------------------------
        # 4. Proses setiap produk
        # -------------------------------------------------
        for item in items:

            produk_id = item["produk_id"]
            jumlah = item["jumlah"]

            if jumlah <= 0:
                raise Exception("Jumlah produk tidak valid.")

            # Lock product and branch-stock rows during checkout.
            cursor.execute("""
                SELECT
                    id,
                    nama,
                    harga
                FROM produk
                WHERE id = %s
                FOR UPDATE
            """, (produk_id,))

            produk = cursor.fetchone()

            if not produk:
                raise Exception(
                    f"Produk dengan ID {produk_id} tidak ditemukan."
                )

            cursor.execute("""
                INSERT IGNORE INTO stok_cabang (cabang_id, produk_id, stok)
                VALUES (%s, %s, 0)
            """, (cabang_id, produk_id))

            cursor.execute("""
                SELECT stok
                FROM stok_cabang
                WHERE cabang_id = %s AND produk_id = %s
                FOR UPDATE
            """, (cabang_id, produk_id))
            stok_cabang = cursor.fetchone()["stok"]

            # -------------------------------------------------
            # 5. Cek stok
            # -------------------------------------------------
            if stok_cabang < jumlah:
                raise Exception(
                    f"Stok {produk['nama']} tidak mencukupi. "
                    f"Tersedia: {stok_cabang}"
                )

            # -------------------------------------------------
            # 6. Hitung subtotal menggunakan harga DB
            # -------------------------------------------------
            subtotal = produk["harga"] * jumlah

            # -------------------------------------------------
            # 7. Simpan detail transaksi
            # -------------------------------------------------
            cursor.execute("""
                INSERT INTO detail_transaksi
                    (transaksi_id, produk_id, jumlah, harga_satuan, subtotal)
                VALUES
                    (%s, %s, %s, %s, %s)
            """, (
                transaksi_id,
                produk_id,
                jumlah,
                produk["harga"],
                subtotal
            ))

            total_harga += subtotal

            # -------------------------------------------------
            # 8. Kurangi stok cabang, bukan stok gudang utama.
            # -------------------------------------------------
            cursor.execute("""
                UPDATE stok_cabang
                SET stok = stok - %s
                WHERE cabang_id = %s AND produk_id = %s
            """, (jumlah, cabang_id, produk_id))

        cursor.execute("""
            UPDATE transaksi
            SET total_harga = %s
            WHERE id = %s
        """, (total_harga, transaksi_id))

        # -------------------------------------------------
        # 9. Commit semua perubahan
        # -------------------------------------------------
        connection.commit()

        return transaksi_id

    except Exception as e:

        # Kalau satu saja gagal,
        # seluruh transaksi dibatalkan
        connection.rollback()

        print("\nCheckout gagal!")
        print("Alasan:", e)

        return None

    finally:
        cursor.close()
        connection.close()
