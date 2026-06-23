from flask import jsonify, request
from datetime import datetime
from sql.database import get_db_connection

def register():
    data = request.get_json()
    account = data.get('account')
    password = data.get('password')
    confirmPassword = data.get('confirmPassword')
    username = data.get('username', '')
    name = data.get('name', '新用户')
    
    if not account or not password or not confirmPassword:
        return jsonify({
            'success': False,
            'message': '账号、密码和确认密码不能为空'
        }), 400
    
    if len(account) != 6:
        return jsonify({
            'success': False,
            'message': '账号必须是6位数字'
        }), 400
    
    if not account.isdigit():
        return jsonify({
            'success': False,
            'message': '账号必须是数字'
        }), 400
    
    if password != confirmPassword:
        return jsonify({
            'success': False,
            'message': '两次输入的密码不一致'
        }), 400
    
    if len(password) < 6:
        return jsonify({
            'success': False,
            'message': '密码长度至少为6位'
        }), 400
    
    db = get_db_connection()
    
    # 检查账号是否存在
    query = "SELECT * FROM users WHERE username = %s"
    result = db.execute_query(query, (account,))
    if result:
        return jsonify({
            'success': False,
            'message': '账号已存在'
        }), 400
    
    # 插入新用户
    insert_query = """
        INSERT INTO users (username, password, email, department, role, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    params = (
        account,
        password,
        f'{account}@example.com',
        '总部',
        'user',
        1,
        created_at
    )
    
    user_id = db.execute_update(insert_query, params)
    
    return jsonify({
        'success': True,
        'message': '注册成功',
        'data': {
            'user': {
                'id': user_id,
                'username': username if username else f'user{account}',
                'account': account,
                'name': name
            }
        }
    })
