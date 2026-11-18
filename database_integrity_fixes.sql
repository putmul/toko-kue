-- Jalankan sekali setelah database_procurement.sql dan database_dss.sql.
-- Migrasi untuk menyamakan ledger stok dan menghubungkan DSS dengan pembelian.
USE sistem_transaksi;

-- Some older installations do not yet have the reorder threshold.
SET @has_stok_minimum = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'produk'
      AND column_name = 'stok_minimum'
);
SET @sql_stok_minimum = IF(
    @has_stok_minimum = 0,
    'ALTER TABLE produk ADD COLUMN stok_minimum INT NOT NULL DEFAULT 0',
    'SELECT 1'
);
PREPARE stmt_stok_minimum FROM @sql_stok_minimum;
EXECUTE stmt_stok_minimum;
DEALLOCATE PREPARE stmt_stok_minimum;

ALTER TABLE stok_mutasi
    MODIFY tipe ENUM(
        'pembelian_supplier',
        'distribusi_keluar',
        'distribusi_masuk',
        'penjualan',
        'pembatalan',
        'penyesuaian'
    ) NOT NULL;

ALTER TABLE stok_mutasi
    ADD COLUMN catatan VARCHAR(255) NULL;

ALTER TABLE pembelian
    ADD COLUMN dss_rekomendasi_id BIGINT UNSIGNED NULL,
    ADD KEY idx_pembelian_dss_rekomendasi (dss_rekomendasi_id),
    ADD CONSTRAINT pembelian_dss_rekomendasi_fk
        FOREIGN KEY (dss_rekomendasi_id)
        REFERENCES dss_rekomendasi_pengadaan(id)
        ON DELETE SET NULL;
