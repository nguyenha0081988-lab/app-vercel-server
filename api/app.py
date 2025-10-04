# File: api/app.py (Đã sửa lỗi cấu hình Vercel/Cloudinary)

from flask import Flask, request, jsonify
import cloudinary.uploader
import cloudinary.api
import os
from io import BytesIO

app = Flask(__name__)

# ====================================================================
# Đọc biến môi trường CLOUDINARY_URL
# Vercel cần biến này để xác thực
# ====================================================================
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL') 
# ====================================================================

# Cấu hình Cloudinary
try:
    if CLOUDINARY_URL:
        # Nếu CLOUDINARY_URL tồn tại, sử dụng nó để cấu hình (Phương pháp được khuyến nghị)
        cloudinary.config(cloudinary_url=CLOUDINARY_URL)
    else:
        # Nếu thiếu CLOUDINARY_URL, ứng dụng sẽ cố gắng đọc 3 biến riêng lẻ (Phương pháp dự phòng)
        cloudinary.config( 
          cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'), 
          api_key = os.environ.get('CLOUDINARY_API_KEY'), 
          api_secret = os.environ.get('CLOUDINARY_API_SECRET')
        )
except Exception as e:
    # Bắt lỗi cấu hình để ít nhất Server có thể khởi động (endpoint '/' hoạt động)
    print(f"Lỗi cấu hình Cloudinary: {e}") 
    pass 

# Kiểm tra sức khỏe Server: Kiểm tra xem Cloudinary đã cấu hình chưa
def is_cloudinary_configured():
    """Kiểm tra xem cấu hình Cloudinary có sẵn sàng cho các lệnh API không."""
    return bool(cloudinary.config().cloud_name)


# 1. API LIST: Liệt kê tất cả file
@app.route('/list', methods=['GET'])
def list_files():
    """Lấy danh sách file và URL của chúng từ Cloudinary."""
    if not is_cloudinary_configured():
         return jsonify({'error': 'Lỗi: Khóa Cloudinary chưa được thiết lập chính xác trên Vercel.'}), 500

    try:
        all_files = []
        
        # Hàm trợ giúp để lấy resources
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

        get_resources("raw")   # Lấy RAW files (TXT, PDF, DOC, ZIP...)
        get_resources("image") # Lấy IMAGE files (JPG, PNG, GIF...)

        return jsonify(all_files), 200

    except Exception as e:
        # Trả về lỗi chi tiết nếu có vấn đề khi gọi API Cloudinary
        return jsonify({'error': f'Lỗi Cloudinary API: {str(e)}. Kiểm tra lại CLOUDINARY_URL.'}), 500

# 2. API UPLOAD: Tải file lên (Ghi đè file trùng tên)
@app.route('/upload', methods=['POST'])
def upload_file():
    """Nhận file từ client và tải lên Cloudinary, ghi đè nếu trùng tên."""
    if not is_cloudinary_configured():
         return jsonify({'error': 'Lỗi: Server API chưa được cấu hình.'}), 500
         
    if 'file' not in request.files:
        return jsonify({'error': 'Không tìm thấy file trong yêu cầu.'}), 400
    
    file = request.files['file']
    filename_base, file_ext = os.path.splitext(file.filename)

    try:
        resource_type = "image" if file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif'] else "raw"

        upload_result = cloudinary.uploader.upload(
            file, 
            resource_type=resource_type,
            public_id=filename_base, 
            overwrite=True 
        )
        
        return jsonify({
            'message': f'File {file.filename} đã tải lên thành công!',
            'url': upload_result['url']
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
