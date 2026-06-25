import pymysql
import os
from dotenv import load_dotenv

load_dotenv('C:/Users/sanjin/Desktop/ruoyi/back/old/.env')

conn = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'ruoyi'),
    charset='utf8mb4'
)

with conn.cursor() as cursor:
    cursor.execute('SHOW TABLES')
    tables = cursor.fetchall()
    print('数据库表列表:')
    for table in tables:
        print(f'  - {table[0]}')
        cursor.execute(f'DESCRIBE {table[0]}')
        columns = cursor.fetchall()
        print('    字段:')
        for col in columns:
            print(f'      {col[0]}: {col[1]}')
        print()

conn.close()