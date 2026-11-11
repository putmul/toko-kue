CREATE DATABASE IF NOT EXISTS knowledge_management
    CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE knowledge_management;

CREATE TABLE IF NOT EXISTS km_category (
    id INT NOT NULL AUTO_INCREMENT,
    nama VARCHAR(100) NOT NULL,
    deskripsi VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_km_category_nama (nama)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS km_article (
    id INT NOT NULL AUTO_INCREMENT,
    judul VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL,
    ringkasan VARCHAR(500) DEFAULT NULL,
    isi LONGTEXT NOT NULL,
    category_id INT NOT NULL,
    author_user_id INT NOT NULL,
    related_product_id INT DEFAULT NULL,
    related_branch_id INT DEFAULT NULL,
    visibility ENUM('internal','cabang','publik') NOT NULL DEFAULT 'internal',
    status ENUM('draft','menunggu_review','published','archived') NOT NULL DEFAULT 'draft',
    published_by_user_id INT DEFAULT NULL,
    published_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_km_article_slug (slug),
    KEY category_id (category_id),
    KEY author_user_id (author_user_id),
    KEY related_product_id (related_product_id),
    KEY related_branch_id (related_branch_id),
    CONSTRAINT km_article_category_fk
        FOREIGN KEY (category_id) REFERENCES km_category (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS km_article_version (
    id INT NOT NULL AUTO_INCREMENT,
    article_id INT NOT NULL,
    version_number INT NOT NULL,
    judul VARCHAR(200) NOT NULL,
    ringkasan VARCHAR(500) DEFAULT NULL,
    isi LONGTEXT NOT NULL,
    changed_by_user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_km_article_version (article_id, version_number),
    CONSTRAINT km_article_version_article_fk
        FOREIGN KEY (article_id) REFERENCES km_article (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS km_recipe (
    article_id INT NOT NULL,
    hasil_jumlah DECIMAL(10,2) DEFAULT NULL,
    hasil_satuan VARCHAR(50) DEFAULT NULL,
    suhu_oven_celsius INT DEFAULT NULL,
    durasi_menit INT DEFAULT NULL,
    peralatan TEXT DEFAULT NULL,
    penyimpanan TEXT DEFAULT NULL,
    informasi_alergen VARCHAR(500) DEFAULT NULL,
    PRIMARY KEY (article_id),
    CONSTRAINT km_recipe_article_fk
        FOREIGN KEY (article_id) REFERENCES km_article (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS km_recipe_ingredient (
    id INT NOT NULL AUTO_INCREMENT,
    article_id INT NOT NULL,
    nama_bahan VARCHAR(150) NOT NULL,
    jumlah DECIMAL(10,2) DEFAULT NULL,
    satuan VARCHAR(50) DEFAULT NULL,
    urutan INT NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    KEY km_recipe_ingredient_article_idx (article_id),
    CONSTRAINT km_recipe_ingredient_article_fk
        FOREIGN KEY (article_id) REFERENCES km_recipe (article_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS km_tag (
    id INT NOT NULL AUTO_INCREMENT,
    nama VARCHAR(60) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_km_tag_nama (nama)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS km_article_tag (
    article_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (article_id, tag_id),
    CONSTRAINT km_article_tag_article_fk
        FOREIGN KEY (article_id) REFERENCES km_article (id) ON DELETE CASCADE,
    CONSTRAINT km_article_tag_tag_fk
        FOREIGN KEY (tag_id) REFERENCES km_tag (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS km_attachment (
    id INT NOT NULL AUTO_INCREMENT,
    article_id INT NOT NULL,
    nama_file VARCHAR(255) NOT NULL,
    path_file VARCHAR(500) NOT NULL,
    tipe_file VARCHAR(100) DEFAULT NULL,
    uploaded_by_user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT km_attachment_article_fk
        FOREIGN KEY (article_id) REFERENCES km_article (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS km_feedback (
    id INT NOT NULL AUTO_INCREMENT,
    article_id INT NOT NULL,
    user_id INT NOT NULL,
    membantu TINYINT(1) NOT NULL,
    komentar VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_km_feedback_user_article (article_id, user_id),
    CONSTRAINT km_feedback_article_fk
        FOREIGN KEY (article_id) REFERENCES km_article (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT IGNORE INTO km_category (id, nama, deskripsi) VALUES
    (1, 'Resep Produksi', 'Resep dan standar pembuatan produk.'),
    (2, 'SOP Operasional', 'Prosedur kerja toko dan cabang.'),
    (3, 'Pelatihan Employee', 'Materi pelatihan untuk employee.'),
    (4, 'FAQ dan Troubleshooting', 'Solusi masalah yang sering terjadi.'),
    (5, 'Best Practice Cabang', 'Pengalaman dan praktik terbaik cabang.');

INSERT IGNORE INTO km_tag (id, nama) VALUES
    (1, 'produksi'),
    (2, 'kasir'),
    (3, 'stok'),
    (4, 'pelatihan'),
    (5, 'resep');

INSERT IGNORE INTO km_article
    (id, judul, slug, ringkasan, isi, category_id, author_user_id,
     related_product_id, visibility, status, published_by_user_id, published_at)
VALUES
    (1, 'SOP Distribusi Stok Gudang ke Cabang',
     'sop-distribusi-stok-gudang-ke-cabang',
     'Panduan request dan distribusi stok ke cabang.',
     'Manager membuat request stok berdasarkan kebutuhan cabang. Admin memeriksa stok gudang, lalu menyetujui atau menolak request. Setelah disetujui, stok gudang berkurang dan stok cabang bertambah.',
     2, 1, NULL, 'internal', 'published', 1, NOW()),
     (2, 'Resep Brownies Cokelat Standar',
     'resep-brownies-cokelat-standar',
     'Materi pelatihan dasar pembuatan brownies.',
     'Gunakan bahan sesuai takaran resep produksi. Pastikan oven telah dipanaskan dan lakukan pemeriksaan kematangan sebelum produk dikemas. Detail takaran dapat disesuaikan oleh admin produksi.',
     1, 1, 1, 'internal', 'published', 1, NOW()),
    (3, 'Panduan Onboarding Kasir Baru',
     'panduan-onboarding-kasir-baru',
     'Materi internal untuk kasir baru.',
     'Pelajari alur menerima pesanan, memeriksa pembayaran, memperbarui status transaksi, dan melakukan rekap harian. Gunakan SOP transaksi sebagai referensi utama.',
     3, 1, NULL, 'internal', 'published', 1, NOW()),
    (4, 'Best Practice Display Cabang Sleman',
     'best-practice-display-cabang-sleman',
     'Pengalaman Cabang Sleman dalam menata display produk.',
     'Produk dengan masa simpan lebih pendek ditempatkan di area yang mudah terlihat. Label harga diperiksa sebelum toko dibuka dan produk dikelompokkan berdasarkan jenisnya.',
     5, 8, NULL, 'cabang', 'published', 1, NOW()),
    (5, 'Tips Menyimpan Brownies di Rumah',
     'tips-menyimpan-brownies-di-rumah',
     'Tips penyimpanan brownies untuk pelanggan.',
     'Simpan brownies dalam wadah tertutup. Untuk konsumsi dalam beberapa hari, letakkan di lemari pendingin dan biarkan mencapai suhu ruang sebelum disajikan.',
     4, 1, 1, 'publik', 'published', 1, NOW());

INSERT IGNORE INTO km_article_version
    (article_id, version_number, judul, ringkasan, isi, changed_by_user_id)
SELECT id, 1, judul, ringkasan, isi, author_user_id
FROM km_article
WHERE id IN (1, 2, 3, 4, 5);

INSERT IGNORE INTO km_recipe
    (article_id, hasil_jumlah, hasil_satuan, suhu_oven_celsius, durasi_menit,
     peralatan, penyimpanan, informasi_alergen)
VALUES
    (2, 1, 'loyang', 170, 30, 'Mixer, loyang, oven, spatula',
     'Simpan dalam wadah tertutup maksimal 3 hari pada suhu ruang.',
     'Mengandung telur, susu, dan gluten.');

INSERT IGNORE INTO km_recipe_ingredient
    (article_id, nama_bahan, jumlah, satuan, urutan)
VALUES
    (2, 'Tepung terigu', 150, 'gram', 1),
    (2, 'Cokelat batang', 200, 'gram', 2),
    (2, 'Telur', 3, 'butir', 3),
    (2, 'Gula pasir', 120, 'gram', 4);

INSERT IGNORE INTO km_article_tag (article_id, tag_id) VALUES
    (1, 3), (1, 4), (2, 1), (2, 4), (2, 5),
    (3, 2), (3, 4), (4, 1), (4, 4), (5, 5);
