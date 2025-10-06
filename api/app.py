import json
import os
import hashlib
from datetime import datetime
from functools import wraps

# Thư viện Flask
from flask import Flask, request, jsonify, abort
from werkzeug.utils import secure_filename
from flask_cors import CORS

# Thư viện ngoài
import requests
import cloudinary
import cloudinary.uploader
import cloudinary.utils

# ====================================================================
# BIẾN CẤU HÌNH VÀ KHỞI TẠO
# ====================================================================

# Lấy Biến môi trường CLOUDINARY_URL (Biến duy nhất được sử dụng)
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')

# Biến CLOUDINARY_CLOUD_NAME sẽ được trích xuất tự động từ URL
CLOUDINARY_CLOUD_NAME = None 

# Định nghĩa Public IDs và tên file tạm thời trên Server
USER_FILE_PUBLIC_ID = 'app_config/users'
LOG_FILE_PUBLIC_ID = 'app_config/activity_log'
USER_LOCAL_TEMP = 'users_temp.json'
LOG_LOCAL_TEMP = 'log_temp.txt'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp_uploads')

# --- KHỞI TẠO FLASK VÀ CẤU HÌNH ---
app = Flask(__name__)
CORS(app) 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Cấu hình Cloudinary (CHỈ DÙNG CLOUDINARY_URL)
if CLOUDINARY_URL:
    try:
        cloudinary.config(cloudinary_url=CLOUDINARY_URL)
        # Trích xuất CLOUD_NAME sau khi cấu hình
        CLOUDINARY_CLOUD_NAME = cloudinary.config().cloud_name
        print("Cloudinary cấu hình thành công bằng CLOUDINARY_URL.")
    except Exception as e:
        print(f"LỖI: Cấu hình Cloudinary bằng URL thất bại: {e}")
        # Đặt lại thành None để báo hiệu cấu hình thất bại
        CLOUDINARY_CLOUD_NAME = None 
else:
    print("CẢNH BÁO: Thiếu biến môi trường CLOUDINARY_URL. Các chức năng Cloudinary sẽ thất bại.")

# ====================================================================
# HÀM TIỆN ÍCH CHUNG VÀ XỬ LÝ DỮ LIỆU CLOUDINARY
# ====================================================================

def hash_password(password):
    """Mã hóa mật khẩu bằng SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def admin_required(f):
    """Decorator kiểm tra quyền admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def download_file_from_cloudinary(public_id, local_filename):
    """Tải file từ Cloudinary về Server tạm thời."""
    if not CLOUDINARY_CLOUD_NAME:
        raise Exception("Cloudinary chưa được cấu hình.")
        
    try:
        # Tải xuống bằng resource_type='raw' cho JSON/TXT
        url = cloudinary.utils.cloudinary_url(public_id, resource_type='raw', format=os.path.splitext(local_filename)[1].strip('.'))[0]
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return local_filename
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise FileNotFoundError(f"File {public_id} not found on Cloudinary.")
        raise
    except Exception as e:
        raise Exception(f"Lỗi tải file {public_id}: {e}")

def upload_file_to_cloudinary(local_filename, public_id):
    """Tải file từ Server tạm thời lên Cloudinary, ghi đè file cũ."""
    if not CLOUDINARY_CLOUD_NAME:
        raise Exception("Cloudinary chưa được cấu hình.")
        
    try:
        result = cloudinary.uploader.upload(
            local_filename,
            resource_type='raw',
            public_id=public_id,
            overwrite=True
        )
        return result
    except Exception as e:
        raise Exception(f"Lỗi tải file lên Cloudinary: {e}")

# --- USER DATA MANAGEMENT (CLOUDINARY) ---

def initialize_default_users():
    """Tạo user admin mặc định và tải lên Cloudinary."""
    default_user = {"admin": {"password": hash_password("123"), "role": "admin"}}
    try:
        with open(USER_LOCAL_TEMP, 'w', encoding='utf-8') as f:
            json.dump(default_user, f, indent=4)
        upload_file_to_cloudinary(USER_LOCAL_TEMP, USER_FILE_PUBLIC_ID)
        os.remove(USER_LOCAL_TEMP)
        return default_user
    except Exception:
        return {} 

def load_users_data():
    """Tải dữ liệu người dùng từ Cloudinary."""
    try:
        download_file_from_cloudinary(USER_FILE_PUBLIC_ID, USER_LOCAL_TEMP)
        with open(USER_LOCAL_TEMP, 'r', encoding='utf-8') as f:
            users = json.load(f)
        os.remove(USER_LOCAL_TEMP)
        return users
    except FileNotFoundError:
        return initialize_default_users() 
    except Exception:
        return initialize_default_users()

