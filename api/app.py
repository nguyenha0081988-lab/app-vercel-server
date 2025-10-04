# File: api/app.py (Đã làm sạch và tối ưu hóa)

from flask import Flask, request, jsonify
import cloudinary.uploader
import cloudinary.api
import os

# --- Khởi tạo ứng dụng ---
app = Flask(__name__)

# Đọc biến môi trường CLOUDINARY_URL (Đã loại bỏ khoảng trắng ẩn)
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL') 
# LƯU Ý: Nếu bạn có biến CLOUDINARY_CLOUD_NAME riêng, nó sẽ được đọc ở đây
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME') 

# --- Cấu hình Cloudinary ---
def setup_cloudinary():
    """Thiết lập cấu hình Cloudinary, ưu tiên CLOUDINARY_URL."""
    if CLOUDINARY_URL:
        # Sử dụng cú pháp URL chuẩn
        cloudinary.config(cloudinary_url=CLOUDINARY_URL)
        return True
    elif CLOUDINARY_CLOUD_NAME:
        # Phương pháp dự phòng 3 biến (Nếu bạn đã thiết lập chúng)
        cloudinary.config(
          cloud_name = CLOUDINARY_CLOUD_NAME,
          api_key = os.environ.get('CLOUDINARY_API_KEY'),
          api_secret = os.environ.get('CLOUDINARY_API_SECRET')
        )
        return True
    return False

# Cấu hình ngay khi ứng dụng khởi động
try:
    IS_CONFIGURED = setup_cloudinary()
except Exception as e:
    # Nếu có lỗi, đặt cấu hình là False
    print(f"Lỗi khởi tạo Cloudinary: {e}")
    IS_CONFIGURED = False

# Kiểm tra sức khỏe Server: Kiểm tra xem Cloudinary đã cấu hình chưa
def is_cloudinary_configured():
    """Kiểm tra xem cấu hình Cloudinary có sẵn sàng cho các lệnh API không."""
    # Kiểm tra biến đã được thiết lập thành công
    return IS_CONFIGURED

# 1. API LIST: Liệt kê tất cả file
@app.route('/list', methods=['GET'])
def list_files():
    """Lấy danh sách file và URL của chúng từ Cloudinary."""
    if not is_cloudinary_configured():
        # Trả về mã lỗi 500 nếu cấu hình thiếu
        return jsonify({'error': 'Lỗi: Khóa Cloudinary chưa được thiết lập chính xác trên Vercel.'}), 500

    # ... (Logic API LIST giữ nguyên, vì nó đã đúng) ...
    try:
        all_files = []
        
        def get_resources(resource_type):
            result = cloudinary.api.resources(
                type="upload",
                resource_type=resource_type,
                max_results=200
            )
            for resource in result.get('resources', []):
                file_name_with_ext = resource.get('public_id') + os.path.splitext(resource.get('url'))[1]
                all_files.append({
                    'name': file_name_with_ext,
                    'size': resource.get('bytes'),
                    'url': resource.get('url')
                })

        get_resources("raw")
        get_resources("image")

        return jsonify(all_files), 200

    except Exception as e:
        return jsonify({'error': f'Lỗi Cloudinary API: {str(e)}. Vui lòng kiểm tra lại CLOUDINARY_URL.'}), 500

# 2. API UPLOAD: Tải file lên
@app.route('/upload', methods=['POST'])
def upload_file():
    """Nhận file từ client và tải lên Cloudinary, ghi đè nếu trùng tên."""
    if not is_cloudinary_configured():
        return jsonify({'error': 'Lỗi: Server API chưa được cấu hình.'}), 500
        
    if 'file' not in request.files:
        return jsonify({'error': 'Không tìm thấy file trong yêu cầu.'}), 400
    
    # ... (Logic API UPLOAD giữ nguyên) ...
    file = request.files['file']
    filename_base, file_ext = os.path.splitext(file.filename)

    try:
        resource_type = "image" if file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif'] else "raw"

        cloudinary.uploader.upload(
            file,
            resource_type=resource_type,
            public_id=filename_base,
            overwrite=True
        )
        
        return jsonify({
            'message': f'File {file.filename} đã tải lên thành công!'
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Lỗi upload lên Cloudinary: {str(e)}'}), 500

# Endpoint mặc định cho Vercel (Kiểm tra sức khỏe Server)
@app.route('/')
def home():
    if not is_cloudinary_configured():
        return "Lỗi: Khóa Cloudinary chưa được thiết lập trong Biến Môi trường Vercel!", 500
    return "Server API Cloudinary đang hoạt động.", 200

if __name__ == '__main__':
    app.run(port=5000)
