import pymysql
from instance.config import SQLALCHEMY_DATABASE_URI
import re

def create_database():
    # 從設定檔解析連線資訊
    # 格式: mysql+pymysql://root:Alice20041104@localhost:3306/hr_db
    pattern = r'mysql\+pymysql://(.*?):(.*?)@(.*?):(.*?)/(.*)'
    match = re.match(pattern, SQLALCHEMY_DATABASE_URI)
    
    if not match:
        print("無法解析 SQLALCHEMY_DATABASE_URI")
        return

    user, password, host, port, db_name = match.groups()

    try:
        # 先連線到 MySQL 伺服器 (不指定資料庫)
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=int(port)
        )
        
        with conn.cursor() as cursor:
            # 建立資料庫
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print(f"成功連線到 MySQL 並確認/建立資料庫: {db_name}")
            
        conn.close()
    except Exception as e:
        print(f"發生錯誤: {e}")
        print("\n提示: 請確認 MySQL 服務已啟動，且帳號密碼正確。")

if __name__ == "__main__":
    create_database()
