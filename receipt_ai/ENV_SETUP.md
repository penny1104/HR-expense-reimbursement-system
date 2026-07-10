# 環境重建說明

本系統需要兩個 conda 環境:

| 環境 | 用途 | 環境檔 |
|------|------|--------|
| `receipt_app`  | 主程序(YOLO torch-gpu + 分類器 tensorflow) | `environment_receipt_app.yml` |
| `ocr_service`  | OCR 子程序(paddle-gpu + PaddleOCR)         | `environment_ocr_service.yml` |

## 一鍵重建

```bash
conda env create -f environment_receipt_app.yml
conda env create -f environment_ocr_service.yml
```

> 環境檔已內含 GPU wheel 的 `--extra-index-url`:
> - torch → `https://download.pytorch.org/whl/cu121`
> - paddlepaddle-gpu → `https://www.paddlepaddle.org.cn/packages/stable/cu126/`

## 若自動安裝 GPU 版失敗,手動裝(備援)

```bash
# receipt_app
conda create -n receipt_app python=3.10 -y
conda activate receipt_app
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
pip install ultralytics tensorflow tf-keras opencc flask

# ocr_service
conda create -n ocr_service python=3.10 -y
conda activate ocr_service
pip install paddlepaddle-gpu==3.3.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
pip install paddleocr opencv-python
```

## 注意

- 需 NVIDIA GPU + 夠新的驅動(本機驗證:RTX 4070 Ti SUPER)。
- torch 與 paddle **不可**裝在同一個環境/process(cuDNN DLL 衝突),
  本系統靠子程序隔離,務必維持兩個獨立環境。
- TensorFlow 在原生 Windows 只跑 CPU(分類器很小,不影響)。
- 若 `ocr_service` 環境名稱或 python 路徑不同,主程序可用環境變數
  `OCR_PYTHON` 指向正確的 python.exe。
