"""
数据库连接模块
提供 MySQL 数据库连接和操作功能
"""

import pymysql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'old', '.env'))


class Database:
    """数据库连接类"""
    
    def __init__(self):
        """初始化数据库连接配置"""
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', 3306))
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.database = os.getenv('DB_NAME', 'ruoyi')
        self.charset = os.getenv('DB_CHARSET', 'utf8mb4')
        self.connection = None
    
    def connect(self):
        """建立数据库连接 - 失败时直接抛出异常"""
        self.connection = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset=self.charset,
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"成功连接到数据库: {self.database}")
        return self.connection
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("数据库连接已关闭")
    
    def _ensure_connection(self):
        """确保数据库连接有效，如果断开则重新连接"""
        if not self.connection:
            self.connect()
            return
        try:
            self.connection.ping(reconnect=True)
        except Exception:
            self.connect()
    
    def execute_query(self, query, params=None):
        """
        执行查询语句 - 失败时直接抛出异常
        
        Args:
            query: SQL 查询语句
            params: 查询参数（可选）
        
        Returns:
            list: 查询结果列表
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchall()
                return result
        except pymysql.err.InterfaceError:
            self.connect()
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchall()
                return result
    
    def execute_update(self, query, params=None):
        """
        执行更新语句（INSERT、UPDATE、DELETE）- 失败时直接抛出异常
        
        Args:
            query: SQL 更新语句
            params: 查询参数（可选）
        
        Returns:
            int: 受影响的行数
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(query, params)
                self.connection.commit()
                return affected_rows
        except pymysql.err.InterfaceError:
            self.connect()
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(query, params)
                self.connection.commit()
                return affected_rows
    
    def execute_batch(self, query, params_list):
        """
        批量执行更新语句 - 失败时直接抛出异常
        
        Args:
            query: SQL 更新语句
            params_list: 参数列表
        
        Returns:
            int: 受影响的行数
        """
        if not self.connection:
            self.connect()
        
        with self.connection.cursor() as cursor:
            affected_rows = cursor.executemany(query, params_list)
            self.connection.commit()
            return affected_rows
    
    def __enter__(self):
        """支持 with 语句"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出 with 语句时自动关闭连接"""
        self.disconnect()


# 创建全局数据库实例
db = Database()


def get_db_connection():
    """
    获取数据库连接
    
    Returns:
        Database: 数据库实例
    """
    if not db.connection:
        db.connect()
    return db


# 测试连接
if __name__ == '__main__':
    with Database() as database:
        # 测试查询
        result = database.execute_query("SELECT VERSION() as version")
        if result:
            print(f"MySQL 版本: {result[0]['version']}")
        
        # 测试数据库列表
        databases = database.execute_query("SHOW DATABASES")
        print(f"可用数据库: {[db['Database'] for db in databases]}")