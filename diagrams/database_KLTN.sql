CREATE DATABASE sanitary_store
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE sanitary_store;

CREATE TABLE users (
    users_id INT AUTO_INCREMENT PRIMARY KEY,
    ho_ten VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    so_dien_thoai VARCHAR(15),
    mat_khau VARCHAR(255) NOT NULL,
    phan_quyen ENUM( 
        'user',
        'admin'
    ) NOT NULL DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE danh_muc (
    danh_muc_id INT AUTO_INCREMENT PRIMARY KEY,
    ten_danh_muc VARCHAR(100) NOT NULL UNIQUE,
    hinh_anh VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE thuong_hieu (
    thuong_hieu_id INT AUTO_INCREMENT PRIMARY KEY,
    ten_thuong_hieu VARCHAR(100) NOT NULL UNIQUE,
    hinh_anh VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE san_pham (
    san_pham_id INT AUTO_INCREMENT PRIMARY KEY,
    danh_muc_id INT NOT NULL,
    thuong_hieu_id INT,
    ma_san_pham VARCHAR(50) NOT NULL UNIQUE,
    ten_san_pham VARCHAR(200) NOT NULL,
    mo_ta TEXT,
    gia DECIMAL(15,2) NOT NULL,
    gia_khuyen_mai DECIMAL(15,2),
    so_luong_ton INT NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sanpham_danhmuc
        FOREIGN KEY (danh_muc_id)
        REFERENCES danh_muc(danh_muc_id),

    CONSTRAINT fk_sanpham_thuonghieu
        FOREIGN KEY (thuong_hieu_id)
        REFERENCES thuong_hieu(thuong_hieu_id)
);

CREATE TABLE hinh_anh_san_pham (
    hinh_anh_id INT AUTO_INCREMENT PRIMARY KEY,
    san_pham_id INT NOT NULL,
    url_anh VARCHAR(500) NOT NULL,
    public_id VARCHAR(255),
    anh_dai_dien BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_hinhanh_sanpham
        FOREIGN KEY (san_pham_id)
        REFERENCES san_pham(san_pham_id)
        ON DELETE CASCADE
);

CREATE TABLE gio_hang (
    gio_hang_id INT AUTO_INCREMENT PRIMARY KEY,
    users_id INT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_giohang_users
        FOREIGN KEY (users_id)
        REFERENCES users(users_id)
        ON DELETE CASCADE
);

CREATE TABLE chi_tiet_gio_hang (
    chi_tiet_gio_hang_id INT AUTO_INCREMENT PRIMARY KEY,
    gio_hang_id INT NOT NULL,
    san_pham_id INT NOT NULL,
    so_luong INT NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ctgh_giohang
        FOREIGN KEY (gio_hang_id)
        REFERENCES gio_hang(gio_hang_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_ctgh_sanpham
        FOREIGN KEY (san_pham_id)
        REFERENCES san_pham(san_pham_id),

    CONSTRAINT uq_giohang_sanpham
        UNIQUE (gio_hang_id, san_pham_id)
);

CREATE TABLE don_hang (
    don_hang_id INT AUTO_INCREMENT PRIMARY KEY,
    users_id INT NOT NULL,
    ma_don_hang VARCHAR(30) NOT NULL UNIQUE,
    ten_nguoi_nhan VARCHAR(100) NOT NULL,
    so_dien_thoai VARCHAR(15) NOT NULL,
    tinh_thanh VARCHAR(100) NOT NULL,
    phuong_xa VARCHAR(100) NOT NULL,
    dia_chi_chi_tiet VARCHAR(255) NOT NULL,
    tam_tinh DECIMAL(15,2) NOT NULL DEFAULT 0,
    phi_van_chuyen DECIMAL(15,2) NOT NULL DEFAULT 0,
    giam_gia DECIMAL(15,2) NOT NULL DEFAULT 0,
    tong_tien DECIMAL(15,2) NOT NULL,
    phuong_thuc_thanh_toan ENUM(
        'cod',
        'chuyen_khoan',
        'online'
    ) NOT NULL DEFAULT 'cod',
    trang_thai_thanh_toan ENUM(
        'chua_thanh_toan',
        'da_thanh_toan',
        'hoan_tien'
    ) NOT NULL DEFAULT 'chua_thanh_toan',
    trang_thai_don_hang ENUM(
        'cho_xu_ly',
        'da_xac_nhan',
        'dang_giao',
        'hoan_thanh',
        'huy_don'
    ) NOT NULL DEFAULT 'cho_xu_ly',
    ghi_chu TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_donhang_users
        FOREIGN KEY (users_id)
        REFERENCES users(users_id)
);

CREATE TABLE chi_tiet_don_hang (
    chi_tiet_don_hang_id INT AUTO_INCREMENT PRIMARY KEY,
    don_hang_id INT NOT NULL,
    san_pham_id INT NOT NULL,
    ten_san_pham VARCHAR(200) NOT NULL,
    so_luong INT NOT NULL,
    don_gia DECIMAL(15,2) NOT NULL,
    thanh_tien DECIMAL(15,2) NOT NULL,
    CONSTRAINT fk_ctdh_donhang
        FOREIGN KEY (don_hang_id)
        REFERENCES don_hang(don_hang_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_ctdh_sanpham
        FOREIGN KEY (san_pham_id)
        REFERENCES san_pham(san_pham_id)
);

CREATE TABLE lich_su_kho (
    lich_su_kho_id INT AUTO_INCREMENT PRIMARY KEY,
    san_pham_id INT NOT NULL,
    loai_giao_dich ENUM(
        'nhap',
        'xuat',
        'dieu_chinh'
    ) NOT NULL,
    so_luong INT NOT NULL,
    so_luong_truoc INT NOT NULL,
    so_luong_sau INT NOT NULL,
    ghi_chu TEXT,
    users_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lichsukho_sanpham
        FOREIGN KEY (san_pham_id)
        REFERENCES san_pham(san_pham_id),

    CONSTRAINT fk_lichsukho_users
        FOREIGN KEY (users_id)
        REFERENCES users(users_id)
);

CREATE TABLE thong_bao (
    thong_bao_id INT AUTO_INCREMENT PRIMARY KEY,
    users_id INT NOT NULL,
    loai_thong_bao ENUM(
        'don_hang_moi',
        'xac_nhan_don',
        'dang_giao',
        'hoan_thanh',
        'huy_don',
        'sap_het_hang'
    ) NOT NULL,
    tieu_de VARCHAR(200) NOT NULL,
    noi_dung TEXT NOT NULL,
    doi_tuong_id INT,
    da_doc BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_thongbao_users
        FOREIGN KEY (users_id)
        REFERENCES users(users_id)
        ON DELETE CASCADE
);

CREATE TABLE danh_gia (
    danh_gia_id INT AUTO_INCREMENT PRIMARY KEY,
    users_id INT NOT NULL,
    san_pham_id INT NOT NULL,
    so_sao TINYINT NOT NULL,
    noi_dung TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_danhgia_users
        FOREIGN KEY (users_id)
        REFERENCES users(users_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_danhgia_sanpham
        FOREIGN KEY (san_pham_id)
        REFERENCES san_pham(san_pham_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_so_sao
        CHECK (so_sao BETWEEN 1 AND 5),

    CONSTRAINT uq_danhgia_user_sanpham
        UNIQUE (users_id, san_pham_id)
);