import csv
import json
import os
import random
import re
from collections import defaultdict
from datetime import datetime
from flask import request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing

# 添加数据库导入
from sql.database import get_db_connection

class OrganizationManager:
    """组织架构管理器 - 使用数据库存储"""
    
    def __init__(self, csv_path=None, org_txt_path=None):
        self.csv_path = csv_path or 'C:\\Users\\sanjin\\Desktop\\ruoyi\\back\\data\\users.csv'
        self.org_txt_path = org_txt_path or 'C:\\Users\\sanjin\\Desktop\\ruoyi\\back\\data\\organization.txt'
        self.users = []
        self.org_tree = {}
        # 缓存机制
        self._cache = {
            'users': None,
            'users_mtime': 0,
            'org_tree': None,
            'org_tree_mtime': 0,
            'department_list': None,
            'department_list_mtime': 0,
            '_role_groups': None,
            '_total_counts': None,
            '_role_meta': None,
            '_org_dict': None,
        }
        self._cache_ttl = 300  # 缓存有效期（秒）
        
        # 多进程预加载数据（首次启动时）
        self._preload_data()
    
    def _preload_data(self):
        """预加载数据（串行，避免多线程共享数据库连接）"""
        import time
        start_time = time.time()
        
        users = self._load_users_from_db()
        org_dict = self._load_org_from_db()
        
        # 存储到缓存
        self._cache['users'] = users
        self._cache['users_mtime'] = time.time()
        self._cache['_org_dict'] = org_dict
        self._cache['_org_dict_mtime'] = time.time()
        
        elapsed = time.time() - start_time
        print(f"[INFO] 预加载完成: {len(users)} 用户, {len(org_dict)} 部门, 耗时 {elapsed:.3f}s")
    
    def _load_users_from_db(self):
        """从数据库加载用户数据"""
        db = get_db_connection()
        result = db.execute_query("SELECT * FROM users")
        print(f"[INFO] 从数据库加载用户数据: {len(result)} 条")
        return result
    
    def _load_org_from_db(self):
        """从数据库加载组织架构数据"""
        org_dict = {}
        db = get_db_connection()
        result = db.execute_query("SELECT * FROM organization")
        for row in result:
            org_name = row.get('name', '')
            if org_name:
                org_dict[org_name] = {
                    'role': row.get('role', ''),
                    'superior department': row.get('superior_department', ''),
                    'below department': row.get('below_department', ''),
                    'create_data': row.get('create_date', ''),
                    'functionary': row.get('functionary', '')
                }
        print(f"[INFO] 从数据库加载组织架构数据: {len(org_dict)} 条")
        return org_dict
    
    def _invalidate_cache(self):
        """清除缓存（用于数据修改后）"""
        self._cache['users'] = None
        self._cache['org_tree'] = None
        self._cache['department_list'] = None
        self._cache['_org_dict'] = None
        self._cache['_role_meta'] = None
        self._cache['_role_groups'] = None
        self._cache['_total_counts'] = None
    
    def load_users(self, use_cache=True):
        """从数据库加载用户数据（带缓存）"""
        import time
        
        # 检查预加载的缓存是否有效
        if use_cache and self._cache['users'] is not None:
            cache_age = time.time() - self._cache['users_mtime']
            if cache_age < self._cache_ttl:
                self.users = self._cache['users']
                return True
        
        # 重新从数据库加载
        self.users = self._load_users_from_db()
        
        # 更新缓存
        self._cache['users'] = self.users.copy()
        self._cache['users_mtime'] = time.time()
        return True
    
    def parse_role(self, role_str):
        """解析角色字符串为层级列表"""
        if not role_str or role_str == '0':
            return [0]
        parts = role_str.split('.')
        return [int(p) for p in parts]
    
    def _get_org_txt_meta(self):
        """从数据库获取部门元数据，返回 {role: {name, created_at, superior}} 与所有已知 role 集合"""
        # 优先使用缓存
        cached_meta = self._cache.get('_role_meta')
        if cached_meta is not None:
            return cached_meta
        
        org_dict = self._cache.get('_org_dict')
        if org_dict is None:
            org_dict = self._load_org_from_db()
            self._cache['_org_dict'] = org_dict
        
        role_meta = {}
        for org_name, fields in org_dict.items():
            role = fields.get('role', '').strip()
            if not role:
                if org_name == '总部':
                    role = '0'
                elif org_name.startswith('部门'):
                    role = org_name[2:]
                else:
                    role = org_name
            role_meta[role] = {
                'name': org_name,
                'functionary': fields.get('functionary', ''),
                'created_at': fields.get('create_data', ''),
                'superior': fields.get('superior department', '无')
            }
        
        # 缓存结果
        self._cache['_role_meta'] = role_meta
        return role_meta
    
    def _compute_total_counts(self, role_groups):
        """预计算每个 role 的子孙注册用户总数"""
        all_roles = list(role_groups.keys())
        total_counts = {}
        for role in all_roles:
            count = 0
            role_dot = role + '.'
            for k, v in role_groups.items():
                if k == role or k.startswith(role_dot):
                    count += len(v)
            total_counts[role] = count
        return total_counts
    
    def build_org_tree(self, use_cache=True):
        """构建组织架构树（综合数据库用户数据与组织架构数据，带缓存）"""
        import time
        
        # 检查缓存是否有效
        if use_cache and self._cache['org_tree'] is not None:
            cache_age = time.time() - self._cache['org_tree_mtime']
            if cache_age < self._cache_ttl:
                self.org_tree = self._cache['org_tree']
                return self.org_tree
        
        # 确保用户数据已加载
        self.load_users(use_cache=use_cache)
        
        role_groups = defaultdict(list)
        for user in self.users:
            role = user.get('role', '0')
            role_groups[role].append(user)
        
        # 预计算每个 role 的子孙用户总数
        total_counts = self._compute_total_counts(role_groups)
        
        # 从数据库获取部门元数据
        role_meta = self._get_org_txt_meta()
        
        # 收集所有已知 role（用户数据 + 组织架构的并集）
        all_roles = set(role_groups.keys()) | set(role_meta.keys())
        
        # 辅助：检查某 role 在任一数据源中有子级
        def _has_children(parent_role):
            prefix = parent_role + '.'
            for r in all_roles:
                if r.startswith(prefix):
                    return True
            return False
        
        # 根节点
        root_meta = role_meta.get('0', {})
        self.org_tree = {
            'role': '0',
            'name': root_meta.get('name', '总经理'),
            'functionary': root_meta.get('functionary', ''),
            'created_at': root_meta.get('created_at', ''),
            'users': role_groups.get('0', []),
            'children': []
        }
        
        # 一级部门：先看数据库中总部 listed 了哪些 below department
        root_below = role_meta.get('0', {}).get('superior', '')
        if root_below and root_below != '无':
            below_parts = [b.strip() for b in root_below.split(',') if b.strip()]
            manager_roles = []
            for b in below_parts:
                r = self._org_name_to_role(b)
                manager_roles.append(r)
        else:
            manager_roles = []
            for r in all_roles:
                parts = r.split('.')
                if len(parts) == 1 and r != '0' and r.isdigit():
                    manager_roles.append(r)
            if not manager_roles:
                manager_roles = ['1', '2', '3', '4']
        
        for mgr_role in sorted(manager_roles, key=lambda x: int(x)):
            manager_users = role_groups.get(mgr_role, [])
            has_in_csv = mgr_role in role_groups
            has_in_org = mgr_role in role_meta
            has_children = _has_children(mgr_role)
            
            if has_in_csv or has_in_org or has_children:
                meta = role_meta.get(mgr_role, {})
                manager_info = {
                    'role': mgr_role,
                    'name': meta.get('name', f'部门{mgr_role}'),
                    'functionary': meta.get('functionary', ''),
                    'created_at': meta.get('created_at', ''),
                    'users': manager_users,
                    'total_count': total_counts.get(mgr_role, len(manager_users)),
                    'children': []
                }
                manager_info['children'] = self._build_subordinate_tree_v2(
                    mgr_role, role_groups, role_meta, all_roles, total_counts
                )
                self.org_tree['children'].append(manager_info)
        
        # 更新缓存
        self._cache['org_tree'] = self.org_tree
        self._cache['org_tree_mtime'] = time.time()
        self._cache['_role_groups'] = role_groups
        self._cache['_total_counts'] = total_counts
        
        return self.org_tree
    
    def get_children_by_role(self, parent_role):
        """按需加载指定部门的直接子部门（分层加载）"""
        # 确保用户数据已加载
        self.load_users(use_cache=True)
        
        # 尝试复用缓存的 role_groups 和 total_counts
        role_groups = self._cache.get('_role_groups')
        total_counts = self._cache.get('_total_counts')
        
        if role_groups is None:
            role_groups = defaultdict(list)
            for user in self.users:
                r = user.get('role', '0')
                role_groups[r].append(user)
            total_counts = self._compute_total_counts(role_groups)
        elif total_counts is None:
            total_counts = self._compute_total_counts(role_groups)
        
        # 使用缓存的 role_meta
        role_meta = self._get_org_txt_meta()
        
        # 收集所有已知 role
        all_roles = set(role_groups.keys()) | set(role_meta.keys())
        
        # 构建查找函数
        def _sort_key(r):
            parts = [int(p) for p in r.split('.')]
            return parts
        
        # 收集直接子部门
        prefix = parent_role + '.'
        direct_children = set()
        for role in all_roles:
            if role.startswith(prefix):
                sub_parts = role[len(prefix):].split('.')
                if len(sub_parts) == 1:  # 只取一级子
                    direct_children.add(role)
        
        children = []
        for role in sorted(direct_children, key=_sort_key):
            meta = role_meta.get(role, {})
            dept_users = role_groups.get(role, [])
            tc = total_counts.get(role, len(dept_users))
            
            # 检查是否有更深层级的子部门
            has_more_children = any(
                r.startswith(role + '.') and r != role
                for r in all_roles
            )
            
            children.append({
                'role': role,
                'name': meta.get('name', f'部门{role}'),
                'functionary': meta.get('functionary', ''),
                'created_at': meta.get('created_at', ''),
                'users': dept_users,
                'total_count': tc,
                'has_children': has_more_children,
                'children': []
            })
        
        return children
    
    def _build_subordinate_tree_v2(self, parent_role, role_groups, role_meta, all_roles, total_counts=None):
        """递归构建下属树（综合数据库数据）"""
        children = []
        prefix = parent_role + '.'
        
        # 收集所有直接子 role
        direct_children = set()
        for role in all_roles:
            if role.startswith(prefix):
                sub_parts = role[len(prefix):].split('.')
                if len(sub_parts) == 1:  # 只取一级子
                    direct_children.add(role)
        
        def _sort_key(r):
            parts = [int(p) for p in r.split('.')]
            return parts
        
        for role in sorted(direct_children, key=_sort_key):
            meta = role_meta.get(role, {})
            # 使用预计算值，没有则实时计算
            if total_counts is not None:
                tc = total_counts.get(role, len(role_groups.get(role, [])))
            else:
                tc = sum(len(v) for k, v in role_groups.items()
                         if k == role or k.startswith(role + '.'))
            children.append({
                'role': role,
                'name': meta.get('name', f'部门{role}'),
                'functionary': meta.get('functionary', ''),
                'created_at': meta.get('created_at', ''),
                'users': role_groups.get(role, []),
                'total_count': tc,
                'children': self._build_subordinate_tree_v2(role, role_groups, role_meta, all_roles, total_counts)
            })
        
        return children
    
    def _build_subordinate_tree(self, manager_role, role_groups):
        """递归构建下属树（仅基于用户数据）"""
        children = []
        for role in role_groups:
            import re
            pattern = re.escape(manager_role) + r'\.\d+(\.\d+)*$'
            if re.match(pattern, role):
                sub_parts = role.replace(f'{manager_role}.', '').split('.')
                if len(sub_parts) == 1:
                    children.append({
                        'role': role,
                        'name': f'员工{role}',
                        'users': role_groups[role],
                        'children': self._build_subordinate_tree(role, role_groups)
                    })
        return children
    
    def get_department_list(self):
        """获取部门列表（树形结构，综合数据库数据）"""
        role_groups = defaultdict(list)
        for user in self.users:
            role = user.get('role', '0')
            role_groups[role].append(user)
        
        role_meta = self._get_org_txt_meta()
        all_roles = set(role_groups.keys()) | set(role_meta.keys())
        
        all_depts = []
        # 添加总部（只添加一次）
        all_depts.append({
            'id': '0',
            'name': '总部',
            'count': sum(len(v) for v in role_groups.values())
        })
        
        # 一级部门
        root_below = role_meta.get('0', {}).get('below_department', '')
        if root_below and root_below != '无':
            dept1_org_names = [b.strip() for b in root_below.split(',') if b.strip()]
        else:
            dept1_org_names = []
        
        dept1_roles = [self._org_name_to_role(n) for n in dept1_org_names]
        if not dept1_roles:
            dept1_roles = sorted([r for r in all_roles if r.count('.') == 0 and r != '0' and r.isdigit()], key=int)
        if not dept1_roles:
            dept1_roles = ['1', '2', '3', '4']
        
        for idx, dept_role in enumerate(sorted(dept1_roles, key=int)):
            org_name = dept1_org_names[idx] if idx < len(dept1_org_names) else f'部门{dept_role}'
            count = 0
            for r in role_groups:
                if r == dept_role or r.startswith(f'{dept_role}.'):
                    count += len(role_groups[r])
            dept_meta = role_meta.get(dept_role, {})
            all_depts.append({
                'id': dept_role,
                'name': dept_meta.get('name', org_name),
                'count': count
            })
            
            # 子部门
            dept_below = dept_meta.get('below_department', '')
            if not dept_below or dept_below == '无':
                # 从用户数据推断
                sub_roles = set()
                for r in all_roles:
                    if r.startswith(f'{dept_role}.'):
                        parts = r.split('.')
                        if len(parts) == 2:
                            sub_roles.add(r)
            else:
                sub_org_names = [b.strip() for b in dept_below.split(',') if b.strip()]
                sub_roles = {self._org_name_to_role(n) for n in sub_org_names}
            
            for sub_role in sorted(sub_roles, key=lambda x: [int(p) for p in x.split('.')]):
                sub_count = 0
                for r in role_groups:
                    if r == sub_role or r.startswith(f'{sub_role}.'):
                        sub_count += len(role_groups[r])
                sub_meta = role_meta.get(sub_role, {})
                all_depts.append({
                    'id': sub_role,
                    'name': sub_meta.get('name', f'子部门{sub_role}'),
                    'count': sub_count
                })
        
        return all_depts
    
    def get_user_by_role(self, role):
        """根据角色获取用户列表"""
        result = []
        for user in self.users:
            user_role = user.get('role', '')
            if user_role == role or user_role.startswith(f'{role}.'):
                result.append(user)
        return result
    
    def get_user_info(self, user_id):
        """根据ID获取用户信息"""
        for user in self.users:
            if user.get('id') == str(user_id):
                return user
        return None
    
    def get_employee_info(self, user_id):
        """员工信息查看 - 获取员工的详细信息"""
        user = self.get_user_info(user_id)
        if not user:
            return None
        
        role = user.get('role', '0')
        department = self._get_department_by_role(role)
        
        return {
            'id': user.get('id'),
            'username': user.get('username'),
            'account': user.get('account'),
            'name': user.get('name'),
            'department': department,
            'role': role,
            'role_level': self._get_role_level(role),
            'created_at': user.get('created_at'),
            'image': user.get('image', '')
        }
    
    def get_department_info(self, dept_id):
        """部门信息查看 - 获取部门的详细信息"""
        role_groups = defaultdict(list)
        for user in self.users:
            role = user.get('role', '0')
            role_groups[role].append(user)
        
        # 获取部门名称
        role_meta = self._get_org_txt_meta()
        dept_meta = role_meta.get(dept_id, {})
        dept_name = dept_meta.get('name', '')
        
        if dept_id == '0':
            dept_name = '总部'
        elif not dept_name:
            if dept_id in ['1', '2', '3', '4']:
                dept_name = f'部门{dept_id}'
            else:
                return None
        
        # 获取部门员工列表
        employees = []
        manager = None
        
        for role in role_groups:
            if role == dept_id or role.startswith(f'{dept_id}.'):
                for user in role_groups[role]:
                    emp_info = {
                        'id': user.get('id'),
                        'name': user.get('name'),
                        'username': user.get('username'),
                        'role': user.get('role'),
                        'role_level': self._get_role_level(user.get('role'))
                    }
                    employees.append(emp_info)
                    # 判断是否为部门负责人（角色为纯数字，没有小数点）
                    if role == dept_id:
                        manager = emp_info
        
        # 计算部门层级
        max_depth = 1
        for emp in employees:
            depth = emp['role'].count('.') + 1
            if depth > max_depth:
                max_depth = depth
        
        return {
            'id': dept_id,
            'name': dept_name,
            'manager': manager,
            'total_employees': len(employees),
            'hierarchy_levels': max_depth,
            'employees': employees
        }
    
    def _get_department_by_role(self, role):
        """根据角色获取所属部门"""
        if role == '0':
            return '总部'
        elif role.startswith('1'):
            return '部门1'
        elif role.startswith('2'):
            return '部门2'
        elif role.startswith('3'):
            return '部门3'
        elif role.startswith('4'):
            return '部门4'
        return '未知部门'
    
    def _get_role_level(self, role):
        """获取角色层级描述"""
        if not role:
            return '未知'
        depth = role.count('.') + 1
        if depth == 1:
            if role == '0':
                return '总经理'
            return '部门经理'
        elif depth == 2:
            return '主管'
        else:
            return f'普通员工{depth-2}'
    
    def get_org_hierarchy(self):
        """获取完整的组织架构层级"""
        if not self.users:
            self.load_users()
        
        hierarchy = {
            'total_users': len(self.users),
            'levels': []
        }
        
        level_counts = defaultdict(int)
        for user in self.users:
            role = user.get('role', '0')
            depth = role.count('.') + 1
            level_counts[depth] += 1
        
        total_levels = max(level_counts.keys()) if level_counts else 1
        
        for level in range(1, total_levels + 1):
            hierarchy['levels'].append({
                'level': level,
                'count': level_counts.get(level, 0),
                'description': self._get_level_description(level)
            })
        
        return hierarchy
    
    def _get_level_description(self, level):
        """获取层级描述"""
        descriptions = {
            1: '最高管理层',
            2: '部门经理层',
            3: '主管层',
            4: '普通员工层'
        }
        return descriptions.get(level, f'第{level}层级')
    
    def export_org_data(self, output_path):
        """导出组织架构数据为 JSON"""
        org_data = {
            'tree': self.build_org_tree(),
            'departments': self.get_department_list(),
            'hierarchy': self.get_org_hierarchy()
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(org_data, f, ensure_ascii=False, indent=2)
            print(f"[成功] 组织架构数据已导出到 {output_path}")
            return True
        except Exception as e:
            print(f"[错误] 导出失败：{e}")
            return False
    
    def search_departments_or_employees(self, keyword, search_type='all', fuzzy_match=True):
        """搜索部门或员工"""
        if not keyword:
            return {'departments': [], 'employees': []}
        
        keyword_lower = keyword.lower()
        keyword_pinyin = self._to_pinyin(keyword_lower)
        result = {
            'departments': [],
            'employees': []
        }
        
        # 搜索部门
        role_groups = defaultdict(list)
        for user in self.users:
            role = user.get('role', '0')
            role_groups[role].append(user)
        
        # 获取所有部门
        departments = self.get_department_list()
        for dept in departments:
            dept_name = dept.get('name', '').lower()
            dept_id = dept.get('id', '')
            dept_name_pinyin = self._to_pinyin(dept_name)
            
            should_match = False
            matched_field = None
            match_score = 0
            
            if search_type == 'all' or search_type == 'name':
                if keyword_lower in dept_name:
                    should_match = True
                    matched_field = 'name'
                    match_score = 100
                elif fuzzy_match and keyword_pinyin and keyword_pinyin in dept_name_pinyin:
                    should_match = True
                    matched_field = 'name_pinyin'
                    match_score = 80
                elif fuzzy_match and self._fuzzy_match(keyword_lower, dept_name):
                    should_match = True
                    matched_field = 'name_fuzzy'
                    match_score = 60
                elif keyword_lower in dept_id:
                    should_match = True
                    matched_field = 'id'
                    match_score = 90
            
            if search_type == 'all' or search_type == 'role':
                if keyword in dept_id or dept_id.startswith(keyword):
                    if not matched_field:
                        should_match = True
                        matched_field = 'role'
                        match_score = 95
            
            if should_match:
                count = 0
                for role in role_groups:
                    if role == dept_id or role.startswith(f'{dept_id}.'):
                        count += len(role_groups[role])
                
                result['departments'].append({
                    'id': dept_id,
                    'name': dept.get('name'),
                    'count': count,
                    'matched_field': matched_field,
                    'match_score': match_score
                })
        
        # 搜索员工
        for user in self.users:
            name = user.get('name', '').lower()
            username = user.get('username', '').lower()
            account = user.get('account', '').lower()
            role = user.get('role', '')
            department = user.get('department', '').lower()
            name_pinyin = self._to_pinyin(name)
            dept_pinyin = self._to_pinyin(department)
            
            matched_field = None
            match_score = 0
            
            if search_type == 'all' or search_type == 'name':
                if keyword_lower in name:
                    matched_field = 'name'
                    match_score = 100
                elif fuzzy_match and keyword_pinyin and keyword_pinyin in name_pinyin:
                    matched_field = 'name_pinyin'
                    match_score = 80
                elif fuzzy_match and self._fuzzy_match(keyword_lower, name):
                    matched_field = 'name_fuzzy'
                    match_score = 60
                elif keyword_lower in username:
                    matched_field = 'username'
                    match_score = 95
                elif keyword_lower in department:
                    matched_field = 'department'
                    match_score = 90
                elif fuzzy_match and keyword_pinyin and keyword_pinyin in dept_pinyin:
                    matched_field = 'department_pinyin'
                    match_score = 75
            
            if search_type == 'all' or search_type == 'role':
                if role == keyword or role.startswith(keyword + '.') or keyword.startswith(role + '.'):
                    if not matched_field:
                        matched_field = 'role'
                        match_score = 95
            
            if matched_field:
                result['employees'].append({
                    'id': user.get('id'),
                    'name': user.get('name'),
                    'username': user.get('username'),
                    'account': user.get('account'),
                    'role': role,
                    'department': user.get('department'),
                    'role_level': self._get_role_level(role),
                    'matched_field': matched_field,
                    'match_score': match_score
                })
        
        # 按匹配度排序
        result['departments'].sort(key=lambda x: x['match_score'], reverse=True)
        result['employees'].sort(key=lambda x: x['match_score'], reverse=True)
        
        return result
    
    def _to_pinyin(self, text):
        """将中文转换为拼音首字母（简化版）"""
        pinyin_map = {
            '部': 'b', '门': 'm', '总': 'z', '经': 'j', '理': 'l',
            '员': 'y', '工': 'g', '主': 'z', '管': 'g', '普': 'p',
            '通': 't', '高': 'g', '层': 'c', '经': 'j', '营': 'y'
        }
        
        result = ''
        for char in text:
            if char in pinyin_map:
                result += pinyin_map[char]
            elif char.isalpha():
                result += char
        return result
    
    def _fuzzy_match(self, pattern, text):
        """模糊匹配：检查 pattern 中的字符是否按顺序出现在 text 中"""
        if not pattern or not text:
            return False
        
        pattern = pattern.lower()
        text = text.lower()
        
        pattern = ''.join(c for c in pattern if c.isalnum())
        text = ''.join(c for c in text if c.isalnum())
        
        if not pattern:
            return False
        
        pattern_idx = 0
        for char in text:
            if char == pattern[pattern_idx]:
                pattern_idx += 1
                if pattern_idx == len(pattern):
                    return True
        
        return False
    
    # ==================== 组织架构数据库读写辅助 ====================
    
    def _role_to_org_name(self, role):
        """将 role 编号映射为部门名"""
        if role == '0':
            return '总部'
        return f'部门{role}'
    
    def _org_name_to_role(self, org_name):
        """将部门名反向映射为 role 编号"""
        if org_name == '总部':
            return '0'
        org_dict = self._cache.get('_org_dict')
        if org_dict is None:
            org_dict = self._load_org_from_db()
            self._cache['_org_dict'] = org_dict
        if org_name in org_dict and 'role' in org_dict[org_name]:
            return org_dict[org_name]['role']
        if org_name.startswith('部门'):
            return org_name[2:]
        return org_name
    
    # ==================== 创建/解散部门（数据库操作）====================
    
    def create_department(self, parent_role, dept_name, manager_name=''):
        """创建新部门（数据库版本）"""
        self.load_users()
        
        if parent_role == '0':
            # 总部下创建一级部门
            top_nums = []
            for user in self.users:
                role = user.get('role', '')
                if role != '0' and '.' not in role:
                    try:
                        top_nums.append(int(role))
                    except ValueError:
                        pass
            # 同时检查数据库中的一级部门
            db = get_db_connection()
            result = db.execute_query("SELECT role FROM organization WHERE role NOT LIKE '%.%' AND role != '0'")
            for row in result:
                try:
                    top_nums.append(int(row['role']))
                except ValueError:
                    pass
            next_num = max(top_nums) + 1 if top_nums else 1
            new_role = str(next_num)
        else:
            # 查找 parent_role 下的最大子 role 编号
            sub_nums = []
            prefix = parent_role + '.'
            for user in self.users:
                role = user.get('role', '')
                if role.startswith(prefix) and role.count('.') == parent_role.count('.') + 1:
                    try:
                        num = int(role.split('.')[-1])
                        sub_nums.append(num)
                    except ValueError:
                        pass
            # 同时检查数据库中的子部门
            result = db.execute_query(f"SELECT role FROM organization WHERE role LIKE '{prefix}%'")
            for row in result:
                role = row['role']
                if role.startswith(prefix) and role.count('.') == parent_role.count('.') + 1:
                    try:
                        num = int(role.split('.')[-1])
                        sub_nums.append(num)
                    except ValueError:
                        pass
            
            next_num = max(sub_nums) + 1 if sub_nums else 1
            new_role = f"{parent_role}.{next_num}"
        
        # 根据父级 role 生成上级部门名
        parent_dept_name = self._get_dept_name_by_role(parent_role)
        parent_org_name = self._role_to_org_name(parent_role)
        
        # 写入数据库
        db = get_db_connection()
        # 插入新部门
        query = """
            INSERT INTO organization (name, superior_department, below_department, create_date, functionary, role)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (dept_name, parent_org_name, '无', datetime.now().strftime('%Y-%m-%d'), manager_name, new_role)
        db.execute_update(query, params)
        
        # 更新父部门的 below_department 字段
        query = "SELECT below_department FROM organization WHERE name = %s"
        result = db.execute_query(query, (parent_org_name,))
        if result:
            below = result[0].get('below_department', '无')
            if below == '无':
                below = dept_name
            else:
                existing = [b.strip() for b in below.split(',') if b.strip() and b.strip() != '无']
                if dept_name not in existing:
                    existing.append(dept_name)
                    below = ','.join(existing)
            update_query = "UPDATE organization SET below_department = %s WHERE name = %s"
            db.execute_update(update_query, (below, parent_org_name))
        
        # 清除缓存
        self._invalidate_cache()
        
        return {
            'role': new_role,
            'name': dept_name,
            'functionary': manager_name,
            'parent_role': parent_role,
            'parent_name': parent_dept_name,
            'users': [],
            'children': []
        }, None, None
    
    def delete_department(self, role):
        """解散/删除部门（数据库版本）"""
        if role == '0':
            return False, "不能删除总部（根部门）"
        
        db = get_db_connection()
        
        # 获取部门名称
        query = "SELECT name, superior_department FROM organization WHERE role = %s"
        result = db.execute_query(query, (role,))
        if not result:
            return False, "部门不存在"
        
        dept_name = result[0]['name']
        parent_name = result[0]['superior_department']
        
        # 删除部门
        query = "DELETE FROM organization WHERE role = %s OR role LIKE %s"
        db.execute_update(query, (role, f"{role}.%"))
        
        # 更新父部门的 below_department 字段
        if parent_name and parent_name != '无':
            query = "SELECT below_department FROM organization WHERE name = %s"
            result = db.execute_query(query, (parent_name,))
            if result:
                below = result[0].get('below_department', '无')
                if below != '无':
                    existing = [b.strip() for b in below.split(',') if b.strip() and b.strip() != '无']
                    if dept_name in existing:
                        existing.remove(dept_name)
                        new_below = ','.join(existing) if existing else '无'
                        update_query = "UPDATE organization SET below_department = %s WHERE name = %s"
                        db.execute_update(update_query, (new_below, parent_name))
        
        # 清除缓存
        self._invalidate_cache()
        
        return True, "删除成功"
    
    def _get_dept_name_by_role(self, role):
        """根据 role 获取部门名称"""
        role_meta = self._get_org_txt_meta()
        if role in role_meta:
            return role_meta[role].get('name', f'部门{role}')
        return f'部门{role}'