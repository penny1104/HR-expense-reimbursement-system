# 差旅報銷系統 (Travel Expense System)

這是一個基於 Flask 與 PostgreSQL 的差旅報銷系統，專案已經使用 Docker 容器化，方便開發與部署。

## 開發環境建置 (For Flask Developer)

為了方便開發，本專案已設定好 Docker Compose，你可以一鍵同時啟動 **Flask 網站** 與 **PostgreSQL 資料庫**。

### 1. 環境變數設定
在啟動專案之前，請先設定資料庫的環境變數。請在專案根目錄下，將 `.env.example` 複製一份並命名為 `.env`：
```bash
# Windows (PowerShell)
cp .env.example .env
```
這會確保你在本地端執行 Python 腳本時，能使用正確的密碼 (`your_password_here`) 連線到 Docker 內的資料庫。

### 2. 啟動專案 (Docker)
請確認你的電腦已安裝並開啟 Docker Desktop。
打開終端機 (Terminal / PowerShell)，在專案根目錄下執行：
```bash
docker compose up -d --build
```
*這會自動下載需要的環境、建立 PostgreSQL 資料庫，並將 Flask 網站跑在背景。*

### 3. 初始化與查看資料庫
專案啟動後，你需要建立資料表並寫入預設的測試資料（含測試帳號與申請單）。請執行：
```bash
python risk_db.py
```
若想確認資料庫是否成功寫入，可以使用我們準備好的小工具來查看內容：
```bash
python view_db.py
```

### 4. 開發與熱重載 (Hot Reload)
- 網站網址為：[http://localhost:5000](http://localhost:5000)
- `docker-compose.yml` 內已經設定了 `volumes: - ./:/app` 與 `FLASK_DEBUG=1`。
- **這代表當你修改本地端的 `app.py` 或是任何 `templates/` 下的 HTML 檔案並存檔時，Flask 會自動重新載入，你只需要重新整理網頁即可看到變更，不需重新打包 Docker！**

### 5. 查看 Log (除錯用)
如果程式執行發生錯誤，你想看 Flask 印出的錯誤訊息，可以執行：
```bash
docker compose logs -f web
```
*(按 `Ctrl + C` 可離開 log 畫面)*

### 6. 關閉專案
開發結束後，若要關閉容器：
```bash
docker compose down
```

## 測試帳號
系統啟動時會自動在 PostgreSQL 建立以下測試帳號：
- 員工：`employee` / `emp123`
- 會計：`accountant` / `acc123`
- 主管：`manager` / `mgr123`
