import os

import pymysql
from flask import Flask, flash, redirect, render_template, url_for
# from flask_wtf import FlaskForm
# from werkzeug.security import generate_password_hash
# from wtforms import EmailField, PasswordField, StringField, SubmitField
# from wtforms.validators import (
#     DataRequired, Email, EqualTo, InputRequired, Length, Optional, Regexp,
# )

# db.py đọc .env khi được import.
from db import get_db_connection, lay_du_lieu_trang_chu, lay_chi_tiet_san_pham, lay_gio_hang


from flask import (
    flash,abort, redirect, render_template, request, session, url_for,
)

from tai_khoan import (
    DangKyForm,
    DangNhapForm,
    DangXuatForm,
    EmailDaTonTai,
    tao_tai_khoan,
    xac_thuc_tai_khoan,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_HTTPONLY"] = True # Ngăn JavaScript trong trang đọc cookie phiên đăng nhập.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax" # Hạn chế gửi cookie khi yêu cầu đến từ website khác, giúp giảm nguy cơ CSRF.


@app.route("/")
def trang_chu():
    return render_template(
        "home.html",
        home_data=lay_du_lieu_trang_chu(),
    )

def dich_den_sau_dang_nhap():
    """Chỉ cho chuyển về trang chủ hoặc URL giỏ hàng của hệ thống."""
    if request.args.get("next") == "gio_hang":
        return url_for("gio_hang")
    return url_for("trang_chu")

@app.route("/dangky", methods=["GET", "POST"])
def dangky():
    if session.get("users_id"):
        return redirect(dich_den_sau_dang_nhap())

    form = DangKyForm()
    if form.validate_on_submit():
        try:
            tao_tai_khoan(
                form.ho_ten.data,
                form.email.data,
                form.so_dien_thoai.data,
                form.mat_khau.data,
            )
        except EmailDaTonTai:
            form.email.errors.append("Email này đã được đăng ký.")
        except pymysql.MySQLError:
            app.logger.exception("Lỗi database khi đăng ký.")
            flash("Không thể tạo tài khoản. Vui lòng thử lại.", "error")
        else:
            flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
            next_page = "gio_hang" if request.args.get("next") == "gio_hang" else None
            return redirect(url_for("dangnhap", next=next_page))

    return render_template("dangky.html", form=form)


@app.route("/dangnhap", methods=["GET", "POST"])
def dangnhap():
    if session.get("users_id"):
        return redirect(dich_den_sau_dang_nhap())
    
    form = DangNhapForm()
    if form.validate_on_submit():
        try:
            user = xac_thuc_tai_khoan(form.email.data, form.mat_khau.data)
        except pymysql.MySQLError:
            app.logger.exception("Lỗi database khi đăng nhập.")
            flash("Không thể đăng nhập lúc này. Vui lòng thử lại.", "error")
        else:
            if user:
                session.clear()
                session["users_id"] = user["users_id"]
                session["ho_ten"] = user["ho_ten"]
                session["phan_quyen"] = user["phan_quyen"]
                flash("Đăng nhập thành công.", "success")
                return redirect(dich_den_sau_dang_nhap())

            flash("Email hoặc mật khẩu không đúng.", "error")

    return render_template("dangnhap.html", form=form)

@app.context_processor
def cung_cap_form_dangxuat():
    # Cung cấp form có token CSRF cho các template.
    return {"form_dangxuat": DangXuatForm()}


@app.route("/dangxuat", methods=["POST"])
def dangxuat():
    form = DangXuatForm()

    if not form.validate_on_submit():
        abort(
            400,
            description="Yêu cầu đăng xuất không hợp lệ. Hãy tải lại trang.",
        )

    session.clear()  # Xóa thông tin đăng nhập trong session.
    flash("Bạn đã đăng xuất.", "success")

    return redirect(url_for("dangnhap"))  # Chuyển tới trang đăng nhập.

@app.route("/san-pham/<int:san_pham_id>")
def chi_tiet_san_pham(san_pham_id):
    san_pham = lay_chi_tiet_san_pham(san_pham_id)
    if san_pham is None:
        abort(404)  # ID không tồn tại trong database.
    return render_template("chi_tiet_san_pham.html", san_pham=san_pham)

@app.route("/gio-hang")
def gio_hang():
    users_id = session.get("users_id")
    if not users_id:
        return redirect(url_for("dangnhap", next="gio_hang"))

    try:
        du_lieu_gio_hang = lay_gio_hang(users_id)
    except pymysql.MySQLError:
        app.logger.exception("Lỗi database khi tải giỏ hàng.")
        abort(503, description="Không thể tải giỏ hàng. Vui lòng thử lại sau.")

    return render_template("gio_hang.html", gio_hang=du_lieu_gio_hang)

if __name__ == "__main__":
    app.run(debug=True)