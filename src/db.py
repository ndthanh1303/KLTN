import os
from pathlib import Path

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