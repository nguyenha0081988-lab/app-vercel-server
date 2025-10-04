# File: api/app.py (Code đã được sửa lỗi)

from flask import Flask, request, jsonify
import cloudinary.uploader
import cloudinary.api
import os # Thư viện cần thiết để đọc biến môi trường
from io import BytesIO

app = Flask(__name__)

# ====================================================================
# SỬA LỖI: ĐỌC TỪ BIẾN MÔI TRƯỜNG CỦA VERCEL
# ====================================================================
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME') 
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')
# ====================================================================

# Cấu hình Cloudinary
try:
    # Lệnh này phải nằm trong try/except để tránh lỗi khi các biến chưa được thiết lập
    cloudinary.config( 
      cloud_name = CLOUDINARY_CLOUD_NAME, 
      api_key = CLOUDINARY_API_KEY, 
      api_secret = CLOUDINARY_API_SECRET
    )
except Exception as e:
    print(f"Lỗi cấu hình Cloudinary: {e}") 
    pass # Bỏ qua lỗi cấu hình để Vercel có thể chạy được endpoint '/'

# 1. API LIST: Liệt kê tất cả file
@app.route('/list', methods=['GET'])
def list_files():
    """Lấy danh sách file và URL của chúng từ Cloudinary."""
    try:
        all_files = []
        
        # Lấy danh sách RAW files (TXT, PDF, DOC, ZIP...)
        raw_result = cloudinary.api.resources(
            type="upload", 
            resource_type="raw", 
            max_results=200
        )
        for resource in raw_result.get('resources', []):
            file_name_with_ext = resource.get('public_id') + os.path.splitext(resource.get('url'))[1]
            all_files.append({
                'name': file_name_with_ext,
                'size': resource.get('bytes'),
                'url': resource.get('url') 
            })
            
        # Lấy danh sách IMAGE files (JPG, PNG, GIF...)
        image_result = cloudinary.api.resources(
            type="upload", 
            resource_type="image",
            max_results=200
        )
        for resource in image_result.get('resources', []):
             file_name_with_ext = resource.get('public_id') + os.path.splitext(resource.get('url'))[1]
             all_files.append({
                'name': file_name_with_ext,
                'size': resource.get('bytes'),
                'url': resource.get('url')
            })

        return jsonify(all_files), 200

    except Exception as e:
        # Trả về lỗi chi tiết nếu có vấn đề khi gọi API Cloudinary
        return jsonify({'error': f'Lỗi Cloudinary/API: {str(e)}'}), 500

# 2. API UPLOAD: Tải file lên (Ghi đè file trùng tên)
@app.route('/upload', methods=['POST'])
def upload_file():
    """Nhận file từ client và tải lên Cloudinary, ghi đè nếu trùng tên."""
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
    # Kiểm tra xem cấu hình có được tải không
    if not CLOUDINARY_CLOUD_NAME:
        return "Lỗi: Khóa Cloudinary chưa được thiết lập trong Biến Môi trường Vercel!", 500
    return "Server API Cloudinary đang hoạt động.", 200

if __name__ == '__main__':
    app.run(port=5000)
