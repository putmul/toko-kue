-- Expert System untuk evaluasi supplier dan kebutuhan pembelian.
-- Jalankan setelah database_procurement.sql dan database_branch_stock.sql.
USE sistem_transaksi;

CREATE TABLE IF NOT EXISTS expert_rule (
    id INT NOT NULL AUTO_INCREMENT,
    kode_rule VARCHAR(80) NOT NULL,
    nama_rule VARCHAR(150) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    deskripsi TEXT NOT NULL,
    ambang DECIMAL(12,4) DEFAULT NULL,
    satuan VARCHAR(40) DEFAULT NULL,
    aktif TINYINT(1) NOT NULL DEFAULT 1,
    source_article_slug VARCHAR(220) DEFAULT NULL,
    diperbarui_oleh INT DEFAULT NULL,
    diperbarui_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_expert_rule_code (kode_rule),
    CONSTRAINT expert_rule_user_fk FOREIGN KEY (diperbarui_oleh)
        REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS expert_supplier_evaluation (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    supplier_id INT NOT NULL,
    produk_id INT NOT NULL,
    periode_mulai DATE NOT NULL,
    periode_selesai DATE NOT NULL,
    jumlah_pembelian INT NOT NULL DEFAULT 0,
    jumlah_diterima INT NOT NULL DEFAULT 0,
    jumlah_tepat_waktu INT NOT NULL DEFAULT 0,
    jumlah_terlambat INT NOT NULL DEFAULT 0,
    jumlah_insiden INT NOT NULL DEFAULT 0,
    tingkat_keterlambatan DECIMAL(6,3) NOT NULL DEFAULT 0,
    tingkat_insiden DECIMAL(6,3) NOT NULL DEFAULT 0,
    status_evaluasi VARCHAR(30) NOT NULL,
    diagnosis TEXT NOT NULL,
    rekomendasi_tindakan TEXT NOT NULL,
    dibuat_oleh INT DEFAULT NULL,
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_expert_eval_supplier_product (supplier_id, produk_id, id),
    KEY idx_expert_eval_status (status_evaluasi),
    CONSTRAINT expert_eval_supplier_fk FOREIGN KEY (supplier_id)
        REFERENCES supplier(id) ON DELETE CASCADE,
    CONSTRAINT expert_eval_product_fk FOREIGN KEY (produk_id)
        REFERENCES produk(id) ON DELETE CASCADE,
    CONSTRAINT expert_eval_user_fk FOREIGN KEY (dibuat_oleh)
        REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS expert_supplier_incident (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    supplier_id INT NOT NULL,
    produk_id INT NOT NULL,
    pembelian_id INT DEFAULT NULL,
    jenis VARCHAR(40) NOT NULL,
    jumlah INT NOT NULL DEFAULT 1,
    keterangan VARCHAR(500) NOT NULL,
    terjadi_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dibuat_oleh INT DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_expert_incident_supplier_product (supplier_id, produk_id),
    CONSTRAINT expert_incident_supplier_fk FOREIGN KEY (supplier_id)
        REFERENCES supplier(id) ON DELETE CASCADE,
    CONSTRAINT expert_incident_product_fk FOREIGN KEY (produk_id)
        REFERENCES produk(id) ON DELETE CASCADE,
    CONSTRAINT expert_incident_purchase_fk FOREIGN KEY (pembelian_id)
        REFERENCES pembelian(id) ON DELETE SET NULL,
    CONSTRAINT expert_incident_user_fk FOREIGN KEY (dibuat_oleh)
        REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS expert_supplier_action (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    supplier_id INT NOT NULL,
    produk_id INT NOT NULL,
    evaluation_id BIGINT UNSIGNED DEFAULT NULL,
    jenis_tindakan VARCHAR(50) NOT NULL,
    alasan TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'terbuka',
    tanggal_evaluasi_ulang DATE DEFAULT NULL,
    dibuat_oleh INT DEFAULT NULL,
    disetujui_oleh INT DEFAULT NULL,
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    diselesaikan_pada DATETIME DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_expert_action_status (status),
    CONSTRAINT expert_action_supplier_fk FOREIGN KEY (supplier_id)
        REFERENCES supplier(id) ON DELETE CASCADE,
    CONSTRAINT expert_action_product_fk FOREIGN KEY (produk_id)
        REFERENCES produk(id) ON DELETE CASCADE,
    CONSTRAINT expert_action_eval_fk FOREIGN KEY (evaluation_id)
        REFERENCES expert_supplier_evaluation(id) ON DELETE SET NULL,
    CONSTRAINT expert_action_created_user_fk FOREIGN KEY (dibuat_oleh)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT expert_action_approved_user_fk FOREIGN KEY (disetujui_oleh)
        REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS expert_notification (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    fingerprint VARCHAR(180) NOT NULL,
    jenis VARCHAR(50) NOT NULL,
    produk_id INT DEFAULT NULL,
    cabang_id INT DEFAULT NULL,
    supplier_id INT DEFAULT NULL,
    prioritas VARCHAR(20) NOT NULL DEFAULT 'normal',
    judul VARCHAR(200) NOT NULL,
    pesan TEXT NOT NULL,
    rule_code VARCHAR(80) DEFAULT NULL,
    source_article_slug VARCHAR(220) DEFAULT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'terbuka',
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dibaca_pada DATETIME DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_expert_notification_fingerprint (fingerprint),
    KEY idx_expert_notification_status (status),
    CONSTRAINT expert_notification_product_fk FOREIGN KEY (produk_id)
        REFERENCES produk(id) ON DELETE SET NULL,
    CONSTRAINT expert_notification_branch_fk FOREIGN KEY (cabang_id)
        REFERENCES cabang(id) ON DELETE SET NULL,
    CONSTRAINT expert_notification_supplier_fk FOREIGN KEY (supplier_id)
        REFERENCES supplier(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO expert_rule
    (kode_rule, nama_rule, domain, deskripsi, ambang, satuan, source_article_slug)
VALUES
    ('ES_PURCHASE_REORDER', 'Kebutuhan pembelian ulang', 'pembelian',
     'Stok tersedia berada pada atau di bawah titik pemesanan ulang.', 1, 'boolean',
     'sop-pengadaan-ulang-dan-notifikasi-stok'),
    ('ES_SUPPLIER_LATE_WARNING', 'Keterlambatan supplier', 'supplier',
     'Supplier masuk pengawasan jika tingkat keterlambatan melewati ambang.', 0.10, 'rasio',
     'sop-evaluasi-supplier'),
    ('ES_SUPPLIER_LATE_BLOCK', 'Keterlambatan kritis supplier', 'supplier',
     'Supplier tidak layak sementara jika tingkat keterlambatan terlalu tinggi.', 0.30, 'rasio',
     'sop-penanganan-supplier-bermasalah'),
    ('ES_SUPPLIER_INCIDENT_WARNING', 'Insiden supplier', 'supplier',
     'Supplier masuk pengawasan jika insiden kerusakan atau retur melewati ambang.', 0.10, 'rasio',
     'sop-evaluasi-supplier'),
    ('ES_SUPPLIER_INCIDENT_BLOCK', 'Insiden kritis supplier', 'supplier',
     'Supplier tidak layak sementara jika insiden melewati ambang kritis.', 0.20, 'rasio',
     'sop-penanganan-supplier-bermasalah')
ON DUPLICATE KEY UPDATE
    nama_rule = VALUES(nama_rule), deskripsi = VALUES(deskripsi),
    ambang = VALUES(ambang), satuan = VALUES(satuan),
    source_article_slug = VALUES(source_article_slug);
