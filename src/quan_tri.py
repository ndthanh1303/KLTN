"""Danh sách và thao tác quản trị cho sản phẩm, đơn hàng và tồn kho."""
from contextlib import closing, contextmanager
from math import ceil

import pymysql

from db import get_db_connection
from mua_hang import MAX_INT, TRANG_THAI_DON


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
        "cot": [("thuong_hieu_id", "ID", "so"), ("hinh_anh", "Ảnh", "anh"),
                ("ten_thuong_hieu", "Tên thương hiệu", "chu"), ("created_at", "Ngày tạo", "ngay")],
        "select": "t.thuong_hieu_id, t.hinh_anh, t.ten_thuong_hieu, t.created_at",
        "from": "thuong_hieu t", "order": "t.thuong_hieu_id DESC",
        "search": ["t.ten_thuong_hieu"],
    },
    "danh-muc": {
        "tieu_de": "Danh mục", "mo_ta": "Danh mục sản phẩm của cửa hàng.",
        "cot": [("danh_muc_id", "ID", "so"), ("hinh_anh", "Ảnh", "anh"),
                ("ten_danh_muc", "Tên danh mục", "chu"), ("created_at", "Ngày tạo", "ngay")],
        "select": "t.danh_muc_id, t.hinh_anh, t.ten_danh_muc, t.created_at",
        "from": "danh_muc t", "order": "t.danh_muc_id DESC",
        "search": ["t.ten_danh_muc"],
    },
    "san-pham": {
        "tieu_de": "Sản phẩm", "mo_ta": "Danh sách sản phẩm, giá bán và số lượng tồn hiện tại.",
        "cot": [("url_anh", "Ảnh", "anh"), ("ma_san_pham", "Mã sản phẩm", "chu"), ("ten_san_pham", "Tên sản phẩm", "chu"),
                ("ten_danh_muc", "Danh mục", "chu"), ("ten_thuong_hieu", "Thương hiệu", "chu"),
                ("gia", "Giá bán", "tien"), ("so_luong_ton", "Tồn kho", "ton")],
        "select": """t.san_pham_id, t.ma_san_pham, t.ten_san_pham,
                     dm.ten_danh_muc, th.ten_thuong_hieu, t.so_luong_ton,
                     CASE WHEN t.gia_khuyen_mai >= 0 AND t.gia_khuyen_mai < t.gia
                          THEN t.gia_khuyen_mai ELSE t.gia END AS gia,
                     (SELECT ha.url_anh FROM hinh_anh_san_pham ha
                      WHERE ha.san_pham_id = t.san_pham_id
                      ORDER BY ha.anh_dai_dien DESC, ha.hinh_anh_id ASC LIMIT 1) AS url_anh""",
        "from": "san_pham t LEFT JOIN danh_muc dm ON dm.danh_muc_id=t.danh_muc_id LEFT JOIN thuong_hieu th ON th.thuong_hieu_id=t.thuong_hieu_id",
        "order": "t.san_pham_id DESC", "search": ["t.ten_san_pham", "t.ma_san_pham"],
    },
    "don-hang": {
        "tieu_de": "Đơn hàng", "mo_ta": "Theo dõi các đơn hàng được tạo trên website.",
        "cot": [("ma_don_hang", "Mã đơn hàng", "chu"), ("ten_nguoi_nhan", "Người nhận", "chu"),
                ("so_dien_thoai", "Số điện thoại", "chu"), ("tong_tien", "Tổng tiền", "tien"),
                ("trang_thai_don_hang", "Trạng thái", "don"), ("created_at", "Ngày tạo", "ngay")],
        "select": "t.don_hang_id, t.ma_don_hang, t.ten_nguoi_nhan, t.so_dien_thoai, t.tong_tien, t.trang_thai_don_hang, t.created_at",
        "from": "don_hang t", "order": "t.created_at DESC, t.don_hang_id DESC",
        "search": ["t.ma_don_hang", "t.ten_nguoi_nhan", "t.so_dien_thoai"],
    },
    "ton-kho": {
        "tieu_de": "Tồn kho sản phẩm", "mo_ta": "Sản phẩm có tồn kho thấp được xếp trước; ngưỡng cảnh báo là 5.",
        "cot": [("ma_san_pham", "Mã sản phẩm", "chu"), ("ten_san_pham", "Tên sản phẩm", "chu"), ("so_luong_ton", "Số lượng tồn", "ton")],
        "select": "t.san_pham_id, t.ma_san_pham, t.ten_san_pham, t.so_luong_ton",
        "from": "san_pham t", "order": "t.so_luong_ton ASC, t.san_pham_id DESC",
        "search": ["t.ma_san_pham", "t.ten_san_pham"],
    },
    "lich-su-kho": {
        "tieu_de": "Lịch sử nhập / xuất", "mo_ta": "Các giao dịch nhập, xuất và điều chỉnh đã được ghi nhận.",
        "cot": [("ten_san_pham", "Sản phẩm", "chu"), ("loai_giao_dich", "Giao dịch", "kho"),
                ("so_luong", "Số lượng", "so"), ("so_luong_truoc", "Trước", "so"), ("so_luong_sau", "Sau", "so"),
                ("ghi_chu", "Ghi chú", "chu"), ("ho_ten", "Người thực hiện", "chu"), ("created_at", "Thời gian", "ngay")],
        "select": "sp.ten_san_pham, t.loai_giao_dich, t.so_luong, t.so_luong_truoc, t.so_luong_sau, t.ghi_chu, u.ho_ten, t.created_at",
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
        "select": "t.tieu_de, t.noi_dung, t.da_doc, t.created_at, t.loai_thong_bao, t.doi_tuong_id",
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


# Chỉ lấy tên bảng và cột từ cấu hình cố định này.
DU_LIEU_QUAN_TRI = {
    "thuong-hieu": ("thuong_hieu", "thuong_hieu_id", "ten_thuong_hieu", "thương hiệu"),
    "danh-muc": ("danh_muc", "danh_muc_id", "ten_danh_muc", "danh mục"),
    "san-pham": ("san_pham", "san_pham_id", "ten_san_pham", "sản phẩm"),
}

CHUYEN_TRANG_THAI_DON = {
    "cho_xu_ly": ("da_xac_nhan", "huy_don"),
    "da_xac_nhan": ("dang_giao", "huy_don"),
    "dang_giao": ("hoan_thanh",),
}
LOAI_THONG_BAO_DON = {
    "da_xac_nhan": "xac_nhan_don", "dang_giao": "dang_giao",
    "hoan_thanh": "hoan_thanh", "huy_don": "huy_don",
}


class LoiQuanTri(ValueError):
    def __init__(self, message, ma_http=409):
        super().__init__(message)
        self.ma_http = ma_http


@contextmanager
def _giao_dich_quan_tri():
    """Một thao tác ghi được lưu trọn vẹn hoặc hoàn tác toàn bộ."""
    with closing(get_db_connection()) as connection:
        try:
            with connection.cursor() as cursor:
                yield cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _doc_ban_ghi(cursor, ma_module, ban_ghi_id, khoa=False):
    bang, cot_id, _, _ = DU_LIEU_QUAN_TRI[ma_module]
    cursor.execute(
        f"SELECT * FROM {bang} WHERE {cot_id} = %s" + (" FOR UPDATE" if khoa else ""),
        (ban_ghi_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise LoiQuanTri("Bản ghi không còn tồn tại.", 404)
    return row


def _doc_anh_san_pham(cursor, san_pham_id):
    cursor.execute(
        """SELECT hinh_anh_id, url_anh, anh_dai_dien FROM hinh_anh_san_pham
           WHERE san_pham_id = %s ORDER BY anh_dai_dien DESC, hinh_anh_id ASC""",
        (san_pham_id,),
    )
    return cursor.fetchall()


def lay_ban_ghi_quan_tri(ma_module, ban_ghi_id):
    with closing(get_db_connection()) as connection, connection.cursor() as cursor:
        row = _doc_ban_ghi(cursor, ma_module, ban_ghi_id)
        if ma_module == "san-pham":
            row["hinh_anh"] = _doc_anh_san_pham(cursor, ban_ghi_id)
        return row


def lay_tuy_chon_san_pham():
    with closing(get_db_connection()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT danh_muc_id, ten_danh_muc FROM danh_muc ORDER BY ten_danh_muc")
        danh_muc = [(r["danh_muc_id"], r["ten_danh_muc"]) for r in cursor.fetchall()]
        cursor.execute("SELECT thuong_hieu_id, ten_thuong_hieu FROM thuong_hieu ORDER BY ten_thuong_hieu")
        thuong_hieu = [(r["thuong_hieu_id"], r["ten_thuong_hieu"]) for r in cursor.fetchall()]
        return danh_muc, thuong_hieu


def luu_nhom_san_pham(ma_module, ban_ghi_id, ten, hinh_anh):
    bang, cot_id, cot_ten, nhan = DU_LIEU_QUAN_TRI[ma_module]
    try:
        with _giao_dich_quan_tri() as cursor:
            if ban_ghi_id is None:
                cursor.execute(f"INSERT INTO {bang} ({cot_ten}, hinh_anh) VALUES (%s,%s)", (ten, hinh_anh))
            else:
                _doc_ban_ghi(cursor, ma_module, ban_ghi_id, khoa=True)
                cursor.execute(
                    f"UPDATE {bang} SET {cot_ten} = %s, hinh_anh = %s WHERE {cot_id} = %s",
                    (ten, hinh_anh, ban_ghi_id),
                )
    except pymysql.IntegrityError as error:
        if error.args[0] == 1062:
            raise LoiQuanTri(f"Tên {nhan} đã tồn tại.") from error
        raise


def _luu_anh_san_pham(cursor, san_pham_id, urls, public_ids):
    # Giữ nguyên bản ghi và public_id của ảnh có URL không đổi.
    anh_giu_lai = {}
    urls_moi = set(urls)
    for anh in _doc_anh_san_pham(cursor, san_pham_id):
        url, anh_id = anh["url_anh"], anh["hinh_anh_id"]
        if url in urls_moi and url not in anh_giu_lai:
            anh_giu_lai[url] = anh
        else:
            cursor.execute("DELETE FROM hinh_anh_san_pham WHERE hinh_anh_id = %s", (anh_id,))
    for i, url in enumerate(urls):
        la_anh_dai_dien = i == 0
        cu = anh_giu_lai.get(url)
        if cu is None:
            cursor.execute(
                """INSERT INTO hinh_anh_san_pham (san_pham_id, url_anh, public_id, anh_dai_dien)
                   VALUES (%s,%s,%s,%s)""",
                (san_pham_id, url, public_ids.get(url), la_anh_dai_dien),
            )
        elif bool(cu["anh_dai_dien"]) != la_anh_dai_dien:
            cursor.execute(
                "UPDATE hinh_anh_san_pham SET anh_dai_dien = %s WHERE hinh_anh_id = %s",
                (la_anh_dai_dien, cu["hinh_anh_id"]),
            )


def luu_san_pham_quan_tri(san_pham_id, du_lieu, anh, public_ids=None):
    gia_tri = (
        du_lieu["ma_san_pham"], du_lieu["ten_san_pham"], du_lieu["danh_muc_id"],
        du_lieu["thuong_hieu_id"] or None, du_lieu["gia"], du_lieu["gia_khuyen_mai"], du_lieu["mo_ta"] or None,
    )
    try:
        with _giao_dich_quan_tri() as cursor:
            if san_pham_id is None:
                cursor.execute(
                    """INSERT INTO san_pham
                       (ma_san_pham, ten_san_pham, danh_muc_id, thuong_hieu_id, gia, gia_khuyen_mai, mo_ta)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""", gia_tri,
                )
                san_pham_id = cursor.lastrowid
            else:
                _doc_ban_ghi(cursor, "san-pham", san_pham_id, khoa=True)
                # Tồn kho chỉ thay đổi qua giao dịch kho hoặc khi đặt/hủy đơn.
                cursor.execute(
                    """UPDATE san_pham SET ma_san_pham = %s, ten_san_pham = %s, danh_muc_id = %s,
                       thuong_hieu_id = %s, gia = %s, gia_khuyen_mai = %s, mo_ta = %s WHERE san_pham_id = %s""",
                    gia_tri + (san_pham_id,),
                )
            _luu_anh_san_pham(cursor, san_pham_id, anh, public_ids or {})
    except pymysql.IntegrityError as error:
        if error.args[0] == 1062:
            raise LoiQuanTri("Mã sản phẩm đã tồn tại.") from error
        if error.args[0] == 1452:
            raise LoiQuanTri("Danh mục hoặc thương hiệu không còn tồn tại. Vui lòng chọn lại.") from error
        raise
    return san_pham_id


def xoa_ban_ghi_quan_tri(ma_module, ban_ghi_id):
    bang, cot_id, _, nhan = DU_LIEU_QUAN_TRI[ma_module]
    try:
        with _giao_dich_quan_tri() as cursor:
            row = _doc_ban_ghi(cursor, ma_module, ban_ghi_id, khoa=True)
            if ma_module == "san-pham":
                if row["so_luong_ton"] != 0:
                    raise LoiQuanTri("Không thể xóa sản phẩm còn tồn kho.")
                # Giữ đánh giá vì khóa ngoại của bảng này cho phép xóa theo sản phẩm.
                cursor.execute("SELECT 1 FROM danh_gia WHERE san_pham_id = %s LIMIT 1", (ban_ghi_id,))
                if cursor.fetchone() is not None:
                    raise LoiQuanTri("Không thể xóa sản phẩm đã có đánh giá.")
            cursor.execute(f"DELETE FROM {bang} WHERE {cot_id} = %s", (ban_ghi_id,))
    except pymysql.IntegrityError as error:
        if error.args[0] == 1451:
            ly_do = "đang có trong giỏ hàng, đơn hàng hoặc lịch sử kho" if ma_module == "san-pham" else "đang được sản phẩm sử dụng"
            raise LoiQuanTri(f"Không thể xóa {nhan} {ly_do}.") from error
        raise


def _ghi_thay_doi_ton(cursor, san_pham_id, loai, truoc, sau, ghi_chu, users_id):
    if not 0 <= sau <= MAX_INT:
        raise LoiQuanTri("Số tồn sau thay đổi nằm ngoài giới hạn cho phép.")
    if truoc == sau:
        raise LoiQuanTri("Số tồn mới trùng với số tồn hiện tại.")
    cursor.execute("UPDATE san_pham SET so_luong_ton = %s WHERE san_pham_id = %s", (sau, san_pham_id))
    cursor.execute(
        """INSERT INTO lich_su_kho (san_pham_id, loai_giao_dich, so_luong, so_luong_truoc,
                                   so_luong_sau, ghi_chu, users_id) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (san_pham_id, loai, abs(sau - truoc), truoc, sau, ghi_chu, users_id),
    )


def cap_nhat_ton_quan_tri(san_pham_id, loai, so_luong, ton_truoc, ghi_chu, users_id):
    if loai not in ("nhap", "dieu_chinh") or type(so_luong) is not int or not 0 <= so_luong <= MAX_INT:
        raise LoiQuanTri("Thao tác hoặc số lượng không hợp lệ.", 422)
    if (loai == "nhap" and so_luong == 0) or (loai == "dieu_chinh" and not ghi_chu):
        raise LoiQuanTri("Nhập số lượng dương khi nhập kho, hoặc lý do khi điều chỉnh.", 422)
    with _giao_dich_quan_tri() as cursor:
        sp = _doc_ban_ghi(cursor, "san-pham", san_pham_id, khoa=True)
        truoc = sp["so_luong_ton"]
        if truoc != ton_truoc:
            raise LoiQuanTri("Số tồn đã thay đổi. Vui lòng tải lại trang trước khi lưu.")
        sau = truoc + so_luong if loai == "nhap" else so_luong
        _ghi_thay_doi_ton(cursor, san_pham_id, loai, truoc, sau, ghi_chu or "Nhập kho thủ công", users_id)


def lay_chi_tiet_don_quan_tri(don_hang_id):
    with closing(get_db_connection()) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM don_hang WHERE don_hang_id = %s", (don_hang_id,))
        don = cursor.fetchone()
        if don is None:
            raise LoiQuanTri("Đơn hàng không còn tồn tại.", 404)
        cursor.execute(
            """SELECT ten_san_pham, so_luong, don_gia, thanh_tien FROM chi_tiet_don_hang
               WHERE don_hang_id = %s ORDER BY chi_tiet_don_hang_id""", (don_hang_id,),
        )
        don["san_pham"] = cursor.fetchall()
        return don


def _hoan_kho_don_hang(cursor, don, users_id):
    # Đối chiếu lịch sử xuất của checkout để tránh cộng kho cho đơn nhập thủ công.
    cursor.execute(
        """SELECT san_pham_id, SUM(so_luong) AS so_luong FROM chi_tiet_don_hang
           WHERE don_hang_id = %s GROUP BY san_pham_id""", (don["don_hang_id"],),
    )
    chi_tiet = {r["san_pham_id"]: int(r["so_luong"]) for r in cursor.fetchall()}
    cursor.execute(
        """SELECT san_pham_id, SUM(so_luong) AS so_luong FROM lich_su_kho
           WHERE loai_giao_dich = 'xuat' AND ghi_chu = %s AND users_id = %s GROUP BY san_pham_id""",
        (f"Đặt hàng {don['ma_don_hang']}", don["users_id"]),
    )
    da_tru = {r["san_pham_id"]: int(r["so_luong"]) for r in cursor.fetchall()}
    if not chi_tiet or chi_tiet != da_tru or any(qty <= 0 for qty in da_tru.values()):
        raise LoiQuanTri("Lịch sử xuất kho không khớp với đơn. Hãy kiểm tra dữ liệu kho trước khi hủy.")
    # Cùng thứ tự khóa sản phẩm với luồng tạo đơn.
    for san_pham_id in sorted(da_tru):
        sp = _doc_ban_ghi(cursor, "san-pham", san_pham_id, khoa=True)
        truoc = sp["so_luong_ton"]
        _ghi_thay_doi_ton(cursor, san_pham_id, "nhap", truoc, truoc + da_tru[san_pham_id],
                          f"Hoàn kho đơn {don['ma_don_hang']}", users_id)


def cap_nhat_trang_thai_don_quan_tri(don_hang_id, trang_thai_cu, trang_thai_moi, users_id):
    with _giao_dich_quan_tri() as cursor:
        cursor.execute("SELECT * FROM don_hang WHERE don_hang_id = %s FOR UPDATE", (don_hang_id,))
        don = cursor.fetchone()
        if don is None:
            raise LoiQuanTri("Đơn hàng không còn tồn tại.", 404)
        if don["trang_thai_don_hang"] != trang_thai_cu:
            raise LoiQuanTri("Trạng thái đơn vừa thay đổi. Vui lòng tải lại trang.")
        if trang_thai_moi not in CHUYEN_TRANG_THAI_DON.get(trang_thai_cu, ()):
            raise LoiQuanTri("Không thể chuyển đơn sang trạng thái này.", 422)
        if trang_thai_moi == "huy_don":
            if don["trang_thai_thanh_toan"] == "da_thanh_toan":
                raise LoiQuanTri("Đơn đã thanh toán. Cần xử lý hoàn tiền trước khi hủy.")
            _hoan_kho_don_hang(cursor, don, users_id)
        cursor.execute(
            "UPDATE don_hang SET trang_thai_don_hang = %s WHERE don_hang_id = %s", (trang_thai_moi, don_hang_id),
        )
        nhan = TRANG_THAI_DON[trang_thai_moi]
        cursor.execute(
            """INSERT INTO thong_bao (users_id, loai_thong_bao, tieu_de, noi_dung, doi_tuong_id)
               VALUES (%s,%s,%s,%s,%s)""",
            (don["users_id"], LOAI_THONG_BAO_DON[trang_thai_moi], f"{nhan}: {don['ma_don_hang']}",
             f"Đơn {don['ma_don_hang']} đã chuyển sang trạng thái {nhan.lower()}.", don_hang_id),
        )
