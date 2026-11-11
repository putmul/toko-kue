from model.database import get_connection


def tambah_produk(nama, harga, stok):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO produk
                (nama, harga, stok)
            VALUES
                (%s, %s, %s)
        """, (nama, harga, stok))

        connection.commit()

        return True

    except Exception as e:
        connection.rollback()

        print("Error tambah produk:", e)

        return False

    finally:
        cursor.close()
        connection.close()


def update_stok(produk_id, stok_baru):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE produk
            SET stok = %s
            WHERE id = %s
        """, (stok_baru, produk_id))

        if cursor.rowcount == 0:
            return False

        connection.commit()

        return True

    except Exception as e:
        connection.rollback()

        print("Error update stok:", e)

        return False

    finally:
        cursor.close()
        connection.close()


def update_produk(produk_id, nama, harga):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE produk
            SET nama = %s, harga = %s
            WHERE id = %s
        """, (nama, harga, produk_id))

        if cursor.rowcount == 0:
            cursor.execute("SELECT id FROM produk WHERE id = %s", (produk_id,))
            if not cursor.fetchone():
                return False

        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print("Error update produk:", e)
        return False
    finally:
        cursor.close()
        connection.close()


def hapus_produk(produk_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM produk WHERE id = %s", (produk_id,))
        if cursor.rowcount == 0:
            return False, "Produk tidak ditemukan."

        connection.commit()
        return True, "Produk berhasil dihapus."
    except Exception as e:
        connection.rollback()
        print("Error hapus produk:", e)
        return False, "Produk tidak dapat dihapus karena sudah digunakan dalam transaksi atau pembelian."
    finally:
        cursor.close()
        connection.close()


def get_stok_produk_per_cabang(cabang_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                p.id AS produk_id,
                p.nama,
                p.harga,
                p.stok AS stok_gudang,
                c.id AS cabang_id,
                c.nama AS cabang,
                COALESCE(sc.stok, 0) AS stok_cabang
            FROM produk p
            CROSS JOIN cabang c
            LEFT JOIN stok_cabang sc
                ON sc.produk_id = p.id
               AND sc.cabang_id = c.id
            WHERE c.status = 'aktif'
        """
        params = ()
        if cabang_id is not None:
            query += " AND c.id = %s"
            params = (cabang_id,)
        query += """
            ORDER BY p.id, c.nama
        """
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def distribusikan_stok(produk_id, cabang_id, jumlah):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if jumlah <= 0:
            raise ValueError("Jumlah distribusi harus lebih dari 0.")

        cursor.execute("""
            SELECT stok
            FROM produk
            WHERE id = %s
            FOR UPDATE
        """, (produk_id,))
        produk = cursor.fetchone()
        if not produk:
            raise ValueError("Produk tidak ditemukan.")

        if produk["stok"] < jumlah:
            raise ValueError("Stok gudang tidak mencukupi.")

        cursor.execute("""
            SELECT id
            FROM cabang
            WHERE id = %s AND status = 'aktif'
        """, (cabang_id,))
        if not cursor.fetchone():
            raise ValueError("Cabang tidak ditemukan atau nonaktif.")

        cursor.execute("""
            UPDATE produk
            SET stok = stok - %s
            WHERE id = %s
        """, (jumlah, produk_id))

        cursor.execute("""
            INSERT INTO stok_cabang (cabang_id, produk_id, stok)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE stok = stok + VALUES(stok)
        """, (cabang_id, produk_id, jumlah))

        connection.commit()
        return True, "Stok berhasil didistribusikan."
    except Exception as e:
        connection.rollback()
        print("Error distribusi stok:", e)
        return False, str(e)
    finally:
        cursor.close()
        connection.close()


def distribusikan_stok_bulk(distributions):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        for produk_id, cabang_id, jumlah in distributions:
            if jumlah <= 0:
                continue

            cursor.execute("""
                SELECT stok
                FROM produk
                WHERE id = %s
                FOR UPDATE
            """, (produk_id,))
            produk = cursor.fetchone()
            if not produk:
                raise ValueError("Produk tidak ditemukan.")
            if produk["stok"] < jumlah:
                raise ValueError(
                    f"Stok gudang tidak mencukupi untuk produk ID {produk_id}."
                )

            cursor.execute("""
                SELECT id
                FROM cabang
                WHERE id = %s AND status = 'aktif'
            """, (cabang_id,))
            if not cursor.fetchone():
                raise ValueError("Cabang tidak ditemukan atau nonaktif.")

            cursor.execute("""
                UPDATE produk
                SET stok = stok - %s
                WHERE id = %s
            """, (jumlah, produk_id))
            cursor.execute("""
                INSERT INTO stok_cabang (cabang_id, produk_id, stok)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE stok = stok + VALUES(stok)
            """, (cabang_id, produk_id, jumlah))

        connection.commit()
        return True, "Distribusi stok berhasil disimpan."
    except Exception as e:
        connection.rollback()
        print("Error distribusi stok bulk:", e)
        return False, str(e)
    finally:
        cursor.close()
        connection.close()

def get_semua_produk(cabang_id=None):

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            if cabang_id is None:
                cursor.execute("""
                    SELECT id, nama, harga, stok
                    FROM produk
                    ORDER BY id
                """)
            else:
                cursor.execute("""
                    SELECT
                        p.id,
                        p.nama,
                        p.harga,
                        COALESCE(sc.stok, 0) AS stok
                    FROM produk p
                    LEFT JOIN stok_cabang sc
                        ON sc.produk_id = p.id
                       AND sc.cabang_id = %s
                    ORDER BY p.id
                """, (cabang_id,))

            return cursor.fetchall()

        finally:
            cursor.close()
            connection.close()
