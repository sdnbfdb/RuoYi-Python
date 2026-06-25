from flask import jsonify, request
import csv
import os
import threading

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.csv')

file_lock = threading.RLock()

def get_user_by_account(account):
    if not os.path.exists(USERS_FILE):
        return None
    
    with open(USERS_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('account') == account:
                return row
    return None

def update_user_info():
    data = request.get_json()
    
    account = data.get('account')
    name = data.get('name')
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')
    image_url = data.get('image')
    
    if not account:
        return jsonify({
            'success': False,
            'message': '账号不能为空'
        }), 400
    
    user = get_user_by_account(account)
    
    if not user:
        return jsonify({
            'success': False,
            'message': '用户不存在'
        }), 404
    
    if new_password and not confirm_password:
        return jsonify({
            'success': False,
            'message': '请确认新密码'
        }), 400
    
    if new_password and confirm_password and new_password != confirm_password:
        return jsonify({
            'success': False,
            'message': '两次输入的密码不一致'
        }), 400
    
    if new_password and len(new_password) < 6:
        return jsonify({
            'success': False,
            'message': '密码长度至少为6位'
        }), 400
    
    with file_lock:
        users = []
        with open(USERS_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            users = list(reader)
        
        updated_users = []
        for u in users:
            if u.get('account') == account:
                if name:
                    u['name'] = name
                if new_password:
                    u['password'] = new_password
                if image_url is not None:
                    u['image'] = image_url
            updated_users.append(u)
        
        with open(USERS_FILE, 'w', encoding='utf-8', newline='') as f:
            all_keys = set()
            for u in updated_users:
                all_keys.update(u.keys())
            
            fieldnames = ['id', 'username', 'account', 'password', 'name', 'created_at', 'image']
            final_fieldnames = [fn for fn in fieldnames if fn in all_keys] + [fn for fn in all_keys if fn not in fieldnames]
            
            writer = csv.DictWriter(f, fieldnames=final_fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(updated_users)
    
    updated_user = get_user_by_account(account)
    
    return jsonify({
        'success': True,
        'message': '信息更新成功',
        'data': {
            'id': int(updated_user.get('id', 0)),
            'username': updated_user.get('username', ''),
            'account': updated_user.get('account', ''),
            'name': updated_user.get('name', ''),
            'image': updated_user.get('image', '')
        }
    })

def get_user_info():
    account = request.args.get('account') or request.headers.get('X-Account', '123456')
    
    user = get_user_by_account(account)
    
    if not user:
        return jsonify({
            'success': False,
            'message': '用户不存在'
        }), 404
    
    # 获取角色级别描述
    role = user.get('role', '')
    role_level = _get_role_level(role)
    
    return jsonify({
        'success': True,
        'data': {
            'id': int(user.get('id', 0)),
            'username': user.get('username', ''),
            'account': user.get('account', ''),
            'name': user.get('name', ''),
            'image': user.get('image', ''),
            'created_at': user.get('created_at', ''),
            'role': role,
            'department': user.get('department', ''),
            'role_level': role_level
        }
    })

def _get_role_level(role):
    """根据角色编号获取角色级别描述"""
    if not role or role == '0':
        return '最高管理层'
    level = role.count('.') + 1
    descriptions = {
        1: '部门经理层',
        2: '主管层',
        3: '普通员工层'
    }
    return descriptions.get(level, f'第{level}层级')
