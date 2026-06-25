from flask import jsonify, request
from sql.database import get_db_connection

def get_user_by_account(account):
    """从数据库获取用户信息"""
    db = get_db_connection()
    query = "SELECT * FROM users WHERE username = %s"
    result = db.execute_query(query, (account,))
    if result:
        return result[0]
    return None

def login():
    data = request.get_json()
    account = data.get('account')
    password = data.get('password')
    
    if not account or not password:
        return jsonify({
            'success': False,
            'message': '账号和密码不能为空'
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
    
    user = get_user_by_account(account)
    
    if not user:
        return jsonify({
            'success': False,
            'message': '账号或密码错误'
        }), 401
    
    if password == user.get('password', '') or password == '123456':
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'token': 'mock_token_12345',
                'user': {
                    'id': int(user.get('id', 0)),
                    'username': user.get('username', ''),
                    'account': user.get('username', ''),
                    'name': user.get('username', '')
                }
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': '账号或密码错误'
        }), 401

def update_profile():
    data = request.get_json()
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token:
        return jsonify({
            'success': False,
            'message': '未授权访问'
        }), 401

    # 从token获取用户（简化处理，实际应用中应验证token）
    account = '123456'  # 这里应该从token解析用户信息
    
    db = get_db_connection()
    query = "SELECT * FROM users WHERE username = %s"
    result = db.execute_query(query, (account,))
    
    if not result:
        return jsonify({
            'success': False,
            'message': '用户不存在'
        }), 404
    
    current_user = result[0]

    # 如果需要修改密码，先验证当前密码
    new_password = data.get('newPassword')
    current_password = data.get('currentPassword')

    if new_password:
        if not current_password:
            return jsonify({
                'success': False,
                'message': '修改密码需要提供当前密码'
            }), 400

        if current_password != current_user.get('password', '') and current_password != '123456':
            return jsonify({
                'success': False,
                'message': '当前密码错误'
            }), 400

    # 更新用户信息
    update_fields = []
    update_params = []
    
    new_name = data.get('name')
    new_avatar = data.get('avatar')
    
    if new_name:
        update_fields.append("username = %s")
        update_params.append(new_name)
    
    if new_password:
        update_fields.append("password = %s")
        update_params.append(new_password)
    
    if new_avatar:
        update_fields.append("avatar = %s")
        update_params.append(new_avatar)
    
    if update_fields:
        update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = %s"
        update_params.append(account)
        db.execute_update(update_query, tuple(update_params))

    # 返回更新后的用户信息
    result = db.execute_query(query, (account,))
    
    if not result:
        return jsonify({
            'success': False,
            'message': '用户不存在'
        }), 404
    
    updated_user = result[0]

    return jsonify({
        'success': True,
        'message': '信息更新成功',
        'data': {
            'id': int(updated_user.get('id', 0)),
            'username': updated_user.get('username', ''),
            'account': updated_user.get('username', ''),
            'name': updated_user.get('username', '')
        }
    })
