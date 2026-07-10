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

from flask import Flask, request, jsonify
import cv2
import numpy as np

from ocr_engine.pipeline import run_pipeline

app = Flask(__name__)

@app.route('/ocr', methods=['POST'])
def ocr_api():
    file = request.files['image']
    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)

    result = run_pipeline(img)

    # 回傳完整欄位，確保向前相容性與除錯資訊
    return jsonify(result)


if __name__ == "__main__":
    # use_reloader=False:避免 Flask 重載器重複啟動 OCR 子程序(佔雙倍 GPU)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
