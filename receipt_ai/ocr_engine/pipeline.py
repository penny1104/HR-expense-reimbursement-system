from .ocr import run_ocr, run_ocr_crop
from .detector import detect_receipt
from .extractor import extract_fields
from .classifier import classify_receipt
from .field_detector import detect_fields
import cv2
import os


def run_pipeline(img, image_path=None):

    # 1. 裁切收據
    cropped = detect_receipt(img)

    if image_path:
        os.makedirs("debug_images", exist_ok=True)
        cv2.imwrite("debug_images/0_cropped.jpg", cropped)

    # 2. 分類器判斷類型(電子 / 手寫);失敗則回 None,稍後用文字判斷
    receipt_type, cls_conf = classify_receipt(cropped)

    # 3. 全圖 OCR(回傳 dict,含 texts 和 ordered)
    ocr_result = run_ocr(cropped)

    # 4. YOLO 框出各欄位 → 框內 OCR,組成輔助判決 hints
    yolo_hints = {}
    yolo_boxes = {}
    if receipt_type in ('electronic', 'handwritten'):
        fields = detect_fields(cropped, receipt_type)
        for name, info in fields.items():
            yolo_hints[name] = run_ocr_crop(info['crop'])
            yolo_boxes[name] = {
                'box': info['box'],
                'conf': round(info['conf'], 3),
                'text': yolo_hints[name],
            }

    # 5. 欄位抽取:分類器決定路徑、YOLO 為主 regex 為輔
    extract_fields_result = extract_fields(
        ocr_result['texts'],
        ocr_result['ordered'],
        receipt_type=receipt_type,
        yolo_hints=yolo_hints,
    )

    # 6. 智慧差旅報銷類別推導 (相容人事系統前端)
    raw_text_str = "".join(ocr_result['texts'])
    travel_category = "雜費"
    if any(k in raw_text_str for k in ["高鐵", "計程車", "車票", "捷運", "客運", "交通", "TAXI", "taxi", "機票", "火車"]):
        travel_category = "交通費"
    elif any(k in raw_text_str for k in ["住宿", "飯店", "旅館", "酒店", "民宿", "房費"]):
        travel_category = "住宿費"
    elif any(k in raw_text_str for k in ["餐", "便當", "伙食", "早餐", "午餐", "晚餐", "麵", "飯", "咖啡", "飲料", "食堂", "美味"]):
        travel_category = "伙食費"

    result = {
        **extract_fields_result,
        "category": travel_category,               # 差旅報銷類別 (例如交通費、住宿費)
        "receipt_type": receipt_type,             # 分類器判定憑證類型 (electronic / handwritten)
        "classifier_confidence": round(cls_conf, 3),
        "yolo_fields": yolo_boxes,                 # YOLO 框出的欄位(位置+信心+文字)
        "raw_text": ocr_result['texts'],
        "data": extract_fields_result.get("date"), # 重複的日期欄位 (相容舊版前端)
    }

    return result
