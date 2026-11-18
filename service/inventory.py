"""Shared stock mutation helpers.

Every operational stock change should be made while holding the relevant row
lock and should leave an audit record in ``stok_mutasi``.
"""


def record_mutation(cursor, produk_id, cabang_id, tipe, referensi_id,
                    jumlah, stok_sebelum, stok_sesudah, dibuat_oleh=None,
                    catatan=None):
    cursor.execute("""
        INSERT INTO stok_mutasi
            (produk_id, cabang_id, tipe, referensi_id, jumlah,
             stok_sebelum, stok_sesudah, dibuat_oleh, catatan)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        produk_id, cabang_id, tipe, referensi_id, jumlah,
        stok_sebelum, stok_sesudah, dibuat_oleh, catatan
    ))


def ensure_non_negative(value, message="Stok tidak boleh negatif."):
    if value < 0:
        raise ValueError(message)
