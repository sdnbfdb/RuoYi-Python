"""
工具函数模块
提供知识库调用、组织架构调用和用户信息管理的工具函数
支持 @AI助手、@知识库、@联网搜索 等机器人调用
"""

import os
import sys
import json
import requests
import base64
from datetime import datetime
import uuid
import io

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from knowledge.knowledge import load_knowledge_data

# 生成文件保存目录
PHOTO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'AIuser', 'photo')
VIDEO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'AIuser', 'video')

# 确保目录存在
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)


def generate_qr_code(data: str, size: int = 256) -> dict:
    """
    生成二维码图片
    
    Args:
        data: 要编码的内容（URL或文本）
        size: 二维码大小（像素），默认256
        
    Returns:
        dict: 包含 success、message、base64 字段
    """
    try:
        import qrcode
        from PIL import Image
        
        # 创建二维码对象
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # 添加数据
        qr.add_data(data)
        qr.make(fit=True)
        
        # 生成图像
        img = qr.make_image(fill_color='black', back_color='white')
        
        # 调整大小
        if size != 256:
            img = img.resize((size, size), Image.LANCZOS)
        
        # 转换为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = buffer.getvalue()
        
        return {
            'success': True,
            'message': '二维码生成成功',
            'base64': img_base64,
            'size': size
        }
        
    except ImportError as e:
        return {
            'success': False,
            'message': f'缺少必要依赖: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'二维码生成失败: {str(e)}'
        }


def download_file(url: str, save_dir: str, filename: str = None) -> dict:
    """
    下载文件到指定目录
    
    Args:
        url: 文件URL
        save_dir: 保存目录
        filename: 可选文件名，默认为UUID生成
        
    Returns:
        dict: 包含 success、message、file_path、url 字段
    """
    try:
        # 生成唯一文件名
        if not filename:
            # 从URL中提取文件扩展名（去掉查询参数）
            url_path = url.split('?')[0]  # 去掉查询参数
            ext = os.path.splitext(url_path)[1] or '.png'
            if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.mp4', '.avi', '.mov']:
                ext = '.png'  # 默认使用png格式
            filename = f"{uuid.uuid4().hex}{ext}"
        
        file_path = os.path.join(save_dir, filename)
        
        # 下载文件
        response = requests.get(url, timeout=60, verify=False)
        response.raise_for_status()
        
        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        return {
            'success': True,
            'message': '文件下载成功',
            'file_path': file_path,
            'url': url,
            'filename': filename
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'文件下载失败: {str(e)}',
            'url': url
        }


