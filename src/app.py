import os
import time
from secrets import token_hex
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import pymysql
from flask import Flask, flash, redirect, render_template, url_for


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

from mua_hang import (
    MuaHangForm, CapNhatGioHangForm, XoaGioHangForm, ChonGioHangForm,
    DatHangForm, LoiMuaHang, TRANG_THAI_DON,
    thay_doi_gio_hang, xoa_san_pham_gio_hang, lay_du_lieu_dat_hang,
    lay_thong_tin_nhan_hang, tao_don_hang, lay_don_mua, lay_chi_tiet_don_mua,
)

app = Flask(__name__)
app.config["PHI_VAN_CHUYEN"] = "0"  # Tạm tính 0 đồng; chỉnh theo chính sách cửa hàng.

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
    """Chỉ cho chuyển tới các trang nội bộ nằm trong danh sách cho phép."""
    dich_den = {
        "gio_hang": "gio_hang", "dat_hang": "dat_hang",
        "don_mua": "don_mua", "mua_hang": "gio_hang",
    }
    return url_for(dich_den.get(request.args.get("next"), "trang_chu"))

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
            next_page = request.args.get("next")
            if next_page not in ("gio_hang", "dat_hang", "don_mua", "mua_hang"):
                next_page = None
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
                y_dinh = session.get("y_dinh_mua") if request.args.get("next") == "mua_hang" else None
                session.clear()
                session["users_id"] = user["users_id"]
                session["ho_ten"] = user["ho_ten"]
                session["phan_quyen"] = user["phan_quyen"]
                flash("Đăng nhập thành công.", "success")
                if y_dinh:
                    return redirect(_tiep_tuc_mua_sau_dang_nhap(user["users_id"], y_dinh), code=303)
                return redirect(dich_den_sau_dang_nhap())

            flash("Email hoặc mật khẩu không đúng.", "error")

    return render_template("dangnhap.html", form=form)

@app.context_processor
def cung_cap_form_dangxuat():
    # Cung cấp form có token CSRF cho các template.
    return {
        "form_dangxuat": DangXuatForm(),
        "form_mua_hang": MuaHangForm(),
        "trang_thai_don": TRANG_THAI_DON,
    }


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

    return render_template(
        "gio_hang.html",
        gio_hang=du_lieu_gio_hang,
        san_pham_duoc_chon=session.get("chon_gio_hang"),
    )

def _kiem_tra_csrf(form):
    if form.csrf_token.errors:
        abort(400, description="Phiên biểu mẫu đã hết hạn. Vui lòng tải lại trang.")


def _mua_ngay_ve_gio_hang(users_id, san_pham_id, so_luong):
    """Lưu số lượng muốn mua và chỉ tích sản phẩm này trong giỏ."""
    thay_doi_gio_hang(users_id, san_pham_id, so_luong, tao_neu_chua_co=True)
    session["chon_gio_hang"] = [san_pham_id]
    session.pop("chon_dat_hang", None)
    flash("Đã chọn sản phẩm trong giỏ hàng. Vui lòng kiểm tra số lượng trước khi đặt hàng.", "success")
    return url_for("gio_hang")


def _tiep_tuc_mua_sau_dang_nhap(users_id, y_dinh):
    """Chỉ gọi sau POST đăng nhập thành công để hoàn tất thao tác khách đã chọn."""
    if (not isinstance(y_dinh, dict) or type(y_dinh.get("luc_tao")) is not int
            or not 0 <= time.time() - y_dinh["luc_tao"] <= 1800):
        flash("Yêu cầu mua đã hết hạn. Vui lòng chọn lại sản phẩm.", "error")
        return url_for("trang_chu")
    pid, qty = y_dinh.get("san_pham_id"), y_dinh.get("so_luong")
    if type(pid) is not int or type(qty) is not int or pid < 1 or qty < 1:
        return url_for("trang_chu")
    if y_dinh.get("hanh_dong") not in ("them", "mua_ngay"):
        return url_for("trang_chu")
    try:
        if y_dinh["hanh_dong"] == "mua_ngay":
            return _mua_ngay_ve_gio_hang(users_id, pid, qty)
        thay_doi_gio_hang(users_id, pid, qty, cong_them=True)
    except LoiMuaHang as error:
        flash(str(error), "error")
    except pymysql.MySQLError:
        app.logger.exception("Lỗi thêm vào giỏ sau đăng nhập.")
        flash("Không thể thêm sản phẩm lúc này. Vui lòng thử lại.", "error")
    else:
        flash("Đã thêm sản phẩm vào giỏ hàng thành công.", "cart_success")
    if y_dinh.get("noi_ve") == "trang_chu":
        return url_for("trang_chu")
    return url_for("chi_tiet_san_pham", san_pham_id=pid)


