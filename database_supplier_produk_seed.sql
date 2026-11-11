-- Seeder supplier dan relasi supplier-produk untuk DSS pengadaan.
-- Jalankan setelah database_procurement.sql.
-- Skrip aman dijalankan berulang kali.

USE sistem_transaksi;

-- Dua supplier berikut sudah tersedia pada database awal.
-- Lima supplier baru ditambahkan berdasarkan nama perusahaan agar tidak
-- bergantung pada nomor ID AUTO_INCREMENT.
INSERT INTO supplier
    (nama_perusahaan, nama_kontak, telepon, email, alamat, status)
SELECT 'PT Kue Nusantara', 'Ibu Rani', '081234567893',
       'kue.nusantara@example.com', 'Bantul', 'aktif'
WHERE NOT EXISTS (
    SELECT 1 FROM supplier WHERE nama_perusahaan = 'PT Kue Nusantara'
);

INSERT INTO supplier
    (nama_perusahaan, nama_kontak, telepon, email, alamat, status)
SELECT 'CV Rasa Bahagia', 'Bapak Andi', '081234567894',
       'rasa.bahagia@example.com', 'Sleman', 'aktif'
WHERE NOT EXISTS (
    SELECT 1 FROM supplier WHERE nama_perusahaan = 'CV Rasa Bahagia'
);

INSERT INTO supplier
    (nama_perusahaan, nama_kontak, telepon, email, alamat, status)
SELECT 'UD Aroma Manis', 'Ibu Wulan', '081234567895',
       'aroma.manis@example.com', 'Kulon Progo', 'aktif'
WHERE NOT EXISTS (
    SELECT 1 FROM supplier WHERE nama_perusahaan = 'UD Aroma Manis'
);

INSERT INTO supplier
    (nama_perusahaan, nama_kontak, telepon, email, alamat, status)
SELECT 'PT Boga Prima', 'Ibu Siska', '081234567896',
       'boga.prima@example.com', 'Yogyakarta', 'aktif'
WHERE NOT EXISTS (
    SELECT 1 FROM supplier WHERE nama_perusahaan = 'PT Boga Prima'
);

INSERT INTO supplier
    (nama_perusahaan, nama_kontak, telepon, email, alamat, status)
SELECT 'CV Sari Rasa', 'Bapak Dedi', '081234567897',
       'sari.rasa@example.com', 'Gunungkidul', 'aktif'
WHERE NOT EXISTS (
    SELECT 1 FROM supplier WHERE nama_perusahaan = 'CV Sari Rasa'
);

-- Relasi diambil berdasarkan nama sehingga tetap benar meskipun ID produk
-- atau ID supplier berbeda pada database lain.
-- Harga beli, lead time, minimum order, dan reliabilitas sengaja dibuat
-- berbeda agar dapat dipakai sebagai kriteria DSS.
INSERT INTO supplier_produk
    (supplier_id, produk_id, harga_beli, waktu_pengiriman_hari,
     minimum_order, tingkat_keandalan, status)
SELECT s.id, p.id, x.harga_beli, x.waktu_pengiriman_hari,
       x.minimum_order, x.tingkat_keandalan, 'aktif'
