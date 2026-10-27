"""Menu và truy vấn danh sách cho khu vực quản trị; bước này chỉ đọc dữ liệu."""
from math import ceil

from db import get_db_connection


# Tên module cố định; không nhận tên bảng/cột SQL từ trình duyệt.
NHOM_MODULE_ADMIN = [
    ("Điều hành", [("tong-quan", "Bảng điều khiển", "grid")]),
    ("Quản lý sản phẩm", [
        ("thuong-hieu", "Thương hiệu", "tag"),
        ("danh-muc", "Danh mục", "layers"),
        ("san-pham", "Sản phẩm", "box"),
    ]),
    ("Quản lý bán hàng", [
        ("don-hang", "Đơn hàng", "bag"),
        ("danh-gia", "Đánh giá sản phẩm", "star"),
    ]),
    ("Quản lý tồn kho", [
        ("ton-kho", "Tồn kho sản phẩm", "warehouse"),
        ("lich-su-kho", "Lịch sử nhập / xuất", "history"),
    ]),
    ("Quản lý hệ thống", [
        ("tai-khoan", "Tài khoản", "users"),
        ("thong-bao", "Thông báo", "bell"),
    ]),
    ("Báo cáo", [("bao-cao", "Bán hàng theo tháng", "chart")]),
]