@app.route("/san-pham/<int:san_pham_id>/mua", methods=["POST"])
def mua_san_pham(san_pham_id):
    form = MuaHangForm()
    if not form.validate_on_submit():
        _kiem_tra_csrf(form)
        flash("Vui lòng chọn thao tác mua và nhập số lượng nguyên dương.", "error")
        return redirect(url_for("chi_tiet_san_pham", san_pham_id=san_pham_id), code=303)
    if not session.get("users_id"):
        # Chỉ giữ ý định trong session; chưa thay đổi database khi chưa đăng nhập.
        session["y_dinh_mua"] = {
            "san_pham_id": san_pham_id, "so_luong": form.so_luong.data,
            "hanh_dong": form.hanh_dong.data, "noi_ve": form.noi_ve.data,
            "luc_tao": int(time.time()),
        }
        flash("Vui lòng đăng nhập để tiếp tục mua hàng.", "info")
        return redirect(url_for("dangnhap", next="mua_hang"), code=303)
    try:
        if form.hanh_dong.data == "mua_ngay":
            return redirect(
                _mua_ngay_ve_gio_hang(session["users_id"], san_pham_id, form.so_luong.data),
                code=303,
            )
        thay_doi_gio_hang(session["users_id"], san_pham_id, form.so_luong.data, cong_them=True)
    except LoiMuaHang as error:
        flash(str(error), "error")
    except pymysql.MySQLError:
        app.logger.exception("Lỗi thêm sản phẩm vào giỏ.")
        flash("Không thể thêm sản phẩm lúc này. Vui lòng thử lại.", "error")
    else:
        flash("Đã thêm sản phẩm vào giỏ hàng thành công.", "cart_success")
    if form.noi_ve.data == "trang_chu":
        return redirect(url_for("trang_chu"), code=303)
    return redirect(url_for("chi_tiet_san_pham", san_pham_id=san_pham_id), code=303)


@app.route("/gio-hang/<int:san_pham_id>/cap-nhat", methods=["POST"])
def cap_nhat_gio_hang(san_pham_id):
    if not session.get("users_id"):
        return redirect(url_for("dangnhap", next="gio_hang"), code=303)
    form = CapNhatGioHangForm()
    if not form.validate_on_submit():
        _kiem_tra_csrf(form)
        flash("Số lượng phải là số nguyên dương.", "error")
    else:
        try:
            thay_doi_gio_hang(session["users_id"], san_pham_id, form.so_luong.data)
        except LoiMuaHang as error:
            flash(str(error), "error")
        except pymysql.MySQLError:
            app.logger.exception("Lỗi cập nhật giỏ.")
            flash("Không thể cập nhật giỏ hàng. Vui lòng thử lại.", "error")
        else:
            flash("Đã cập nhật số lượng.", "success")
    return redirect(url_for("gio_hang"), code=303)


@app.route("/gio-hang/<int:san_pham_id>/xoa", methods=["POST"])
def xoa_khoi_gio_hang(san_pham_id):
    if not session.get("users_id"):
        return redirect(url_for("dangnhap", next="gio_hang"), code=303)
    form = XoaGioHangForm()
    if not form.validate_on_submit():
        _kiem_tra_csrf(form)
        abort(400)
    try:
        xoa_san_pham_gio_hang(session["users_id"], san_pham_id)
    except LoiMuaHang as error:
        flash(str(error), "error")
    except pymysql.MySQLError:
        app.logger.exception("Lỗi xóa sản phẩm trong giỏ.")
        flash("Không thể xóa sản phẩm. Vui lòng thử lại.", "error")
    else:
        flash("Đã xóa sản phẩm khỏi giỏ hàng.", "success")
    return redirect(url_for("gio_hang"), code=303)


@app.route("/dat-hang/chon", methods=["POST"])
def chon_san_pham_dat_hang():
    if not session.get("users_id"):
        return redirect(url_for("dangnhap", next="gio_hang"), code=303)
    form = ChonGioHangForm()
    try:
        san_pham = lay_gio_hang(session["users_id"])["san_pham"]
    except pymysql.MySQLError:
        app.logger.exception("Lỗi đọc sản phẩm được chọn.")
        abort(503, description="Không thể đọc giỏ hàng. Vui lòng thử lại sau.")
    form.san_pham_id.choices = [(sp["san_pham_id"], sp["ten_san_pham"]) for sp in san_pham]
    if not form.validate_on_submit():
        _kiem_tra_csrf(form)
        flash("Vui lòng chọn sản phẩm đang có trong giỏ hàng của bạn.", "error")
        return redirect(url_for("gio_hang"), code=303)
    session["chon_dat_hang"] = {"nguon": "gio_hang", "ids": sorted(set(form.san_pham_id.data))}
    session["chon_gio_hang"] = session["chon_dat_hang"]["ids"]
    return redirect(url_for("dat_hang"), code=303)


