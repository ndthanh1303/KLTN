USE sanitary_store;

INSERT INTO danh_muc (ten_danh_muc, hinh_anh)
VALUES
('Bồn cầu', NULL),
('Lavabo', NULL),
('Sen tắm', NULL),
('Vòi lavabo', NULL),
('Bồn tắm', NULL),
('Phụ kiện phòng tắm', NULL);

INSERT INTO thuong_hieu (ten_thuong_hieu, hinh_anh)
VALUES
('TOTO', NULL),
('INAX', NULL),
('Caesar', NULL),
('Viglacera', NULL),
('American Standard', NULL);

INSERT INTO san_pham
(
    danh_muc_id,
    thuong_hieu_id,
    ma_san_pham,
    ten_san_pham,
    mo_ta,
    gia,
    gia_khuyen_mai,
    so_luong_ton
)
VALUES

(1, 1, 'TOTO-MS885',
 'Bồn cầu một khối TOTO MS885',
 'Bồn cầu một khối thiết kế hiện đại, dễ vệ sinh.',
 8500000, 7900000, 15),

(1, 2, 'INAX-AC969',
 'Bồn cầu một khối INAX AC-969',
 'Bồn cầu nguyên khối INAX phù hợp phòng tắm hiện đại.',
 7200000, 6800000, 12),

(2, 1, 'TOTO-LW896',
 'Lavabo đặt bàn TOTO LW896',
 'Lavabo đặt bàn thiết kế hiện đại.',
 3200000, 2950000, 20),

(2, 2, 'INAX-AL2398',
 'Lavabo đặt bàn INAX AL-2398',
 'Lavabo INAX phù hợp nhiều không gian phòng tắm.',
 2800000, NULL, 16),

(3, 1, 'TOTO-TBW01010',
 'Sen tắm TOTO TBW01010',
 'Bộ sen tắm nóng lạnh TOTO.',
 3800000, 3450000, 14),

(3, 2, 'INAX-BFV1113',
 'Sen tắm INAX BFV-1113S',
 'Sen tắm nóng lạnh INAX dành cho gia đình.',
 2900000, NULL, 17),

(4, 1, 'TOTO-TLG04301',
 'Vòi lavabo TOTO TLG04301',
 'Vòi lavabo nóng lạnh thiết kế tối giản.',
 2650000, NULL, 20),

(4, 2, 'INAX-LFV1402',
 'Vòi lavabo INAX LFV-1402S',
 'Vòi lavabo nóng lạnh INAX.',
 1750000, 1590000, 22),

(5, 1, 'TOTO-PAY1710',
 'Bồn tắm TOTO PAY1710',
 'Bồn tắm nằm thiết kế sang trọng.',
 18500000, 17500000, 5),

(6, 2, 'INAX-KF545',
 'Kệ kính phòng tắm INAX KF-545VA',
 'Kệ kính phòng tắm nhỏ gọn.',
 750000, 690000, 30);
 
 
 INSERT INTO hinh_anh_san_pham (
    san_pham_id,
    url_anh,
    public_id,
    anh_dai_dien
)
VALUES (
    1,
    'https://res.cloudinary.com/aol7hxoc/image/upload/v1791301204/sp_toto.png',
    'sanitary-store/products/sp_toto.png',
    TRUE
);


 INSERT INTO hinh_anh_san_pham (
    san_pham_id,
    url_anh,
    public_id,
    anh_dai_dien
)
VALUES (
    1,
    'https://res.cloudinary.com/aol7hxoc/image/upload/v1791301395/sp_toto_2.png',
    'sanitary-store/products/sp_toto_2.png',
    FALSE
);

UPDATE danh_muc
SET hinh_anh = 'https://res.cloudinary.com/aol7hxoc/image/upload/v1791301462/b%E1%BB%93n_c%E1%BA%A7u.png'
WHERE danh_muc_id = 1;

UPDATE thuong_hieu
SET hinh_anh = 'https://res.cloudinary.com/aol7hxoc/image/upload/v1791301291/brard_toto.png'
WHERE thuong_hieu_id = 1;