def save_to_database(user_id: str, content: str, content_type: str = 'text', file_url: str = None) -> dict:
    """
    保存聊天历史到数据库
    
    Args:
        user_id: 用户ID
        content: 内容
        content_type: 内容类型，可选 'text', 'image', 'video'
        file_url: 文件URL（如果是图片或视频）
        
    Returns:
        dict: 包含 success、message 字段
    """
    try:
        import sys as _sys, os as _os
        _back = _os.path.dirname(_os.path.dirname(os.path.abspath(__file__)))
        if _back not in _sys.path:
            _sys.path.insert(0, _back)
        
        from sql.database import get_db_connection
        
        db = get_db_connection()
        db.execute_query(
            'INSERT INTO chat_history (user_id, content, content_type, file_url, created_at) VALUES (%s, %s, %s, %s, %s)',
            (user_id, content, content_type, file_url, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        
        return {
            'success': True,
            'message': '历史记录保存成功'
        }
    except Exception as e:
        print(f"[错误] 保存到数据库失败: {e}")
        return {
            'success': False,
            'message': f'保存到数据库失败: {str(e)}'
        }


def _write_org_txt(org_file, org_dict):
    """
    将组织架构字典写回 organization.txt 文件
    """
    lines = ['department：{superior department：below department：create_data：functionary：role：}']
    for dept_name, fields in org_dict.items():
        inner_parts = []
        for k in ['superior department', 'below department', 'create_data', 'functionary', 'role']:
            v = fields.get(k, '无')
            inner_parts.append(k)
            inner_parts.append(v)
        inner = '：'.join(inner_parts)
        line = f'{dept_name}：{{{inner}：}}'
        lines.append(line)
    
    try:
        with open(org_file, 'w', newline='', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception as e:
        print(f"[错误] 写入 organization.txt 失败: {e}")


def _extract_json_from_response(result):
    """
    从 Flask Response 对象中提取 JSON 数据
    
    Args:
        result: 可能是字典或 Flask Response 对象
    
    Returns:
        dict: 提取的字典数据
    """
    if hasattr(result, 'get_json'):
        # Flask Response 对象
        try:
            return result.get_json()
        except:
            return {'success': False, 'message': '无法解析响应'}
    elif isinstance(result, dict):
        # 已经是字典
        return result
    else:
        return {'success': False, 'message': f'未知响应类型: {type(result)}'}


def call_knowledge_base(action: str, **kwargs) -> dict:
    """
    知识库调用工具函数
    
    Args:
        action: 操作类型，可选值: 'list', 'detail', 'create', 'search', 'extract'
        **kwargs: 额外参数
            - knowledge_id: 资料ID（用于 detail, extract 操作）
            - title: 标题（用于 create 操作）
            - description: 描述（用于 create 操作）
            - content: 内容（用于 create 操作）
            - files: 文件列表（用于 create 操作）
            - search: 搜索关键词（用于 search 操作）
            - extract_fields: 要提取的字段列表（用于 extract 操作）
    
    Returns:
        dict: 操作结果，包含 success 和 data 字段
    """
    try:
        if action == 'list':
            # 获取知识库列表（使用内部函数直接读取数据）
            data = load_knowledge_data()
            return {'success': True, 'data': data, 'total': len(data)}
        
        elif action == 'detail':
            # 获取资料详情
            knowledge_id = kwargs.get('knowledge_id')
            if not knowledge_id:
                return {'success': False, 'message': '缺少 knowledge_id 参数'}
            
            data = load_knowledge_data()
            item = next((item for item in data if item.get('id') == knowledge_id), None)
            
            if item:
                return {'success': True, 'data': item}
            else:
                return {'success': False, 'message': '资料不存在'}
        
        elif action == 'create':
            # 创建新资料（需要通过 API 调用）
            title = kwargs.get('title', '')
            description = kwargs.get('description', '')
            content = kwargs.get('content', '')
            
            if not title:
                return {'success': False, 'message': '标题不能为空'}
            
            return {'success': False, 'message': '创建操作需要通过表单上传，请使用网页界面操作'}
        
        elif action == 'search':
            # 搜索资料
            search_keyword = kwargs.get('search', '')
            data = load_knowledge_data()
            
            if not search_keyword:
                return {'success': True, 'data': data, 'total': len(data)}
            
            kw_lower = search_keyword.lower().strip()
            # 去掉常见文件扩展名用于模糊匹配
            kw_no_ext = kw_lower
            for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.md']:
                if kw_no_ext.endswith(ext):
                    kw_no_ext = kw_no_ext[:-len(ext)]
                    break
            
            def match_item(item):
                title = item.get('title', '').lower()
                desc = item.get('description', '').lower()
                item_id = item.get('id', '').lower()
                # 匹配标题、描述、ID
                if kw_lower in title or kw_lower in desc or kw_lower == item_id:
                    return True
                # 去掉扩展名后匹配标题
                if kw_no_ext and kw_no_ext != kw_lower and kw_no_ext in title:
                    return True
                # 匹配附件文件名
                for att in item.get('attachments', []):
                    if kw_lower in att.get('filename', '').lower():
                        return True
                    if kw_no_ext and kw_no_ext in att.get('filename', '').lower():
                        return True
                return False
            
            filtered = [item for item in data if match_item(item)]
            
            return {'success': True, 'data': filtered, 'total': len(filtered)}
        
        elif action == 'extract':
            # 提取知识库内容
            knowledge_id = kwargs.get('knowledge_id')
            extract_fields = kwargs.get('extract_fields', [])
            
            if not knowledge_id:
                return {'success': False, 'message': '缺少 knowledge_id 参数'}
            
            data = load_knowledge_data()
            item = next((item for item in data if item.get('id') == knowledge_id), None)
            
            if not item:
                return {'success': False, 'message': '资料不存在'}
            
            # 如果指定了提取字段，则只返回指定字段
            if extract_fields:
                extracted = {}
                for field in extract_fields:
                    if field in item:
                        extracted[field] = item[field]
                return {'success': True, 'data': extracted}
            
            # 否则返回完整内容（排除内部字段）
            cleaned_data = {k: v for k, v in item.items() if not k.startswith('_')}
            return {'success': True, 'data': cleaned_data}
        
        elif action == 'delete':
            # 删除资料
            knowledge_id = kwargs.get('knowledge_id')
            if not knowledge_id:
                return {'success': False, 'message': '缺少 knowledge_id 参数'}
            
            data = load_knowledge_data()
            target_item = next((item for item in data if item.get('id') == knowledge_id), None)
            
            if not target_item:
                return {'success': False, 'message': '资料不存在'}
            
            # 删除附件文件
            for attachment in target_item.get('attachments', []):
                try:
                    saved_name = attachment.get('saved_name', '')
                    if saved_name:
                        filepath = os.path.join(UPLOAD_DIR, saved_name)
                        if os.path.exists(filepath):
                            os.remove(filepath)
                except Exception as e:
                    print(f'Delete attachment error: {e}')
            
            # 删除知识库数据文件
            try:
                if os.path.exists(DATA_DIR):
                    for filename in os.listdir(DATA_DIR):
                        if filename.startswith(knowledge_id + '_') and filename.endswith('.txt'):
                            filepath = os.path.join(DATA_DIR, filename)
                            if os.path.exists(filepath):
                                os.remove(filepath)
                            break
                
                # 更新索引文件
                from knowledge.knowledge import update_index_file as _update
                _update()
            except Exception as e:
                print(f'Delete knowledge file error: {e}')
            
            return {'success': True, 'message': '删除成功', 'data': {'deleted_id': knowledge_id}}
        
        else:
            return {'success': False, 'message': f'不支持的操作类型: {action}'}
    
    except Exception as e:
        return {'success': False, 'message': f'知识库调用失败: {str(e)}'}


def call_search_api(query: str) -> dict:
    """
    调用博查搜索 API 进行联网搜索
    
    Args:
        query: 搜索关键词
    
    Returns:
        dict: 搜索结果，包含 success 和 data 字段
    """
    try:
        # 从环境变量获取 API 配置
        api_key = os.getenv('SEARCH_API_KEY')
        
        if not api_key:
            return {
                'success': False,
                'message': '博查搜索 API 配置未设置'
            }
        
        # 博查搜索 API 请求（根据官方文档）
        url = 'https://api.bocha.cn/v1/web-search'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'query': query,
            'summary': True,
            'freshness': 'noLimit',
            'count': 20
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            
            # 检查 API 返回的状态码（博查 API 返回 200 表示成功）
            if result.get('code') == 200 or result.get('code') == '200':
                return {
                    'success': True,
                    'message': result.get('msg') or '搜索成功',
                    'data': result.get('data', {})
                }
            else:
                return {
                    'success': False,
                    'message': result.get('msg', '搜索失败'),
                    'data': result
                }
        else:
            return {
                'success': False,
                'message': f'搜索失败，状态码: {response.status_code}',
                'data': response.text
            }
    
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'网络请求失败: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'搜索调用失败: {str(e)}'
        }


def _parse_org_txt(org_file):
    """
    解析 organization.txt 文件（正确解析现有格式）
    
    文件格式：
    department：{superior department：below department：create_data：functionary：role：}
    总部：{superior department：无：below department：部门1,部门2,...：create_data：2026-01-01：functionary：sanjin：role：0：}
    部门1：{superior department：总部：below department：部门1.1,...：create_data：...：functionary：部门1经理：role：1：}
    
    Returns:
        dict: {部门名: {字段名: 值}}
    """
    import re
    from collections import OrderedDict
    
    result = OrderedDict()
    if not os.path.exists(org_file):
        return result
    
    try:
        with open(org_file, 'r', encoding='utf-8-sig') as f:  # 使用 utf-8-sig 处理 BOM
            content = f.read()
        
        # 按行分割，处理各种换行符
        lines = content.splitlines()
    except Exception as e:
        print(f"[错误] 读取 organization.txt 失败: {e}")
        return result
    
    for line in lines:
        line = line.strip()
        if not line:
            # 跳过空行
            continue
        
        # 跳过表头行（可能带有 BOM）
        if line.lstrip('\ufeff').startswith('department：'):
            continue
        
        # 格式: 名称：{k1：v1：k2：v2：...：}
        idx = line.find('：{')
        if idx == -1:
            print(f"[警告] 无法解析行: {repr(line)}")
            continue
        
        name = line[:idx].strip()
        inner = line[idx+2:]  # 跳过 ：{
        
        if inner.endswith('：}'):
            inner = inner[:-2]  # 去掉末尾 ：}
        elif inner.endswith('}'):
            inner = inner[:-1]
        
        # 按全角冒号切分 key:value
        parts = inner.split('：')
        if len(parts) % 2 != 0:
            print(f"[警告] 字段数量不是偶数: {repr(parts)}")
            parts.append('')
        
        fields = {}
        for k, v in zip(parts[0::2], parts[1::2]):
            fields[k.strip()] = v.strip()
        
        result[name] = fields
        print(f"[调试] 解析成功: {name} -> {fields}")
    
    return result


def call_organization(action: str, **kwargs) -> dict:
    """
    组织架构调用工具函数
    
    Args:
        action: 操作类型，可选值: 'get', 'list', 'add', 'update', 'delete', 'adjust'
        **kwargs: 额外参数
            - org_id: 组织ID（用于 get, update, delete 操作）
            - name: 组织名称（用于 add, update, adjust 操作）
            - parent_id: 父组织ID（用于 add, adjust 操作）
            - description: 组织描述（用于 add, update 操作）
            - new_parent_id: 新的父组织ID（用于 adjust 操作）
            - new_name: 新的组织名称（用于 adjust 操作）
    
    Returns:
        dict: 操作结果，包含 success 和 data 字段
    """
    try:
        # 尝试从数据库读取组织架构数据（数据库为主，文件为备）
        def _load_org_from_db():
            try:
                import sys, os as _os
                _back = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
                if _back not in sys.path: sys.path.insert(0, _back)
                from sql.database import get_db_connection
                db = get_db_connection()
                rows = db.execute_query('SELECT * FROM organization ORDER BY id ASC')
                result = {}
                for r in (rows or []):
                    result[r['name']] = {
                        'superior department': r.get('superior_department', ''),
                        'below department': r.get('below_department', ''),
                        'create_data': str(r.get('create_date', '')),
                        'functionary': r.get('functionary', ''),
                        'role': r.get('role', '')
                    }
                return result if result else None
            except Exception as _e:
                print(f'[org] DB读取失败: {_e}')
                return None

        org_dict = _load_org_from_db()
        if not org_dict:
            # 备用：从 txt 文件读取
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
            org_file = os.path.join(data_dir, 'organization.txt')
            os.makedirs(data_dir, exist_ok=True)
            if not os.path.exists(org_file):
                with open(org_file, 'w', encoding='utf-8') as f:
                    f.write('department：{superior department：below department：create_data：functionary：role：}\n')
                    f.write('总部：{superior department：无：below department：无：create_data：2026-01-01：functionary：总经理：role：0：}\n')
            org_dict = _parse_org_txt(org_file)
        
        if action in ('get', 'get_by_name'):
            # 获取单个组织信息（支持按名称或 role 查找）
            org_id = kwargs.get('org_id') or kwargs.get('name')
            if not org_id:
                return {'success': False, 'message': '缺少 org_id 或 name 参数'}
            
            # 先按 role 查找，再按名称查找
            result = None
            for name, fields in org_dict.items():
                if fields.get('role') == str(org_id) or name == org_id:
                    result = {
                        'id': fields.get('role', ''),
                        'name': name,
                        'parent_id': fields.get('superior department', ''),
                        'parent_name': fields.get('superior department', ''),
                        'description': fields.get('functionary', ''),
                        'created_at': fields.get('create_data', ''),
                        'children': [c.strip() for c in fields.get('below department', '').split(',') if c.strip() and c.strip() != '无']
                    }
                    break
            
            if result:
                return {'success': True, 'data': result}
            else:
                return {'success': False, 'message': f'组织「{org_id}」不存在'}
        
        elif action == 'list':
            # 获取组织列表（支持按父部门过滤）
            parent_filter = kwargs.get('parent') or kwargs.get('parent_id') or kwargs.get('parent_name')
            org_data = []
            for name, fields in org_dict.items():
                parent = fields.get('superior department', '')
                if parent_filter and parent != parent_filter and name != parent_filter:
                    continue
                org_data.append({
                    'id': fields.get('role', ''),
                    'name': name,
                    'parent_id': parent,
                    'parent_name': parent,
                    'description': fields.get('functionary', ''),
                    'created_at': fields.get('create_data', ''),
                    'children': [c.strip() for c in fields.get('below department', '').split(',') if c.strip() and c.strip() != '无']
                })
            
            return {'success': True, 'data': org_data, 'total': len(org_data)}
        
        elif action == 'add':
            # 添加新组织
            name = kwargs.get('name', '')
            parent_id = kwargs.get('parent_id', '')
            description = kwargs.get('description', '')
            
            if not name:
                return {'success': False, 'message': '组织名称不能为空'}
            
            # 确定新组织的 role（根据父组织自动生成）
            parent_role = parent_id if parent_id.isdigit() else None
            if not parent_role:
                # 查找父组织的 role
                for org_name, fields in org_dict.items():
                    if org_name == parent_id or fields.get('role') == parent_id:
                        parent_role = fields.get('role')
                        break
            
            if not parent_role:
                parent_role = '0'  # 默认挂到总部下
            
            # 生成新 role（在父组织下找最大子编号+1）
            import re
            max_sub_num = 0
            for org_name, fields in org_dict.items():
                role = fields.get('role', '')
                if role.startswith(parent_role + '.'):
                    parts = role.split('.')
                    if len(parts) == len(parent_role.split('.')) + 1:
                        try:
                            num = int(parts[-1])
                            max_sub_num = max(max_sub_num, num)
                        except:
                            pass
                elif parent_role == '0' and role.isdigit() and role != '0':
                    try:
                        num = int(role)
                        max_sub_num = max(max_sub_num, num)
                    except:
                        pass
            
            new_role = f"{parent_role}.{max_sub_num + 1}" if parent_role != '0' else str(max_sub_num + 1)
            
            # 获取父组织名称
            parent_name = '总部'
            for org_name, fields in org_dict.items():
                if fields.get('role') == parent_role:
                    parent_name = org_name
                    break
            
            # 添加新组织到字典
            org_dict[name] = {
                'superior department': parent_name,
                'below department': '无',
                'create_data': datetime.now().strftime('%Y-%m-%d'),
                'functionary': description or name + '负责人',
                'role': new_role
            }
            
            # 更新父组织的子部门列表
            if parent_name in org_dict:
                below = org_dict[parent_name].get('below department', '无')
                if below == '无':
                    org_dict[parent_name]['below department'] = name
                else:
                    existing = [b.strip() for b in below.split(',') if b.strip() and b.strip() != '无']
                    if name not in existing:
                        existing.append(name)
                        org_dict[parent_name]['below department'] = ','.join(existing)
            
            # 写回文件
            _write_org_txt(org_file, org_dict)
            
            return {
                'success': True,
                'message': '组织添加成功',
                'data': {'id': new_role, 'name': name, 'parent_id': parent_role, 'parent_name': parent_name, 'description': description}
            }
        
        elif action == 'update':
            # 更新组织信息
            org_id = kwargs.get('org_id')
            name = kwargs.get('name')
            parent_id = kwargs.get('parent_id')
            description = kwargs.get('description')
            
            if not org_id:
                return {'success': False, 'message': '缺少 org_id 参数'}
            
            # 查找组织
            found_name = None
            for org_name, fields in org_dict.items():
                if fields.get('role') == org_id or org_name == org_id:
                    found_name = org_name
                    break
            
            if not found_name:
                return {'success': False, 'message': '组织不存在'}
            
            # 更新字段
            if name and name != found_name:
                # 修改名称需要同时更新父组织的子部门列表
                old_name = found_name
                # 更新所有引用
                for on, fields in org_dict.items():
                    if fields.get('superior department') == old_name:
                        fields['superior department'] = name
                    below = fields.get('below department', '')
                    if old_name in below:
                        fields['below department'] = below.replace(old_name, name)
                # 重命名字典键
                org_dict[name] = org_dict.pop(old_name)
                found_name = name
            
            if description:
                org_dict[found_name]['functionary'] = description
            
            if parent_id:
                # 更新父组织
                old_parent = org_dict[found_name].get('superior department', '')
                # 从旧父组织的子列表中移除
                if old_parent in org_dict:
                    below = org_dict[old_parent].get('below department', '')
                    if found_name in below:
                        parts = [b.strip() for b in below.split(',') if b.strip() and b.strip() != '无' and b.strip() != found_name]
                        org_dict[old_parent]['below department'] = ','.join(parts) if parts else '无'
                
                # 查找新父组织名称
                new_parent_name = parent_id
                for on, fields in org_dict.items():
                    if fields.get('role') == parent_id:
                        new_parent_name = on
                        break
                
                # 添加到新父组织的子列表
                org_dict[found_name]['superior department'] = new_parent_name
                if new_parent_name in org_dict:
                    below = org_dict[new_parent_name].get('below department', '无')
                    if below == '无':
                        org_dict[new_parent_name]['below department'] = found_name
                    else:
                        existing = [b.strip() for b in below.split(',') if b.strip() and b.strip() != '无']
                        if found_name not in existing:
                            existing.append(found_name)
                            org_dict[new_parent_name]['below department'] = ','.join(existing)
            
            # 写回文件
            _write_org_txt(org_file, org_dict)
            
            return {'success': True, 'message': '组织更新成功'}
        
        elif action == 'delete':
            # 删除组织
            org_id = kwargs.get('org_id')
            if not org_id:
                return {'success': False, 'message': '缺少 org_id 参数'}
            
            # 查找组织
            found_name = None
            for org_name, fields in org_dict.items():
                if fields.get('role') == org_id or org_name == org_id:
                    found_name = org_name
                    break
            
            if not found_name:
                return {'success': False, 'message': '组织不存在'}
            
            if found_name == '总部':
                return {'success': False, 'message': '不能删除总部'}
            
            # 获取父组织
            parent_name = org_dict[found_name].get('superior department', '')
            
            # 从父组织的子列表中移除
            if parent_name in org_dict:
                below = org_dict[parent_name].get('below department', '')
                if found_name in below:
                    parts = [b.strip() for b in below.split(',') if b.strip() and b.strip() != '无' and b.strip() != found_name]
                    org_dict[parent_name]['below department'] = ','.join(parts) if parts else '无'
            
            # 删除该组织及其所有子组织
            children_to_delete = [found_name]
            idx = 0
            while idx < len(children_to_delete):
                current = children_to_delete[idx]
                # 查找所有子组织
                for org_name in list(org_dict.keys()):
                    if org_dict[org_name].get('superior department') == current:
                        children_to_delete.append(org_name)
                idx += 1
            
            # 删除所有标记的组织
            for org_name in children_to_delete:
                del org_dict[org_name]
            
            # 写回文件
            _write_org_txt(org_file, org_dict)
            
            return {'success': True, 'message': '组织删除成功'}
        
        elif action == 'adjust':
            # 调整组织架构（支持修改名称、调整层级）
            org_id = kwargs.get('org_id')
            new_name = kwargs.get('new_name')
            new_parent_id = kwargs.get('new_parent_id')
            
            if not org_id:
                return {'success': False, 'message': '缺少 org_id 参数'}
            
            if not new_name and new_parent_id is None:
                return {'success': False, 'message': '至少需要提供 new_name 或 new_parent_id'}
            
            # 查找组织
            found_name = None
            for org_name, fields in org_dict.items():
                if fields.get('role') == org_id or org_name == org_id:
                    found_name = org_name
                    break
            
            if not found_name:
                return {'success': False, 'message': '组织不存在'}
            
            # 修改名称
            if new_name and new_name != found_name:
                old_name = found_name
                # 更新所有引用
                for on, fields in org_dict.items():
                    if fields.get('superior department') == old_name:
                        fields['superior department'] = new_name
                    below = fields.get('below department', '')
                    if old_name in below:
                        fields['below department'] = below.replace(old_name, new_name)
                # 重命名字典键
                org_dict[new_name] = org_dict.pop(old_name)
                found_name = new_name
            
            # 修改父组织
            if new_parent_id is not None:
                old_parent = org_dict[found_name].get('superior department', '')
                # 从旧父组织的子列表中移除
                if old_parent in org_dict:
                    below = org_dict[old_parent].get('below department', '')
                    if found_name in below:
                        parts = [b.strip() for b in below.split(',') if b.strip() and b.strip() != '无' and b.strip() != found_name]
                        org_dict[old_parent]['below department'] = ','.join(parts) if parts else '无'
                
                # 查找新父组织名称
                new_parent_name = new_parent_id
                for on, fields in org_dict.items():
                    if fields.get('role') == new_parent_id:
                        new_parent_name = on
                        break
                
                # 添加到新父组织的子列表
                org_dict[found_name]['superior department'] = new_parent_name
                if new_parent_name in org_dict:
                    below = org_dict[new_parent_name].get('below department', '无')
                    if below == '无':
                        org_dict[new_parent_name]['below department'] = found_name
                    else:
                        existing = [b.strip() for b in below.split(',') if b.strip() and b.strip() != '无']
                        if found_name not in existing:
                            existing.append(found_name)
                            org_dict[new_parent_name]['below department'] = ','.join(existing)
            
            # 写回文件
            _write_org_txt(org_file, org_dict)
            
            return {'success': True, 'message': '组织架构调整成功'}
        
        elif action == 'add_members':
            # 添加成员到组织
            org_id = kwargs.get('org_id')
            members = kwargs.get('members', '')
            
            if not org_id:
                return {'success': False, 'message': '缺少 org_id 参数'}
            
            if not members:
                return {'success': False, 'message': '缺少 members 参数'}
            
            # 查找组织
            found_name = None
            for org_name, fields in org_dict.items():
                if fields.get('role') == org_id or org_name == org_id:
                    found_name = org_name
                    break
            
            if not found_name:
                return {'success': False, 'message': '组织不存在'}
            
            # 获取现有成员
            current_members = org_dict[found_name].get('functionary', '')
            
            # 添加新成员（用逗号分隔）
            if current_members and current_members != '无':
                member_list = [m.strip() for m in current_members.split(',') if m.strip()]
            else:
                member_list = []
            
            # 添加新成员
            new_member_list = [m.strip() for m in members.split(',') if m.strip()]
            for member in new_member_list:
                if member not in member_list:
                    member_list.append(member)
            
            # 更新成员列表
            org_dict[found_name]['functionary'] = ','.join(member_list)
            
            # 写回文件
            _write_org_txt(org_file, org_dict)
            
            return {'success': True, 'message': '成员添加成功', 'data': {'members': member_list}}
        
        else:
            return {'success': False, 'message': f'不支持的操作类型: {action}'}
    
    except Exception as e:
        return {'success': False, 'message': f'组织架构调用失败: {str(e)}'}


def call_user_profile(action: str, **kwargs) -> dict:
    """
    用户信息管理工具函数
    
    Args:
        action: 操作类型，可选值: 'get', 'update'
        **kwargs: 额外参数
            - user_id: 用户ID（必须）
            - username: 用户名（用于 update 操作）
            - nickname: 昵称（用于 update 操作）
            - email: 邮箱（用于 update 操作）
            - phone: 手机号（用于 update 操作）
            - avatar: 头像路径（用于 update 操作）
    
    Returns:
        dict: 操作结果，包含 success 和 data 字段
    """
    try:
        # 从数据库读取用户信息
        def _load_user_from_db(uid):
            try:
                import sys, os as _os
                _back = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
                if _back not in sys.path: sys.path.insert(0, _back)
                from sql.database import get_db_connection
                db = get_db_connection()
                rows = db.execute_query('SELECT * FROM users WHERE id = %s LIMIT 1', (uid,))
                return rows[0] if rows else None
            except Exception as _e:
                print(f'[user] DB读取失败: {_e}')
                return None

        user_id = kwargs.get('user_id')
        if not user_id:
            return {'success': False, 'message': '缺少 user_id 参数，请告知用户提供用户ID'}
        
        if action == 'get':
            user = _load_user_from_db(user_id)
            if user:
                # 过滤敏感字段
                safe_user = {
                    'id': user.get('id'),
                    'username': user.get('username', ''),
                    'account': user.get('account', ''),
                    'name': user.get('name', ''),
                    'email': user.get('email', ''),
                    'phone': user.get('phone', ''),
                    'avatar': user.get('avatar', ''),
                    'role': user.get('role', ''),
                }
                return {'success': True, 'data': safe_user}
            else:
                return {'success': False, 'message': '用户不存在'}
        
        elif action == 'update':
            try:
                import sys, os as _os
                _back = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
                if _back not in sys.path: sys.path.insert(0, _back)
                from sql.database import get_db_connection
                db = get_db_connection()
                updated_fields = ['username', 'nickname', 'email', 'phone', 'avatar', 'name']
                update_data = {k: v for k, v in kwargs.items() if k in updated_fields and v is not None}
                if not update_data:
                    return {'success': False, 'message': '没有需要更新的字段'}
                set_clause = ', '.join([f'{k}=%s' for k in update_data])
                db.execute_query(
                    f'UPDATE users SET {set_clause} WHERE id=%s',
                    list(update_data.values()) + [user_id]
                )
                return {'success': True, 'message': '用户信息更新成功', 'data': update_data}
            except Exception as _e:
                return {'success': False, 'message': f'更新失败: {_e}'}
        else:
            return {'success': False, 'message': f'不支持的操作类型: {action}'}
    
    except Exception as e:
        return {'success': False, 'message': f'用户信息管理失败: {str(e)}'}


def call_robot(robot_name: str, action: str, **kwargs) -> dict:
    """
    机器人调用统一接口
    根据机器人名称路由到相应的工具函数
    
    Args:
        robot_name: 机器人名称，可选值: 'AI助手', '个人助手', '知识库', '联网搜索', '组织管理'
        action: 操作类型
        **kwargs: 额外参数
    
    Returns:
        dict: 操作结果，包含 success 和 data 字段
    """
    try:
        if robot_name == 'AI助手' or robot_name == '个人助手':
            # AI助手/个人助手支持：组织架构调整、个人信息修改、表格处理
            if action in ['get', 'list', 'add', 'update', 'delete', 'adjust']:
                return call_organization(action, **kwargs)
            elif action in ['user_get', 'user_update']:
                # 转换用户操作
                if action == 'user_get':
                    return call_user_profile('get', **kwargs)
                elif action == 'user_update':
                    return call_user_profile('update', **kwargs)
            elif action in ['table_create', 'table_delete', 'table_add_row', 'table_delete_row', 
                           'table_add_column', 'table_delete_column', 'table_statistics', 
                           'table_chart', 'table_export', 'table_filter']:
                # 表格处理操作
                return call_table_tool(action, **kwargs)
            else:
                return {'success': False, 'message': f'{robot_name}不支持的操作类型: {action}'}
        
        elif robot_name == '知识库':
            # 知识库支持：内容查询、内容提取
            if action in ['list', 'detail', 'search', 'extract']:
                return call_knowledge_base(action, **kwargs)
            else:
                return {'success': False, 'message': f'知识库不支持的操作类型: {action}'}
        
        elif robot_name == '联网搜索':
            # 联网搜索支持：网络搜索、实时信息查询
            query = kwargs.get('query', kwargs.get('keyword', '')).strip()
            if not query:
                return {'success': False, 'message': '请输入搜索关键词，例如：@联网搜索 人工智能最新发展'}
            
            if len(query) < 2:
                return {'success': False, 'message': '搜索关键词过于简短，请提供更具体的搜索内容'}
            
            result = call_search_api(query)
            return {
                'success': result.get('success', False),
                'message': result.get('message', '搜索完成'),
                'data': {'robot': robot_name, 'action': action, 'params': kwargs, 'search_result': result.get('data', {})}
            }
        
        elif robot_name == '组织管理':
            # 组织管理支持：组织架构调整、部门管理
            print("调用组织管理机器人:", action, kwargs)
            result = call_organization(action, **kwargs)
            return {
                'success': True,
                'message': f'组织管理操作完成',
                'data': {'robot': robot_name, 'action': action, 'params': kwargs, 'result': result}
            }
        
        else:
            return {'success': False, 'message': f'未知机器人: {robot_name}'}
    
    except Exception as e:
        return {'success': False, 'message': f'机器人调用失败: {str(e)}'}


def call_table_tool(action: str, **kwargs) -> dict:
    """
    表格处理工具统一入口
    
    Args:
        action: 操作类型，可选值: 'table_view', 'table_create', 'table_delete', 'table_add_row', 
                'table_delete_row', 'table_add_column', 'table_delete_column',
                'table_statistics', 'table_chart', 'table_export', 'table_filter'
        **kwargs: 额外参数
    
    Returns:
        dict: 操作结果，包含 success、message 和 data 字段
    """
    try:
        # 获取表格数据（从kwargs或会话中）
        table_data = kwargs.get('table_data')
        
        if action == 'table_view':
            # 查看表格 - 直接返回表格数据
            if table_data and table_data.get('headers'):
                return {
                    'success': True,
                    'message': '表格查看成功',
                    'table_data': table_data
                }
            else:
                return {'success': False, 'message': '表格数据为空或无效'}
        
        elif action == 'table_create':
            headers = kwargs.get('headers', [])
            data = kwargs.get('data', [])
            table_name = kwargs.get('table_name')
            return create_table(headers, data, table_name)
        
        elif action == 'table_delete':
            return delete_table(table_data)
        
        elif action == 'table_add_row':
            row_data = kwargs.get('row_data', [])
            position = kwargs.get('position')
            return add_row(table_data, row_data, position)
        
        elif action == 'table_delete_row':
            row_index = kwargs.get('row_index', 0)
            return delete_row(table_data, row_index)
        
        elif action == 'table_add_column':
            column_name = kwargs.get('column_name', '')
            column_data = kwargs.get('column_data', [])
            default_value = kwargs.get('default_value')
            return add_column(table_data, column_name, column_data, default_value)
        
        elif action == 'table_delete_column':
            column_name = kwargs.get('column_name', '')
            return delete_column(table_data, column_name)
        
        elif action == 'table_statistics':
            column_name = kwargs.get('column_name')
            return calculate_statistics(table_data, column_name)
        
        elif action == 'table_chart':
            chart_type = kwargs.get('chart_type', 'bar')
            x_column = kwargs.get('x_column')
            y_column = kwargs.get('y_column')
            title = kwargs.get('title')
            width = kwargs.get('width', 800)
            height = kwargs.get('height', 600)
            # 如果未指定列，调用 AI 推荐最合适的列
            if not x_column or not y_column:
                ai_suggestion = _ask_ai_for_chart_columns(table_data, chart_type)
                if ai_suggestion:
                    x_column = x_column or ai_suggestion.get('x_column')
                    y_column = y_column or ai_suggestion.get('y_column')
                    if not title:
                        title = ai_suggestion.get('title')
            return generate_chart(table_data, chart_type, x_column, y_column, title, width, height)
        
        elif action == 'table_export':
            export_format = kwargs.get('format', 'csv')
            filename = kwargs.get('filename')
            return export_table(table_data, export_format, filename)
        
        elif action == 'table_filter':
            filter_conditions = kwargs.get('filter_conditions', {})
            return filter_table(table_data, filter_conditions)
        
        else:
            return {'success': False, 'message': f'不支持的表格操作: {action}'}
    
    except Exception as e:
        return {'success': False, 'message': f'表格操作失败: {str(e)}'}


def get_task_status(task_id: str, task_type: str = 'image', user_id: str = None) -> dict:
    """
    查询异步任务状态，任务完成时自动下载文件并保存到指定目录
    
    Args:
        task_id: 任务ID
        task_type: 任务类型，'image' 或 'video'
        user_id: 用户ID（可选，用于保存历史记录）
    
    Returns:
        dict: 包含 success、message、data 字段
    """
    try:
        api_key = os.getenv('QWEN_API_KEY') or os.getenv('API_KEY')
        
        if not api_key:
            return {
                'success': False,
                'message': '通义千问 API 配置未设置'
            }
        
        # 根据任务类型选择不同的API端点
        if task_type == 'image':
            url = f'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
        elif task_type == 'video':
            url = f'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
        else:
            return {
                'success': False,
                'message': f'不支持的任务类型: {task_type}'
            }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            
            # 打印调试日志
            print(f"[调试] 任务状态查询响应: {result}")
            
            # 检查是否有错误
            if 'code' in result and result['code'] != '200':
                return {
                    'success': False,
                    'message': result.get('message', '查询任务状态失败'),
                    'data': result
                }
            
            # 解析任务状态
            output = result.get('output', {})
            task_status = output.get('task_status', 'UNKNOWN')
            
            print(f"[调试] 任务状态: {task_status}, output: {output}")
            
            if task_status == 'SUCCEEDED':
                # 提取结果
                results = output.get('results', [])
                
                if task_type == 'image':
                    items = []
                    for r in results:
                        if 'url' in r:
                            download_result = download_file(r['url'], PHOTO_DIR)
                            if download_result['success']:
                                items.append({
                                    'url': r.get('url'),
                                    'local_url': f"/media/photo/{download_result['filename']}",
                                    'revised_prompt': r.get('prompt', ''),
                                    'local_path': download_result['file_path'],
                                    'filename': download_result['filename']
                                })
                                if user_id:
                                    save_to_database(user_id, r.get('prompt', ''), 'image', download_result['file_path'])
                            else:
                                items.append({
                                    'url': r.get('url'),
                                    'revised_prompt': r.get('prompt', ''),
                                    'error': download_result['message']
                                })
                    return {
                        'success': True,
                        'message': '任务完成',
                        'data': {
                            'task_id': task_id,
                            'task_status': task_status,
                            'images': items,
                            'async': False
                        }
                    }
                elif task_type == 'video':
                    items = []
                    for r in results:
                        if 'url' in r:
                            download_result = download_file(r['url'], VIDEO_DIR)
                            if download_result['success']:
                                items.append({
                                    'url': r.get('url'),
                                    'local_url': f"/media/video/{download_result['filename']}",
                                    'duration': r.get('duration', 0),
                                    'resolution': r.get('resolution', '720p'),
                                    'local_path': download_result['file_path'],
                                    'filename': download_result['filename']
                                })
                                if user_id:
                                    save_to_database(user_id, r.get('prompt', ''), 'video', download_result['file_path'])
                            else:
                                items.append({
                                    'url': r.get('url'),
                                    'duration': r.get('duration', 0),
                                    'resolution': r.get('resolution', '720p'),
                                    'error': download_result['message']
                                })
                    return {
                        'success': True,
                        'message': '任务完成',
                        'data': {
                            'task_id': task_id,
                            'task_status': task_status,
                            'videos': items,
                            'async': False
                        }
                    }
            elif task_status in ['PENDING', 'RUNNING', 'UNKNOWN']:
                # UNKNOWN状态可能表示任务正在初始化，继续轮询
                return {
                    'success': True,
                    'message': '任务处理中',
                    'data': {
                        'task_id': task_id,
                        'task_status': task_status,
                        'async': True
                    }
                }
            elif task_status == 'FAILED':
                return {
                    'success': False,
                    'message': '任务失败',
                    'data': {
                        'task_id': task_id,
                        'task_status': task_status,
                        'error': output.get('message', '未知错误'),
                        'details': output
                    }
                }
            else:
                # 处理其他未知状态，返回原始数据但标记为成功以便继续轮询
                return {
                    'success': True,
                    'message': f'任务状态: {task_status}',
                    'data': {
                        'task_id': task_id,
                        'task_status': task_status,
                        'async': True,
                        'raw_data': result
                    }
                }
        else:
            return {
                'success': False,
                'message': f'查询失败，状态码: {response.status_code}',
                'data': response.text
            }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'查询任务状态失败: {str(e)}'
        }


def generate_image(prompt: str, **kwargs) -> dict:
    """
    文生图函数 - 使用通义千问API生成图片，生成后自动下载到本地并保存到数据库
    
    Args:
        prompt: 图片描述文本
        **kwargs: 额外参数
            - size: 图片尺寸，可选值: '1024*1024', '720*1280', '1280*720'，默认 '1024*1024'
            - n: 生成图片数量，默认 1
            - model: 使用的模型，默认 'qwen-vl-max'
            - seed: 随机种子，用于生成确定性结果
            - user_id: 用户ID（可选，用于保存历史记录）
    
    Returns:
        dict: 包含 success、message、data 字段
            - success: 是否成功
            - message: 结果消息
            - data: 生成的图片数据，包含 images 数组（含本地路径）
    """
    try:
        # 从环境变量获取 API 配置
        api_key = os.getenv('QWEN_API_KEY') or os.getenv('API_KEY')
        user_id = kwargs.get('user_id')
        
        if not api_key:
            return {
                'success': False,
                'message': '通义千问 API 配置未设置，请在 .env 文件中配置 QWEN_API_KEY'
            }
        
        # 获取参数
        size = kwargs.get('size', '1024*1024')
        n = kwargs.get('n', 1)
        model = kwargs.get('model', 'wanx-v1')  # 默认 wanx-v1
        seed = kwargs.get('seed')
        
        if not prompt or len(prompt.strip()) < 2:
            return {
                'success': False,
                'message': '请输入图片描述文本，至少2个字符'
            }
        
        # 通义千问文生图 API
        url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable'  # 必须使用异步模式
        }
        
        # 构建请求体（通义千问格式）
        # 支持的尺寸格式: '1024*1024', '720*1280', '1280*720'
        valid_sizes = ['1024*1024', '720*1280', '1280*720']
        formatted_size = size.replace('*', 'x').replace('1024x1024', '1024*1024').replace('720x1280', '720*1280').replace('1280x720', '1280*720')
        if formatted_size not in valid_sizes:
            formatted_size = '1024*1024'
        
        payload = {
            'model': model,  # 使用透传的 model，默认 wanx-v1
            'input': {
                'prompt': prompt.strip()
            },
            'parameters': {
                'size': formatted_size,
                'n': n
            }
        }
        
        if seed is not None:
            payload['parameters']['seed'] = seed
        
        # 发送请求
        response = requests.post(url, headers=headers, json=payload, timeout=60, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            
            # 检查是否有错误
            if 'code' in result and result['code'] != '200':
                return {
                    'success': False,
                    'message': result.get('message', '图片生成失败'),
                    'data': result
                }
            
            # 检查是否是异步任务
            if 'output' in result and 'task_id' in result['output']:
                task_id = result['output']['task_id']
                task_status = result['output'].get('task_status', 'PENDING')
                
                # 如果任务还在处理中（包括UNKNOWN状态），返回任务ID供后续查询
                if task_status == 'PENDING' or task_status == 'RUNNING' or task_status == 'UNKNOWN':
                    return {
                        'success': True,
                        'message': '图片生成任务已提交，正在处理中',
                        'data': {
                            'task_id': task_id,
                            'task_status': task_status,
                            'model': 'wanx-v1',
                            'prompt': prompt,
                            'size': size,
                            'async': True
                        }
                    }
                
                # 如果任务已完成，尝试获取结果并下载图片
                if task_status == 'SUCCEEDED' and 'results' in result['output']:
                    images = []
                    for item in result['output']['results']:
                        if 'url' in item:
                            # 下载图片到本地
                            download_result = download_file(item['url'], PHOTO_DIR)
                            if download_result['success']:
                                images.append({
                                    'url': item['url'],
                                    'local_url': f"/media/photo/{download_result['filename']}",
                                    'revised_prompt': item.get('prompt', prompt),
                                    'local_path': download_result['file_path'],
                                    'filename': download_result['filename']
                                })
                                # 保存到数据库
                                if user_id:
                                    save_to_database(user_id, item.get('prompt', prompt), 'image', download_result['file_path'])
                            else:
                                images.append({
                                    'url': item['url'],
                                    'revised_prompt': item.get('prompt', prompt),
                                    'error': download_result['message']
                                })
                    
                    if images:
                        return {
                            'success': True,
                            'message': f'成功生成 {len(images)} 张图片',
                            'data': {
                                'images': images,
                                'model': 'wanx-v1',
                                'prompt': prompt,
                                'size': size,
                                'async': False
                            }
                        }
            
            # 处理其他情况
            return {
                'success': False,
                'message': '无法解析API响应',
                'data': result
            }
        else:
            return {
                'success': False,
                'message': f'图片生成失败，状态码: {response.status_code}',
                'data': response.text
            }
    
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'网络请求失败: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'文生图调用失败: {str(e)}'
        }


