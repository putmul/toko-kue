-- Expert System pemilihan kue untuk pelanggan.
-- Jalankan setelah schema inti dan database_branch_stock.sql.
USE sistem_transaksi;

CREATE TABLE IF NOT EXISTS customer_es_product_profile (
    id INT NOT NULL AUTO_INCREMENT,
    produk_id INT NOT NULL,
    intensitas_coklat TINYINT UNSIGNED NOT NULL DEFAULT 0,
    tingkat_kemanisan TINYINT UNSIGNED NOT NULL DEFAULT 0,
    tingkat_kepahitan TINYINT UNSIGNED NOT NULL DEFAULT 0,
    tekstur ENUM('lembut','renyah','creamy') NOT NULL DEFAULT 'lembut',
    kategori ENUM('cake','brownies','donat','cookies','pastry','lainnya')
        NOT NULL DEFAULT 'lainnya',
    mengandung_susu TINYINT(1) NOT NULL DEFAULT 0,
    mengandung_telur TINYINT(1) NOT NULL DEFAULT 0,
    mengandung_kacang TINYINT(1) NOT NULL DEFAULT 0,
    mengandung_gluten TINYINT(1) NOT NULL DEFAULT 0,
    diperbarui_oleh INT DEFAULT NULL,
    diperbarui_pada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_customer_es_produk (produk_id),
    CONSTRAINT customer_es_produk_fk
        FOREIGN KEY (produk_id) REFERENCES produk(id) ON DELETE CASCADE,
    CONSTRAINT customer_es_user_fk
        FOREIGN KEY (diperbarui_oleh) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Profil awal untuk katalog contoh. Admin tetap dapat mengoreksinya melalui UI.
INSERT INTO customer_es_product_profile
    (produk_id, intensitas_coklat, tingkat_kemanisan, tingkat_kepahitan,
     tekstur, kategori, mengandung_susu, mengandung_telur,
     mengandung_kacang, mengandung_gluten)
SELECT p.id, x.coklat, x.manis, x.pahit, x.tekstur, x.kategori,
       x.susu, x.telur, x.kacang, x.gluten
FROM produk p
JOIN (
    SELECT 'Brownies Cokelat' nama, 95 coklat, 75 manis, 5 pahit, 'lembut' tekstur, 'brownies' kategori, 1 susu, 1 telur, 0 kacang, 1 gluten
    UNION ALL SELECT 'Brownies Keju', 35, 75, 5, 'lembut', 'brownies', 1, 1, 0, 1
    UNION ALL SELECT 'Cheesecake', 20, 80, 5, 'creamy', 'cake', 1, 1, 0, 1
    UNION ALL SELECT 'Red Velvet Cake', 20, 75, 5, 'lembut', 'cake', 1, 1, 0, 1
    UNION ALL SELECT 'Tiramisu', 65, 65, 20, 'creamy', 'cake', 1, 1, 0, 1
    UNION ALL SELECT 'Chiffon Cake', 10, 55, 5, 'lembut', 'cake', 0, 1, 0, 1
    UNION ALL SELECT 'Bolu Pandan', 5, 65, 5, 'lembut', 'cake', 0, 1, 0, 1
    UNION ALL SELECT 'Bolu Cokelat', 80, 70, 5, 'lembut', 'cake', 1, 1, 0, 1
    UNION ALL SELECT 'Bolu Keju', 30, 70, 5, 'lembut', 'cake', 1, 1, 0, 1
    UNION ALL SELECT 'Klepon Cake', 5, 80, 5, 'lembut', 'cake', 0, 1, 0, 1
    UNION ALL SELECT 'Carrot Cake', 10, 65, 5, 'lembut', 'cake', 1, 1, 0, 1
    UNION ALL SELECT 'Black Forest', 85, 75, 10, 'lembut', 'cake', 1, 1, 0, 1
    UNION ALL SELECT 'Lapis Legit', 10, 90, 5, 'lembut', 'cake', 1, 1, 0, 1
    UNION ALL SELECT 'Donat Cokelat', 80, 85, 5, 'lembut', 'donat', 1, 1, 0, 1
    UNION ALL SELECT 'Donat Keju', 25, 85, 5, 'lembut', 'donat', 1, 1, 0, 1
    UNION ALL SELECT 'Donat Gula', 5, 90, 5, 'lembut', 'donat', 0, 1, 0, 1
    UNION ALL SELECT 'Croissant', 10, 45, 5, 'renyah', 'pastry', 1, 1, 0, 1
    UNION ALL SELECT 'Cinnamon Roll', 15, 80, 5, 'lembut', 'pastry', 1, 1, 0, 1
    UNION ALL SELECT 'Choco Chip Cookies', 75, 60, 5, 'renyah', 'cookies', 1, 1, 0, 1
    UNION ALL SELECT 'Butter Cookies', 10, 65, 5, 'renyah', 'cookies', 1, 1, 0, 1
    UNION ALL SELECT 'Kue buatan Mas Dais', 50, 70, 10, 'lembut', 'lainnya', 1, 1, 0, 1
    UNION ALL SELECT 'Kue la Peace', 30, 65, 10, 'creamy', 'lainnya', 1, 1, 0, 1
) x ON x.nama = p.nama
ON DUPLICATE KEY UPDATE
    intensitas_coklat = VALUES(intensitas_coklat),
    tingkat_kemanisan = VALUES(tingkat_kemanisan),
    tingkat_kepahitan = VALUES(tingkat_kepahitan),
    tekstur = VALUES(tekstur),
    kategori = VALUES(kategori),
    mengandung_susu = VALUES(mengandung_susu),
    mengandung_telur = VALUES(mengandung_telur),
    mengandung_kacang = VALUES(mengandung_kacang),
    mengandung_gluten = VALUES(mengandung_gluten);
