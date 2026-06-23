"""
数据迁移脚本
将现有的数据文件导入到数据库中
"""

import os
import sys
import pymysql
from dotenv import load_dotenv

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'old', '.env'))


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'ruoyi'),
        charset=os.getenv('DB_CHARSET', 'utf8mb4'),
        cursorclass=pymysql.cursors.DictCursor
    )


def execute_sql_file(filepath):
    """执行 SQL 文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割 SQL 语句
        sql_statements = sql_content.split(';')
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for sql in sql_statements:
                    sql = sql.strip()
                    if sql and not sql.startswith('--'):
                        cursor.execute(sql)
                conn.commit()
        print(f"成功执行 SQL 文件: {filepath}")
    except Exception as e:
        print(f"执行 SQL 文件失败: {e}")


def import_organization_data():
    """导入组织架构数据"""
    org_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'organization.txt')
    
    if not os.path.exists(org_file_path):
        print(f"组织架构文件不存在: {org_file_path}")
        return
    
    try:
        # 读取组织架构文件
        with open(org_file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        # 解析数据
        data = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 解析格式：部门名：{superior department：值：below department：值：...：}
            if '：{' in line:
                parts = line.split('：{', 1)
                dept_name = parts[0].strip()
                content = parts[1].rstrip('}：').strip()
                
                # 解析内部键值对
                fields = {}
                pairs = content.split('：')
                for i in range(0, len(pairs), 2):
                    if i + 1 < len(pairs):
                        key = pairs[i].strip()
                        value = pairs[i + 1].strip()
                        fields[key] = value
                
                data.append({
                    'name': dept_name,
                    'superior_department': fields.get('superior department', '无'),
                    'below_department': fields.get('below department', ''),
                    'create_date': fields.get('create_data', None),
                    'functionary': fields.get('functionary', ''),
                    'role': fields.get('role', '')
                })
        
        # 插入数据库
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 先清空表
                cursor.execute("DELETE FROM organization WHERE id > 16")
                
                # 批量插入
                insert_sql = """
                    INSERT INTO organization (name, superior_department, below_department, create_date, functionary, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                values = []
                for item in data[1:]:  # 跳过第一行（表头）
                    create_date = item['create_date']
                    if create_date and len(create_date) == 10:
                        create_date = create_date + ' 00:00:00'
                    
                    values.append((
                        item['name'],
                        item['superior_department'],
                        item['below_department'],
                        create_date,
                        item['functionary'],
                        item['role']
                    ))
                
                cursor.executemany(insert_sql, values)
                conn.commit()
                
        print(f"成功导入 {len(data) - 1} 条组织架构数据")
        
    except Exception as e:
        print(f"导入组织架构数据失败: {e}")


def import_knowledge_data():
    """导入知识库数据"""
    knowledge_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'knowledge')
    
    if not os.path.exists(knowledge_dir):
        print(f"知识库目录不存在: {knowledge_dir}")
        return
    
    try:
        files = [f for f in os.listdir(knowledge_dir) if f.endswith('.txt')]
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for filename in files:
                    filepath = os.path.join(knowledge_dir, filename)
                    
                    # 读取文件内容
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 获取文件大小
                    file_size = os.path.getsize(filepath)
                    
                    # 获取文件类型
                    file_type = filename.split('.')[-1] if '.' in filename else 'txt'
                    
                    # 插入数据库
                    insert_sql = """
                        INSERT INTO knowledge (file_name, file_path, content, file_size, file_type)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE content = VALUES(content), file_size = VALUES(file_size)
                    """
                    
                    cursor.execute(insert_sql, (filename, filepath, content, file_size, file_type))
                
                conn.commit()
        
        print(f"成功导入 {len(files)} 条知识库数据")
        
    except Exception as e:
        print(f"导入知识库数据失败: {e}")


def import_upload_files():
    """导入上传文件数据"""
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'knowledge')
    
    if not os.path.exists(upload_dir):
        print(f"上传文件目录不存在: {upload_dir}")
        return
    
    try:
        files = [f for f in os.listdir(upload_dir) if f.endswith('.txt')]
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for filename in files:
                    filepath = os.path.join(upload_dir, filename)
                    
                    # 获取原始文件名（从存储文件名中提取）
                    original_name = filename.split('_')[-1] if '_' in filename else filename
                    
                    # 获取文件大小
                    file_size = os.path.getsize(filepath)
                    
                    # 获取文件类型
                    file_type = filename.split('.')[-1] if '.' in filename else 'txt'
                    
                    # 插入数据库
                    insert_sql = """
                        INSERT INTO upload_files (original_name, storage_name, file_path, file_size, file_type)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE file_size = VALUES(file_size)
                    """
                    
                    cursor.execute(insert_sql, (original_name, filename, filepath, file_size, file_type))
                
                conn.commit()
        
        print(f"成功导入 {len(files)} 条上传文件数据")
        
    except Exception as e:
        print(f"导入上传文件数据失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("数据迁移脚本")
    print("=" * 60)
    
    # 1. 执行初始化 SQL
    print("\n1. 执行数据库初始化...")
    sql_file = os.path.join(os.path.dirname(__file__), 'init.sql')
    execute_sql_file(sql_file)
    
    # 2. 导入组织架构数据
    print("\n2. 导入组织架构数据...")
    import_organization_data()
    
    # 3. 导入知识库数据
    print("\n3. 导入知识库数据...")
    import_knowledge_data()
    
    # 4. 导入上传文件数据
    print("\n4. 导入上传文件数据...")
    import_upload_files()
    
    print("\n" + "=" * 60)
    print("数据迁移完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()