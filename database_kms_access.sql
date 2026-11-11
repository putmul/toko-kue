USE sistem_transaksi;

ALTER TABLE users
    MODIFY role ENUM('admin','manajer_cabang','kasir','pegawai_produksi','pelanggan')
    NOT NULL DEFAULT 'pelanggan';

ALTER TABLE employee
    MODIFY jabatan ENUM('admin','manajer_cabang','kasir','pegawai_produksi')
    NOT NULL;
