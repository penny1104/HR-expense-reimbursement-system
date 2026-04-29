# HR Application

這是一個以 Python Flask 建構的內部差旅費報銷系統。

## 系統架構
- **後端**: Flask (Python)
- **資料庫**: SQLAlchemy (MySQL)
- **前端**: HTML, Bootstrap 5

## 開發環境設定

1. **安裝依賴套件**:
   ```bash
   pip install -r requirements.txt
   ```

2. **設定資料庫 (MySQL)**:
   - 確定本地端運行 MySQL，並建立名為 `hr_db` 的資料庫。
   - 預設連線字串位於 `app.py` 內: `mysql+pymysql://root:password@localhost:3306/hr_db` (可根據實際情況修改)。

3. **啟動應用程式**:
   ```bash
   python app.py
   ```
   系統將會在 `http://localhost:3000` 啟動。

## 初始測試帳號
在第一次啟動專案時，若資料庫為空，可以手動註冊或透過 `python` 指令在 terminal 下新增一筆測試員工資料。
