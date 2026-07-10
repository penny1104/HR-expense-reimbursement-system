"""
YOLO 欄位偵測 — 框出收據上各欄位的位置,供「輔助判決」使用。

電子發票權重 (electronic.pt) 類別:
    amount, buyer_taxid, date, invoice_num, seller, seller_taxid
手寫收據權重 (handwritten.pt) 類別:
    amount, buyer, buyer_taxid, date, stamp

回傳每個欄位「信心最高」的那一框,並附上裁切後的影像。
"""
import os

_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
_WEIGHTS = {
    "electronic":  os.path.join(_MODEL_DIR, "electronic.pt"),
    "handwritten": os.path.join(_MODEL_DIR, "handwritten.pt"),
}

_models = {}   # 快取已載入的 YOLO 模型


def _get_model(receipt_type):
    if receipt_type not in _WEIGHTS:
        return None
    if receipt_type not in _models:
        from ultralytics import YOLO
        _models[receipt_type] = YOLO(_WEIGHTS[receipt_type])
    return _models[receipt_type]


def detect_fields(img, receipt_type, conf=0.25, pad=4):
    """
    對影像跑對應類型的 YOLO,回傳:
      {
        class_name: {
          'box':  (x1, y1, x2, y2),
          'conf': float,
          'crop': np.ndarray,   # 該欄位裁切影像(含小邊距)
        }, ...
      }
    每個類別只保留信心最高的一框。失敗回傳 {}。
    """
    model = _get_model(receipt_type)
    if model is None:
        return {}

    try:
        results = model.predict(img, conf=conf, verbose=False)
    except Exception as e:
        print(f"[field_detector] YOLO 推論失敗: {e}")
        return {}

    h, w = img.shape[:2]
    fields = {}

    for res in results:
        names = res.names
        boxes = res.boxes
        if boxes is None:
            continue
        for b in boxes:
            cls_id = int(b.cls[0])
            cls_name = names[cls_id]
            score = float(b.conf[0])
            # 同類別保留信心最高
            if cls_name in fields and fields[cls_name]['conf'] >= score:
                continue
            x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(w, x2 + pad)
            y2 = min(h, y2 + pad)
            crop = img[y1:y2, x1:x2].copy()
            fields[cls_name] = {
                'box': (x1, y1, x2, y2),
                'conf': score,
                'crop': crop,
            }

    return fields