def generate_video(prompt: str, **kwargs) -> dict:
    """
    文生视频函数 - 使用通义千问API生成视频，生成后自动下载到本地并保存到数据库
    
    Args:
        prompt: 视频描述文本
        **kwargs: 额外参数
            - duration: 视频时长（秒），默认 5
            - fps: 帧率，默认 24
            - resolution: 视频分辨率，可选值: '720p', '1080p'，默认 '720p'
            - model: 使用的模型，默认 'qwen-vl-max'
            - seed: 随机种子，用于生成确定性结果
            - user_id: 用户ID（可选，用于保存历史记录）
    
    Returns:
        dict: 包含 success、message、data 字段
            - success: 是否成功
            - message: 结果消息
            - data: 生成的视频数据，包含 videos 数组（含本地路径）
    """
    try:
        # 从环境变量获取 API 配置
        api_key = os.getenv('QWEN_API_KEY') or os.getenv('API_KEY')
        user_id = kwargs.get('user_id')
        
        if not api_key:
            return {
                'success': False,
                'message': '通义千问 API 配置未设置，请在 .env 文件中配置 QWEN_API_KEY'
            }
        
        # 获取参数
        duration = kwargs.get('duration', 5)
        fps = kwargs.get('fps', 24)
        resolution = kwargs.get('resolution', '720p')
        model = kwargs.get('model', 'wanx-v1')  # 默认 wanx-v1
        seed = kwargs.get('seed')
        
        if not prompt or len(prompt.strip()) < 2:
            return {
                'success': False,
                'message': '请输入视频描述文本，至少2个字符'
            }
        
        # 通义千问文生视频 API
        url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable'
        }
        
        # 构建请求体（通义千问格式）
        payload = {
            'model': model,  # 使用透传的 model，默认 wanx-v1
            'input': {
                'prompt': prompt.strip()
            },
            'parameters': {
                'duration': duration,
                'fps': fps,
                'resolution': resolution
            }
        }
        
        if seed is not None:
            payload['parameters']['seed'] = seed
        
        # 发送请求
        response = requests.post(url, headers=headers, json=payload, timeout=120, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            
            # 检查是否有错误
            if 'code' in result and result['code'] != '200':
                return {
                    'success': False,
                    'message': result.get('message', '视频生成失败'),
                    'data': result
                }
            
            # 检查是否是异步任务
            if 'output' in result and 'task_id' in result['output']:
                task_id = result['output']['task_id']
                task_status = result['output'].get('task_status', 'PENDING')
                
                # 如果任务还在处理中（包括UNKNOWN状态），返回任务ID供后续查询
                if task_status == 'PENDING' or task_status == 'RUNNING' or task_status == 'UNKNOWN':
                    return {
                        'success': True,
                        'message': '视频生成任务已提交，正在处理中',
                        'data': {
                            'task_id': task_id,
                            'task_status': task_status,
                            'model': model,
                            'prompt': prompt,
                            'duration': duration,
                            'resolution': resolution,
                            'async': True
                        }
                    }
                
                # 如果任务已完成，尝试获取结果并下载视频
                if task_status == 'SUCCEEDED' and 'results' in result['output']:
                    videos = []
                    for item in result['output']['results']:
                        if 'url' in item:
                            download_result = download_file(item['url'], VIDEO_DIR)
                            if download_result['success']:
                                videos.append({
                                    'url': item['url'],
                                    'local_url': f"/media/video/{download_result['filename']}",
                                    'duration': item.get('duration', duration),
                                    'resolution': item.get('resolution', resolution),
                                    'local_path': download_result['file_path'],
                                    'filename': download_result['filename']
                                })
                                if user_id:
                                    save_to_database(user_id, prompt, 'video', download_result['file_path'])
                            else:
                                videos.append({
                                    'url': item['url'],
                                    'duration': item.get('duration', duration),
                                    'resolution': item.get('resolution', resolution),
                                    'error': download_result['message']
                                })
                    
                    if videos:
                        return {
                            'success': True,
                            'message': f'成功生成 {len(videos)} 个视频',
                            'data': {
                                'videos': videos,
                                'model': model,
                                'prompt': prompt,
                                'duration': duration,
                                'resolution': resolution,
                                'async': False
                            }
                        }
            
            # 提取生成的视频URL（同步模式）
            videos = []
            if 'output' in result and 'results' in result['output']:
                for item in result['output']['results']:
                    if 'url' in item:
                        download_result = download_file(item['url'], VIDEO_DIR)
                        if download_result['success']:
                            videos.append({
                                'url': item['url'],
                                'local_url': f"/media/video/{download_result['filename']}",
                                'duration': item.get('duration', duration),
                                'resolution': item.get('resolution', resolution),
                                'local_path': download_result['file_path'],
                                'filename': download_result['filename']
                            })
                            if user_id:
                                save_to_database(user_id, prompt, 'video', download_result['file_path'])
                        else:
                            videos.append({
                                'url': item['url'],
                                'duration': item.get('duration', duration),
                                'resolution': item.get('resolution', resolution),
                                'error': download_result['message']
                            })
            
            if videos:
                return {
                    'success': True,
                    'message': f'成功生成 {len(videos)} 个视频',
                    'data': {
                        'videos': videos,
                        'model': model,
                        'prompt': prompt,
                        'duration': duration,
                        'resolution': resolution
                    }
                }
            else:
                return {
                    'success': False,
                    'message': '视频生成成功但未返回视频URL',
                    'data': result
                }
        else:
            return {
                'success': False,
                'message': f'视频生成失败，状态码: {response.status_code}',
                'data': response.text
            }
    
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'网络请求失败: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'文生视频调用失败: {str(e)}'
        }


