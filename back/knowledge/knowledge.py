from flask import jsonify, request, send_from_directory
import os
import uuid
import json
import threading
from datetime import datetime
from util.file_utils import (
    ensure_directory_exists,
    generate_unique_filename,
    sanitize_filename,
    get_file_size_display,
    save_file as save_upload_file,
    write_file_content,
    read_file_content,
    list_files_in_directory,
    delete_file,
    get_file_type_by_extension,
    generate_file_id,
    get_current_timestamp
)

# 添加数据库导入
from sql.database import get_db_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, '..', 'uploads', 'knowledge')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
                      'txt', 'md', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3'}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

file_lock = threading.RLock()

def ensure_dirs():
    ensure_directory_exists(UPLOAD_DIR)

def get_type_label(type_code):
    type_map = {
        'doc': '文档',
        'video': '视频',
        'image': '图片',
        'other': '其他'
    }
    return type_map.get(type_code, '其他')

# ==================== 数据库操作函数 ====================

def save_knowledge_to_db(knowledge_item):
    """保存知识库数据到数据库"""
    db = get_db_connection()
    query = """
        INSERT INTO knowledge (id, title, type, tags, description, content, 
                              attachments, qa_records, created_by, created_at, updated_at, 
                              total_size, attachment_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            title = VALUES(title),
            type = VALUES(type),
            tags = VALUES(tags),
            description = VALUES(description),
            content = VALUES(content),
            attachments = VALUES(attachments),
            qa_records = VALUES(qa_records),
            updated_at = VALUES(updated_at),
            total_size = VALUES(total_size),
            attachment_count = VALUES(attachment_count)
    """
    params = (
        knowledge_item.get('id', ''),
        knowledge_item.get('title', ''),
        knowledge_item.get('type', 'other'),
        json.dumps(knowledge_item.get('tags', [])),
        knowledge_item.get('description', ''),
        knowledge_item.get('content', ''),
        json.dumps(knowledge_item.get('attachments', [])),
        json.dumps(knowledge_item.get('qa_records', [])),
        knowledge_item.get('created_by', ''),
        knowledge_item.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        knowledge_item.get('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        knowledge_item.get('total_size', 0),
        knowledge_item.get('attachment_count', 0)
    )
    db.execute_update(query, params)
    return True

def load_knowledge_data():
    """加载知识库数据（从数据库加载）"""
    return load_knowledge_from_db()

def load_knowledge_from_db():
    """从数据库加载知识库数据"""
    db = get_db_connection()
    result = db.execute_query("SELECT * FROM knowledge ORDER BY created_at DESC")
    
    data = []
    for row in result:
        created_at = row.get('created_at', '')
        updated_at = row.get('updated_at', '')
        
        if hasattr(created_at, 'strftime'):
            created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(updated_at, 'strftime'):
            updated_at = updated_at.strftime('%Y-%m-%d %H:%M:%S')
        
        item = {
            'id': row.get('id', ''),
            'title': row.get('title', ''),
            'type': row.get('type', 'other'),
            'tags': json.loads(row.get('tags', '[]')),
            'description': row.get('description', ''),
            'content': row.get('content', ''),
            'created_at': created_at,
            'updated_at': updated_at,
            'created_by': row.get('created_by', ''),
            'total_size': row.get('total_size', 0),
            'attachment_count': row.get('attachment_count', 0),
            'attachments': json.loads(row.get('attachments', '[]')),
            'qa_records': json.loads(row.get('qa_records', '[]'))
        }
        data.append(item)
    
    return data

def get_knowledge_by_id(knowledge_id):
    """根据ID获取知识库详情"""
    db = get_db_connection()
    query = "SELECT * FROM knowledge WHERE id = %s"
    result = db.execute_query(query, (knowledge_id,))
    
    if result:
        row = result[0]
        
        created_at = row.get('created_at', '')
        updated_at = row.get('updated_at', '')
        
        if hasattr(created_at, 'strftime'):
            created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(updated_at, 'strftime'):
            updated_at = updated_at.strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'id': row.get('id', ''),
            'title': row.get('title', ''),
            'type': row.get('type', 'other'),
            'tags': json.loads(row.get('tags', '[]')),
            'description': row.get('description', ''),
            'content': row.get('content', ''),
            'created_at': created_at,
            'updated_at': updated_at,
            'created_by': row.get('created_by', ''),
            'total_size': row.get('total_size', 0),
            'attachment_count': row.get('attachment_count', 0),
            'attachments': json.loads(row.get('attachments', '[]')),
            'qa_records': json.loads(row.get('qa_records', '[]'))
        }
    return None

