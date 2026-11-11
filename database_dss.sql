-- DSS pemilihan supplier dan rekomendasi pengadaan.
-- Jalankan setelah database_procurement.sql, database_branch_stock.sql,
-- dan database_supplier_produk_seed.sql.
USE sistem_transaksi;

CREATE TABLE IF NOT EXISTS dss_kriteria_supplier (
    id INT(11) NOT NULL AUTO_INCREMENT,
    kode_kriteria VARCHAR(50) NOT NULL,
    nama_kriteria VARCHAR(100) NOT NULL,
    tipe ENUM('cost','benefit') NOT NULL,
    bobot DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    aktif TINYINT(1) NOT NULL DEFAULT 1,
    sumber_data VARCHAR(50) NOT NULL,
    diperbarui_oleh INT(11) DEFAULT NULL,
    diperbarui_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_dss_kriteria_kode (kode_kriteria),
    CONSTRAINT dss_kriteria_user_fk
        FOREIGN KEY (diperbarui_oleh) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT IGNORE INTO dss_kriteria_supplier
    (kode_kriteria, nama_kriteria, tipe, bobot, aktif, sumber_data)
VALUES
    ('harga_beli', 'Harga beli', 'cost', 35.00, 1, 'harga_beli'),
    ('waktu_pengiriman', 'Waktu pengiriman', 'cost', 25.00, 1, 'waktu_pengiriman_hari'),
    ('minimum_order', 'Minimum order', 'cost', 15.00, 1, 'minimum_order'),
    ('keandalan', 'Tingkat keandalan', 'benefit', 25.00, 1, 'tingkat_keandalan');

CREATE TABLE IF NOT EXISTS dss_rekomendasi_pengadaan (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    produk_id INT(11) NOT NULL,
    cabang_id INT(11) DEFAULT NULL,
    jumlah_kebutuhan INT(11) NOT NULL,
    stok_gudang INT(11) NOT NULL DEFAULT 0,
    stok_cabang INT(11) NOT NULL DEFAULT 0,
    supplier_terpilih_id INT(11) DEFAULT NULL,
    jumlah_pembelian INT(11) NOT NULL DEFAULT 0,
    total_biaya DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    skor_tertinggi DECIMAL(10,6) NOT NULL DEFAULT 0.000000,
    status ENUM('draft','digunakan') NOT NULL DEFAULT 'draft',
    dibuat_oleh INT(11) NOT NULL,
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_dss_rekomendasi_produk (produk_id),
    KEY idx_dss_rekomendasi_tanggal (dibuat_pada),
    CONSTRAINT dss_rekomendasi_produk_fk
        FOREIGN KEY (produk_id) REFERENCES produk(id),
    CONSTRAINT dss_rekomendasi_cabang_fk
        FOREIGN KEY (cabang_id) REFERENCES cabang(id)
        ON DELETE SET NULL,
    CONSTRAINT dss_rekomendasi_supplier_fk
        FOREIGN KEY (supplier_terpilih_id) REFERENCES supplier(id)
        ON DELETE SET NULL,
    CONSTRAINT dss_rekomendasi_user_fk
        FOREIGN KEY (dibuat_oleh) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS dss_rekomendasi_detail (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    rekomendasi_id BIGINT UNSIGNED NOT NULL,
    supplier_id INT(11) NOT NULL,
    harga_beli DECIMAL(12,2) NOT NULL,
    waktu_pengiriman_hari INT(11) NOT NULL,
    minimum_order INT(11) NOT NULL,
    tingkat_keandalan DECIMAL(5,2) NOT NULL,
    skor_harga DECIMAL(10,6) NOT NULL DEFAULT 0.000000,
    skor_pengiriman DECIMAL(10,6) NOT NULL DEFAULT 0.000000,
    skor_minimum_order DECIMAL(10,6) NOT NULL DEFAULT 0.000000,
    skor_keandalan DECIMAL(10,6) NOT NULL DEFAULT 0.000000,
    skor_akhir DECIMAL(10,6) NOT NULL DEFAULT 0.000000,
    peringkat INT(11) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_dss_detail_supplier (rekomendasi_id, supplier_id),
    CONSTRAINT dss_detail_rekomendasi_fk
        FOREIGN KEY (rekomendasi_id) REFERENCES dss_rekomendasi_pengadaan(id)
        ON DELETE CASCADE,
    CONSTRAINT dss_detail_supplier_fk
        FOREIGN KEY (supplier_id) REFERENCES supplier(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
