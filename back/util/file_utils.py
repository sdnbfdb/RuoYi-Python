import os
import uuid
import shutil
from datetime import datetime

def ensure_directory_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path

def generate_unique_filename(original_filename):
    ext = os.path.splitext(original_filename)[1]
    return f"{uuid.uuid4().hex}{ext}"

def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def get_file_size_display(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def save_file(file, save_dir):
    ensure_directory_exists(save_dir)
    
    original_filename = file.filename
    safe_filename = sanitize_filename(original_filename)
    unique_filename = generate_unique_filename(safe_filename)
    save_path = os.path.join(save_dir, unique_filename)
    
    file.save(save_path)
    
    file_size = os.path.getsize(save_path)
    
    return {
        'filename': original_filename,
        'saved_name': unique_filename,
        'path': save_path,
        'size': file_size,
        'size_display': get_file_size_display(file_size)
    }

def read_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file_content(file_path, content):
    ensure_directory_exists(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def append_file_content(file_path, content):
    ensure_directory_exists(os.path.dirname(file_path))
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(content)

def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

def list_files_in_directory(dir_path):
    if not os.path.exists(dir_path):
        return []
    
    files = []
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        if os.path.isfile(file_path):
            files.append({
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'size_display': get_file_size_display(os.path.getsize(file_path)),
                'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return files

def copy_file(source_path, dest_path):
    ensure_directory_exists(os.path.dirname(dest_path))
    shutil.copy2(source_path, dest_path)
    return dest_path

def move_file(source_path, dest_path):
    ensure_directory_exists(os.path.dirname(dest_path))
    shutil.move(source_path, dest_path)
    return dest_path

def get_file_extension(filename):
    return os.path.splitext(filename)[1].lower()

def get_file_type_by_extension(filename):
    ext = get_file_extension(filename)
    
    doc_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md', '.rtf']
    image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']
    video_exts = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm']
    audio_exts = ['.mp3', '.wav', '.ogg', '.flac', '.aac']
    archive_exts = ['.zip', '.rar', '.7z', '.tar', '.gz']
    
    if ext in doc_exts:
        return 'doc'
    elif ext in image_exts:
        return 'image'
    elif ext in video_exts:
        return 'video'
    elif ext in audio_exts:
        return 'audio'
    elif ext in archive_exts:
        return 'archive'
    else:
        return 'other'

def generate_file_id():
    return str(uuid.uuid4().int)[:8]

def get_current_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def is_image_file(filename):
    ext = get_file_extension(filename)
    image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']
    return ext in image_exts

def get_image_url(filename, base_url='http://localhost:5000'):
    return f"{base_url}/image/{filename}"

def read_image_file(file_path):
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'rb') as f:
        return f.read()

def get_image_info(file_path):
    if not os.path.exists(file_path):
        return None
    
    try:
        import struct
        
        file_size = os.path.getsize(file_path)
        ext = get_file_extension(file_path)
        
        width = 0
        height = 0
        
        with open(file_path, 'rb') as f:
            header = f.read(32)
            
            if ext in ['.jpg', '.jpeg']:
                if header[6:10] == b'JFIF':
                    offset = 2
                    while offset + 7 < len(header):
                        if header[offset] == 0xFF and header[offset + 1] == 0xC0:
                            height = (header[offset + 5] << 8) | header[offset + 6]
                            width = (header[offset + 7] << 8) | header[offset + 8]
                            break
                        offset += 1
                        
            elif ext == '.png':
                if header[:8] == b'\x89PNG\r\n\x1a\n':
                    width = struct.unpack('>I', header[16:20])[0]
                    height = struct.unpack('>I', header[20:24])[0]
                    
            elif ext == '.gif':
                if header[:6] in [b'GIF87a', b'GIF89a']:
                    width = struct.unpack('<H', header[6:8])[0]
                    height = struct.unpack('<H', header[8:10])[0]
        
        return {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'extension': ext,
            'size': file_size,
            'size_display': get_file_size_display(file_size),
            'width': width,
            'height': height
        }
    except Exception:
        return {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'extension': ext,
            'size': file_size,
            'size_display': get_file_size_display(file_size),
            'width': 0,
            'height': 0
        }

def save_base64_image(base64_data, save_dir):
    import base64
    
    if base64_data.startswith('data:image/'):
        img_data = base64_data.split(',')[1]
        img_format = base64_data.split(';')[0].split('/')[1]
        img_bytes = base64.b64decode(img_data)
        
        ensure_directory_exists(save_dir)
        
        filename = f"{uuid.uuid4().hex}.{img_format}"
        save_path = os.path.join(save_dir, filename)
        
        with open(save_path, 'wb') as f:
            f.write(img_bytes)
        
        file_size = os.path.getsize(save_path)
        
        return {
            'filename': filename,
            'path': save_path,
            'size': file_size,
            'size_display': get_file_size_display(file_size),
            'format': img_format
        }
    else:
        return None
