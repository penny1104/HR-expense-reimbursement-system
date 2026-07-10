# 透過 Flask 寫入資料庫執行步驟

本專案使用 Flask 提供的 API，可以讓你將資料寫入 PostgreSQL 資料庫。目前負責接收與寫入申請資料的 API 為 `/api/ocr-upload`。

## 1. 確認服務已啟動

確保 Docker Compose 已經成功啟動了你的 Web (Flask) 與 DB (PostgreSQL) 服務：

```bash
docker compose up -d
```

你的 Flask 伺服器應該會在 `http://localhost:5000` 運行。

## 2. API 說明

*   **Endpoint:** `/api/ocr-upload`
*   **Method:** `POST`
*   **Content-Type:** `application/json`

### 必填欄位 (Required Fields):
*   `request_id` (整數): 出差申請單的 ID。
*   `amount` (整數): 申請金額。
*   `date` (字串): 日期 (例如: "2023-10-25")。
*   `location` (字串): 地點。

### 選填欄位 (Optional Fields):
*   `tax_id` (字串): 統一編號。
*   `submitter_id` (整數): 提交者 ID (預設為 1)。

## 3. 測試寫入資料

你可以使用不同的工具來發送 POST 請求以寫入資料庫。

### 方法 A: 使用 cURL (終端機)

打開終端機並執行以下指令：

```bash
curl -X POST http://localhost:5000/api/ocr-upload \
-H "Content-Type: application/json" \
-d '{
    "request_id": 1,
    "amount": 1500,
    "date": "2023-10-25",
    "location": "台北市",
    "tax_id": "12345678",
    "submitter_id": 1
}'
```
> **注意 (Windows 用戶):** 如果在 Windows 的 cmd 或 PowerShell 中執行 cURL 發生跳脫字元錯誤，建議改用 Postman 或 Python 腳本測試。

### 方法 B: 使用 Python `requests` 模組

你可以撰寫一個簡單的 Python 腳本來測試：

```python
import requests

url = "http://localhost:5000/api/ocr-upload"
data = {
    "request_id": 1,
    "amount": 1200,
    "date": "2023-10-26",
    "location": "新竹市",
    "tax_id": "87654321",
    "submitter_id": 1
}

response = requests.post(url, json=data)
print(response.json())
```

### 方法 C: 使用 Postman 軟體

1. 打開 Postman，建立一個新的 Request。
2. 選擇 HTTP Method 為 **POST**。
3. URL 填入 `http://localhost:5000/api/ocr-upload`。
4. 切換到 **Body** 標籤頁，選擇 **raw** 並將格式設定為 **JSON**。
5. 填入以下 JSON 資料：
   ```json
   {
       "request_id": 2,
       "amount": 3000,
       "date": "2023-10-27",
       "location": "台中市"
   }
   ```
6. 點擊 **Send** 按鈕。

## 4. 驗證資料是否寫入成功

若 API 呼叫成功，你會收到類似以下的 JSON 回應：

```json
{
  "status": "success",
  "message": "OCR 資料已處理並成功寫入資料庫",
  "record_id": 1,
  "risk_level": "Low",
  "risk_reason": "無異常"
}
```

同時，你可以登入系統後台 (`http://localhost:5000/login`)，進入 Dashboard (`/dashboard`) 來查看剛才透過 API 新增的資料紀錄。
