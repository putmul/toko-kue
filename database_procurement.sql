-- Procurement, supplier-product mapping, and branch distribution.
USE sistem_transaksi;

CREATE TABLE IF NOT EXISTS supplier_produk (
    id INT(11) NOT NULL AUTO_INCREMENT,
    supplier_id INT(11) NOT NULL,
    produk_id INT(11) NOT NULL,
    harga_beli DECIMAL(12,2) NOT NULL,
    waktu_pengiriman_hari INT(11) NOT NULL DEFAULT 1,
    minimum_order INT(11) NOT NULL DEFAULT 1,
    tingkat_keandalan DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    status ENUM('aktif','nonaktif') NOT NULL DEFAULT 'aktif',
    PRIMARY KEY (id),
    UNIQUE KEY uq_supplier_produk (supplier_id, produk_id),
    CONSTRAINT supplier_produk_supplier_fk FOREIGN KEY (supplier_id) REFERENCES supplier(id),
    CONSTRAINT supplier_produk_produk_fk FOREIGN KEY (produk_id) REFERENCES produk(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

ALTER TABLE pembelian
    MODIFY cabang_id INT(11) NULL,
    MODIFY status ENUM('dipesan','diproses','diterima','dibatalkan') NOT NULL DEFAULT 'dipesan';

ALTER TABLE pembelian
    ADD COLUMN tanggal_diterima DATETIME NULL,
    ADD COLUMN catatan VARCHAR(255) NULL;

CREATE TABLE IF NOT EXISTS distribusi_stok (
    id INT(11) NOT NULL AUTO_INCREMENT,
    permintaan_id INT(11) DEFAULT NULL,
    employee_id INT(11) NOT NULL,
    cabang_id INT(11) NOT NULL,
    tanggal DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('diproses','dikirim','diterima','dibatalkan') NOT NULL DEFAULT 'diproses',
    catatan VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (id),
    KEY permintaan_id (permintaan_id),
    KEY employee_id (employee_id),
    KEY cabang_id (cabang_id),
    CONSTRAINT distribusi_permintaan_fk FOREIGN KEY (permintaan_id) REFERENCES permintaan_stok(id),
    CONSTRAINT distribusi_employee_fk FOREIGN KEY (employee_id) REFERENCES employee(id),
    CONSTRAINT distribusi_cabang_fk FOREIGN KEY (cabang_id) REFERENCES cabang(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS detail_distribusi_stok (
    id INT(11) NOT NULL AUTO_INCREMENT,
    distribusi_id INT(11) NOT NULL,
    produk_id INT(11) NOT NULL,
    jumlah INT(11) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_distribusi_produk (distribusi_id, produk_id),
    CONSTRAINT detail_distribusi_fk FOREIGN KEY (distribusi_id) REFERENCES distribusi_stok(id),
    CONSTRAINT detail_distribusi_produk_fk FOREIGN KEY (produk_id) REFERENCES produk(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS stok_mutasi (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    produk_id INT(11) NOT NULL,
    cabang_id INT(11) DEFAULT NULL,
    tipe ENUM('pembelian_supplier','distribusi_keluar','distribusi_masuk','penyesuaian') NOT NULL,
    referensi_id INT(11) DEFAULT NULL,
    jumlah INT(11) NOT NULL,
    stok_sebelum INT(11) NOT NULL,
    stok_sesudah INT(11) NOT NULL,
    dibuat_oleh INT(11) DEFAULT NULL,
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_mutasi_produk (produk_id),
    KEY idx_mutasi_referensi (tipe, referensi_id),
    CONSTRAINT stok_mutasi_produk_fk FOREIGN KEY (produk_id) REFERENCES produk(id),
    CONSTRAINT stok_mutasi_cabang_fk FOREIGN KEY (cabang_id) REFERENCES cabang(id),
    CONSTRAINT stok_mutasi_user_fk FOREIGN KEY (dibuat_oleh) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Relasi supplier-produk diisi oleh database_supplier_produk_seed.sql.
-- Jangan menghubungkan seluruh supplier dengan seluruh produk karena setiap
-- supplier hanya menyediakan jenis kue tertentu.
