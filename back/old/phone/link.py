import os
import json
import base64
from datetime import datetime

# 用户连接状态持久化文件（解决Flask多进程内存不共享问题）
USERS_FILE = os.path.join(os.path.dirname(__file__), 'connected_users.json')


def _load_users() -> dict:
    """从文件加载已连接用户"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_users(users: dict) -> None:
    """保存已连接用户到文件"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def send_to_connected_user(user_id: str, content: str, format_type: str = "formatted") -> dict:
    """
    发送内容给通过二维码连接的用户
    
    Args:
        user_id: 连接用户的ID
        content: 要发送的内容（包含文字和图片信息）
        format_type: 发送格式，"formatted"表示保持原格式，"document"表示生成PDF文档
    
    Returns:
        发送结果字典
    """
    # 检查用户是否已连接
    users = _load_users()
    if user_id not in users:
        return {
            "success": False,
            "message": f"用户 {user_id} 未连接或已断开"
        }
    
    # 根据格式类型处理内容
    if format_type == "document":
        # 生成PDF格式文档
        result = _generate_pdf_document(user_id, content)
    else:
        # 保持原格式发送
        result = _send_with_original_format(user_id, content)
    
    return result

def _generate_pdf_document(user_id: str, content: dict) -> dict:
    """
    生成PDF格式文档并发送给用户
    
    Args:
        user_id: 连接用户的ID
        content: 内容字典，包含texts和images
    
    Returns:
        发送结果字典
    """
    try:
        # 延迟导入reportlab（避免启动时加载失败）
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        
        # 生成文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"message_{user_id}_{timestamp}.pdf"
        
        # 输出目录
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建PDF文档
        pdf_path = os.path.join(output_dir, filename)
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        
        # 获取样式
        styles = getSampleStyleSheet()
        
        # 创建自定义样式（支持中文）
        try:
            # 尝试注册中文字体（Windows系统）
            font_path = 'C:/Windows/Fonts/msyh.ttc'  # 微软雅黑
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                title_style = ParagraphStyle('ChineseTitle', parent=styles['Title'], fontName='Chinese')
                normal_style = ParagraphStyle('ChineseNormal', parent=styles['Normal'], fontName='Chinese')
            else:
                title_style = styles['Title']
                normal_style = styles['Normal']
        except:
            title_style = styles['Title']
            normal_style = styles['Normal']
        
        # 构建PDF内容
        story = []
        
        # 标题
        story.append(Paragraph("消息文档", title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # 基本信息
        users = _load_users()
        story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        story.append(Paragraph(f"接收用户: {users.get(user_id, {}).get('name', '未知用户')}", normal_style))
        story.append(Spacer(1, 1*cm))
        
        # 保存图片并收集信息
        saved_images = []
        
        # 添加文字内容
        if content.get('texts'):
            story.append(Paragraph("【文字内容】", normal_style))
            story.append(Spacer(1, 0.3*cm))
            for idx, text in enumerate(content.get('texts', []), 1):
                # 处理文字中的特殊字符
                safe_text = text.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
                story.append(Paragraph(f"{idx}. {safe_text}", normal_style))
                story.append(Spacer(1, 0.2*cm))
            story.append(Spacer(1, 0.5*cm))
        
        # 添加图片
        if content.get('images'):
            story.append(Paragraph("【图片】", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            for idx, img in enumerate(content.get('images', []), 1):
                img_data = img.get('base64', '') or img.get('url', '')
                img_filename = img.get('filename', f'图片{idx}')
                
                if img_data:
                    try:
                        # 处理base64格式的图片
                        if img_data.startswith('data:image/'):
                            parts = img_data.split(',')
                            if len(parts) == 2:
                                data = parts[1]
                                img_bytes = base64.b64decode(data)
                                img_stream = BytesIO(img_bytes)
                                
                                # 获取图片格式
                                header = parts[0]
                                format_match = header.split('/')[1].split(';')[0].lower()
                                
                                # 保存图片文件
                                saved_img_filename = f"image_{user_id}_{timestamp}_{idx}.{format_match}"
                                saved_img_path = os.path.join(output_dir, saved_img_filename)
                                with open(saved_img_path, 'wb') as f:
                                    f.write(img_bytes)
                                
                                saved_images.append({
                                    'filename': saved_img_filename,
                                    'path': saved_img_filename,
                                    'original_name': img_filename
                                })
                                
                                # 添加图片到PDF
                                story.append(Paragraph(f"图片 {idx}: {img_filename}", normal_style))
                                try:
                                    # 尝试使用PIL处理图片
                                    from PIL import Image as PILImage
                                    pil_img = PILImage.open(img_stream)
                                    
                                    # 调整图片大小（最大宽度15cm）
                                    max_width = 15*cm
                                    img_width, img_height = pil_img.size
                                    aspect = img_height / img_width
                                    display_width = min(max_width, img_width * 0.5)
                                    display_height = display_width * aspect
                                    
                                    # 重置stream位置
                                    img_stream.seek(0)
                                    
                                    pdf_img = Image(img_stream, width=display_width, height=display_height)
                                    story.append(pdf_img)
                                except Exception as img_err:
                                    print(f"处理图片失败: {img_err}")
                                    story.append(Paragraph(f"[图片加载失败]", normal_style))
                                
                                story.append(Spacer(1, 0.5*cm))
                        
                        # 处理URL格式的图片
                        elif img_data.startswith('http://') or img_data.startswith('https://'):
                            try:
                                import requests
                                response = requests.get(img_data, timeout=15, verify=False)
                                response.raise_for_status()
                                img_bytes = response.content
                                img_stream = BytesIO(img_bytes)
                                
                                # 获取图片格式
                                content_type = response.headers.get('Content-Type', '')
                                if content_type.startswith('image/'):
                                    format_match = content_type.split('/')[1].lower()
                                else:
                                    url_ext = img_data.split('.')[-1].split('?')[0].lower()
                                    format_match = url_ext if url_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp'] else 'jpg'
                                
                                # 保存图片文件
                                saved_img_filename = f"image_{user_id}_{timestamp}_{idx}.{format_match}"
                                saved_img_path = os.path.join(output_dir, saved_img_filename)
                                with open(saved_img_path, 'wb') as f:
                                    f.write(img_bytes)
                                
                                saved_images.append({
                                    'filename': saved_img_filename,
                                    'path': saved_img_filename,
                                    'original_name': img_filename
                                })
                                
                                # 添加图片到PDF
                                story.append(Paragraph(f"图片 {idx}: {img_filename}", normal_style))
                                try:
                                    from PIL import Image as PILImage
                                    pil_img = PILImage.open(img_stream)
                                    
                                    max_width = 15*cm
                                    img_width, img_height = pil_img.size
                                    aspect = img_height / img_width
                                    display_width = min(max_width, img_width * 0.5)
                                    display_height = display_width * aspect
                                    
                                    img_stream.seek(0)
                                    pdf_img = Image(img_stream, width=display_width, height=display_height)
                                    story.append(pdf_img)
                                except Exception as img_err:
                                    print(f"处理URL图片失败: {img_err}")
                                    story.append(Paragraph(f"[图片加载失败]", normal_style))
                                
                                story.append(Spacer(1, 0.5*cm))
                            except Exception as url_err:
                                print(f"下载URL图片失败: {url_err}")
                                saved_images.append({
                                    'filename': img_filename,
                                    'path': img_data,
                                    'original_name': img_filename,
                                    'is_external': True
                                })
                                story.append(Paragraph(f"图片 {idx}: {img_filename} [外部链接]", normal_style))
                                story.append(Spacer(1, 0.5*cm))
                    
                    except Exception as e:
                        print(f"处理图片 {idx} 失败: {e}")
                        story.append(Paragraph(f"[图片 {idx} 处理失败]", normal_style))
                        story.append(Spacer(1, 0.5*cm))
        
        # 结束标记
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("=== 文档结束 ===", normal_style))
        
        # 生成PDF
        doc.build(story)
        
        # 发送给用户（包含图片文件信息）
        users = _load_users()
        if user_id in users:
            message_entry = {
                'type': 'document_with_images',
                'filename': filename,
                'path': filename,
                'images': saved_images,
                'texts': content.get('texts', []),
                'timestamp': datetime.now().isoformat()
            }
            users[user_id]['last_message'] = message_entry
            if 'unread_messages' not in users[user_id]:
                users[user_id]['unread_messages'] = []
            users[user_id]['unread_messages'].append(message_entry)
            _save_users(users)
        
        return {
            "success": True,
            "message": f"PDF文档已生成并发送（包含{len(saved_images)}张图片）",
            "filename": filename,
            "path": filename,
            "images": saved_images,
            "user_id": user_id,
            "user_name": users.get(user_id, {}).get('name', '未知用户')
        }
    
    except Exception as e:
        print(f"生成PDF失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"生成PDF失败: {str(e)}"
        }

def _send_with_original_format(user_id: str, content: dict) -> dict:
    """
    保持原格式发送内容给用户
    
    Args:
        user_id: 连接用户的ID
        content: 内容字典，包含texts和images
    
    Returns:
        发送结果字典
    """
    try:
        users = _load_users()
        user_info = users.get(user_id, {})
        
        # 构建保持格式的内容结构
        formatted_content = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_name": user_info.get('name', '未知用户'),
            "content": {
                "texts": content.get('texts', []),
                "images": content.get('images', []),
                "format": "original"
            }
        }
        
        # 构建图片列表（含 base64 数据用于前端预览）
        image_list = []
        for img in content.get('images', []):
            img_item = {
                'filename': img.get('filename', '图片'),
                'size': img.get('size', '未知'),
                'format': img.get('format', 'UNKNOWN')
            }
            if img.get('base64'):
                img_item['base64'] = img['base64']
            image_list.append(img_item)
        
        formatted_content = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_name": user_info.get('name', '未知用户'),
            "content": {
                "texts": content.get('texts', []),
                "images": image_list,
                "format": "original"
            }
        }
        
        # 发送给用户（保存到用户连接记录）
        message_entry = {
            'type': 'formatted',
            'content': formatted_content,
            'timestamp': datetime.now().isoformat()
        }
        if user_id in users:
            users[user_id]['last_message'] = message_entry
            if 'unread_messages' not in users[user_id]:
                users[user_id]['unread_messages'] = []
            users[user_id]['unread_messages'].append(message_entry)
            _save_users(users)
        
        # 记录发送历史
        history_dir = os.path.join(os.path.dirname(__file__), 'history')
        os.makedirs(history_dir, exist_ok=True)
        history_file = os.path.join(history_dir, f"{user_id}_history.json")
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        history.append(formatted_content)
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": "内容已按原格式发送",
            "user_id": user_id,
            "user_name": user_info.get('name', '未知用户'),
            "text_count": len(content.get('texts', [])),
            "image_count": len(content.get('images', []))
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"发送失败: {str(e)}"
        }

