from flask import jsonify, request
import os
import uuid
from datetime import datetime

IMAGE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'image')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_image():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({
            'success': False,
            'message': '未授权访问，请先登录'
        }), 401
    
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': '没有上传文件'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': '文件名不能为空'
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'message': '不支持的文件格式，仅支持: png, jpg, jpeg, gif, webp'
        }), 400
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    
    filepath = os.path.join(IMAGE_DIR, filename)
    file.save(filepath)
    
    file_size = os.path.getsize(filepath)
    
    image_url = f'/image/{filename}'
    
    return jsonify({
        'success': True,
        'message': '图片上传成功',
        'data': {
            'filename': filename,
            'url': image_url,
            'size': file_size
        }
    })

def serve_image(filename):
    from flask import send_from_directory
    
    if not filename:
        return jsonify({
            'success': False,
            'message': '文件名不能为空'
        }), 400
    
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(IMAGE_DIR, safe_filename)
    
    if not os.path.exists(filepath):
        return jsonify({
            'success': False,
            'message': '文件不存在'
        }), 404
    
    return send_from_directory(IMAGE_DIR, safe_filename)