FROM supplier s
CROSS JOIN produk p
JOIN (
    SELECT 'CV Makmur Jaya' AS supplier, 'Brownies Cokelat' AS produk, 24000.00 AS harga_beli, 2 AS waktu_pengiriman_hari, 10 AS minimum_order, 92.00 AS tingkat_keandalan
    UNION ALL SELECT 'CV Makmur Jaya', 'Brownies Keju', 29000.00, 2, 10, 92.00
    UNION ALL SELECT 'CV Makmur Jaya', 'Donat Gula', 1200.00, 2, 20, 92.00
    UNION ALL SELECT 'CV Makmur Jaya', 'Choco Chip Cookies', 10500.00, 3, 10, 90.00
    UNION ALL SELECT 'CV Makmur Jaya', 'Butter Cookies', 9800.00, 3, 10, 90.00
    UNION ALL SELECT 'PT Manis Sejahtera', 'Donat Gula', 1400.00, 3, 20, 88.00
    UNION ALL SELECT 'PT Manis Sejahtera', 'Donat Cokelat', 1800.00, 3, 20, 88.00
    UNION ALL SELECT 'PT Manis Sejahtera', 'Cheesecake', 33000.00, 3, 8, 87.00
    UNION ALL SELECT 'PT Manis Sejahtera', 'Red Velvet Cake', 37000.00, 4, 8, 85.00
    UNION ALL SELECT 'PT Manis Sejahtera', 'Bolu Pandan', 20000.00, 3, 10, 87.00
    UNION ALL SELECT 'PT Manis Sejahtera', 'Bolu Keju', 23000.00, 3, 10, 87.00
    UNION ALL SELECT 'PT Manis Sejahtera', 'Croissant', 7000.00, 2, 10, 90.00
    UNION ALL SELECT 'PT Manis Sejahtera', 'Cinnamon Roll', 7000.00, 2, 10, 90.00
    UNION ALL SELECT 'PT Kue Nusantara', 'Tiramisu', 35000.00, 2, 8, 91.00
    UNION ALL SELECT 'PT Kue Nusantara', 'Chiffon Cake', 21000.00, 2, 10, 90.00
    UNION ALL SELECT 'PT Kue Nusantara', 'Klepon Cake', 24500.00, 3, 8, 89.00
    UNION ALL SELECT 'PT Kue Nusantara', 'Carrot Cake', 30000.00, 3, 8, 89.00
    UNION ALL SELECT 'PT Kue Nusantara', 'Black Forest', 39000.00, 3, 6, 90.00
    UNION ALL SELECT 'PT Kue Nusantara', 'Lapis Legit', 4500.00, 2, 15, 92.00
    UNION ALL SELECT 'CV Rasa Bahagia', 'Brownies Cokelat', 25000.00, 3, 10, 88.00
    UNION ALL SELECT 'CV Rasa Bahagia', 'Brownies Keju', 30000.00, 3, 10, 88.00
    UNION ALL SELECT 'CV Rasa Bahagia', 'Bolu Cokelat', 21500.00, 2, 10, 91.00
    UNION ALL SELECT 'CV Rasa Bahagia', 'Donat Cokelat', 1900.00, 2, 20, 91.00
    UNION ALL SELECT 'CV Rasa Bahagia', 'Donat Keju', 2600.00, 2, 20, 91.00
    UNION ALL SELECT 'CV Rasa Bahagia', 'Kue buatan Mas Dais', 48000.00, 4, 5, 84.00
    UNION ALL SELECT 'UD Aroma Manis', 'Tiramisu', 36000.00, 3, 8, 87.00
    UNION ALL SELECT 'UD Aroma Manis', 'Chiffon Cake', 22000.00, 3, 10, 86.00
    UNION ALL SELECT 'UD Aroma Manis', 'Black Forest', 40000.00, 4, 6, 86.00
    UNION ALL SELECT 'UD Aroma Manis', 'Lapis Legit', 4700.00, 3, 15, 88.00
     UNION ALL SELECT 'UD Aroma Manis', 'Kue la Peace', 50000.00, 4, 5, 83.00
     UNION ALL SELECT 'UD Aroma Manis', 'Choco Chip Cookies', 11000.00, 3, 10, 89.00
     UNION ALL SELECT 'PT Boga Prima', 'Brownies Cokelat', 23800.00, 2, 10, 90.00
     UNION ALL SELECT 'PT Boga Prima', 'Brownies Keju', 28500.00, 2, 10, 90.00
     UNION ALL SELECT 'PT Boga Prima', 'Donat Gula', 1250.00, 2, 20, 91.00
     UNION ALL SELECT 'PT Boga Prima', 'Donat Cokelat', 1750.00, 2, 20, 91.00
     UNION ALL SELECT 'PT Boga Prima', 'Cheesecake', 32500.00, 3, 8, 89.00
     UNION ALL SELECT 'PT Boga Prima', 'Red Velvet Cake', 36500.00, 3, 8, 88.00
     UNION ALL SELECT 'PT Boga Prima', 'Bolu Pandan', 19800.00, 2, 10, 89.00
     UNION ALL SELECT 'PT Boga Prima', 'Bolu Keju', 22800.00, 2, 10, 89.00
     UNION ALL SELECT 'PT Boga Prima', 'Croissant', 6800.00, 2, 10, 91.00
     UNION ALL SELECT 'PT Boga Prima', 'Cinnamon Roll', 6800.00, 2, 10, 91.00
     UNION ALL SELECT 'PT Boga Prima', 'Tiramisu', 34500.00, 2, 8, 90.00
     UNION ALL SELECT 'PT Boga Prima', 'Chiffon Cake', 20800.00, 2, 10, 89.00
     UNION ALL SELECT 'PT Boga Prima', 'Klepon Cake', 24200.00, 3, 8, 88.00
     UNION ALL SELECT 'PT Boga Prima', 'Carrot Cake', 29500.00, 3, 8, 88.00
     UNION ALL SELECT 'PT Boga Prima', 'Black Forest', 38500.00, 3, 6, 89.00
     UNION ALL SELECT 'PT Boga Prima', 'Lapis Legit', 4400.00, 2, 15, 91.00
     UNION ALL SELECT 'PT Boga Prima', 'Bolu Cokelat', 21000.00, 2, 10, 90.00
     UNION ALL SELECT 'PT Boga Prima', 'Donat Keju', 2500.00, 2, 20, 90.00
     UNION ALL SELECT 'PT Boga Prima', 'Butter Cookies', 9600.00, 3, 10, 89.00
     UNION ALL SELECT 'CV Sari Rasa', 'Brownies Cokelat', 24500.00, 3, 10, 89.00
     UNION ALL SELECT 'CV Sari Rasa', 'Brownies Keju', 29500.00, 3, 10, 89.00
     UNION ALL SELECT 'CV Sari Rasa', 'Donat Gula', 1300.00, 3, 20, 89.00
     UNION ALL SELECT 'CV Sari Rasa', 'Donat Cokelat', 1850.00, 3, 20, 89.00
     UNION ALL SELECT 'CV Sari Rasa', 'Cheesecake', 33500.00, 4, 8, 86.00
     UNION ALL SELECT 'CV Sari Rasa', 'Red Velvet Cake', 37500.00, 4, 8, 85.00
     UNION ALL SELECT 'CV Sari Rasa', 'Bolu Pandan', 20200.00, 3, 10, 86.00
     UNION ALL SELECT 'CV Sari Rasa', 'Bolu Keju', 23200.00, 3, 10, 86.00
     UNION ALL SELECT 'CV Sari Rasa', 'Croissant', 7200.00, 3, 10, 88.00
     UNION ALL SELECT 'CV Sari Rasa', 'Cinnamon Roll', 7200.00, 3, 10, 88.00
     UNION ALL SELECT 'CV Sari Rasa', 'Tiramisu', 35500.00, 3, 8, 86.00
     UNION ALL SELECT 'CV Sari Rasa', 'Chiffon Cake', 21500.00, 3, 10, 85.00
     UNION ALL SELECT 'CV Sari Rasa', 'Klepon Cake', 25000.00, 4, 8, 85.00
     UNION ALL SELECT 'CV Sari Rasa', 'Carrot Cake', 30500.00, 4, 8, 85.00
     UNION ALL SELECT 'CV Sari Rasa', 'Black Forest', 39500.00, 4, 6, 86.00
     UNION ALL SELECT 'CV Sari Rasa', 'Lapis Legit', 4600.00, 3, 15, 89.00
     UNION ALL SELECT 'CV Sari Rasa', 'Bolu Cokelat', 22000.00, 3, 10, 89.00
     UNION ALL SELECT 'CV Sari Rasa', 'Donat Keju', 2700.00, 3, 20, 89.00
     UNION ALL SELECT 'CV Sari Rasa', 'Kue buatan Mas Dais', 47000.00, 4, 5, 85.00
     UNION ALL SELECT 'CV Sari Rasa', 'Kue la Peace', 49000.00, 4, 5, 84.00
     UNION ALL SELECT 'CV Sari Rasa', 'Butter Cookies', 10000.00, 3, 10, 88.00
 ) x ON x.supplier = s.nama_perusahaan AND x.produk = p.nama
WHERE s.status = 'aktif'
  AND NOT EXISTS (
      SELECT 1 FROM supplier_produk existing
      WHERE existing.supplier_id = s.id AND existing.produk_id = p.id
  );

-- Verifikasi: seluruh produk harus memiliki minimal satu supplier.
SELECT p.id AS produk_id, p.nama AS produk,
       COUNT(CASE WHEN sp.status = 'aktif' AND s.status = 'aktif'
                  THEN sp.supplier_id END) AS jumlah_supplier_aktif
FROM produk p
LEFT JOIN supplier_produk sp ON sp.produk_id = p.id
LEFT JOIN supplier s ON s.id = sp.supplier_id
GROUP BY p.id, p.nama
ORDER BY p.id;

SELECT s.id AS supplier_id, s.nama_perusahaan, p.id AS produk_id,
       p.nama AS produk, sp.harga_beli, sp.waktu_pengiriman_hari,
       sp.minimum_order, sp.tingkat_keandalan
FROM supplier_produk sp
JOIN supplier s ON s.id = sp.supplier_id
JOIN produk p ON p.id = sp.produk_id
ORDER BY s.id, p.id;
