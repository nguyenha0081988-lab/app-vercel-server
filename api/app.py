# File: api/app.py (Đã thêm chức năng Đổi tên)

from flask import Flask, request, jsonify
import cloudinary.uploader
import cloudinary.api
import os
import urllib.parse # Thư viện cần thiết để giải mã URL

app = Flask(__name__)

# Đọc biến môi trường CLOUDINARY_URL
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL') 

# --- Cấu hình Cloudinary ---
try:
    if CLOUDINARY_URL:
        cloudinary.config(cloudinary_url=CLOUDINARY_URL, secure=True)
    
    IS_CONFIGURED = bool(cloudinary.config().cloud_name)
    
except Exception as e:
    print(f"Lỗi khởi tạo Cloudinary: {e}")
    IS_CONFIGURED = False

def is_cloudinary_configured():
    return IS_CONFIGURED

# 1. API LIST: Liệt kê tất cả file (Đã lọc bỏ file mẫu)
@app.route('/list', methods=['GET'])
def list_files():
    if not is_cloudinary_configured():
        return jsonify({'error': 'Lỗi: Khóa Cloudinary chưa được thiết lập chính xác.'}), 500

    all_files = []
    
    def get_resources(resource_type):
        try:
            result = cloudinary.api.resources(
                type="upload",
                resource_type=resource_type,
                max_results=200
            )
            for resource in result.get('resources', []):
                file_name_with_ext = resource.get('public_id') + os.path.splitext(resource.get('url'))[1]
                
                if file_name_with_ext.startswith('samples/'):
                    continue
                
                all_files.append({
                    'name': file_name_with_ext,
                    'size': resource.get('bytes'),
                    'url': resource.get('url')
                })
        except Exception as e:
            print(f"Lỗi khi lấy tài nguyên {resource_type}: {e}")
            pass

    get_resources("raw")
    get_resources("image")

    return jsonify(all_files), 200

# 2. API UPLOAD: Tải file lên 
@app.route('/upload', methods=['POST'])
def upload_file():
    if not is_cloudinary_configured():
        return jsonify({'error': 'Lỗi: Server API chưa được cấu hình.'}), 500
        
    if 'file' not in request.files:
        return jsonify({'error': 'Không tìm thấy file trong yêu cầu.'}), 400
    
    file = request.files['file']
    filename_base, file_ext = os.path.splitext(file.filename)

    try:
        resource_type = "image" if file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else "raw"

        cloudinary.uploader.upload(
            file,
            resource_type=resource_type,
            public_id=filename_base,
            overwrite=True
        )
        
        return jsonify({'message': f'File {file.filename} đã tải lên thành công!'}), 201
    
    except Exception as e:
        return jsonify({'error': f'Lỗi upload lên Cloudinary: {str(e)}'}), 500

# 3. API DELETE: Xóa file khỏi Cloudinary
@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    if not is_cloudinary_configured():
        return jsonify({'error': 'Lỗi: Server API chưa được cấu hình.'}), 500
    
    # GIẢI MÃ URL TRƯỚC KHI XỬ LÝ
    decoded_filename = urllib.parse.unquote(filename) 
    public_id, file_ext = os.path.splitext(decoded_filename)
    
    is_deleted = False
    resource_types_to_try = ["image", "raw"]
    
    for r_type in resource_types_to_try:
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=r_type
            )
            
            if result.get('result') == 'ok':
                is_deleted = True
                break 
                
        except Exception as e:
            print(f"Lỗi khi thử xóa loại {r_type}: {e}")
            pass 

    if is_deleted:
        return jsonify({'message': f'File {decoded_filename} đã xóa thành công.'}), 200
    else:
        return jsonify({'error': f'Thất bại: Không thể xóa file {decoded_filename}. Khóa API hợp lệ nhưng file có thể không tồn tại.'}), 500

# 4. API RENAME: Đổi tên file (CHỨC NĂNG MỚI)
@app.route('/rename', methods=['POST'])
def rename_file():
    if not is_cloudinary_configured():
        return jsonify({'error': 'Lỗi: Server API chưa được cấu hình.'}), 500

    old_filename_encoded = request.form.get('old_filename')
    new_filename_base = request.form.get('new_filename_base') 
    file_ext = request.form.get('file_ext') 

    if not old_filename_encoded or not new_filename_base or not file_ext:
        return jsonify({'error': 'Tham số rename bị thiếu.'}), 400

    old_filename = urllib.parse.unquote(old_filename_encoded)
    old_public_id, _ = os.path.splitext(old_filename)
    new_public_id = new_filename_base

    resource_type = "image" if file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else "raw"

    try:
        # Bước 1: Đổi tên file (Sử dụng hàm rename của Cloudinary)
        upload_result = cloudinary.uploader.rename(
            old_public_id,
            new_public_id, 
            resource_type=resource_type,
            overwrite=True
        )

        return jsonify({
            'message': f'Đã đổi tên thành công từ {old_public_id} thành {new_public_id}{file_ext}',
            'new_filename': new_public_id + file_ext,
            'new_url': upload_result.get('secure_url', upload_result.get('url'))
        }), 200

    except Exception as e:
        return jsonify({'error': f'Lỗi đổi tên: {str(e)}'}), 500


# Endpoint mặc định
@app.route('/')
def home():
    if not is_cloudinary_configured():
        return "Lỗi: Khóa Cloudinary chưa được thiết lập trong Biến Môi trường Vercel!", 500
    return "Server API Cloudinary đang hoạt động TỐT.", 200

if __name__ == '__main__':
    app.run(port=5000)