def register_connected_user(user_id: str, user_name: str = "未知用户") -> dict:
    """
    注册一个已连接的用户
    
    Args:
        user_id: 用户ID
        user_name: 用户名称
    
    Returns:
        注册结果字典
    """
    users = _load_users()
    users[user_id] = {
        'name': user_name,
        'connected_at': datetime.now().isoformat(),
        'last_heartbeat': datetime.now().isoformat(),
        'last_message': None,
        'unread_messages': []
    }
    _save_users(users)
    
    return {
        "success": True,
        "message": f"用户 {user_name} 已连接",
        "user_id": user_id,
        "user_name": user_name
    }

def update_heartbeat(user_id: str) -> dict:
    """
    更新用户心跳时间
    
    Args:
        user_id: 用户ID
    
    Returns:
        更新结果字典
    """
    users = _load_users()
    if user_id in users:
        users[user_id]['last_heartbeat'] = datetime.now().isoformat()
        _save_users(users)
        return {
            "success": True,
            "message": "心跳已更新",
            "user_id": user_id
        }
    return {
        "success": False,
        "message": f"用户 {user_id} 未连接"
    }

def check_expired_users(timeout_seconds: int = 60) -> list:
    """
    检查超时的用户连接
    
    Args:
        timeout_seconds: 超时秒数，默认60秒
    
    Returns:
        被断开的用户列表
    """
    users = _load_users()
    now = datetime.now()
    expired = []
    for user_id, info in list(users.items()):
        last_hb = info.get('last_heartbeat')
        if last_hb:
            try:
                hb_time = datetime.fromisoformat(last_hb)
                if (now - hb_time).total_seconds() > timeout_seconds:
                    expired.append(user_id)
                    del users[user_id]
            except Exception:
                pass
    _save_users(users)
    return expired