MODULE_ADMIN = {
    "thuong-hieu": {
        "tieu_de": "Thương hiệu", "mo_ta": "Các thương hiệu thiết bị vệ sinh trong cửa hàng.",
        "cot": [("thuong_hieu_id", "ID", "so"), ("ten_thuong_hieu", "Tên thương hiệu", "chu"), ("created_at", "Ngày tạo", "ngay")],
        "select": "t.thuong_hieu_id, t.ten_thuong_hieu, t.created_at",
        "from": "thuong_hieu t", "order": "t.thuong_hieu_id DESC",
        "search": ["t.ten_thuong_hieu"],
    },
    "danh-muc": {
        "tieu_de": "Danh mục", "mo_ta": "Danh mục sản phẩm của cửa hàng.",
        "cot": [("danh_muc_id", "ID", "so"), ("ten_danh_muc", "Tên danh mục", "chu"), ("created_at", "Ngày tạo", "ngay")],
        "select": "t.danh_muc_id, t.ten_danh_muc, t.created_at",
        "from": "danh_muc t", "order": "t.danh_muc_id DESC",
        "search": ["t.ten_danh_muc"],
    },
    "san-pham": {
        "tieu_de": "Sản phẩm", "mo_ta": "Danh sách sản phẩm, giá bán và số lượng tồn hiện tại.",
        "cot": [("ma_san_pham", "Mã sản phẩm", "chu"), ("ten_san_pham", "Tên sản phẩm", "chu"),
                ("ten_danh_muc", "Danh mục", "chu"), ("ten_thuong_hieu", "Thương hiệu", "chu"),
                ("gia", "Giá bán", "tien"), ("so_luong_ton", "Tồn kho", "ton")],
        "select": """t.san_pham_id, t.ma_san_pham, t.ten_san_pham,
                     dm.ten_danh_muc, th.ten_thuong_hieu, t.so_luong_ton,
                     CASE WHEN t.gia_khuyen_mai >= 0 AND t.gia_khuyen_mai < t.gia
                          THEN t.gia_khuyen_mai ELSE t.gia END AS gia""",
        "from": "san_pham t LEFT JOIN danh_muc dm ON dm.danh_muc_id=t.danh_muc_id LEFT JOIN thuong_hieu th ON th.thuong_hieu_id=t.thuong_hieu_id",
        "order": "t.san_pham_id DESC", "search": ["t.ten_san_pham", "t.ma_san_pham"],
    },
    "don-hang": {
        "tieu_de": "Đơn hàng", "mo_ta": "Theo dõi các đơn hàng được tạo trên website.",
        "cot": [("ma_don_hang", "Mã đơn hàng", "chu"), ("ten_nguoi_nhan", "Người nhận", "chu"),
                ("so_dien_thoai", "Số điện thoại", "chu"), ("tong_tien", "Tổng tiền", "tien"),
                ("trang_thai_don_hang", "Trạng thái", "don"), ("created_at", "Ngày tạo", "ngay")],
        "select": "t.ma_don_hang, t.ten_nguoi_nhan, t.so_dien_thoai, t.tong_tien, t.trang_thai_don_hang, t.created_at",
        "from": "don_hang t", "order": "t.created_at DESC, t.don_hang_id DESC",
        "search": ["t.ma_don_hang", "t.ten_nguoi_nhan", "t.so_dien_thoai"],
    },
    "ton-kho": {
        "tieu_de": "Tồn kho sản phẩm", "mo_ta": "Sản phẩm có tồn kho thấp được xếp trước; ngưỡng cảnh báo là 5.",
        "cot": [("ma_san_pham", "Mã sản phẩm", "chu"), ("ten_san_pham", "Tên sản phẩm", "chu"), ("so_luong_ton", "Số lượng tồn", "ton")],
        "select": "t.ma_san_pham, t.ten_san_pham, t.so_luong_ton",
        "from": "san_pham t", "order": "t.so_luong_ton ASC, t.san_pham_id DESC",
        "search": ["t.ma_san_pham", "t.ten_san_pham"],
    },
    "lich-su-kho": {
        "tieu_de": "Lịch sử nhập / xuất", "mo_ta": "Các giao dịch nhập, xuất và điều chỉnh đã được ghi nhận.",
        "cot": [("ten_san_pham", "Sản phẩm", "chu"), ("loai_giao_dich", "Giao dịch", "kho"),
                ("so_luong", "Số lượng", "so"), ("so_luong_truoc", "Trước", "so"), ("so_luong_sau", "Sau", "so"),
                ("ho_ten", "Người thực hiện", "chu"), ("created_at", "Thời gian", "ngay")],
        "select": "sp.ten_san_pham, t.loai_giao_dich, t.so_luong, t.so_luong_truoc, t.so_luong_sau, u.ho_ten, t.created_at",
        "from": "lich_su_kho t JOIN san_pham sp ON sp.san_pham_id=t.san_pham_id LEFT JOIN users u ON u.users_id=t.users_id",
        "order": "t.created_at DESC, t.lich_su_kho_id DESC", "search": ["sp.ten_san_pham", "sp.ma_san_pham", "t.ghi_chu"],
    },
    "tai-khoan": {
        "tieu_de": "Tài khoản", "mo_ta": "Tài khoản khách hàng và quản trị viên của website.",
        "cot": [("users_id", "ID", "so"), ("ho_ten", "Họ và tên", "chu"), ("email", "Email", "chu"),
                ("so_dien_thoai", "Số điện thoại", "chu"), ("phan_quyen", "Vai trò", "quyen"), ("created_at", "Ngày tạo", "ngay")],
        # Không truy vấn mật khẩu hoặc password hash để hiển thị.
        "select": "t.users_id, t.ho_ten, t.email, t.so_dien_thoai, t.phan_quyen, t.created_at",
        "from": "users t", "order": "t.users_id DESC", "search": ["t.ho_ten", "t.email", "t.so_dien_thoai"],
    },
    "danh-gia": {
        "tieu_de": "Đánh giá sản phẩm", "mo_ta": "Các nhận xét và số sao do khách hàng gửi.",
        "cot": [("ho_ten", "Khách hàng", "chu"), ("ten_san_pham", "Sản phẩm", "chu"),
                ("so_sao", "Số sao", "sao"), ("noi_dung", "Nội dung", "chu"), ("created_at", "Ngày đánh giá", "ngay")],
        "select": "u.ho_ten, sp.ten_san_pham, t.so_sao, t.noi_dung, t.created_at",
        "from": "danh_gia t JOIN users u ON u.users_id=t.users_id JOIN san_pham sp ON sp.san_pham_id=t.san_pham_id",
        "order": "t.created_at DESC, t.danh_gia_id DESC", "search": ["u.ho_ten", "sp.ten_san_pham", "t.noi_dung"],
    },
    "thong-bao": {
        "tieu_de": "Thông báo", "mo_ta": "Thông báo dành cho tài khoản quản trị đang đăng nhập.",
        "cot": [("tieu_de", "Tiêu đề", "chu"), ("noi_dung", "Nội dung", "chu"), ("da_doc", "Trạng thái", "doc"), ("created_at", "Thời gian", "ngay")],
        "select": "t.tieu_de, t.noi_dung, t.da_doc, t.created_at",
        "from": "thong_bao t", "order": "t.created_at DESC, t.thong_bao_id DESC",
        "search": ["t.tieu_de", "t.noi_dung"],
    },
    "bao-cao": {
        "tieu_de": "Bán hàng theo tháng", "mo_ta": "Số đơn và tổng giá trị đơn đã hoàn thành, tối đa 24 tháng có phát sinh.",
        "cot": [("thang", "Tháng", "chu"), ("so_don", "Đơn hoàn thành", "so"), ("tong_tien", "Giá trị đơn hoàn thành", "tien")],
    },
}