if __name__ == '__main__':
    # 测试示例
    print("=== 测试机器人调用 ===")
    
    # 测试 AI助手 - 添加组织
    org_result = call_robot('AI助手', 'add', name='技术部', parent_id='', description='技术研发部门')
    print("AI助手添加组织:", json.dumps(org_result, ensure_ascii=False))
    
    # 测试 AI助手 - 调整组织架构
    adjust_result = call_robot('AI助手', 'adjust', org_id=org_result['data']['id'], new_name='研发部')
    print("AI助手调整组织:", json.dumps(adjust_result, ensure_ascii=False))
    
    # 测试 知识库 - 获取列表
    kb_result = call_robot('知识库', 'list')
    print("知识库列表:", json.dumps(kb_result, ensure_ascii=False))
    
    # 测试 AI助手 - 更新用户信息
    user_result = call_robot('AI助手', 'user_update', user_id='1', nickname='测试用户', email='test@example.com')
    print("AI助手更新用户:", json.dumps(user_result, ensure_ascii=False))


# ========== 表格处理函数 ==========

def create_table(headers: list, data: list = None, table_name: str = None) -> dict:
    """
    创建表格
    
    Args:
        headers: 表头列表，如 ['姓名', '年龄', '部门']
        data: 表格数据，二维列表，如 [['张三', 25, '技术部'], ['李四', 30, '市场部']]
        table_name: 表格名称（可选）
    
    Returns:
        dict: 包含 success、message、table_data 字段
    """
    try:
        import pandas as pd
        
        if not headers:
            return {'success': False, 'message': '表头不能为空'}
        
        if data is None:
            data = []
        
        # 创建DataFrame
        df = pd.DataFrame(data, columns=headers)
        
        # 生成表格数据
        table_data = {
            'headers': headers,
            'rows': data,
            'row_count': len(data),
            'col_count': len(headers),
            'table_name': table_name or f"表格_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        return {
            'success': True,
            'message': '表格创建成功',
            'table_data': table_data
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'表格创建失败: {str(e)}'
        }


