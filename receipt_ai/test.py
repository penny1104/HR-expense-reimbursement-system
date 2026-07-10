# ── 先關掉各框架的雜訊 log(必須在 import pipeline 前設定) ──
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["GLOG_minloglevel"] = "3"
os.environ["YOLO_VERBOSE"] = "False"

import warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.ERROR)
try:
    from absl import logging as absl_logging
    absl_logging.set_verbosity(absl_logging.ERROR)
except Exception:
    pass

import sys
import cv2
from ocr_engine.pipeline import run_pipeline

# 只輸出這些最終欄位
FIELDS = [
    ("發票類型", "invoice_type"),
    ("發票號碼", "invoice_number"),
    ("日期",     "date"),
    ("賣方",     "vendor"),
    ("金額",     "amount"),
    ("賣方統編", "seller_tax_id"),
    ("買方統編", "buyer_tax_id"),
    ("買方名稱", "buyer_name"),
]


def test_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"圖片讀取失敗: {image_path}")
        return

    r = run_pipeline(img)

    print(f"\n===== {image_path} =====")
    for label, key in FIELDS:
        v = r.get(key)
        print(f"  {label}: {v if v not in (None, '', '無') else '-'}")
    if r.get('date_warning'):
        print(f"  日期提醒: {r.get('date_warning')}")


if __name__ == "__main__":
    pics = sys.argv[1:] or [
        'imgs/test_pic.png', 'imgs/test_pic2.jpeg', 'imgs/test_pic3.png',
        'imgs/test_pic4.jpg', 'imgs/test_pic5.jpg',
    ]
    for pic in pics:
        test_image(pic)