def get_connected_users() -> list:
    """
    获取所有已连接的用户列表
    
    Returns:
        用户列表
    """
    users = _load_users()
    return [
        {
            'user_id': uid,
            'user_name': info.get('name', '未知用户'),
            'connected_at': info.get('connected_at'),
            'has_unread': info.get('last_message') is not None
        }
        for uid, info in users.items()
    ]

def get_unread_messages(user_id: str) -> list:
    """
    获取用户的未读消息列表
    
    Args:
        user_id: 用户ID
    
    Returns:
        未读消息列表
    """
    users = _load_users()
    if user_id not in users:
        return []
    
    messages = users[user_id].get('unread_messages', [])
    # 复制后清空未读列表
    result = messages.copy()
    users[user_id]['unread_messages'] = []
    _save_users(users)
    return result


def disconnect_user(user_id: str) -> dict:
    """
    断开用户连接
    
    Args:
        user_id: 用户ID
    
    Returns:
        断开结果字典
    """
    users = _load_users()
    if user_id in users:
        user_name = users[user_id].get('name', '未知用户')
        del users[user_id]
        _save_users(users)
        return {
            "success": True,
            "message": f"用户 {user_name} 已断开连接",
            "user_id": user_id
        }
    else:
        return {
            "success": False,
            "message": f"用户 {user_id} 不存在或已断开"
        }

# 示例用法
if __name__ == "__main__":
    # 模拟用户连接
    register_connected_user("test_user_001", "测试用户")
    
    # 准备发送内容
    content = {
        "texts": [
            "标题: 矿工的坚守，安全的守护者",
            "正文: 在煤矿的深处，有这样一群默默无闻的英雄...",
            "#煤矿 #安全生产 #矿工精神"
        ],
        "images": [
            {
                "filename": "煤矿场景.jpg",
                "size": "1280x720",
                "format": "JPEG"
            }
        ]
    }
    
    # 测试保持格式发送
    print("=== 测试保持格式发送 ===")
    result = send_to_connected_user("test_user_001", content, "formatted")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 测试文档形式发送
    print("\n=== 测试文档形式发送 ===")
    result = send_to_connected_user("test_user_001", content, "document")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 查看已连接用户
    print("\n=== 已连接用户 ===")
    print(json.dumps(get_connected_users(), ensure_ascii=False, indent=2))
