"""Biểu mẫu và kiểm tra dữ liệu cho các thao tác ghi trong admin."""
from decimal import Decimal
from urllib.parse import urlsplit

from flask_wtf import FlaskForm
from wtforms import DecimalField, HiddenField, IntegerField, SelectField, StringField, TextAreaField
from wtforms.validators import AnyOf, DataRequired, InputRequired, Length, NumberRange, Optional, ValidationError
from wtforms.widgets import HiddenInput

from mua_hang import MAX_INT, MAX_TIEN, TRANG_THAI_DON
from tai_khoan import lam_sach_chuoi


def url_anh_hop_le(value):
    """Chấp nhận URL HTTPS (ví dụ Cloudinary) hoặc ảnh tĩnh trong dự án."""
    if not value or len(value) > 500 or "\\" in value or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    try:
        url = urlsplit(value)
        if value.startswith("/static/"):
            return not url.netloc and ".." not in url.path.split("/")
        return url.scheme == "https" and bool(url.hostname) and url.username is None and url.password is None
    except ValueError:
        return False


def kiem_tra_url_anh(form, field):
    if not url_anh_hop_le(field.data):
        raise ValidationError("Nhập URL ảnh HTTPS hoặc đường dẫn bắt đầu bằng /static/ (tối đa 500 ký tự).")


def kiem_tra_tien(form, field):
    gia = field.data
    if not isinstance(gia, Decimal) or not gia.is_finite() or not 0 <= gia <= MAX_TIEN:
        raise ValidationError("Giá phải là số không âm, tối đa 9.999.999.999.999,99 đồng.")
    if gia != gia.quantize(Decimal("0.01")):
        raise ValidationError("Giá chỉ được có tối đa 2 chữ số thập phân.")


class NhomSanPhamForm(FlaskForm):
    ten = StringField("Tên", filters=[lam_sach_chuoi], validators=[
        DataRequired(message="Vui lòng nhập tên."), Length(max=100),
    ])
    hinh_anh = StringField("Đường dẫn ảnh", filters=[lam_sach_chuoi], validators=[
        Optional(), kiem_tra_url_anh,
    ], description="Có thể để trống hoặc dán URL ảnh HTTPS từ Cloudinary.")


class SanPhamQuanTriForm(FlaskForm):
    ma_san_pham = StringField("Mã sản phẩm", filters=[lam_sach_chuoi], validators=[
        DataRequired(message="Vui lòng nhập mã sản phẩm."), Length(max=50),
    ])
    ten_san_pham = StringField("Tên sản phẩm", filters=[lam_sach_chuoi], validators=[
        DataRequired(message="Vui lòng nhập tên sản phẩm."), Length(max=200),
    ])
    danh_muc_id = SelectField("Danh mục", coerce=int, validators=[
        NumberRange(min=1, message="Vui lòng chọn danh mục."),
    ])
    thuong_hieu_id = SelectField("Thương hiệu", coerce=int, default=0)
    gia = DecimalField("Giá niêm yết (đ)", places=None, validators=[
        InputRequired(message="Vui lòng nhập giá."), kiem_tra_tien,
    ], description="Ví dụ: 1500000. Không dùng dấu phân cách hàng nghìn.")
    gia_khuyen_mai = DecimalField("Giá khuyến mãi (đ)", places=None, validators=[
        Optional(), kiem_tra_tien,
    ], description="Để trống nếu không giảm giá; nếu có, phải thấp hơn giá niêm yết.")
    mo_ta = TextAreaField("Mô tả", filters=[lam_sach_chuoi], validators=[Optional(), Length(max=10000)])
    hinh_anh = TextAreaField("Ảnh sản phẩm", filters=[lam_sach_chuoi], validators=[
        Optional(), Length(max=30000),
    ], description="Mỗi dòng một URL ảnh. Đặt ảnh muốn làm đại diện ở dòng đầu. Xóa dòng để gỡ ảnh.")

    def validate_gia_khuyen_mai(self, field):
        gia = self.gia.data
        if (isinstance(gia, Decimal) and gia.is_finite() and isinstance(field.data, Decimal)
                and field.data.is_finite() and field.data >= gia):
            raise ValidationError("Giá khuyến mãi phải thấp hơn giá niêm yết.")

    def danh_sach_anh(self):
        return [dong.strip() for dong in self.hinh_anh.data.splitlines() if dong.strip()]

    def validate_hinh_anh(self, field):
        anh = self.danh_sach_anh()
        for i, url in enumerate(anh, start=1):
            if not url_anh_hop_le(url):
                raise ValidationError(f"URL ảnh số {i} không hợp lệ. Dùng HTTPS hoặc /static/.")
        if len(anh) != len(set(anh)):
            raise ValidationError("Danh sách ảnh có đường dẫn bị trùng.")


class XoaDuLieuForm(FlaskForm):
    """Chỉ cần CSRF vì bản ghi được xác định bằng URL."""


class TrangThaiDonForm(FlaskForm):
    trang_thai_cu = HiddenField(validators=[InputRequired(), AnyOf(tuple(TRANG_THAI_DON))])
    trang_thai_moi = SelectField("Trạng thái mới", validators=[
        InputRequired(message="Vui lòng chọn trạng thái mới."),
    ])


class DieuChinhKhoForm(FlaskForm):
    ton_truoc = IntegerField(widget=HiddenInput(), validators=[InputRequired(), NumberRange(min=0, max=MAX_INT)])
    loai = SelectField("Thao tác", choices=[("nhap", "Nhập kho"), ("dieu_chinh", "Điều chỉnh tồn kho")])
    so_luong = IntegerField("Số lượng", validators=[
        InputRequired(message="Vui lòng nhập số lượng."),
        NumberRange(min=0, max=MAX_INT, message="Nhập số nguyên từ 0 đến 2.147.483.647."),
    ], description="Nhập kho: số lượng cộng thêm. Điều chỉnh: số tồn thực tế sau khi kiểm kê.")
    ghi_chu = TextAreaField("Ghi chú", filters=[lam_sach_chuoi], validators=[Length(max=2000)],
                           description="Bắt buộc nhập lý do khi điều chỉnh tồn kho.")

    def validate_so_luong(self, field):
        if self.loai.data == "nhap" and field.data == 0:
            raise ValidationError("Số lượng nhập phải lớn hơn 0.")

    def validate_ghi_chu(self, field):
        if self.loai.data == "dieu_chinh" and not field.data:
            raise ValidationError("Vui lòng nhập lý do điều chỉnh.")
