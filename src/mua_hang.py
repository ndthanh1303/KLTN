"""Form, kiểm tra dữ liệu và giao dịch giỏ hàng/đặt hàng dùng chung."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

import pymysql

from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, RadioField, SelectMultipleField, StringField, TextAreaField
from wtforms.validators import AnyOf, DataRequired, InputRequired, Length, NumberRange, Optional, Regexp

from db import get_db_connection, lay_chi_tiet_san_pham, lay_gio_hang
from tai_khoan import lam_sach_chuoi

MAX_INT = 2147483647
MAX_TIEN = Decimal("9999999999999.99")
TRANG_THAI_DON = {
    "cho_xu_ly": "Chờ xử lý",
    "da_xac_nhan": "Đã xác nhận",
    "dang_giao": "Đang giao",
    "hoan_thanh": "Hoàn thành",
    "huy_don": "Đã hủy",
}


class LoiMuaHang(ValueError):
    """Lỗi nghiệp vụ có thể hiển thị cho khách hàng."""


class MuaHangForm(FlaskForm):
    so_luong = IntegerField("Số lượng", default=1, validators=[
        InputRequired(message="Vui lòng nhập số lượng."),
        NumberRange(min=1, max=MAX_INT, message="Số lượng phải là số nguyên dương."),
    ])
    hanh_dong = StringField(validators=[DataRequired(), AnyOf(["them", "mua_ngay"])])
    noi_ve = StringField(default="chi_tiet", validators=[Optional(), AnyOf(["trang_chu", "chi_tiet"])])


class CapNhatGioHangForm(FlaskForm):
    so_luong = IntegerField("Số lượng", validators=[
        InputRequired(), NumberRange(min=1, max=MAX_INT),
    ])


class XoaGioHangForm(FlaskForm):
    pass  # FlaskForm vẫn tạo và kiểm tra CSRF token.


class ChonGioHangForm(FlaskForm):
    san_pham_id = SelectMultipleField(coerce=int, validators=[
        DataRequired(message="Vui lòng chọn ít nhất một sản phẩm."),
    ])


class DatHangForm(FlaskForm):
    ten_nguoi_nhan = StringField("Họ tên người nhận", filters=[lam_sach_chuoi], validators=[
        DataRequired(message="Vui lòng nhập tên người nhận."), Length(max=100),
    ])
    so_dien_thoai = StringField("Số điện thoại", filters=[lam_sach_chuoi], validators=[
        DataRequired(message="Vui lòng nhập số điện thoại."), Length(max=15),
        Regexp(r"^\+?[0-9]{9,14}$", message="Nhập 9–14 chữ số, có thể có dấu + ở đầu."),
    ])
    tinh_thanh = StringField("Tỉnh / Thành phố", filters=[lam_sach_chuoi], validators=[
        DataRequired(message="Vui lòng nhập tỉnh / thành phố."), Length(max=100),
    ])
    phuong_xa = StringField("Phường / Xã", filters=[lam_sach_chuoi], validators=[
        DataRequired(message="Vui lòng nhập phường / xã."), Length(max=100),
    ])
    dia_chi_chi_tiet = StringField("Địa chỉ chi tiết", filters=[lam_sach_chuoi], validators=[
        DataRequired(message="Vui lòng nhập địa chỉ chi tiết."), Length(max=255),
    ])
    ghi_chu = TextAreaField("Ghi chú", filters=[lam_sach_chuoi], validators=[Optional(), Length(max=2000)])
    phuong_thuc_thanh_toan = RadioField("Phương thức thanh toán", choices=[
        ("cod", "Thanh toán khi nhận hàng (COD)"),
    ], default="cod", validate_choice=False, validators=[
        AnyOf(["cod"], message="Vui lòng chọn thanh toán khi nhận hàng."),
    ])
    xac_nhan = HiddenField(validators=[InputRequired(), Length(max=50000)])


def _so_nguyen_duong(value):
    return type(value) is int and 1 <= value <= MAX_INT


def _tien(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or not 0 <= result <= MAX_TIEN:
            raise LoiMuaHang("Giá trị tiền không hợp lệ.")
        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as error:
        raise LoiMuaHang("Giá trị tiền không hợp lệ.") from error


def _gia_ban(sp):
    gia = _tien(sp["gia"])
    km = sp["gia_khuyen_mai"]
    if km is not None and 0 <= km < gia:
        return _tien(km)
    return gia


def _khoa_tai_khoan(cursor, users_id):
    # Cùng một tài khoản chỉ thay đổi giỏ/đặt hàng lần lượt trong giao dịch.
    cursor.execute("SELECT users_id FROM users WHERE users_id = %s FOR UPDATE", (users_id,))
    if cursor.fetchone() is None:
        raise LoiMuaHang("Tài khoản không còn tồn tại. Vui lòng đăng nhập lại.")


def _id_gio_hang(cursor, users_id, tao_moi=False):
    cursor.execute("SELECT gio_hang_id FROM gio_hang WHERE users_id = %s", (users_id,))
    row = cursor.fetchone()
    if row:
        return row["gio_hang_id"]
    if tao_moi:
        cursor.execute("INSERT INTO gio_hang (users_id) VALUES (%s)", (users_id,))
        return cursor.lastrowid
    return None


def _khoa_san_pham(cursor, san_pham_id):
    cursor.execute(
        """SELECT san_pham_id, ten_san_pham, gia, gia_khuyen_mai, so_luong_ton
           FROM san_pham WHERE san_pham_id = %s FOR UPDATE""", (san_pham_id,),
    )
    sp = cursor.fetchone()
    if sp is None:
        raise LoiMuaHang("Sản phẩm không còn tồn tại.")
    return sp


def thay_doi_gio_hang(users_id, san_pham_id, so_luong, cong_them=False, tao_neu_chua_co=False):
    """Cộng/thay số lượng, cho phép tạo dòng mới khi được yêu cầu; chưa trừ kho."""
    if not _so_nguyen_duong(san_pham_id) or not _so_nguyen_duong(so_luong):
        raise LoiMuaHang("Sản phẩm hoặc số lượng không hợp lệ.")
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            _khoa_tai_khoan(cursor, users_id)
            cho_phep_tao = cong_them or tao_neu_chua_co
            gio_hang_id = _id_gio_hang(cursor, users_id, tao_moi=cho_phep_tao)
            if gio_hang_id is None:
                raise LoiMuaHang("Sản phẩm không có trong giỏ hàng của bạn.")
            sp = _khoa_san_pham(cursor, san_pham_id)
            cursor.execute(
                """SELECT so_luong FROM chi_tiet_gio_hang
                   WHERE gio_hang_id = %s AND san_pham_id = %s FOR UPDATE""",
                (gio_hang_id, san_pham_id),
            )
            row = cursor.fetchone()
            if not cho_phep_tao and row is None:
                raise LoiMuaHang("Sản phẩm không có trong giỏ hàng của bạn.")
            moi = so_luong + row["so_luong"] if cong_them and row else so_luong
            if not _so_nguyen_duong(moi) or moi > sp["so_luong_ton"]:
                raise LoiMuaHang(f"{sp['ten_san_pham']} hiện còn {max(0, sp['so_luong_ton'])} sản phẩm.")
            if row:
                cursor.execute(
                    """UPDATE chi_tiet_gio_hang SET so_luong = %s
                       WHERE gio_hang_id = %s AND san_pham_id = %s""",
                    (moi, gio_hang_id, san_pham_id),
                )
            else:
                cursor.execute(
                    """INSERT INTO chi_tiet_gio_hang (gio_hang_id, san_pham_id, so_luong)
                       VALUES (%s, %s, %s)""", (gio_hang_id, san_pham_id, moi),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def xoa_san_pham_gio_hang(users_id, san_pham_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            _khoa_tai_khoan(cursor, users_id)
            gio_hang_id = _id_gio_hang(cursor, users_id)
            cursor.execute(
                "DELETE FROM chi_tiet_gio_hang WHERE gio_hang_id = %s AND san_pham_id = %s",
                (gio_hang_id, san_pham_id),
            )
            if cursor.rowcount == 0:
                raise LoiMuaHang("Sản phẩm không có trong giỏ hàng của bạn.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def lay_du_lieu_dat_hang(users_id, lua_chon, phi_van_chuyen):
    """Đọc lại giá/tồn kho cho các sản phẩm khách muốn thanh toán."""
    nguon = lua_chon.get("nguon", "gio_hang")
    if nguon == "mua_ngay":
        pid, qty = lua_chon.get("san_pham_id"), lua_chon.get("so_luong")
        if not _so_nguyen_duong(pid) or not _so_nguyen_duong(qty):
            raise LoiMuaHang("Số lượng mua ngay không hợp lệ.")
        sp = lay_chi_tiet_san_pham(pid)
        if sp is None:
            raise LoiMuaHang("Sản phẩm không còn tồn tại.")
        sp["so_luong"] = qty
        sp["url_anh"] = sp["hinh_anh"][0]["url_anh"] if sp["hinh_anh"] else None
        san_pham = [sp]
    elif nguon == "gio_hang":
        san_pham = lay_gio_hang(users_id)["san_pham"]
        ids = lua_chon.get("ids")
        if ids is not None:
            if not isinstance(ids, list) or not ids or not all(_so_nguyen_duong(i) for i in ids):
                raise LoiMuaHang("Vui lòng chọn sản phẩm muốn đặt hàng.")
            duoc_chon = set(ids)
            san_pham = [sp for sp in san_pham if sp["san_pham_id"] in duoc_chon]
            if {sp["san_pham_id"] for sp in san_pham} != duoc_chon:
                raise LoiMuaHang("Giỏ hàng đã thay đổi. Vui lòng chọn lại sản phẩm.")
    else:
        raise LoiMuaHang("Nguồn đặt hàng không hợp lệ.")

    if not san_pham:
        raise LoiMuaHang("Giỏ hàng của bạn đang trống.")
    tong_so_luong, tam_tinh = 0, Decimal("0.00")
    for sp in san_pham:
        if not _so_nguyen_duong(sp["so_luong"]) or sp["so_luong"] > sp["so_luong_ton"]:
            raise LoiMuaHang(f"Vui lòng kiểm tra lại số lượng của {sp['ten_san_pham']}.")
        sp["gia_ban"] = _gia_ban(sp)
        sp["thanh_tien"] = sp["gia_ban"] * sp["so_luong"]
        tam_tinh += sp["thanh_tien"]
        tong_so_luong += sp["so_luong"]
    phi = _tien(phi_van_chuyen)
    return {
        "nguon": nguon, "san_pham": san_pham, "tong_so_luong": tong_so_luong,
        "tam_tinh": _tien(tam_tinh), "phi_van_chuyen": phi,
        "tong_tien": _tien(tam_tinh + phi),
    }


def lay_thong_tin_nhan_hang(users_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ho_ten, so_dien_thoai FROM users WHERE users_id = %s", (users_id,))
            return cursor.fetchone() or {}
    finally:
        connection.close()


def tao_don_hang(users_id, thong_tin, xac_nhan, phi_van_chuyen):
    """Thử lại tối đa ba lần nếu InnoDB hủy giao dịch do deadlock."""
    for lan in range(3):
        try:
            return _luu_don_hang(users_id, thong_tin, xac_nhan, phi_van_chuyen)
        except pymysql.OperationalError as error:
            if not error.args or error.args[0] != 1213 or lan == 2:
                raise


def _luu_don_hang(users_id, thong_tin, xac_nhan, phi_van_chuyen):
    """Lưu đơn, trừ kho, ghi lịch sử và xóa dòng giỏ đã mua trong một giao dịch.

    xac_nhan phải được route kiểm tra chữ ký và thời hạn trước khi gọi.
    ma_don_hang là duy nhất để cùng một lần xác nhận không tạo hai đơn.
    """
    ma = xac_nhan.get("ma_don_hang", "")
    items = xac_nhan.get("san_pham", [])
    nguon = xac_nhan.get("nguon")
    if (xac_nhan.get("users_id") != users_id or not re.fullmatch(r"DH[0-9a-f]{24}", ma)
            or nguon not in ("gio_hang", "mua_ngay") or not isinstance(items, list) or not items):
        raise LoiMuaHang("Phiên đặt hàng không hợp lệ. Vui lòng tải lại trang.")
    if nguon == "mua_ngay" and len(items) != 1:
        raise LoiMuaHang("Phiên mua ngay không hợp lệ.")
    if not all(isinstance(i, dict) and _so_nguyen_duong(i.get("id"))
               and _so_nguyen_duong(i.get("so_luong")) for i in items):
        raise LoiMuaHang("Sản phẩm hoặc số lượng không hợp lệ.")
    theo_id = {i["id"]: i for i in items}
    if len(theo_id) != len(items):
        raise LoiMuaHang("Danh sách sản phẩm bị trùng.")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            _khoa_tai_khoan(cursor, users_id)
            cursor.execute(
                "SELECT don_hang_id FROM don_hang WHERE ma_don_hang = %s AND users_id = %s",
                (ma, users_id),
            )
            cu = cursor.fetchone()
            if cu:
                connection.commit()
                return cu["don_hang_id"]  # Bấm hai lần vẫn trả cùng đơn đã tạo.

            phi = _tien(phi_van_chuyen)
            if _tien(xac_nhan.get("phi_van_chuyen")) != phi:
                raise LoiMuaHang("Phí vận chuyển đã thay đổi. Vui lòng kiểm tra lại đơn.")
            gio_hang_id = None
            if nguon == "gio_hang":
                gio_hang_id = _id_gio_hang(cursor, users_id)
                for pid in sorted(theo_id):
                    cursor.execute(
                        """SELECT so_luong FROM chi_tiet_gio_hang
                           WHERE gio_hang_id = %s AND san_pham_id = %s FOR UPDATE""",
                        (gio_hang_id, pid),
                    )
                    row = cursor.fetchone()
                    if row is None or row["so_luong"] != theo_id[pid]["so_luong"]:
                        raise LoiMuaHang("Giỏ hàng đã thay đổi. Vui lòng kiểm tra lại trước khi đặt.")

            san_pham, tam_tinh = [], Decimal("0.00")
            # Khóa theo cùng thứ tự ID để hạn chế deadlock giữa các đơn.
            for pid in sorted(theo_id):
                sp = _khoa_san_pham(cursor, pid)
                qty = theo_id[pid]["so_luong"]
                if qty > sp["so_luong_ton"]:
                    raise LoiMuaHang(f"{sp['ten_san_pham']} không còn đủ số lượng.")
                gia = _gia_ban(sp)
                if gia != _tien(theo_id[pid].get("gia")):
                    raise LoiMuaHang("Giá sản phẩm đã thay đổi. Vui lòng kiểm tra lại trước khi đặt.")
                sp.update(so_luong=qty, don_gia=gia, thanh_tien=_tien(gia * qty))
                tam_tinh += sp["thanh_tien"]
                san_pham.append(sp)
            tam_tinh, tong_tien = _tien(tam_tinh), _tien(tam_tinh + phi)

            cursor.execute(
                """INSERT INTO don_hang
                   (users_id, ma_don_hang, ten_nguoi_nhan, so_dien_thoai,
                    tinh_thanh, phuong_xa, dia_chi_chi_tiet, tam_tinh,
                    phi_van_chuyen, giam_gia, tong_tien, phuong_thuc_thanh_toan,
                    trang_thai_thanh_toan, trang_thai_don_hang, ghi_chu)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,'cod',
                           'chua_thanh_toan','cho_xu_ly',%s)""",
                (users_id, ma, thong_tin["ten_nguoi_nhan"], thong_tin["so_dien_thoai"],
                 thong_tin["tinh_thanh"], thong_tin["phuong_xa"], thong_tin["dia_chi_chi_tiet"],
                 tam_tinh, phi, tong_tien, thong_tin.get("ghi_chu") or None),
            )
            don_hang_id = cursor.lastrowid
            for sp in san_pham:
                pid, qty = sp["san_pham_id"], sp["so_luong"]
                cursor.execute(
                    """UPDATE san_pham SET so_luong_ton = so_luong_ton - %s
                       WHERE san_pham_id = %s AND so_luong_ton >= %s""", (qty, pid, qty),
                )
                if cursor.rowcount != 1:
                    raise LoiMuaHang("Tồn kho vừa thay đổi. Vui lòng kiểm tra lại đơn.")
                cursor.execute(
                    """INSERT INTO chi_tiet_don_hang
                       (don_hang_id, san_pham_id, ten_san_pham, so_luong, don_gia, thanh_tien)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (don_hang_id, pid, sp["ten_san_pham"], qty, sp["don_gia"], sp["thanh_tien"]),
                )
                cursor.execute(
                    """INSERT INTO lich_su_kho
                       (san_pham_id, loai_giao_dich, so_luong, so_luong_truoc,
                        so_luong_sau, ghi_chu, users_id)
                       VALUES (%s,'xuat',%s,%s,%s,%s,%s)""",
                    (pid, qty, sp["so_luong_ton"], sp["so_luong_ton"] - qty,
                     f"Đặt hàng {ma}", users_id),
                )
                if gio_hang_id is not None:
                    cursor.execute(
                        "DELETE FROM chi_tiet_gio_hang WHERE gio_hang_id = %s AND san_pham_id = %s",
                        (gio_hang_id, pid),
                    )
            cursor.execute("SELECT users_id FROM users WHERE phan_quyen = 'admin'")
            for admin in cursor.fetchall():
                cursor.execute(
                    """INSERT INTO thong_bao
                       (users_id, loai_thong_bao, tieu_de, noi_dung, doi_tuong_id)
                       VALUES (%s, 'don_hang_moi', %s, %s, %s)""",
                    (admin["users_id"], f"Đơn hàng mới {ma}",
                     f"{thong_tin['ten_nguoi_nhan']} vừa đặt đơn {ma}.", don_hang_id),
                )
        connection.commit()
        return don_hang_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def lay_don_mua(users_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT don_hang_id, ma_don_hang, tong_tien, trang_thai_don_hang, created_at
                   FROM don_hang WHERE users_id = %s ORDER BY created_at DESC, don_hang_id DESC""",
                (users_id,),
            )
            return list(cursor.fetchall())
    finally:
        connection.close()


def lay_chi_tiet_don_mua(users_id, don_hang_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM don_hang WHERE don_hang_id = %s AND users_id = %s",
                (don_hang_id, users_id),
            )
            don = cursor.fetchone()
            if don is None:
                return None
            cursor.execute(
                """SELECT san_pham_id, ten_san_pham, so_luong, don_gia, thanh_tien
                   FROM chi_tiet_don_hang WHERE don_hang_id = %s
                   ORDER BY chi_tiet_don_hang_id ASC""", (don_hang_id,),
            )
            don["san_pham"] = list(cursor.fetchall())
            return don
    finally:
        connection.close()
