# Receipt System — 發票 / 收據辨識整合系統

整合四個模型的收據辨識 pipeline：

```
輸入圖片
  ↓ detect_receipt()      裁切收據(透視校正)
  ↓ classify_receipt()    Classifier(.h5) 判斷:電子 / 手寫        [主程序]
  ↓ run_ocr()             PaddleOCR 全圖辨識(4 種前處理)          [OCR 子程序 GPU]
  ↓ detect_fields()       對應的 YOLO 權重框出各欄位              [主程序 GPU]
  ↓ extract_fields()      欄位抽取:YOLO 框內 OCR 為主、regex 為輔(輔助判決)
  ↓ 回傳 JSON
```

## 架構:子程序管道(兩個 GPU 框架分離,不走 HTTP)

torch(YOLO) 與 paddle(OCR) 綁不同版本 cuDNN,在同一個 Windows process 內會
DLL 衝突。因此把 OCR 拆成獨立「子程序」,由主程序自動啟動,以 stdin/stdout
管道溝通(不開 port、不走網路):

```
┌─────────────────────────┐   stdin/stdout 管道   ┌──────────────────────────┐
│  主程序 (receipt_app)    │  ───── JSON ──────▶   │  OCR 子程序 (ocr_service)│
│  - YOLO 偵測 (torch GPU) │                       │  - PaddleOCR (paddle GPU)│
│  - 分類器 (tensorflow)   │  ◀──── JSON ──────    │  ocr_worker.py           │
│  - 欄位抽取 / app.py     │   texts / ordered     │  (主程序自動啟動)        │
└─────────────────────────┘                       └──────────────────────────┘
```
兩個 process 各自載入自己的 cuDNN,互不干擾,兩邊都跑 GPU。
OCR 子程序在第一次呼叫時自動啟動、常駐重用,主程序結束時自動關閉。
**使用者只需執行一個指令,不必另外啟動服務。**

## 目錄結構

```
receipt_system/
├── app.py                  Flask API (POST /ocr)
├── test.py                 本機批次測試
├── ocr_worker.py           OCR 子程序(paddle-gpu,主程序自動啟動)
├── start.bat               一鍵啟動 API
├── run_test.bat            一鍵批次測試
├── ocr_engine/
│   ├── pipeline.py         主流程串接
│   ├── detector.py         收據裁切(原始)
│   ├── ocr.py              OCR 客戶端(自動管理 OCR 子程序,管道溝通)
│   ├── extractor.py        欄位抽取(原始 regex + YOLO 輔助判決)
│   ├── classifier.py       Teachable Machine 分類器
│   └── field_detector.py   YOLO 欄位偵測
└── models/
    ├── electronic.pt       電子發票 YOLO 權重
    ├── handwritten.pt      手寫收據 YOLO 權重
    ├── keras_model.h5      電子/手寫分類器
    └── labels.txt          分類器標籤
```

## 環境(兩個)

**`receipt_app`** — 主程序(Python 3.10):
- torch (GPU, cu121) + ultralytics  → YOLO
- tensorflow + tf-keras             → 分類器(原生 Windows 下跑 CPU)
- opencc                            → 繁簡轉換
- flask                             → API

**`ocr_service`** — OCR 子程序(Python 3.10):
- paddlepaddle-gpu (cu126) + paddleocr → OCR(GPU)
- opencv

## 執行(只需一個指令,OCR 子程序自動啟動)

```bash
conda activate receipt_app

# 啟動 API
python app.py            # POST http://127.0.0.1:5000/ocr (form-data: image=檔案)

# 或本機批次測試
python test.py [圖片路徑...]
```

> Windows 可直接雙擊 `start.bat`(啟動 API)或 `run_test.bat`(批次測試)。
> 第一次呼叫時,主程序會自動以 `ocr_service` 環境啟動 OCR 子程序(載入模型約十幾秒),
> 之後常駐重用;主程序結束時自動關閉。
> OCR 子程序的 python 預設為 `ocr_service` 環境,可用環境變數 `OCR_PYTHON` 覆寫。

## 輸出欄位

| 欄位 | 說明 |
|------|------|
| invoice_type | electronic / handwritten |
| invoice_number | 發票號碼(電子) |
| date | 日期 |
| vendor | 賣方名稱 |
| seller_tax_id / buyer_tax_id | 賣方 / 買方統編 |
| buyer_name | 買方名稱(手寫) |
| amount | 金額 |
| category | 分類器判定類型 |
| classifier_confidence | 分類器信心 |
| yolo_fields | 各欄位的 YOLO 框位置、信心、框內文字 |

## 設計說明:輔助判決

- 類型路由：以**分類器**為準，失敗時回退原本的文字判斷 `detect_invoice_type`。
- 欄位抽取：**YOLO 框內 OCR 值優先**，框不到時回退原本的 regex 抽取。
- 原始 OCR 的所有 regex 判斷邏輯**完整保留**,僅作為後備,未刪改。
