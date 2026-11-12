"""Kiểm tra tệp và tải ảnh từ máy chủ Flask lên Cloudinary."""
from contextlib import closing, contextmanager
import logging
import re
from uuid import uuid4

from db import get_db_connection
from quan_tri import LoiQuanTri
from quan_tri_form import url_anh_hop_le


SO_ANH_MOI_TOI_DA = 8
GIOI_HAN_MOI_ANH = 5 * 1024 * 1024
GIOI_HAN_TONG_ANH = 20 * 1024 * 1024
GIOI_HAN_FORM_ANH = GIOI_HAN_TONG_ANH + 1024 * 1024
DINH_DANG_ANH = ("JPEG", "PNG", "GIF", "WEBP")
_logger = logging.getLogger(__name__)


def _kiem_tra_tep_anh(ds_tep):
    """Kiểm tra cả nội dung và kích thước trước khi tải bất kỳ ảnh nào."""
    try:
        from PIL import Image
    except ImportError:
        raise LoiQuanTri("Thiếu Pillow. Hãy cài thư viện tải ảnh theo hướng dẫn.", 503) from None

    tong = 0
    for i, tep in enumerate(ds_tep, 1):
        tep.stream.seek(0, 2)
        kich_thuoc = tep.stream.tell()
        tep.stream.seek(0)
        if not 0 < kich_thuoc <= GIOI_HAN_MOI_ANH:
            raise LoiQuanTri(f"Ảnh số {i} phải có dữ liệu và không vượt 5 MB.", 422)
        tong += kich_thuoc
    if tong > GIOI_HAN_TONG_ANH:
        raise LoiQuanTri("Tổng kích thước ảnh mới không được vượt 20 MB.", 422)

    for i, tep in enumerate(ds_tep, 1):
        try:
            with Image.open(tep.stream, formats=DINH_DANG_ANH) as anh:
                rong, cao = anh.size
                if rong > 8192 or cao > 8192 or rong * cao > 20_000_000:
                    raise LoiQuanTri(f"Ảnh số {i} quá lớn. Tối đa 20 megapixel và 8192 px mỗi chiều.", 422)
                anh.verify()
            tep.stream.seek(0)
            with Image.open(tep.stream, formats=DINH_DANG_ANH) as anh:
                anh.load()
        except LoiQuanTri:
            raise
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
            raise LoiQuanTri(f"Ảnh số {i} không đọc được. Chỉ dùng tệp JPG, PNG, WEBP hoặc GIF hợp lệ.", 422) from None
        finally:
            tep.stream.seek(0)


def _lay_uploader():
    # Import sau khi db.py đã nạp .env ở thư mục gốc dự án.
    try:
        import cloudinary
        from cloudinary import uploader

        cfg = cloudinary.config(secure=True)
    except ImportError:
        raise LoiQuanTri("Thiếu thư viện Cloudinary. Hãy cài theo hướng dẫn tải ảnh.", 503) from None
    except ValueError:
        raise LoiQuanTri("CLOUDINARY_URL không đúng định dạng. Hãy kiểm tra tệp .env.", 503) from None
    if not all((cfg.cloud_name, cfg.api_key, cfg.api_secret)):
        raise LoiQuanTri("Chưa cấu hình CLOUDINARY_URL trong .env ở thư mục gốc dự án.", 503)
    return uploader


def _anh_da_co_trong_database(url, public_id):
    """Kiểm tra trước khi dọn ảnh nếu kết quả ghi database chưa rõ."""
    with closing(get_db_connection()) as conn, conn.cursor() as cursor:
        cursor.execute(
            """SELECT 1 FROM hinh_anh_san_pham WHERE url_anh = %s OR public_id = %s
               UNION ALL SELECT 1 FROM thuong_hieu WHERE hinh_anh = %s
               UNION ALL SELECT 1 FROM danh_muc WHERE hinh_anh = %s LIMIT 1""",
            (url, public_id, url, url),
        )
        return cursor.fetchone() is not None


def _don_anh_moi(uploader, anh_moi, kiem_tra_database):
    # Chỉ dọn các ID mới do chính yêu cầu hiện tại tạo. Giữ ảnh nếu chưa biết DB đã lưu hay chưa.
    for public_id, url in anh_moi.items():
        try:
            if kiem_tra_database and _anh_da_co_trong_database(url, public_id):
                continue
            ket_qua = uploader.destroy(public_id, resource_type="image", type="upload", timeout=8)
            if ket_qua.get("result") not in ("ok", "not found"):
                _logger.warning("Chưa dọn được ảnh tải tạm %s", public_id)
        except Exception:
            _logger.warning("Chưa dọn được ảnh tải tạm %s", public_id)


@contextmanager
def anh_tu_bieu_mau(ma_module, ds_tep, urls_cu, anh_dai_dien_moi=""):
    """Trả về danh sách URL và public_id để lưu cùng bản ghi quản trị."""
    nhieu_anh = ma_module == "san-pham"
    gioi_han = SO_ANH_MOI_TOI_DA if nhieu_anh else 1
    if len(ds_tep) > gioi_han:
        raise LoiQuanTri(f"Mỗi lần lưu chỉ được chọn tối đa {gioi_han} ảnh mới.", 422)

    vi_tri = None
    if nhieu_anh and anh_dai_dien_moi:
        if not re.fullmatch(r"[0-7]", anh_dai_dien_moi) or int(anh_dai_dien_moi) >= len(ds_tep):
            raise LoiQuanTri("Ảnh đại diện đã thay đổi. Vui lòng chọn lại ảnh.", 422)
        vi_tri = int(anh_dai_dien_moi)
    if not ds_tep:
        yield list(urls_cu), {}
        return

    _kiem_tra_tep_anh(ds_tep)
    uploader = _lay_uploader()
    anh_moi = {}
    try:
        for i, tep in enumerate(ds_tep, 1):
            public_id = f"kltn/{ma_module}/{uuid4().hex}"
            anh_moi[public_id] = None  # Có thể Cloudinary đã nhận ảnh dù kết nối bị ngắt.
            ket_qua = uploader.upload(
                tep.stream, resource_type="image", type="upload", public_id=public_id,
                overwrite=False, timeout=30,
            )
            url = ket_qua.get("secure_url")
            if (ket_qua.get("public_id") != public_id or not isinstance(url, str)
                    or not url.startswith("https://") or not url_anh_hop_le(url)):
                raise ValueError("Cloudinary trả thông tin ảnh không hợp lệ.")
            anh_moi[public_id] = url
    except Exception as loi:
        print("Cloudinary:", type(loi).__name__,
              "HTTP:", getattr(loi, "http_code", None), flush=True)
        _don_anh_moi(uploader, anh_moi, kiem_tra_database=False)
        raise LoiQuanTri(f"Chưa tải được ảnh số {i} lên Cloudinary. Kiểm tra kết nối và cấu hình rồi thử lại.", 503) from None

    urls_moi = list(anh_moi.values())
    urls = list(urls_cu) + urls_moi if nhieu_anh else urls_moi
    if vi_tri is not None:
        urls.remove(urls_moi[vi_tri])
        urls.insert(0, urls_moi[vi_tri])
    try:
        yield urls, {url: public_id for public_id, url in anh_moi.items()}
    except Exception:
        _don_anh_moi(uploader, anh_moi, kiem_tra_database=True)
        raise
