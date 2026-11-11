-- ============================================================
-- MIS dan Monitoring untuk database sistem_transaksi
--
-- Modul ini hanya menyimpan data ringkasan dan monitoring.
-- Data transaksi, stok, cabang, dan request tetap dikelola oleh
-- modul TPS/OAS yang sudah ada.
--
-- Skrip bersifat idempotent: aman dijalankan ulang.
-- ============================================================

USE sistem_transaksi;

-- Ringkasan penjualan per hari dan cabang.
CREATE TABLE IF NOT EXISTS mis_penjualan_harian (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    tanggal DATE NOT NULL,
    cabang_id INT(11) NOT NULL,
    jumlah_transaksi INT UNSIGNED NOT NULL DEFAULT 0,
    transaksi_berhasil INT UNSIGNED NOT NULL DEFAULT 0,
    transaksi_diproses INT UNSIGNED NOT NULL DEFAULT 0,
    transaksi_dikirim INT UNSIGNED NOT NULL DEFAULT 0,
    transaksi_selesai INT UNSIGNED NOT NULL DEFAULT 0,
    transaksi_dibatalkan INT UNSIGNED NOT NULL DEFAULT 0,
    pendapatan_berhasil DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    rata_rata_transaksi DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    diperbarui_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_mis_penjualan_harian (tanggal, cabang_id),
    KEY idx_mis_penjualan_tanggal (tanggal),
    CONSTRAINT mis_penjualan_harian_cabang_fk
        FOREIGN KEY (cabang_id) REFERENCES cabang (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Ringkasan produk terjual per hari dan cabang.
CREATE TABLE IF NOT EXISTS mis_penjualan_produk_harian (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    tanggal DATE NOT NULL,
    cabang_id INT(11) NOT NULL,
    produk_id INT(11) NOT NULL,
    jumlah_terjual INT UNSIGNED NOT NULL DEFAULT 0,
    pendapatan DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    diperbarui_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_mis_penjualan_produk (tanggal, cabang_id, produk_id),
    KEY idx_mis_produk_tanggal (tanggal),
    CONSTRAINT mis_penjualan_produk_cabang_fk
        FOREIGN KEY (cabang_id) REFERENCES cabang (id),
    CONSTRAINT mis_penjualan_produk_produk_fk
        FOREIGN KEY (produk_id) REFERENCES produk (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Snapshot stok harian untuk kebutuhan monitoring dan histori.
CREATE TABLE IF NOT EXISTS mis_stok_snapshot (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    tanggal_snapshot DATE NOT NULL,
    cabang_id INT(11) NOT NULL,
    produk_id INT(11) NOT NULL,
    stok_gudang INT NOT NULL DEFAULT 0,
    stok_cabang INT NOT NULL DEFAULT 0,
    stok_minimum INT NOT NULL DEFAULT 0,
    status_stok ENUM('normal','menipis','habis') NOT NULL DEFAULT 'normal',
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    diperbarui_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_mis_stok_snapshot
        (tanggal_snapshot, cabang_id, produk_id),
    KEY idx_mis_stok_status (status_stok),
    CONSTRAINT mis_stok_snapshot_cabang_fk
        FOREIGN KEY (cabang_id) REFERENCES cabang (id),
    CONSTRAINT mis_stok_snapshot_produk_fk
        FOREIGN KEY (produk_id) REFERENCES produk (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Ringkasan permintaan stok per hari dan cabang.
CREATE TABLE IF NOT EXISTS mis_permintaan_stok_harian (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    tanggal DATE NOT NULL,
    cabang_id INT(11) NOT NULL,
    jumlah_request INT UNSIGNED NOT NULL DEFAULT 0,
    request_diproses INT UNSIGNED NOT NULL DEFAULT 0,
    request_selesai INT UNSIGNED NOT NULL DEFAULT 0,
    request_dibatalkan INT UNSIGNED NOT NULL DEFAULT 0,
    total_item_diminta INT UNSIGNED NOT NULL DEFAULT 0,
    total_item_selesai INT UNSIGNED NOT NULL DEFAULT 0,
    dibuat_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    diperbarui_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_mis_permintaan_harian (tanggal, cabang_id),
    KEY idx_mis_permintaan_tanggal (tanggal),
    CONSTRAINT mis_permintaan_harian_cabang_fk
        FOREIGN KEY (cabang_id) REFERENCES cabang (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Daftar alert monitoring yang perlu diperhatikan oleh manajemen.
CREATE TABLE IF NOT EXISTS mis_monitoring_alert (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    fingerprint VARCHAR(150) NOT NULL,
    tipe_sumber ENUM('stok','permintaan_stok','transaksi') NOT NULL,
    sumber_id BIGINT UNSIGNED DEFAULT NULL,
    cabang_id INT(11) DEFAULT NULL,
    produk_id INT(11) DEFAULT NULL,
    tingkat ENUM('info','warning','critical') NOT NULL DEFAULT 'info',
    judul VARCHAR(150) NOT NULL,
    pesan VARCHAR(500) NOT NULL,
    status ENUM('terbuka','ditangani') NOT NULL DEFAULT 'terbuka',
    terdeteksi_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ditangani_pada DATETIME DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_mis_alert_fingerprint (fingerprint),
    KEY idx_mis_alert_status (status),
    KEY idx_mis_alert_cabang (cabang_id),
    CONSTRAINT mis_alert_cabang_fk
        FOREIGN KEY (cabang_id) REFERENCES cabang (id)
        ON DELETE SET NULL,
    CONSTRAINT mis_alert_produk_fk
        FOREIGN KEY (produk_id) REFERENCES produk (id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ============================================================
-- Pengisian data MIS dari data operasional yang sudah tersedia
-- ============================================================

-- 1. Agregasi transaksi per hari dan cabang.
INSERT INTO mis_penjualan_harian (
    tanggal, cabang_id, jumlah_transaksi, transaksi_berhasil,
    transaksi_diproses, transaksi_dikirim, transaksi_selesai,
    transaksi_dibatalkan, pendapatan_berhasil, rata_rata_transaksi
)
SELECT
    DATE(t.tanggal) AS tanggal,
    t.cabang_id,
    COUNT(*) AS jumlah_transaksi,
    SUM(CASE WHEN r.status_rekap = 'berhasil' THEN 1 ELSE 0 END),
    SUM(CASE WHEN t.status = 'diproses' THEN 1 ELSE 0 END),
    SUM(CASE WHEN t.status = 'dikirim' THEN 1 ELSE 0 END),
    SUM(CASE WHEN t.status = 'selesai' THEN 1 ELSE 0 END),
    SUM(CASE WHEN t.status = 'dibatalkan' THEN 1 ELSE 0 END),
    COALESCE(SUM(
        CASE WHEN r.status_rekap = 'berhasil'
             THEN t.total_harga ELSE 0 END
    ), 0),
    COALESCE(AVG(
        CASE WHEN r.status_rekap = 'berhasil'
             THEN t.total_harga ELSE NULL END
    ), 0)
FROM transaksi t
LEFT JOIN rekap_transaksi r ON r.transaksi_id = t.id
WHERE t.cabang_id IS NOT NULL
GROUP BY DATE(t.tanggal), t.cabang_id
ON DUPLICATE KEY UPDATE
    jumlah_transaksi = VALUES(jumlah_transaksi),
    transaksi_berhasil = VALUES(transaksi_berhasil),
    transaksi_diproses = VALUES(transaksi_diproses),
    transaksi_dikirim = VALUES(transaksi_dikirim),
    transaksi_selesai = VALUES(transaksi_selesai),
    transaksi_dibatalkan = VALUES(transaksi_dibatalkan),
    pendapatan_berhasil = VALUES(pendapatan_berhasil),
    rata_rata_transaksi = VALUES(rata_rata_transaksi);

-- 2. Agregasi produk yang terjual dari transaksi yang berhasil direkap.
INSERT INTO mis_penjualan_produk_harian (
    tanggal, cabang_id, produk_id, jumlah_terjual, pendapatan
)
SELECT
    DATE(t.tanggal) AS tanggal,
    t.cabang_id,
    dt.produk_id,
    SUM(dt.jumlah),
    SUM(dt.subtotal)
FROM transaksi t
JOIN rekap_transaksi r
    ON r.transaksi_id = t.id
   AND r.status_rekap = 'berhasil'
JOIN detail_transaksi dt ON dt.transaksi_id = t.id
WHERE t.cabang_id IS NOT NULL
GROUP BY DATE(t.tanggal), t.cabang_id, dt.produk_id
ON DUPLICATE KEY UPDATE
    jumlah_terjual = VALUES(jumlah_terjual),
    pendapatan = VALUES(pendapatan);

-- 3. Snapshot stok terbaru untuk setiap produk di setiap cabang aktif.
INSERT INTO mis_stok_snapshot (
    tanggal_snapshot, cabang_id, produk_id, stok_gudang,
    stok_cabang, stok_minimum, status_stok
)
SELECT
    CURDATE(),
    c.id,
    p.id,
    p.stok,
    COALESCE(sc.stok, 0),
    p.stok_minimum,
    CASE
        WHEN COALESCE(sc.stok, 0) <= 0 THEN 'habis'
        WHEN COALESCE(sc.stok, 0) <= p.stok_minimum THEN 'menipis'
        ELSE 'normal'
    END
FROM cabang c
CROSS JOIN produk p
LEFT JOIN stok_cabang sc
    ON sc.cabang_id = c.id
   AND sc.produk_id = p.id
WHERE c.status = 'aktif'
ON DUPLICATE KEY UPDATE
    stok_gudang = VALUES(stok_gudang),
    stok_cabang = VALUES(stok_cabang),
    stok_minimum = VALUES(stok_minimum),
    status_stok = VALUES(status_stok);

-- 4. Agregasi permintaan stok per hari dan cabang.
INSERT INTO mis_permintaan_stok_harian (
    tanggal, cabang_id, jumlah_request, request_diproses,
    request_selesai, request_dibatalkan, total_item_diminta,
    total_item_selesai
)
SELECT
    DATE(ps.tanggal),
    ps.cabang_id,
    COUNT(DISTINCT ps.id),
    COUNT(DISTINCT CASE WHEN ps.status = 'diproses' THEN ps.id END),
    COUNT(DISTINCT CASE WHEN ps.status = 'selesai' THEN ps.id END),
    COUNT(DISTINCT CASE WHEN ps.status = 'dibatalkan' THEN ps.id END),
    COALESCE(SUM(dps.jumlah), 0),
    COALESCE(SUM(CASE WHEN ps.status = 'selesai' THEN dps.jumlah ELSE 0 END), 0)
FROM permintaan_stok ps
JOIN detail_permintaan_stok dps ON dps.permintaan_id = ps.id
GROUP BY DATE(ps.tanggal), ps.cabang_id
ON DUPLICATE KEY UPDATE
    jumlah_request = VALUES(jumlah_request),
    request_diproses = VALUES(request_diproses),
    request_selesai = VALUES(request_selesai),
    request_dibatalkan = VALUES(request_dibatalkan),
    total_item_diminta = VALUES(total_item_diminta),
    total_item_selesai = VALUES(total_item_selesai);

-- 5. Alert stok menipis atau habis.
INSERT INTO mis_monitoring_alert (
    fingerprint, tipe_sumber, sumber_id, cabang_id, produk_id,
    tingkat, judul, pesan, status
)
SELECT
    CONCAT('stok:', sc.cabang_id, ':', sc.produk_id),
    'stok',
    NULL,
    sc.cabang_id,
    sc.produk_id,
    CASE WHEN sc.stok <= 0 THEN 'critical' ELSE 'warning' END,
    CASE WHEN sc.stok <= 0 THEN 'Stok produk habis' ELSE 'Stok produk menipis' END,
    CONCAT(
        'Stok ', p.nama, ' di ', c.nama, ' saat ini ', sc.stok,
        ' unit. Batas minimum: ', p.stok_minimum, ' unit.'
    ),
    'terbuka'
FROM stok_cabang sc
JOIN produk p ON p.id = sc.produk_id
JOIN cabang c ON c.id = sc.cabang_id
WHERE c.status = 'aktif'
  AND sc.stok <= p.stok_minimum
ON DUPLICATE KEY UPDATE
    tingkat = VALUES(tingkat),
    judul = VALUES(judul),
    pesan = VALUES(pesan),
    status = 'terbuka',
    ditangani_pada = NULL;

-- 6. Alert permintaan stok yang masih diproses.
INSERT INTO mis_monitoring_alert (
    fingerprint, tipe_sumber, sumber_id, cabang_id,
    tingkat, judul, pesan, status
)
SELECT
    CONCAT('permintaan_stok:', ps.id),
    'permintaan_stok',
    ps.id,
    ps.cabang_id,
    'warning',
    'Permintaan stok menunggu proses',
    CONCAT(
        'Permintaan stok #', ps.id, ' dari ', c.nama,
        ' dibuat pada ', DATE_FORMAT(ps.tanggal, '%Y-%m-%d %H:%i'),
        ' dan masih berstatus diproses.'
    ),
    'terbuka'
FROM permintaan_stok ps
JOIN cabang c ON c.id = ps.cabang_id
WHERE ps.status = 'diproses'
ON DUPLICATE KEY UPDATE
    cabang_id = VALUES(cabang_id),
    tingkat = VALUES(tingkat),
    judul = VALUES(judul),
    pesan = VALUES(pesan),
    status = 'terbuka',
    ditangani_pada = NULL;
