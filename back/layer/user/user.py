from .login import login
from .register import register
from .edit import update_user_info, get_user_info
from .upload import upload_image
from .organization import OrganizationManager
from flask import jsonify

def register_user_routes(app):
    app.add_url_rule('/api/auth/login', view_func=login, methods=['POST'])
    app.add_url_rule('/api/auth/register', view_func=register, methods=['POST'])
    app.add_url_rule('/api/auth/update', view_func=update_user_info, methods=['POST'])
    app.add_url_rule('/api/auth/info', view_func=get_user_info, methods=['GET'])
    app.add_url_rule('/api/auth/upload/image', view_func=upload_image, methods=['POST'])
    
    # 组织架构路由
    app.add_url_rule('/api/org/tree', view_func=get_org_tree, methods=['GET'])
    app.add_url_rule('/api/org/departments', view_func=get_org_departments, methods=['GET'])
    app.add_url_rule('/api/org/department/<dept_id>', view_func=get_org_department_info, methods=['GET'])
    app.add_url_rule('/api/org/employee/<user_id>', view_func=get_org_employee_info, methods=['GET'])
    app.add_url_rule('/api/org/children/<parent_role>', view_func=get_org_children, methods=['GET'])
    app.add_url_rule('/api/org/create', view_func=create_org_department, methods=['POST'])
    app.add_url_rule('/api/org/delete/<role>', view_func=delete_org_department, methods=['DELETE'])

# ==================== 组织架构接口 ====================

org_manager = OrganizationManager()

def get_org_tree():
    """获取组织架构树"""
    try:
        tree = org_manager.build_org_tree()
        return jsonify({
            'success': True,
            'data': tree
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def get_org_departments():
    """获取部门列表"""
    try:
        departments = org_manager.get_department_list()
        return jsonify({
            'success': True,
            'data': departments
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def get_org_children(parent_role):
    """获取指定部门的直接子部门"""
    try:
        children = org_manager.get_children_by_role(parent_role)
        return jsonify({
            'success': True,
            'data': children
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def get_org_department_info(dept_id):
    """获取部门详情"""
    try:
        dept_info = org_manager.get_department_info(dept_id)
        if dept_info is None:
            return jsonify({
                'success': False,
                'message': '部门不存在'
            }), 404
        return jsonify({
            'success': True,
            'data': dept_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def get_org_employee_info(user_id):
    """获取员工详情"""
    try:
        emp_info = org_manager.get_employee_info(user_id)
        if emp_info is None:
            return jsonify({
                'success': False,
                'message': '员工不存在'
            }), 404
        return jsonify({
            'success': True,
            'data': emp_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def create_org_department():
    """创建部门"""
    from flask import request
    try:
        data = request.get_json() or {}
        parent_role = data.get('parent_role', '0')
        dept_name = data.get('name', '').strip()
        manager_name = data.get('manager_name', '').strip()
        
        if not dept_name:
            return jsonify({
                'success': False,
                'message': '部门名称不能为空'
            }), 400
        
        result, error, warning = org_manager.create_department(parent_role, dept_name, manager_name)
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 500
        
        return jsonify({
            'success': True,
            'data': result,
            'warning': warning
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def delete_org_department(role):
    """删除部门"""
    try:
        success, message = org_manager.delete_department(role)
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