def delete_knowledge_from_db(knowledge_id):
    """从数据库删除知识库"""
    db = get_db_connection()
    query = "DELETE FROM knowledge WHERE id = %s"
    affected_rows = db.execute_update(query, (knowledge_id,))
    return affected_rows > 0

# ==================== API 函数 ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_knowledge_list():
    filter_type = request.args.get('filter', 'all')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    
    data = load_knowledge_from_db()
    
    filtered_data = []
    for item in data:
        type_match = (filter_type == 'all') or (item.get('type') == filter_type)
        
        search_match = True
        if search:
            search_lower = search.lower()
            title_match = search_lower in item.get('title', '').lower()
            desc_match = search_lower in item.get('description', '').lower()
            tags_match = any(search_lower in tag.lower() for tag in item.get('tags', []))
            search_match = title_match or desc_match or tags_match
        
        if type_match and search_match:
            filtered_data.append(item)
    
    total = len(filtered_data)
    start = (page - 1) * size
    end = start + size
    paginated_data = filtered_data[start:end]
    
    for item in paginated_data:
        total_kb = item.get('total_size', 0) / 1024
        if total_kb >= 1024:
            item['size_display'] = f'{total_kb/1024:.2f} MB'
        elif total_kb > 0:
            item['size_display'] = f'{total_kb:.1f} KB'
        else:
            item['size_display'] = '~0 KB'
    
    return jsonify({
        'success': True,
        'data': {
            'list': paginated_data,
            'total': total,
            'page': page,
            'size': size,
            'pages': (total + size - 1) // size if total > 0 else 0
        }
    })

def get_knowledge_detail(knowledge_id):
    """获取知识库详情"""
    item = get_knowledge_by_id(knowledge_id)
    
    if not item:
        return jsonify({
            'success': False,
            'message': '资料不存在'
        }), 404
    
    total_kb = item.get('total_size', 0) / 1024
    if total_kb >= 1024:
        item['size_display'] = f'{total_kb/1024:.2f} MB'
    elif total_kb > 0:
        item['size_display'] = f'{total_kb:.1f} KB'
    else:
        item['size_display'] = '~0 KB'
    
    return jsonify({
        'success': True,
        'data': item
    })

