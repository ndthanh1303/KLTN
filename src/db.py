import os
from pathlib import Path
from decimal import Decimal
import pymysql
from dotenv import load_dotenv


# File .env nằm tại thư mục KLTN, bên ngoài thư mục src.
# KLTN/
#   .env
#   src/
#     app.py
#     db.py
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


def get_db_connection():
    """Tạo kết nối MySQL; mỗi dòng truy vấn trả về một dictionary."""

    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "123456"),
        database=os.getenv("DB_NAME", "sanitary_store"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=10,
    )


def lay_du_lieu_trang_chu():
    """
    Lấy danh mục, thương hiệu và sản phẩm từ database.

    Nếu bảng chưa có dữ liệu, trả về danh sách rỗng.
    Nếu kết nối hoặc truy vấn thất bại, lỗi được chuyển lên app.py.
    """

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # 1. Danh mục sản phẩm
            cursor.execute("""
                SELECT
                    danh_muc_id,
                    ten_danh_muc,
                    hinh_anh
                FROM danh_muc
                ORDER BY danh_muc_id ASC
            """)
            danh_muc = list(cursor.fetchall())

            # 2. Thương hiệu
            cursor.execute("""
                SELECT
                    thuong_hieu_id,
                    ten_thuong_hieu,
                    hinh_anh
                FROM thuong_hieu
                ORDER BY thuong_hieu_id ASC
            """)
            thuong_hieu = list(cursor.fetchall())

            # 3. Sản phẩm và ảnh đại diện
            # Ưu tiên ảnh được đánh dấu anh_dai_dien.
            # Nếu chưa đánh dấu, dùng ảnh có hinh_anh_id nhỏ nhất.
            cursor.execute("""
                SELECT
                    sp.san_pham_id,
                    sp.danh_muc_id,
                    sp.thuong_hieu_id,
                    sp.ma_san_pham,
                    sp.ten_san_pham,
                    sp.mo_ta,
                    sp.gia,
                    sp.gia_khuyen_mai,
                    sp.so_luong_ton,
                    (
                        SELECT ha.url_anh
                        FROM hinh_anh_san_pham AS ha
                        WHERE ha.san_pham_id = sp.san_pham_id
                        ORDER BY
                            ha.anh_dai_dien DESC,
                            ha.hinh_anh_id ASC
                        LIMIT 1
                    ) AS url_anh
                FROM san_pham AS sp
                ORDER BY
                    sp.created_at DESC,
                    sp.san_pham_id DESC
            """)
            san_pham = list(cursor.fetchall())

        # MySQL trả giá dưới dạng Decimal.
        # Chuyển thành chuỗi để truyền qua JSON, giữ nguyên độ chính xác.
        for sp in san_pham:
            sp["gia"] = str(sp["gia"])

            if sp["gia_khuyen_mai"] is not None:
                sp["gia_khuyen_mai"] = str(sp["gia_khuyen_mai"])

        return {
            "demo": False,
            "danh_muc": danh_muc,
            "thuong_hieu": thuong_hieu,
            "san_pham": san_pham,
        }

    finally:
        connection.close()


def lay_chi_tiet_san_pham(san_pham_id):
    """Lấy một sản phẩm và toàn bộ ảnh; trả None nếu không tìm thấy."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sp.san_pham_id, sp.danh_muc_id, sp.thuong_hieu_id,
                    sp.ma_san_pham, sp.ten_san_pham, sp.mo_ta,
                    sp.gia, sp.gia_khuyen_mai, sp.so_luong_ton,
                    dm.ten_danh_muc, th.ten_thuong_hieu
                FROM san_pham AS sp
                JOIN danh_muc AS dm
                    ON dm.danh_muc_id = sp.danh_muc_id
                LEFT JOIN thuong_hieu AS th
                    ON th.thuong_hieu_id = sp.thuong_hieu_id
                WHERE sp.san_pham_id = %s
                LIMIT 1
                """,
                (san_pham_id,),  # Truyền tham số riêng, không ghép chuỗi SQL.
            )
            san_pham = cursor.fetchone()
            if san_pham is None:
                return None

            cursor.execute(
                """
                SELECT hinh_anh_id, url_anh, anh_dai_dien
                FROM hinh_anh_san_pham
                WHERE san_pham_id = %s AND url_anh <> ''
                ORDER BY anh_dai_dien DESC, hinh_anh_id ASC
                """,
                (san_pham_id,),
            )
            san_pham["hinh_anh"] = list(cursor.fetchall())
            return san_pham
    finally:
        connection.close()