def delete_table(table_data: dict) -> dict:
    """
    删除表格
    
    Args:
        table_data: 表格数据字典
    
    Returns:
        dict: 包含 success、message 字段
    """
    try:
        if not table_data or 'table_name' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        table_name = table_data['table_name']
        
        return {
            'success': True,
            'message': f'表格 "{table_name}" 删除成功',
            'deleted_table': table_name
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'表格删除失败: {str(e)}'
        }


def add_row(table_data: dict, row_data: list, position: int = None) -> dict:
    """
    添加行到表格
    
    Args:
        table_data: 表格数据字典
        row_data: 行数据列表，如 ['王五', 28, '财务部']
        position: 插入位置（可选，默认添加到末尾）
    
    Returns:
        dict: 包含 success、message、table_data 字段
    """
    try:
        if not table_data or 'headers' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        headers = table_data['headers']
        rows = table_data.get('rows', [])
        
        # 检查行数据长度是否匹配表头
        if len(row_data) != len(headers):
            return {'success': False, 'message': f'行数据长度({len(row_data)})与表头数量({len(headers)})不匹配'}
        
        # 插入行
        if position is None or position >= len(rows):
            rows.append(row_data)
        else:
            rows.insert(position, row_data)
        
        # 更新表格数据
        table_data['rows'] = rows
        table_data['row_count'] = len(rows)
        
        return {
            'success': True,
            'message': f'行添加成功（位置: {position if position is not None else len(rows)-1}）',
            'table_data': table_data
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'添加行失败: {str(e)}'
        }


