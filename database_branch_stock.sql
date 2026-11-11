-- Jalankan sekali pada database sistem_transaksi.
-- produk.stok tetap dipakai sebagai stok utama di gudang.

CREATE TABLE IF NOT EXISTS stok_cabang (
    cabang_id INT(11) NOT NULL,
    produk_id INT(11) NOT NULL,
    stok INT(11) NOT NULL DEFAULT 0,
    PRIMARY KEY (cabang_id, produk_id),
    CONSTRAINT stok_cabang_ibfk_1
        FOREIGN KEY (cabang_id) REFERENCES cabang (id),
    CONSTRAINT stok_cabang_ibfk_2
        FOREIGN KEY (produk_id) REFERENCES produk (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS permintaan_stok (
    id INT(11) NOT NULL AUTO_INCREMENT,
    employee_id INT(11) NOT NULL,
    cabang_id INT(11) NOT NULL,
    tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('diproses','selesai','dibatalkan') NOT NULL DEFAULT 'diproses',
    catatan VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (id),
    KEY employee_id (employee_id),
    KEY cabang_id (cabang_id),
    CONSTRAINT permintaan_stok_ibfk_1
        FOREIGN KEY (employee_id) REFERENCES employee (id),
    CONSTRAINT permintaan_stok_ibfk_2
        FOREIGN KEY (cabang_id) REFERENCES cabang (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS detail_permintaan_stok (
    id INT(11) NOT NULL AUTO_INCREMENT,
    permintaan_id INT(11) NOT NULL,
    produk_id INT(11) NOT NULL,
    jumlah INT(11) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uniq_permintaan_produk (permintaan_id, produk_id),
    KEY produk_id (produk_id),
    CONSTRAINT detail_permintaan_stok_ibfk_1
        FOREIGN KEY (permintaan_id) REFERENCES permintaan_stok (id),
    CONSTRAINT detail_permintaan_stok_ibfk_2
        FOREIGN KEY (produk_id) REFERENCES produk (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS rekap_transaksi (
    id INT(11) NOT NULL AUTO_INCREMENT,
    transaksi_id INT(11) NOT NULL,
    employee_id INT(11) NOT NULL,
    cabang_id INT(11) NOT NULL,
    status_rekap ENUM('berhasil','dibatalkan') NOT NULL DEFAULT 'berhasil',
    catatan VARCHAR(255) DEFAULT NULL,
    tanggal_rekap DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uniq_rekap_transaksi (transaksi_id),
    KEY employee_id (employee_id),
    KEY cabang_id (cabang_id),
    CONSTRAINT rekap_transaksi_ibfk_1
        FOREIGN KEY (transaksi_id) REFERENCES transaksi (id),
    CONSTRAINT rekap_transaksi_ibfk_2
        FOREIGN KEY (employee_id) REFERENCES employee (id),
    CONSTRAINT rekap_transaksi_ibfk_3
        FOREIGN KEY (cabang_id) REFERENCES cabang (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