def create_knowledge():
    """创建知识库资料"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    print(f'\n=== 创建知识库资料 ===')
    print(f'Token: {token[:20] if token else "None"}...')
    
    if not token:
        print('[ERROR] 错误: 未提供Token')
        return jsonify({
            'success': False,
            'message': '未授权访问，请先登录'
        }), 401
    
    data = request.form.to_dict() or request.get_json(silent=True) or {}
    
    print(f'表单数据: {list(data.keys())}')
    print(f'上传的文件: {list(request.files.keys())}')
    
    title = data.get('title', '').strip()
    knowledge_type = data.get('type', '').strip()
    description = data.get('description', '').strip()
    content = data.get('content', '').strip()
    
    print(f'标题: {title}')
    print(f'类型: {knowledge_type}')
    
    attachments = []
    
    if 'files' in request.files:
        files = request.files.getlist('files')
        print(f'文件数量: {len(files)}')
        
        for idx, file in enumerate(files):
            if file and file.filename:
                print(f'处理文件 {idx+1}: {file.filename}')
                
                if not allowed_file(file.filename):
                    print(f'  ⚠️ 文件格式不允许: {file.filename}')
                    continue
                
                file_content = file.read()
                if len(file_content) > MAX_FILE_SIZE:
                    print(f'  ⚠️ 文件太大: {len(file_content)} bytes')
                    continue
                
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                filename = f'{uuid.uuid4().hex}.{ext}'
                filepath = os.path.join(UPLOAD_DIR, filename)
                
                ensure_dirs()
                
                with open(filepath, 'wb') as f:
                    f.write(file_content)
                
                size_kb = len(file_content) / 1024
                size_display = f'{size_kb:.1f} KB' if size_kb < 1024 else f'{size_kb/1024:.2f} MB'
                
                attachments.append({
                    'id': uuid.uuid4().hex[:8],
                    'filename': file.filename,
                    'saved_name': filename,
                    'url': f'/uploads/knowledge/{filename}',
                    'size': len(file_content),
                    'size_display': size_display,
                    'type': ext
                })
                
                print(f'  [OK] 保存成功: {filename} ({size_display})')
    
    if not title and attachments:
        title = attachments[0]['filename'].rsplit('.', 1)[0]
        print(f'从文件名自动提取标题: {title}')
    
    if not knowledge_type and attachments:
        first_ext = attachments[0]['type']
        doc_exts = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md'}
        image_exts = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg'}
        video_exts = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv'}
        
        if first_ext in doc_exts:
            knowledge_type = 'doc'
        elif first_ext in image_exts:
            knowledge_type = 'image'
        elif first_ext in video_exts:
            knowledge_type = 'video'
        else:
            knowledge_type = 'other'
        
        print(f'从扩展名自动判断类型: {knowledge_type}')
    
    print(f'最终标题: {title}')
    print(f'最终类型: {knowledge_type}')
    print(f'附件数量: {len(attachments)}')
    
    if not title:
        print('[ERROR] 错误: 标题为空且无有效附件')
        return jsonify({
            'success': False,
            'message': '请上传文件或填写标题'
        }), 400
    
    if not knowledge_type:
        knowledge_type = 'other'
    
    new_id = str(uuid.uuid4().int)[:8]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 获取问答记录
    qa_records = data.get('qa_records', [])
    
    new_knowledge = {
        'id': new_id,
        'title': title,
        'type': knowledge_type,
        'tags': [],
        'description': description,
        'content': content,
        'attachments': attachments,
        'qa_records': qa_records,
        'created_by': token[:20] if len(token) > 20 else token,
        'created_at': now,
        'updated_at': now,
        'total_size': sum(att['size'] for att in attachments),
        'attachment_count': len(attachments)
    }
    
    # 保存到数据库
    save_knowledge_to_db(new_knowledge)
    
    print(f'[OK] 资料创建成功!')
    print(f'   附件数: {len(attachments)}')
    
    total_size_kb = sum(att['size'] for att in attachments) / 1024
    size_display = f'{total_size_kb:.1f} KB' if total_size_kb < 1024 else f'{total_size_kb/1024:.2f} MB'
    new_knowledge['size_display'] = size_display
    
    return jsonify({
        'success': True,
        'message': '资料创建成功',
        'data': new_knowledge
    })

def update_knowledge(knowledge_id):
    """更新知识库资料"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({
            'success': False,
            'message': '未授权访问，请先登录'
        }), 401
    
    # 从数据库获取现有数据
    target_item = get_knowledge_by_id(knowledge_id)
    
    if target_item is None:
        return jsonify({
            'success': False,
            'message': '资料不存在'
        }), 404
    
    form_data = request.form.to_dict() or request.get_json(silent=True) or {}
    
    title = form_data.get('title', target_item.get('title', '')).strip() or target_item.get('title', '')
    knowledge_type = form_data.get('type', target_item.get('type', '')).strip() or target_item.get('type', 'other')
    description = form_data.get('description', target_item.get('description', '')).strip()
    content = form_data.get('content', target_item.get('content', '')).strip()
    
    valid_types = ['doc', 'video', 'image', 'other']
    if knowledge_type not in valid_types:
        knowledge_type = target_item.get('type', 'other') or 'other'
    
    attachments = list(target_item.get('attachments', []))
    
    if 'files' in request.files:
        files = request.files.getlist('files')
        
        for file in files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    continue
                
                file_content = file.read()
                if len(file_content) > MAX_FILE_SIZE:
                    continue
                
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                filename = f'{uuid.uuid4().hex}.{ext}'
                filepath = os.path.join(UPLOAD_DIR, filename)
                
                ensure_dirs()
                
                with open(filepath, 'wb') as f:
                    f.write(file_content)
                
                size_kb = len(file_content) / 1024
                size_display = f'{size_kb:.1f} KB' if size_kb < 1024 else f'{size_kb/1024:.2f} MB'
                
                attachments.append({
                    'id': uuid.uuid4().hex[:8],
                    'filename': file.filename,
                    'saved_name': filename,
                    'url': f'/uploads/knowledge/{filename}',
                    'size': len(file_content),
                    'size_display': size_display,
                    'type': ext
                })
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    updated_item = {
        **target_item,
        'title': title,
        'type': knowledge_type,
        'description': description,
        'content': content,
        'attachments': attachments,
        'updated_at': now,
        'total_size': sum(att['size'] for att in attachments),
        'attachment_count': len(attachments)
    }
    
    # 更新数据库
    save_knowledge_to_db(updated_item)
    
    total_size_kb = sum(att['size'] for att in attachments) / 1024
    size_display = f'{total_size_kb:.1f} KB' if total_size_kb < 1024 else f'{total_size_kb/1024:.2f} MB'
    updated_item['size_display'] = size_display
    
    return jsonify({
        'success': True,
        'message': '资料更新成功',
        'data': updated_item
    })