def lay_danh_sach_quan_tri(ma_module, users_id, tu_khoa="", trang=1):
    """Phân trang và tìm kiếm; mọi giá trị nhập được truyền bằng tham số SQL."""
    cau_hinh = MODULE_ADMIN.get(ma_module)
    if cau_hinh is None:
        return None
    q = (tu_khoa or "").strip()[:150]
    try:
        page = max(1, int(trang))
    except (TypeError, ValueError):
        page = 1

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if ma_module == "bao-cao":
                cursor.execute(
                    """SELECT DATE_FORMAT(created_at, '%%Y-%%m') AS thang,
                              COUNT(*) AS so_don, SUM(tong_tien) AS tong_tien
                       FROM don_hang WHERE trang_thai_don_hang = %s
                       GROUP BY DATE_FORMAT(created_at, '%%Y-%%m')
                       ORDER BY thang DESC LIMIT 24""", ("hoan_thanh",),
                )
                rows = cursor.fetchall()
                total, page, pages, q = len(rows), 1, 1, ""
            else:
                dieu_kien, params = [], []
                if ma_module == "thong-bao":
                    dieu_kien.append("t.users_id = %s")
                    params.append(users_id)
                if q:
                    dieu_kien.append("(" + " OR ".join(c + " LIKE %s" for c in cau_hinh["search"]) + ")")
                    params.extend(["%" + q + "%"] * len(cau_hinh["search"]))
                where = " WHERE " + " AND ".join(dieu_kien) if dieu_kien else ""
                cursor.execute("SELECT COUNT(*) AS tong FROM " + cau_hinh["from"] + where, tuple(params))
                total = int(cursor.fetchone()["tong"])
                pages = max(1, ceil(total / 15))
                page = min(page, pages)
                cursor.execute(
                    "SELECT " + cau_hinh["select"] + " FROM " + cau_hinh["from"] + where
                    + " ORDER BY " + cau_hinh["order"] + " LIMIT %s OFFSET %s",
                    tuple(params) + (15, (page - 1) * 15),
                )
                rows = cursor.fetchall()
        return {
            "cau_hinh": cau_hinh, "dong": rows, "tong": total, "trang": page,
            "so_trang": pages, "q": q, "tim_kiem": ma_module != "bao-cao",
            "tu": (page - 1) * 15 + 1 if total else 0,
            "den": min(page * 15, total) if ma_module != "bao-cao" else total,
        }
    finally:
        connection.close()
