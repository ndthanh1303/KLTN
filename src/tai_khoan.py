"""Form và hàm tài khoản dùng chung cho các route trong app.py."""

import pymysql
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired, Email, EqualTo, InputRequired, Length, Optional, Regexp,
)

from db import get_db_connection


def lam_sach_chuoi(value):
    """Bỏ khoảng trắng đầu/cuối; không dùng hàm này cho mật khẩu."""
    return (value or "").strip()


def chuan_hoa_email(value):
    return lam_sach_chuoi(value).lower()


def truong_email():
    """Tạo một trường email mới với cùng bộ kiểm tra cho mỗi form."""
    return EmailField(
        "Email",
        filters=[chuan_hoa_email],
        validators=[
            DataRequired(message="Vui lòng nhập email."),
            Length(max=150, message="Email không vượt quá 150 ký tự."),
            Email(message="Email không hợp lệ."),
        ],
    )


def truong_mat_khau(dang_ky=False):
    gioi_han = (
        Length(min=8, max=128, message="Mật khẩu cần từ 8 đến 128 ký tự.")
        if dang_ky
        else Length(max=128, message="Mật khẩu không vượt quá 128 ký tự.")
    )
    return PasswordField(
        "Mật khẩu",
        validators=[
            InputRequired(message="Vui lòng nhập mật khẩu."),
            gioi_han,
        ],
    )


class DangKyForm(FlaskForm):
    ho_ten = StringField(
        "Họ và tên",
        filters=[lam_sach_chuoi],
        validators=[
            DataRequired(message="Vui lòng nhập họ tên."),
            Length(max=100, message="Họ tên không vượt quá 100 ký tự."),
        ],
    )
    email = truong_email()
    so_dien_thoai = StringField(
        "Số điện thoại (không bắt buộc)",
        filters=[lam_sach_chuoi],
        validators=[
            Optional(),
            Length(max=15, message="Số điện thoại không vượt quá 15 ký tự."),
            Regexp(
                r"^\+?[0-9]{9,14}$",
                message="Nhập 9–14 chữ số, có thể có dấu + ở đầu.",
            ),
        ],
    )
    mat_khau = truong_mat_khau(dang_ky=True)
    xac_nhan_mat_khau = PasswordField(
        "Nhập lại mật khẩu",
        validators=[
            InputRequired(message="Vui lòng nhập lại mật khẩu."),
            EqualTo("mat_khau", message="Hai mật khẩu không khớp."),
        ],
    )
    submit = SubmitField("Đăng ký")


class DangNhapForm(FlaskForm):
    email = truong_email()
    mat_khau = truong_mat_khau()
    submit = SubmitField("Đăng nhập")

class DangNhapAdminForm(FlaskForm):
    ten_dang_nhap = StringField(
        "Tên đăng nhập",
        default="admin",
        validators=[
            InputRequired(message="Vui lòng nhập tên đăng nhập."),
            Length(max=50, message="Tên đăng nhập không vượt quá 50 ký tự."),
            Regexp(r"\Aadmin\Z", message="Tên đăng nhập quản trị phải là admin."),
        ],
    )
    mat_khau = truong_mat_khau()  # Dùng lại kiểm tra mật khẩu của form hiện có.
    ghi_nho = BooleanField("Ghi nhớ đăng nhập trong 7 ngày")
    submit = SubmitField("Đăng nhập")

class DangXuatForm(FlaskForm):
    submit = SubmitField("Đăng xuất")

class EmailDaTonTai(Exception):
    """Email vi phạm ràng buộc UNIQUE của bảng users."""


def tao_tai_khoan(ho_ten, email, so_dien_thoai, mat_khau):
    """Nhận dữ liệu đã qua DangKyForm; tạo tài khoản và giỏ hàng rỗng."""
    password_hash = generate_password_hash(mat_khau)
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO users
                        (ho_ten, email, so_dien_thoai, mat_khau, phan_quyen)
                    VALUES (%s, %s, %s, %s, 'user')
                    """,
                    (
                        lam_sach_chuoi(ho_ten),
                        chuan_hoa_email(email),
                        lam_sach_chuoi(so_dien_thoai) or None,
                        password_hash,
                    ),
                )
            except pymysql.IntegrityError as error:
                if error.args and error.args[0] == 1062:
                    raise EmailDaTonTai() from error
                raise

            users_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO gio_hang (users_id) VALUES (%s)",
                (users_id,),
            )
        connection.commit()
        return users_id
    except (pymysql.MySQLError, EmailDaTonTai):
        # Nếu một INSERT thất bại, hủy cả hai thao tác.
        connection.rollback()
        raise
    finally:
        connection.close()


def tim_tai_khoan_theo_email(email):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT users_id, ho_ten, email, mat_khau, phan_quyen
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (chuan_hoa_email(email),),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def tim_tai_khoan_theo_id(users_id):
    """Đọc quyền hiện tại từ database; không lấy password hash cho bước phân quyền."""
    if type(users_id) is not int or users_id < 1:
        return None
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT users_id, ho_ten, email, phan_quyen
                   FROM users WHERE users_id = %s LIMIT 1""",
                (users_id,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def kiem_tra_mat_khau(mat_khau_da_bam, mat_khau_nhap):
    if not isinstance(mat_khau_da_bam, str) or not isinstance(mat_khau_nhap, str):
        return False
    try:
        return check_password_hash(mat_khau_da_bam, mat_khau_nhap)
    except (ValueError, TypeError):
        return False


def xac_thuc_tai_khoan(email, mat_khau):
    """Trả thông tin tài khoản khi đúng mật khẩu, ngược lại trả None."""
    user = tim_tai_khoan_theo_email(email)
    if not user or not kiem_tra_mat_khau(user["mat_khau"], mat_khau):
        return None

    # Không đưa password hash vào session hoặc kết quả xác thực.
    return {
        "users_id": user["users_id"],
        "ho_ten": user["ho_ten"],
        "email": user["email"],
        "phan_quyen": user["phan_quyen"],
    }


class LoiCauHinhAdmin(Exception):
    """Cần chỉ định ADMIN_USER_ID khi có nhiều tài khoản quản trị."""


def xac_thuc_quan_tri(ten_dang_nhap, mat_khau, users_id=None):
    """Tên cố định admin; mật khẩu thuộc đúng một tài khoản quản trị trong DB."""
    if ten_dang_nhap != "admin":
        return None
    if users_id is not None and (type(users_id) is not int or users_id < 1):
        raise LoiCauHinhAdmin("ADMIN_USER_ID phải là users_id nguyên dương.")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if users_id is None:
                # Đọc tối đa hai dòng để phát hiện trường hợp tên admin bị mơ hồ.
                cursor.execute(
                    """SELECT users_id, ho_ten, email, mat_khau, phan_quyen
                       FROM users WHERE phan_quyen = %s
                       ORDER BY users_id LIMIT 2""",
                    ("admin",),
                )
            else:
                cursor.execute(
                    """SELECT users_id, ho_ten, email, mat_khau, phan_quyen
                       FROM users WHERE users_id = %s AND phan_quyen = %s
                       LIMIT 1""",
                    (users_id, "admin"),
                )
            tai_khoan = cursor.fetchall()
    finally:
        connection.close()

    if len(tai_khoan) > 1:
        raise LoiCauHinhAdmin("Có nhiều admin. Hãy cấu hình ADMIN_USER_ID trong app.py.")
    if not tai_khoan or not kiem_tra_mat_khau(tai_khoan[0]["mat_khau"], mat_khau):
        return None
    user = tai_khoan[0]
    return {key: user[key] for key in ("users_id", "ho_ten", "email", "phan_quyen")}