def lay_gio_hang(users_id):
    """Đọc giỏ hàng của một tài khoản và tính tiền bằng Decimal."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ctgh.chi_tiet_gio_hang_id,
                    ctgh.so_luong,
                    sp.san_pham_id,
                    sp.ma_san_pham,
                    sp.ten_san_pham,
                    sp.gia,
                    sp.gia_khuyen_mai,
                    sp.so_luong_ton,
                    (
                        SELECT ha.url_anh
                        FROM hinh_anh_san_pham AS ha
                        WHERE ha.san_pham_id = sp.san_pham_id
                            AND ha.url_anh <> ''
                        ORDER BY ha.anh_dai_dien DESC, ha.hinh_anh_id ASC
                        LIMIT 1
                    ) AS url_anh
                FROM gio_hang AS gh
                JOIN chi_tiet_gio_hang AS ctgh
                    ON ctgh.gio_hang_id = gh.gio_hang_id
                JOIN san_pham AS sp
                    ON sp.san_pham_id = ctgh.san_pham_id
                WHERE gh.users_id = %s
                ORDER BY ctgh.created_at DESC, ctgh.chi_tiet_gio_hang_id DESC
                """,
                (users_id,),  # Luôn lọc theo tài khoản lấy từ session.
            )
            san_pham = list(cursor.fetchall())

        tong_so_luong = 0
        tong_tien = Decimal("0")

        for sp in san_pham:
            gia_km = sp["gia_khuyen_mai"]
            # Áp dụng cùng quy tắc giá khuyến mãi với trang chi tiết.
            dang_giam_gia = (
                gia_km is not None and 0 <= gia_km < sp["gia"]
            )
            sp["gia_ban"] = gia_km if dang_giam_gia else sp["gia"]
            sp["thanh_tien"] = sp["gia_ban"] * sp["so_luong"]
            tong_so_luong += sp["so_luong"]
            tong_tien += sp["thanh_tien"]

        return {
            "san_pham": san_pham,
            "tong_so_luong": tong_so_luong,
            "tong_tien": tong_tien,
        }
    finally:
        connection.close()


def lay_thong_ke_quan_tri():
    """Đọc số liệu thật cho trang tổng quan; không thay đổi dữ liệu cửa hàng."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                   (SELECT COUNT(*) FROM san_pham) AS tong_san_pham,
                   (SELECT COUNT(*) FROM don_hang) AS tong_don_hang,
                   (SELECT COUNT(*) FROM don_hang WHERE trang_thai_don_hang = %s) AS don_cho_xu_ly,
                   (SELECT COUNT(*) FROM users WHERE phan_quyen = %s) AS tong_khach_hang""",
                ("cho_xu_ly", "user"),
            )
            thong_ke = cursor.fetchone()
            cursor.execute(
                """SELECT ma_don_hang, ten_nguoi_nhan, tong_tien,
                          trang_thai_don_hang, created_at
                   FROM don_hang
                   ORDER BY created_at DESC, don_hang_id DESC LIMIT 5"""
            )
            don_gan_day = cursor.fetchall()
            cursor.execute(
                """SELECT ma_san_pham, ten_san_pham, so_luong_ton
                   FROM san_pham WHERE so_luong_ton <= %s
                   ORDER BY so_luong_ton ASC, san_pham_id DESC LIMIT 5""",
                (5,),
            )
            ton_kho_thap = cursor.fetchall()
        return {"thong_ke": thong_ke, "don_gan_day": don_gan_day, "ton_kho_thap": ton_kho_thap}
    finally:
        connection.close()