def delete_row(table_data: dict, row_index: int) -> dict:
    """
    从表格删除行
    
    Args:
        table_data: 表格数据字典
        row_index: 要删除的行索引（从0开始）
    
    Returns:
        dict: 包含 success、message、table_data 字段
    """
    try:
        if not table_data or 'rows' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        rows = table_data['rows']
        
        # 检查行索引是否有效
        if row_index < 0 or row_index >= len(rows):
            return {'success': False, 'message': f'行索引 {row_index} 超出范围（0-{len(rows)-1}）'}
        
        # 删除行
        deleted_row = rows.pop(row_index)
        
        # 更新表格数据
        table_data['rows'] = rows
        table_data['row_count'] = len(rows)
        
        return {
            'success': True,
            'message': f'行删除成功（索引: {row_index}）',
            'deleted_row': deleted_row,
            'table_data': table_data
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'删除行失败: {str(e)}'
        }


def add_column(table_data: dict, column_name: str, column_data: list = None, default_value: any = None) -> dict:
    """
    添加列到表格
    
    Args:
        table_data: 表格数据字典
        column_name: 列名
        column_data: 列数据列表（可选）
        default_value: 默认值（当列数据不足时使用）
    
    Returns:
        dict: 包含 success、message、table_data 字段
    """
    try:
        if not table_data or 'headers' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        headers = table_data['headers']
        rows = table_data.get('rows', [])
        
        # 检查列名是否已存在
        if column_name in headers:
            return {'success': False, 'message': f'列名 "{column_name}" 已存在'}
        
        # 添加列名
        headers.append(column_name)
        
        # 添加列数据
        if column_data is None:
            column_data = []
        
        for i in range(len(rows)):
            if i < len(column_data):
                rows[i].append(column_data[i])
            else:
                rows[i].append(default_value if default_value is not None else '')
        
        # 更新表格数据
        table_data['headers'] = headers
        table_data['rows'] = rows
        table_data['col_count'] = len(headers)
        
        return {
            'success': True,
            'message': f'列添加成功（列名: {column_name}）',
            'table_data': table_data
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'添加列失败: {str(e)}'
        }


def delete_column(table_data: dict, column_name: str) -> dict:
    """
    从表格删除列
    
    Args:
        table_data: 表格数据字典
        column_name: 要删除的列名
    
    Returns:
        dict: 包含 success、message、table_data 字段
    """
    try:
        if not table_data or 'headers' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        headers = table_data['headers']
        rows = table_data.get('rows', [])
        
        # 检查列名是否存在
        if column_name not in headers:
            return {'success': False, 'message': f'列名 "{column_name}" 不存在'}
        
        # 获取列索引
        col_index = headers.index(column_name)
        
        # 删除列名
        headers.pop(col_index)
        
        # 删除每行的对应列数据
        for row in rows:
            if col_index < len(row):
                row.pop(col_index)
        
        # 更新表格数据
        table_data['headers'] = headers
        table_data['rows'] = rows
        table_data['col_count'] = len(headers)
        
        return {
            'success': True,
            'message': f'列删除成功（列名: {column_name}）',
            'deleted_column': column_name,
            'table_data': table_data
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'删除列失败: {str(e)}'
        }


