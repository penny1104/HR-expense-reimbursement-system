# 這是一個範例設定檔。
# 請將此檔案複製並重新命名為 config.py，放置在 instance/ 資料夾中，並填入你自己的資料庫密碼。

# 請將 password 替換成你的 MySQL 密碼
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:password@localhost:3306/hr_db'

# 關閉 SQLAlchemy 追蹤修改，節省效能
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask 應用程式的安全金鑰 (請在正式環境中更換為複雜的隨機字串)
SECRET_KEY = 'dev-secret-key-change-in-production'
