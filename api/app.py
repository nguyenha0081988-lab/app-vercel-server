# File: api/app.py (Đã sửa lỗi logic triệt để)

from flask import Flask, request, jsonify
import cloudinary.uploader
import cloudinary.api
import os

app = Flask(__name__)

# Đọc biến môi trường CLOUDINARY_URL
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL') 

# Cấu hình Cloudinary
try:
    if CLOUDINARY_URL:
        cloudinary.config(cloudinary_url=CLOUDINARY_URL, secure=True)
    
    IS_CONFIGURED = bool(cloudinary.config().cloud_name)
    
except Exception as e:
    print(f"Lỗi khởi tạo Cloudinary: {e}")
    IS_CONFIGURED = False

# Kiểm tra sức khỏe Server: Kiểm tra xem Cloudinary đã cấu hình chưa
def is_cloudinary_configured():
    return IS_CONFIGURED

# 1. API LIST: Liệt kê tất cả file (SỬA LỖI LOGIC TỐI ƯU)
@app.route('/list', methods=['GET'])
def list_files():
    """Lấy danh sách file và URL của chúng từ Cloudinary."""
    if not is_cloudinary_configured():
        return jsonify({'error': 'Lỗi: Khóa Cloudinary chưa được thiết lập chính xác trên Vercel.'}), 500

    all_files = []
    
    # Hàm trợ giúp để lấy resources
    def get_resources(resource_type):
        try:
            # Thử gọi API. Nếu loại này trống, Cloudinary trả về mảng rỗng.
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
        except Exception as e:
            # Rất quan trọng: Báo lỗi nhưng KHÔNG CRASH SERVER
            print(f"Lỗi khi lấy tài nguyên {resource_type}: {e}")
            pass

    get_resources("raw")
    get_resources("image")

    return jsonify(all_files), 200

# 2. API UPLOAD: Tải file lên (Giữ nguyên)
@app.route('/upload', methods=['POST'])
def upload_file():
    if not is_cloudinary_configured():
        return jsonify({'error': 'Lỗi: Server API chưa được cấu hình.'}), 500
        
    if 'file' not in request.files:
        return jsonify({'error': 'Không tìm thấy file trong yêu cầu.'}), 400
    
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

# Endpoint mặc định (Giữ nguyên)
@app.route('/')
def home():
    if not is_cloudinary_configured():
        return "Lỗi: Khóa Cloudinary chưa được thiết lập trong Biến Môi trường Vercel!", 500
    return "Server API Cloudinary đang hoạt động TỐT.", 200

if __name__ == '__main__':
    app.run(port=5000)