def delete_knowledge(knowledge_id):
    """删除知识库资料"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({
            'success': False,
            'message': '未授权访问，请先登录'
        }), 401
    
    # 从数据库获取数据
    target_item = get_knowledge_by_id(knowledge_id)
    
    if target_item is None:
        return jsonify({
            'success': False,
            'message': '资料不存在'
        }), 404
    
    # 删除附件文件
    for attachment in target_item.get('attachments', []):
        try:
            saved_name = attachment.get('saved_name', '')
            if saved_name:
                filepath = os.path.join(UPLOAD_DIR, saved_name)
                if os.path.exists(filepath):
                    os.remove(filepath)
        except Exception as e:
            print(f'Delete file error: {e}')
    
    # 从数据库删除
    delete_knowledge_from_db(knowledge_id)
    
    return jsonify({
        'success': True,
        'message': '删除成功',
        'data': {
            'deleted_id': knowledge_id
        }
    })

def upload_attachment():
    """上传附件"""
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
    
    if not file or not file.filename:
        return jsonify({
            'success': False,
            'message': '文件名不能为空'
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'message': f'不支持的文件格式，支持: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
        }), 400
    
    file_content = file.read()
    
    if len(file_content) > MAX_FILE_SIZE:
        return jsonify({
            'success': False,
            'message': f'文件大小超过限制（最大{MAX_FILE_SIZE//(1024*1024)}MB）'
        }), 400
    
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    filename = f'{uuid.uuid4().hex}.{ext}'
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    ensure_dirs()
    
    with open(filepath, 'wb') as f:
        f.write(file_content)
    
    size_kb = len(file_content) / 1024
    size_display = f'{size_kb:.1f} KB' if size_kb < 1024 else f'{size_kb/1024:.2f} MB'
    
    attachment_info = {
        'id': uuid.uuid4().hex[:8],
        'filename': file.filename,
        'saved_name': filename,
        'url': f'/uploads/knowledge/{filename}',
        'size': len(file_content),
        'size_display': size_display,
        'type': ext
    }
    
    return jsonify({
        'success': True,
        'message': '附件上传成功',
        'data': attachment_info
    })

def serve_attachment(filename):
    """提供附件下载"""
    if not filename:
        return jsonify({
            'success': False,
            'message': '文件名不能为空'
        }), 400
    
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(UPLOAD_DIR, safe_filename)
    
    if not os.path.exists(filepath):
        return jsonify({
            'success': False,
            'message': '文件不存在'
        }), 404
    
    return send_from_directory(UPLOAD_DIR, safe_filename)

def get_statistics():
    """获取统计信息"""
    data = load_knowledge_from_db()
    
    stats = {
        'total': len(data),
        'by_type': {},
        'by_tag': {},
        'total_attachments': 0,
        'total_size': 0
    }
    
    for item in data:
        type_name = item.get('type', 'other')
        stats['by_type'][type_name] = stats['by_type'].get(type_name, 0) + 1
        
        for tag in item.get('tags', []):
            stats['by_tag'][tag] = stats['by_tag'].get(tag, 0) + 1
        
        att_count = item.get('attachment_count', 0)
        att_size = item.get('total_size', 0)
        stats['total_attachments'] += att_count
        stats['total_size'] += att_size
    
    stats['total_size_display'] = f'{stats["total_size"]/1024:.1f} KB' if stats['total_size'] < 1024*1024 else f'{stats["total_size"]/(1024*1024):.2f} MB'
    
    return jsonify({
        'success': True,
        'data': stats
    })

def add_qa_record(knowledge_id):
    """为知识库添加问答记录"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({
            'success': False,
            'message': '未授权访问，请先登录'
        }), 401
    
    # 从数据库获取数据
    target_item = get_knowledge_by_id(knowledge_id)
    
    if target_item is None:
        return jsonify({
            'success': False,
            'message': '资料不存在'
        }), 404
    
    # 获取新的问答记录
    qa_data = request.get_json(silent=True) or {}
    question = qa_data.get('question', '').strip()
    answer = qa_data.get('answer', '').strip()
    
    if not question:
        return jsonify({
            'success': False,
            'message': '问题不能为空'
        }), 400
    
    # 创建新的问答记录
    qa_record = {
        'id': str(uuid.uuid4().int)[:8],
        'question': question,
        'answer': answer,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 添加到问答记录列表
    qa_records = target_item.get('qa_records', [])
    qa_records.append(qa_record)
    target_item['qa_records'] = qa_records
    target_item['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 保存到数据库
    save_knowledge_to_db(target_item)
    
    print(f'[OK] 问答记录添加成功! 知识库ID: {knowledge_id}, 记录ID: {qa_record["id"]}')
    
    return jsonify({
        'success': True,
        'message': '问答记录添加成功',
        'data': qa_record
    })