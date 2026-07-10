# 🚀 HR Travel Reimbursement System (HR 差旅自動報銷系統)

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-lightgrey.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.0+-purple.svg)

這是一個基於 Python Flask 開發的**內部差旅費報銷系統**。旨在解決企業內部紙本報銷流程繁瑣、無法即時控管預算等痛點，並透過**自動化風險評估模型**來降低財務風險。

---

## ✨ 核心亮點功能

### 1. 👥 多重角色與權限控管 (RBAC)
- **一般員工 (Employee)**：可提出出差申請、儲存草稿、檢視報銷進度與歷史紀錄。
- **部門主管 (Manager)**：審核部屬的出差申請，並針對「高風險」的報銷單進行二次確認與批示。
- **財務會計 (Accountant)**：負責最終撥款審核，確保公司資金流向正確。

### 2. 🛡️ 智慧風險評估模型 (Risk Assessment)
報銷單送出時，系統將自動比對多項指標（例如：平日/假日住宿費上限、跨區報銷、單據是否齊全、實際金額是否超標），自動判定為 **Low Risk** 或 **High Risk**。
- **低風險 (Low Risk)**：系統自動略過主管層級，直接送交會計審核，加速撥款流程 (Fast-track)。
- **高風險 (High Risk)**：強制送交部門主管進行檢核，且需填寫駁回/核准原因。

### 3. 📊 現代化儀表板 (Dashboard)
整合 Bootstrap 5 打造的響應式儀表板，讓使用者登入後能一目了然：待辦事項數量、最近的申請單狀態、退回案件提醒。

---

## 🏗️ 系統架構圖

> *(圖片位於 `docs/系統架構圖.png`，此處為展示用佔位符)*
![System Architecture](docs/系統架構圖.png)

---

## 🛠️ 技術棧 (Tech Stack)

* **後端框架**: Python Flask
* **資料庫 ORM**: SQLAlchemy
* **資料庫**: MySQL (透過 `pymysql` 連線)
* **前端介面**: HTML5, Jinja2, Bootstrap 5
* **身分驗證**: Flask-Login

---

## 🚀 快速啟動 (Quick Start)

### 1. 安裝環境依賴

請確保你的電腦已安裝 Python 3，接著在專案根目錄下執行：

```bash
pip install -r requirements.txt
```

### 2. 設定資料庫與環境變數

1. 確保你的本機已安裝並啟動 MySQL 服務。
2. 在 MySQL 中建立一個名為 `hr_db` 的資料庫。
3. 複製範例設定檔並修改密碼：
   ```bash
   # 將範例設定檔複製一份命名為 config.py，並移入 instance 資料夾中
   mkdir -p instance
   cp config.example.py instance/config.py
   ```
4. 打開 `instance/config.py`，將裡面的 `root:password` 替換為你實際的 MySQL 帳號密碼。

### 3. 初始化資料庫並啟動應用程式

```bash
# 啟動系統 (系統會自動呼叫 create_all() 建立資料表並寫入測試帳號)
python app.py
```
伺服器啟動後，請在瀏覽器輸入 `http://localhost:3000`。

### 4. 測試帳號 (預設密碼皆為 `password123`)
- **主管**：`0000001m`
- **員工**：`0000001s`
- **會計**：`0000001a`

---

## 📁 專案目錄結構
```text
hr-app/
├── app/                  # Flask 核心應用程式
│   ├── templates/        # 前端 HTML (Jinja2)
│   ├── __init__.py       # app factory
│   ├── models.py         # 資料庫模型定義
│   └── routes.py         # 路由與核心商業邏輯 (審核、風險模型)
├── docs/                 # 專案設計文件與架構圖
├── instance/             # (被 Git 忽略) 本地安全設定檔與 DB
├── requirements.txt      # 依賴套件清單
├── config.example.py     # 設定檔範本
└── app.py                # 程式進入點
```

---
*Developed by (Your Name / Portfolio)*