def _bo_ky_dat_hang():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="dat-hang-v1")


@app.route("/dat-hang", methods=["GET", "POST"])
def dat_hang():
    users_id = session.get("users_id")
    if not users_id:
        return redirect(url_for("dangnhap", next="dat_hang"), code=303)
    form = DatHangForm()
    phi = app.config["PHI_VAN_CHUYEN"]
    if request.method == "POST":
        hop_le = form.validate_on_submit()
        _kiem_tra_csrf(form)
        if hop_le:
            try:
                xac_nhan = _bo_ky_dat_hang().loads(form.xac_nhan.data, max_age=1800)
                if not isinstance(xac_nhan, dict):
                    raise LoiMuaHang("Phiên đặt hàng không hợp lệ.")
                don_hang_id = tao_don_hang(users_id, form.data, xac_nhan, phi)
            except (BadSignature, SignatureExpired):
                flash("Phiên đặt hàng đã hết hạn hoặc không hợp lệ. Vui lòng kiểm tra lại đơn.", "error")
                return redirect(url_for("dat_hang"), code=303)
            except LoiMuaHang as error:
                flash(str(error), "error")
            except pymysql.MySQLError:
                app.logger.exception("Lỗi lưu đơn hàng.")
                abort(503, description="Không thể hoàn tất đặt hàng. Vui lòng thử lại sau.")
            else:
                session.pop("chon_dat_hang", None)
                flash("Đặt hàng thành công! Cửa hàng sẽ xử lý đơn của bạn.", "success")
                return redirect(url_for("chi_tiet_don_mua", don_hang_id=don_hang_id), code=303)

    lua_chon = session.get("chon_dat_hang", {"nguon": "gio_hang"})
    try:
        du_lieu = lay_du_lieu_dat_hang(users_id, lua_chon, phi)
        if request.method == "GET":
            nguoi_nhan = lay_thong_tin_nhan_hang(users_id)
            form.ten_nguoi_nhan.data = nguoi_nhan.get("ho_ten", session.get("ho_ten", ""))
            form.so_dien_thoai.data = nguoi_nhan.get("so_dien_thoai", "")
    except LoiMuaHang as error:
        flash(str(error), "error")
        if lua_chon.get("nguon") == "mua_ngay":
            return redirect(url_for("chi_tiet_san_pham", san_pham_id=lua_chon["san_pham_id"]))
        return redirect(url_for("gio_hang"))
    except pymysql.MySQLError:
        app.logger.exception("Lỗi tải trang đặt hàng.")
        abort(503, description="Không thể tải trang đặt hàng. Vui lòng thử lại sau.")

    # Giá được ký để khách xác nhận đúng số tiền đã xem; backend vẫn đọc lại DB khi lưu.
    form.xac_nhan.data = _bo_ky_dat_hang().dumps({
        "users_id": users_id, "ma_don_hang": "DH" + token_hex(12),
        "nguon": du_lieu["nguon"], "phi_van_chuyen": str(du_lieu["phi_van_chuyen"]),
        "san_pham": [{"id": sp["san_pham_id"], "so_luong": sp["so_luong"], "gia": str(sp["gia_ban"])}
                     for sp in du_lieu["san_pham"]],
    })
    return render_template("dat_hang.html", form=form, dat_hang=du_lieu)


@app.route("/don-mua")
def don_mua():
    if not session.get("users_id"):
        return redirect(url_for("dangnhap", next="don_mua"))
    try:
        danh_sach = lay_don_mua(session["users_id"])
    except pymysql.MySQLError:
        app.logger.exception("Lỗi đọc đơn mua.")
        abort(503, description="Không thể tải đơn mua. Vui lòng thử lại sau.")
    return render_template("don_mua.html", danh_sach_don=danh_sach)


@app.route("/don-mua/<int:don_hang_id>")
def chi_tiet_don_mua(don_hang_id):
    if not session.get("users_id"):
        return redirect(url_for("dangnhap", next="don_mua"))
    try:
        don = lay_chi_tiet_don_mua(session["users_id"], don_hang_id)
    except pymysql.MySQLError:
        app.logger.exception("Lỗi đọc chi tiết đơn mua.")
        abort(503, description="Không thể tải đơn mua. Vui lòng thử lại sau.")
    if don is None:
        abort(404)
    return render_template("chi_tiet_don_hang.html", don_hang=don)


if __name__ == "__main__":
    app.run(debug=True)