def calculate_statistics(table_data: dict, column_name: str = None) -> dict:
    """
    计算表格统计信息
    
    Args:
        table_data: 表格数据字典
        column_name: 要统计的列名（可选，不指定则统计所有数值列）
    
    Returns:
        dict: 包含 success、message、statistics 字段
    """
    try:
        import pandas as pd
        import numpy as np
        
        if not table_data or 'rows' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        headers = table_data['headers']
        rows = table_data.get('rows', [])
        
        if not rows:
            return {'success': False, 'message': '表格为空，无法计算统计信息'}
        
        # 创建DataFrame
        df = pd.DataFrame(rows, columns=headers)
        
        # 选择要统计的列
        if column_name:
            if column_name not in headers:
                return {'success': False, 'message': f'列名 "{column_name}" 不存在'}
            columns_to_analyze = [column_name]
        else:
            # 自动选择数值列
            columns_to_analyze = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not columns_to_analyze:
            return {'success': False, 'message': '没有可统计的数值列'}
        
        # 计算统计信息
        statistics = {}
        for col in columns_to_analyze:
            try:
                col_data = pd.to_numeric(df[col], errors='coerce').dropna()
                if len(col_data) > 0:
                    statistics[col] = {
                        'count': int(len(col_data)),
                        'mean': float(col_data.mean()),
                        'median': float(col_data.median()),
                        'std': float(col_data.std()),
                        'min': float(col_data.min()),
                        'max': float(col_data.max()),
                        'sum': float(col_data.sum()),
                        'q25': float(col_data.quantile(0.25)),
                        'q75': float(col_data.quantile(0.75))
                    }
            except Exception as e:
                print(f"统计列 {col} 失败: {e}")
                continue
        
        return {
            'success': True,
            'message': f'统计计算成功（{len(statistics)} 个数值列）',
            'statistics': statistics,
            'analyzed_columns': columns_to_analyze
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'统计计算失败: {str(e)}'
        }


def _simplify_pie_data(values, labels, max_sectors=10, min_percent=2):
    """
    简化饼图数据：限制扇区数量，合并小比例数据为"其他"
    
    Args:
        values: 数值序列
        labels: 标签序列
        max_sectors: 最大扇区数量
        min_percent: 最小百分比阈值（低于此值的合并为"其他"）
    
    Returns:
        tuple: (简化后的values, 简化后的labels)
    """
    import pandas as pd
    
    total = values.sum()
    if total == 0:
        return values, labels
    
    # 计算百分比并排序
    percentages = (values / total) * 100
    sorted_indices = percentages.sort_values(ascending=False).index
    
    sorted_values = values[sorted_indices]
    sorted_labels = labels[sorted_indices]
    
    # 筛选出百分比 >= min_percent 的数据
    large_sectors = sorted_values[percentages[sorted_indices] >= min_percent]
    large_labels = sorted_labels[percentages[sorted_indices] >= min_percent]
    
    # 如果数量超过 max_sectors，只取前 max_sectors-1 个
    if len(large_sectors) > max_sectors:
        large_sectors = large_sectors[:max_sectors-1]
        large_labels = large_labels[:max_sectors-1]
    
    # 计算剩余部分的总和
    remaining_sum = values.sum() - large_sectors.sum()
    
    if remaining_sum > 0 and len(large_sectors) > 0:
        # 使用 pd.concat 替代已弃用的 Series.append()
        other_series = pd.Series([remaining_sum], index=['其他'])
        large_sectors = pd.concat([large_sectors, other_series])
        other_labels = pd.Series(['其他'], index=['其他'])
        large_labels = pd.concat([large_labels, other_labels])
    
    return large_sectors, large_labels


def _ask_ai_for_chart_columns(table_data: dict, chart_type: str = 'bar') -> dict:
    """
    将表格列名和类型信息发给 AI，让模型推荐最合适的 x_column 和 y_column。
    返回格式: {'x_column': '...', 'y_column': '...', 'title': '...'}
    """
    try:
        import pandas as pd
        import json
        import requests
        import os
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
        api_key = os.getenv('API_KEY') or os.getenv('QWEN_API_KEY')
        if not api_key:
            return None

        headers_list = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        if not headers_list or not rows:
            return None

        # 构建列信息摘要（strip 列名以去除制表符等空白字符）
        df = pd.DataFrame(rows, columns=headers_list)
        # 建立 strip 后列名 -> 原始列名 的映射，用于验证 AI 返回结果
        strip_to_orig = {col.strip(): col for col in headers_list}
        stripped_headers = list(strip_to_orig.keys())

        col_info = []
        for col in headers_list:
            stripped_col = col.strip()
            # 判断类型
            numeric_vals = pd.to_numeric(df[col], errors='coerce').dropna()
            total = len(df[col].dropna())
            if len(numeric_vals) / max(total, 1) >= 0.7:
                dtype = 'numeric'
                sample = str(numeric_vals.iloc[0]) if len(numeric_vals) > 0 else ''
                unique_count = int(numeric_vals.nunique())
            else:
                dtype = 'text'
                sample = str(df[col].iloc[0]) if len(df[col]) > 0 else ''
                unique_count = int(df[col].nunique())
            col_info.append({
                'name': stripped_col,  # 传给 AI 的是 strip 后的列名
                'type': dtype,
                'unique_count': unique_count,
                'row_count': total,
                'sample': sample[:30]
            })

        chart_type_zh = {'bar': '柱状图', 'line': '折线图', 'pie': '饼图', 'scatter': '散点图', 'histogram': '直方图'}.get(chart_type, chart_type)

        prompt = (
            f"我有一个表格，需要生成{chart_type_zh}。"
            f"以下是表格列信息（共{len(headers_list)}列，{len(rows)}行）\n"
            + "".join(
                f"- 列名：{c['name']}，类型：{c['type']}，唯一値：{c['unique_count']}个，样例：{c['sample']}\n"
                for c in col_info
            )
            + f"\n请分析哪些列适合作为{chart_type_zh}的X轴和Y轴（或饼图的标签列和数値列）。"
            u"必须以JSON格式返回，格式为："
            u'{"x_column": "列名", "y_column": "列名", "title": "图表标题"}，'
            u'只返回JSON，不要其他解释。'
        )

        base_url = os.getenv('BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions')
        resp = requests.post(
            base_url,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'qwen-turbo',
                'messages': [
                    {'role': 'system', 'content': '你是数据分析专家，擅长判断表格列的语义和适用场景。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1,
                'max_tokens': 200
            },
            timeout=15,
            verify=False
        )
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content'].strip()
            # 提取JSON内容
            import re
            m = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if m:
                suggestion = json.loads(m.group(0))
                # 验证列名：AI返回的是 strip 后的列名，需映射回原始带空白的列名
                x_stripped = suggestion.get('x_column', '').strip()
                y_stripped = suggestion.get('y_column', '').strip()
                suggestion['x_column'] = strip_to_orig.get(x_stripped) or (x_stripped if x_stripped in headers_list else None)
                suggestion['y_column'] = strip_to_orig.get(y_stripped) or (y_stripped if y_stripped in headers_list else None)
                print(f'[AI列推荐] chart_type={chart_type}, suggestion={suggestion}')
                return suggestion
        return None
    except Exception as e:
        print(f'[AI列推荐失败] {e}')
        return None


def generate_chart(table_data: dict, chart_type: str = 'bar', x_column: str = None, y_column: str = None, 
                   title: str = None, width: int = 800, height: int = 600) -> dict:
    """
    生成统计图表
    
    Args:
        table_data: 表格数据字典
        chart_type: 图表类型，可选 'bar', 'line', 'pie', 'scatter', 'histogram'
        x_column: X轴列名
        y_column: Y轴列名
        title: 图表标题
        width: 图表宽度（像素）
        height: 图表高度（像素）
    
    Returns:
        dict: 包含 success、message、chart_image 字段
    """
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        if not table_data or 'rows' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        headers_raw = table_data['headers']
        rows = table_data.get('rows', [])
        
        if not rows:
            return {'success': False, 'message': '表格为空，无法生成图表'}
        
        # 创建DataFrame，并对列名 strip 去除制表符等空白字符
        df = pd.DataFrame(rows, columns=headers_raw)
        df.columns = [c.strip() for c in df.columns]
        headers = list(df.columns)
        
        # 对传入的列名也 strip，确保匹配
        if x_column:
            x_column = x_column.strip()
        if y_column:
            y_column = y_column.strip()
        
        # 自动检测数值列和非数值列
        numeric_cols = []
        non_numeric_cols = []
        for col in headers:
            try:
                test_values = pd.to_numeric(df[col], errors='coerce')
                if test_values.dropna().shape[0] > 0:
                    numeric_cols.append(col)
                else:
                    non_numeric_cols.append(col)
            except:
                non_numeric_cols.append(col)
        
        # 将数值列转换为数值类型
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(width/100, height/100))
        
        # 根据数据量动态调整图表宽度
        if len(rows) > 20:
            fig.set_size_inches(min(width/100 + len(rows)/5, 30), height/100)
        
        # 根据图表类型绘制
        if chart_type == 'bar':
            if x_column and y_column:
                if x_column in headers and y_column in headers:
                    df[y_column] = pd.to_numeric(df[y_column], errors='coerce')
                    df.plot.bar(x=x_column, y=y_column, ax=ax)
                else:
                    return {'success': False, 'message': '指定的列名不存在'}
            else:
                if numeric_cols:
                    x_col = non_numeric_cols[0] if non_numeric_cols else headers[0]
                    y_col = numeric_cols[0]
                    df.plot.bar(x=x_col, y=y_col, ax=ax)
                elif len(headers) >= 2:
                    df.plot.bar(x=headers[0], y=headers[1], ax=ax)
                else:
                    return {'success': False, 'message': '表格列数不足，无法生成柱状图'}
            # 旋转X轴标签避免重叠
            plt.xticks(rotation=45, ha='right', fontsize=8)
        
        elif chart_type == 'line':
            if x_column and y_column:
                if x_column in headers and y_column in headers:
                    df[y_column] = pd.to_numeric(df[y_column], errors='coerce')
                    df.plot.line(x=x_column, y=y_column, ax=ax)
                else:
                    return {'success': False, 'message': '指定的列名不存在'}
            else:
                if numeric_cols:
                    x_col = non_numeric_cols[0] if non_numeric_cols else headers[0]
                    y_col = numeric_cols[0]
                    df.plot.line(x=x_col, y=y_col, ax=ax)
                elif len(headers) >= 2:
                    df.plot.line(x=headers[0], y=headers[1], ax=ax)
                else:
                    return {'success': False, 'message': '表格列数不足，无法生成折线图'}
            # 旋转X轴标签避免重叠
            plt.xticks(rotation=45, ha='right', fontsize=8)
        
        elif chart_type == 'pie':
            if y_column:
                if y_column in headers:
                    try:
                        values = pd.to_numeric(df[y_column], errors='coerce').dropna()
                        labels = df.get(x_column, df.index) if x_column else df.index
                        labels = labels[values.index]
                        
                        values, labels = _simplify_pie_data(values, labels)
                        
                        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
                        ax.axis('equal')
                    except:
                        return {'success': False, 'message': f'列 "{y_column}" 无法转换为数值'}
                else:
                    return {'success': False, 'message': '指定的列名不存在'}
            else:
                # 自动选择数值列 - 优先语义上更合适做饮图的列（不是ID类高重复列）
                y_column = None
                _prefer_kw = ['金额', '数量', '总计', '汇总', '小计', '价貎', '价格', '收入', '支出', '利润', '成本', '销售', '财务']
                _avoid_kw = ['代码', '编号', 'id', 'ID', '号码', '编码', '类型', '日期']
                # 第一轮：优先关键词匹配的数值列
                for col in headers:
                    if any(k in col for k in _avoid_kw):
                        continue
                    if any(k in col for k in _prefer_kw):
                        try:
                            v = pd.to_numeric(df[col], errors='coerce')
                            if v.dropna().shape[0] > 0 and v.sum() != 0:
                                y_column = col
                                break
                        except:
                            pass
                # 第二轮：任意数值列（跳过ID类，跳过唯一値超过90%的列）
                if y_column is None:
                    for col in headers:
                        if any(k in col for k in _avoid_kw):
                            continue
                        try:
                            v = pd.to_numeric(df[col], errors='coerce').dropna()
                            if v.shape[0] > 0 and v.sum() != 0:
                                unique_ratio = v.nunique() / len(v)
                                if unique_ratio < 0.9:  # 过于唯一的列可能ID
                                    y_column = col
                                    break
                        except:
                            continue
                # 第三轮：如果还是没有，取任意非零数值列
                if y_column is None:
                    for col in headers:
                        try:
                            v = pd.to_numeric(df[col], errors='coerce').dropna()
                            if v.shape[0] > 0 and v.sum() != 0:
                                y_column = col
                                break
                        except:
                            continue
                
                if y_column:
                    try:
                        values = pd.to_numeric(df[y_column], errors='coerce').dropna()
                        # 如果没有有效的数值，返回错误
                        if values.empty:
                            return {'success': False, 'message': f'列 "{y_column}" 没有有效的数值数据'}
                        
                        # 使用第一列作为标签（如果第一列不是数值列）
                        if headers[0] != y_column:
                            labels = df[headers[0]]
                        else:
                            labels = df.index
                        labels = labels[values.index]
                        
                        values, labels = _simplify_pie_data(values, labels)
                        
                        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
                        ax.axis('equal')
                    except Exception as e:
                        return {'success': False, 'message': f'自动选择的列 "{y_column}" 无法转换为数值: {str(e)}'}
                else:
                    return {'success': False, 'message': '饼图需要指定数值列或表格中需要有数值列'}
        
        elif chart_type == 'scatter':
            if x_column and y_column:
                if x_column in headers and y_column in headers:
                    df[x_column] = pd.to_numeric(df[x_column], errors='coerce')
                    df[y_column] = pd.to_numeric(df[y_column], errors='coerce')
                    ax.scatter(df[x_column], df[y_column])
                    ax.set_xlabel(x_column)
                    ax.set_ylabel(y_column)
                else:
                    return {'success': False, 'message': '指定的列名不存在'}
            else:
                # 自动选择：需要两个数值列
                if len(numeric_cols) >= 2:
                    ax.scatter(df[numeric_cols[0]], df[numeric_cols[1]])
                    ax.set_xlabel(numeric_cols[0])
                    ax.set_ylabel(numeric_cols[1])
                elif len(headers) >= 2:
                    df[headers[0]] = pd.to_numeric(df[headers[0]], errors='coerce')
                    df[headers[1]] = pd.to_numeric(df[headers[1]], errors='coerce')
                    ax.scatter(df[headers[0]], df[headers[1]])
                    ax.set_xlabel(headers[0])
                    ax.set_ylabel(headers[1])
                else:
                    return {'success': False, 'message': '表格列数不足，无法生成散点图'}
        
        elif chart_type == 'histogram':
            if y_column:
                if y_column in headers:
                    try:
                        values = pd.to_numeric(df[y_column], errors='coerce').dropna()
                        ax.hist(values, bins=20)
                        ax.set_xlabel(y_column)
                    except:
                        return {'success': False, 'message': f'列 "{y_column}" 无法转换为数值'}
                else:
                    return {'success': False, 'message': '指定的列名不存在'}
            else:
                # 自动选择数值列
                if numeric_cols:
                    values = df[numeric_cols[0]].dropna()
                    ax.hist(values, bins=20)
                    ax.set_xlabel(numeric_cols[0])
                else:
                    return {'success': False, 'message': '没有可用的数值列'}
        
        else:
            return {'success': False, 'message': f'不支持的图表类型: {chart_type}'}
        
        # 设置标题
        if title:
            ax.set_title(title)
        else:
            ax.set_title(f'{chart_type.capitalize()} Chart')
        
        # 调整布局
        plt.tight_layout()
        
        # 转换为base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        return {
            'success': True,
            'message': f'图表生成成功（类型: {chart_type}）',
            'chart_image': f'data:image/png;base64,{img_base64}',
            'chart_type': chart_type,
            'width': width,
            'height': height
        }
    
    except ImportError as e:
        return {
            'success': False,
            'message': f'缺少必要依赖: {str(e)}，请安装 matplotlib 和 pandas'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'图表生成失败: {str(e)}'
        }


