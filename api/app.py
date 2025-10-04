# File: api/app.py (Chỉ thay thế phần đầu)

from flask import Flask, request, jsonify
import cloudinary.uploader
import cloudinary.api
import os 
from io import BytesIO

app = Flask(__name__)

# ====================================================================
# SỬA LỖI CUỐI CÙNG: Ưu tiên dùng Biến Môi trường CLOUDINARY_URL
# ====================================================================
# Đọc biến môi trường CLOUDINARY_URL (cú pháp ưa thích của thư viện)
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL') 
# ====================================================================

# Cấu hình Cloudinary
try:
    if CLOUDINARY_URL:
        # Nếu CLOUDINARY_URL tồn tại, sử dụng nó để cấu hình
        cloudinary.config(cloudinary_url=CLOUDINARY_URL)
        print("Sử dụng CLOUDINARY_URL để cấu hình.")
    else:
        # Nếu không, cố gắng dùng 3 biến riêng lẻ (cho môi trường DEV)
        cloudinary.config( 
          cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'), 
          api_key = os.environ.get('CLOUDINARY_API_KEY'), 
          api_secret = os.environ.get('CLOUDINARY_API_SECRET')
        )

except Exception as e:
    print(f"Lỗi cấu hình Cloudinary: {e}") 
    pass 

# ... (Phần còn lại của code Server API giữ nguyên) ...

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
