-- Migrasi artikel KMS dari konteks produksi ke operasional toko/reseller.
USE knowledge_management;

INSERT IGNORE INTO km_category (nama, deskripsi) VALUES
    ('Penerimaan Barang', 'Pemeriksaan kue yang datang dari supplier.'),
    ('Penyimpanan Kue', 'Panduan penyimpanan dan rotasi stok kue.'),
    ('Masa Simpan', 'Pemeriksaan masa simpan dan penanganan produk mendekati kedaluwarsa.'),
    ('Retur Barang', 'Prosedur retur barang rusak atau tidak sesuai.'),
    ('Evaluasi Supplier', 'Evaluasi kinerja dan pemulihan supplier.');

UPDATE km_article
SET status = 'archived'
WHERE judul IN (
    'Resep Brownies Cokelat Standar'
);

INSERT INTO km_article
    (judul, slug, ringkasan, isi, category_id, author_user_id,
     visibility, status, published_by_user_id, published_at)
SELECT 'SOP Penerimaan Barang', 'sop-penerimaan-barang',
       'Prosedur memeriksa kue yang diterima dari supplier.',
       'Cocokkan barang dengan purchase order. Periksa jenis, jumlah, kondisi kemasan, tanggal penerimaan, dan masa simpan. Pisahkan barang yang rusak atau tidak sesuai. Barang yang lolos pemeriksaan dapat dicatat sebagai stok.',
       id, 1, 'internal', 'published', 1, NOW()
FROM km_category WHERE nama = 'Penerimaan Barang'
AND NOT EXISTS (SELECT 1 FROM km_article WHERE slug = 'sop-penerimaan-barang');

INSERT INTO km_article
    (judul, slug, ringkasan, isi, category_id, author_user_id,
     visibility, status, published_by_user_id, published_at)
SELECT 'SOP Penyimpanan Kue', 'sop-penyimpanan-kue',
       'Prosedur menyimpan dan merotasi stok kue.',
       'Simpan kue sesuai karakteristik produknya. Gunakan prinsip FEFO, yaitu produk dengan masa simpan paling pendek dikeluarkan lebih dahulu. Beri label tanggal penerimaan dan pisahkan produk yang mendekati batas masa simpan.',
       id, 1, 'internal', 'published', 1, NOW()
FROM km_category WHERE nama = 'Penyimpanan Kue'
AND NOT EXISTS (SELECT 1 FROM km_article WHERE slug = 'sop-penyimpanan-kue');

INSERT INTO km_article
    (judul, slug, ringkasan, isi, category_id, author_user_id,
     visibility, status, published_by_user_id, published_at)
SELECT 'SOP Pengecekan Masa Simpan', 'sop-pengecekan-masa-simpan',
       'Prosedur memeriksa masa simpan kue secara berkala.',
       'Periksa masa simpan setiap hari. Tandai produk normal, mendekati kedaluwarsa, dan kritis. Produk yang mendekati batas harus diprioritaskan untuk dijual, didiskon, atau diajukan untuk retur sesuai kebijakan supplier.',
       id, 1, 'internal', 'published', 1, NOW()
FROM km_category WHERE nama = 'Masa Simpan'
AND NOT EXISTS (SELECT 1 FROM km_article WHERE slug = 'sop-pengecekan-masa-simpan');

INSERT INTO km_article
    (judul, slug, ringkasan, isi, category_id, author_user_id,
     visibility, status, published_by_user_id, published_at)
SELECT 'SOP Retur Barang Rusak', 'sop-retur-barang-rusak',
       'Prosedur menangani barang rusak atau tidak sesuai pesanan.',
       'Pisahkan barang rusak dari stok jual. Catat produk, jumlah, alasan, supplier, dan nomor pembelian. Simpan bukti kondisi barang, ajukan retur kepada supplier, lalu perbarui stok dan histori performa supplier.',
       id, 1, 'internal', 'published', 1, NOW()
FROM km_category WHERE nama = 'Retur Barang'
AND NOT EXISTS (SELECT 1 FROM km_article WHERE slug = 'sop-retur-barang-rusak');

INSERT INTO km_article
    (judul, slug, ringkasan, isi, category_id, author_user_id,
     visibility, status, published_by_user_id, published_at)
SELECT 'SOP Evaluasi Supplier', 'sop-evaluasi-supplier',
       'Panduan mengevaluasi performa supplier berdasarkan histori pembelian.',
       'Evaluasi ketepatan waktu, jumlah barang diterima, kondisi barang, retur, dan kepatuhan masa simpan. Supplier dengan performa buruk diberi status pengawasan dan tindakan perbaikan. Evaluasi dilakukan per supplier dan produk.',
       id, 1, 'internal', 'published', 1, NOW()
FROM km_category WHERE nama = 'Evaluasi Supplier'
AND NOT EXISTS (SELECT 1 FROM km_article WHERE slug = 'sop-evaluasi-supplier');

INSERT INTO km_article
    (judul, slug, ringkasan, isi, category_id, author_user_id,
     visibility, status, published_by_user_id, published_at)
SELECT 'SOP Penanganan Supplier Bermasalah', 'sop-penanganan-supplier-bermasalah',
       'Panduan tindakan ketika performa supplier menurun.',
       'Tinjau alasan keterlambatan, kerusakan, atau kekurangan barang. Berikan peringatan, minta klarifikasi, batasi pemesanan, atau blokir sementara sesuai tingkat masalah. Semua tindakan harus dicatat dan disetujui manajer.',
       id, 1, 'internal', 'published', 1, NOW()
FROM km_category WHERE nama = 'Evaluasi Supplier'
AND NOT EXISTS (SELECT 1 FROM km_article WHERE slug = 'sop-penanganan-supplier-bermasalah');

INSERT INTO km_article
    (judul, slug, ringkasan, isi, category_id, author_user_id,
     visibility, status, published_by_user_id, published_at)
SELECT 'SOP Pengadaan Ulang dan Notifikasi Stok', 'sop-pengadaan-ulang-dan-notifikasi-stok',
       'Panduan menindaklanjuti pemberitahuan kebutuhan pembelian.',
       'Periksa notifikasi stok dan pastikan tidak ada purchase order aktif untuk produk yang sama. Tinjau supplier yang layak, lanjutkan analisis DSS, dan buat pembelian setelah mendapat persetujuan admin atau manajer.',
       id, 1, 'internal', 'published', 1, NOW()
FROM km_category WHERE nama = 'Evaluasi Supplier'
AND NOT EXISTS (SELECT 1 FROM km_article WHERE slug = 'sop-pengadaan-ulang-dan-notifikasi-stok');

INSERT IGNORE INTO km_article_version
    (article_id, version_number, judul, ringkasan, isi, changed_by_user_id)
SELECT id, 1, judul, ringkasan, isi, author_user_id
FROM km_article
WHERE slug IN (
    'sop-penerimaan-barang', 'sop-penyimpanan-kue',
    'sop-pengecekan-masa-simpan', 'sop-retur-barang-rusak',
    'sop-evaluasi-supplier', 'sop-penanganan-supplier-bermasalah',
    'sop-pengadaan-ulang-dan-notifikasi-stok'
);