def save_users_data(users):
    """Lưu dữ liệu người dùng vào file users.json trên Cloudinary."""
    try:
        with open(USER_LOCAL_TEMP, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
        upload_file_to_cloudinary(USER_LOCAL_TEMP, USER_FILE_PUBLIC_ID)
        os.remove(USER_LOCAL_TEMP)
    except Exception as e:
        print(f"LỖI KHÔNG THỂ LƯU USER LÊN CLOUDINARY: {e}")

# --- LOG DATA MANAGEMENT (CLOUDINARY) ---

def read_logs_from_cloudinary():
    """Đọc toàn bộ lịch sử log từ Cloudinary."""
    try:
        download_file_from_cloudinary(LOG_FILE_PUBLIC_ID, LOG_LOCAL_TEMP)
        with open(LOG_LOCAL_TEMP, 'r', encoding='utf-8') as f:
            logs = f.readlines()
        os.remove(LOG_LOCAL_TEMP)
        return logs
    except FileNotFoundError:
        return []
    except Exception:
        return ["--- Lỗi đọc log từ Cloudinary ---"]


def log_action_server(username, action, details="", status="Thành công"):
    """Ghi log hoạt động vào Cloudinary Log File."""
    try:
        logs = read_logs_from_cloudinary()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_log_entry = f"[{timestamp}] - User:{username} - {action}: {details} ({status})\n"
        
        logs.append(new_log_entry)
        
        with open(LOG_LOCAL_TEMP, 'w', encoding='utf-8') as f:
            f.writelines(logs)

        upload_file_to_cloudinary(LOG_LOCAL_TEMP, LOG_FILE_PUBLIC_ID)
        os.remove(LOG_LOCAL_TEMP)
    except Exception as e:
        print(f"LỖI LỚN KHI GHI LOG LÊN CLOUDINARY: {e}")

# ====================================================================
# API ROUTES CHO FILE MEDIA
# ====================================================================

# 1. Tải lên file media
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    
    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    if uploaded_file:
        filename = secure_filename(uploaded_file.filename)
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        uploaded_file.save(local_path)
        
        try:
            result = cloudinary.uploader.upload(local_path, folder="client_files", public_id=os.path.splitext(filename)[0], overwrite=True)
            os.remove(local_path) 
            
            return jsonify({
                "message": "Upload successful",
                "filename": result['public_id'].split('/')[-1] + '.' + result['format'],
                "url": result['secure_url']
            }), 200
        except Exception as e:
            os.remove(local_path)
            return jsonify({"message": f"Cloudinary upload failed: {e}"}), 500
    
    return jsonify({"message": "Something went wrong"}), 500

# 2. Lấy danh sách file media
@app.route('/list', methods=['GET'])
def list_files():
    try:
        result = cloudinary.api.resources(type="upload", prefix="client_files/", max_results=500)
        
        files_list = []
        for resource in result['resources']:
            filename_with_ext = resource['public_id'].split('/')[-1] + '.' + resource['format']
            files_list.append({
                "name": filename_with_ext,
                "url": resource['secure_url'],
                "size": resource['bytes']
            })
            
        return jsonify(files_list), 200
    except Exception as e:
        return jsonify({"message": f"Error listing files: {e}"}), 500

# 3. Xóa file media
@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        base_name, ext = os.path.splitext(filename)
        public_id = "client_files/" + base_name
        
        result = cloudinary.uploader.destroy(public_id, resource_type="raw") 
        
        if result.get('result') == 'ok':
            return jsonify({"message": f"File {filename} deleted successfully"}), 200
        else:
            return jsonify({"message": f"File deletion failed: {result.get('result')}"}), 404
    except Exception as e:
        return jsonify({"message": f"Error deleting file: {e}"}), 500

# ====================================================================
# API ROUTES CHO USER VÀ LOG (DỮ LIỆU CẤU TRÚC)
# ====================================================================

# --- USER ROUTES ---

# 1. GET /users: Lấy danh sách người dùng
@app.route('/users', methods=['GET'])
@admin_required
def get_users():
    users_data = load_users_data()
    users_list = [{"username": u, "role": d.get("role", "user")} for u, d in users_data.items()]
    return jsonify(users_list), 200

# 2. POST /users/auth: Xác thực đăng nhập
@app.route('/users/auth', methods=['POST'])
def authenticate():
    data = request.get_json()
    username = data.get('username')
    password_hash = data.get('password_hash')
    
    users_data = load_users_data()
    
    if username in users_data and users_data[username]['password'] == password_hash:
        role = users_data[username].get('role', 'user')
        return jsonify({"success": True, "username": username, "role": role}), 200
    
    return jsonify({"success": False, "message": "Sai tên đăng nhập hoặc mật khẩu"}), 401

# 3. POST /users/add: Thêm người dùng mới
@app.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    data = request.get_json()
    username = data.get('username')
    password_hash = data.get('password_hash')
    role = data.get('role', 'user')
    
    users_data = load_users_data()
    
    if username in users_data:
        return jsonify({"success": False, "message": "Tên đăng nhập đã tồn tại"}), 409
    
    users_data[username] = {"password": password_hash, "role": role}
    save_users_data(users_data)
    
    return jsonify({"success": True, "message": "Người dùng đã được thêm"}), 201

# 4. DELETE /users/delete/<username>: Xóa người dùng
@app.route('/users/delete/<username>', methods=['DELETE'])
@admin_required
def delete_user(username):
    users_data = load_users_data()
    
    if username == "admin":
        return jsonify({"success": False, "message": "Không thể xóa tài khoản admin gốc"}), 403
    
    if username in users_data:
        del users_data[username]
        save_users_data(users_data)
        return jsonify({"success": True, "message": f"Người dùng {username} đã bị xóa"}), 200
    
    return jsonify({"success": False, "message": "Người dùng không tồn tại"}), 404

# --- LOG ROUTES ---

# 1. POST /log/record: Ghi log hoạt động
@app.route('/log/record', methods=['POST'])
def record_log():
    data = request.get_json()
    username = data.get('username')
    action = data.get('action')
    details = data.get('details', "")
    status = data.get('status', "Thành công")
    
    log_action_server(username, action, details, status)
    
    return jsonify({"success": True, "message": "Log đã được ghi"}), 200

# 2. GET /log/read: Đọc toàn bộ log
@app.route('/log/read', methods=['GET'])
@admin_required
def read_all_logs():
    logs = read_logs_from_cloudinary()
    return jsonify([log.strip() for log in logs]), 200


if __name__ == '__main__':
    # Khởi tạo CSDL người dùng lần đầu nếu chưa có
    load_users_data()
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
