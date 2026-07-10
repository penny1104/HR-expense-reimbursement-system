# PostgreSQL 遷移完成報告

我已經完成將專案從 SQLite 切換為 PostgreSQL 的所有必要修改！

## 變更項目

1. **資料庫模組 ([risk_db.py](file:///c:/Users/jeffr/.antigravity/sq-risk/risk_db.py))**:
   - 將 `sqlite3` 替換為 `psycopg2`，並使用 `DictCursor` 讓查詢結果維持可透過字典讀取的特性。
   - 將資料表建立語法中的 `AUTOINCREMENT` 改為 PostgreSQL 的 `SERIAL`。
   - 將所有 SQL 參數佔位符從 `?` 更新為 `%s`。
   - 加入了 `python-dotenv` 模組，讓系統能安全地從環境變數讀取連線資訊。

2. **工具模組 ([view_db.py](file:///c:/Users/jeffr/.antigravity/sq-risk/view_db.py))**:
   - 同樣切換至 `psycopg2` 讀取資料庫，並支援讀取環境變數。

3. **設定檔管理**:
   - 建立了 **[.env.example](file:///c:/Users/jeffr/.antigravity/sq-risk/.env.example)** 作為您的設定檔範本。
   - 建立了 **[requirements.txt](file:///c:/Users/jeffr/.antigravity/sq-risk/requirements.txt)**，確保環境相依套件清晰。

## 接下來您可以怎麼做？

> [!IMPORTANT]
> **建立您的本地環境設定檔**
> 請在專案根目錄建立一個 `.env` 檔案，並將 `.env.example` 中的內容複製進去，然後填上您日後架設好的 PostgreSQL 的帳號密碼。

1. 當您準備好 PostgreSQL 資料庫後，請先確保 `.env` 檔案設定正確。
2. 執行 `python risk_db.py` 即可自動初始化 PostgreSQL 資料表，並跑過測試情境。
3. 執行 `python view_db.py` 可以查看資料表內容是否寫入成功。
4. 執行 `python app.py` 啟動 Flask 網站進行完整測試！