def export_table(table_data: dict, export_format: str = 'csv', filename: str = None) -> dict:
    """
    导出表格到文件
    
    Args:
        table_data: 表格数据字典
        export_format: 导出格式，可选 'csv', 'excel', 'json'
        filename: 文件名（可选）
    
    Returns:
        dict: 包含 success、message、file_path 字段
    """
    try:
        import pandas as pd
        
        if not table_data or 'rows' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        headers = table_data['headers']
        rows = table_data.get('rows', [])
        
        # 修复行列数不一致的问题
        fixed_rows = []
        for row in rows:
            # 确保每行的列数与表头一致
            if len(row) > len(headers):
                fixed_row = row[:len(headers)]
            elif len(row) < len(headers):
                fixed_row = row + [''] * (len(headers) - len(row))
            else:
                fixed_row = row
            fixed_rows.append(fixed_row)
        
        # 创建DataFrame
        df = pd.DataFrame(fixed_rows, columns=headers)
        
        # 生成文件名
        if not filename:
            table_name = table_data.get('table_name', 'table')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{table_name}_{timestamp}.{export_format}"
        
        # 确保导出目录存在
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        file_path = os.path.join(export_dir, filename)
        
        # 根据格式导出
        if export_format == 'csv':
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
        elif export_format == 'excel':
            df.to_excel(file_path, index=False, engine='openpyxl')
        elif export_format == 'json':
            df.to_json(file_path, orient='records', force_ascii=False, indent=2)
        else:
            return {'success': False, 'message': f'不支持的导出格式: {export_format}'}
        
        return {
            'success': True,
            'message': f'表格导出成功（格式: {export_format}）',
            'file_path': file_path,
            'row_count': len(fixed_rows),
            'col_count': len(headers)
        }
    except ImportError as e:
        return {
            'success': False,
            'message': f'缺少必要依赖: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'表格导出失败: {str(e)}'
        }


def filter_table(table_data: dict, filter_conditions: dict) -> dict:
    """
    过滤表格数据
    
    Args:
        table_data: 表格数据字典
        filter_conditions: 过滤条件，如 {'年龄': {'operator': '>', 'value': 25}}
                         支持的操作符: '>', '<', '>=', '<=', '==', '!=', 'contains'
    
    Returns:
        dict: 包含 success、message、filtered_table_data 字段
    """
    try:
        import pandas as pd
        
        if not table_data or 'rows' not in table_data:
            return {'success': False, 'message': '表格数据无效'}
        
        headers = table_data['headers']
        rows = table_data.get('rows', [])
        
        # 创建DataFrame
        df = pd.DataFrame(rows, columns=headers)
        
        # 应用过滤条件
        for column, condition in filter_conditions.items():
            if column not in headers:
                continue
            
            operator = condition.get('operator', '==')
            value = condition.get('value')
            
            try:
                if operator == '>':
                    df = df[pd.to_numeric(df[column], errors='coerce') > value]
                elif operator == '<':
                    df = df[pd.to_numeric(df[column], errors='coerce') < value]
                elif operator == '>=':
                    df = df[pd.to_numeric(df[column], errors='coerce') >= value]
                elif operator == '<=':
                    df = df[pd.to_numeric(df[column], errors='coerce') <= value]
                elif operator == '==':
                    df = df[df[column] == value]
                elif operator == '!=':
                    df = df[df[column] != value]
                elif operator == 'contains':
                    df = df[df[column].astype(str).str.contains(str(value), na=False)]
            except Exception as e:
                print(f"过滤条件应用失败: {e}")
                continue
        
        # 构建过滤后的表格数据
        filtered_table_data = {
            'headers': headers,
            'rows': df.values.tolist(),
            'row_count': len(df),
            'col_count': len(headers),
            'table_name': table_data.get('table_name', '') + '_filtered'
        }
        
        return {
            'success': True,
            'message': f'过滤完成（{len(df)} 行匹配条件）',
            'filtered_table_data': filtered_table_data,
            'original_count': len(rows),
            'filtered_count': len(df)
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'表格过滤失败: {str(e)}'
        }