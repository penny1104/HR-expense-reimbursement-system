import cv2
import numpy as np


def _order_points(pts):
    """將四個點排列成 [左上, 右上, 右下, 左下]"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # 左上
    rect[2] = pts[np.argmax(s)]   # 右下
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # 右上
    rect[3] = pts[np.argmax(diff)]  # 左下
    return rect


def _perspective_transform(img, pts):
    """四點透視轉換"""
    rect = _order_points(pts)
    tl, tr, br, bl = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = int(max(height_a, height_b))

    if max_w <= 0 or max_h <= 0:
        return img

    dst = np.array([
        [0, 0],
        [max_w - 1, 0],
        [max_w - 1, max_h - 1],
        [0, max_h - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(img, M, (max_w, max_h))


def detect_receipt(img):
    """
    偵測並裁切白色紙質收據 / 發票。
    1. 以亮度閾值找白紙區域
    2. 若輪廓近似四邊形 → 透視校正
    3. 否則 → bounding rect 裁切
    4. 找不到有效區域 → 原圖回傳
    """
    h_img, w_img = img.shape[:2]
    img_area = h_img * w_img

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # 白紙偵測：亮度高於 160
    _, thresh = cv2.threshold(blur, 160, 255, cv2.THRESH_BINARY)

    # 形態學閉合，填補文字造成的空洞
    kernel = np.ones((25, 25), np.uint8)
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return img

    # 取面積最大、且至少占圖片 10% 的輪廓
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    best = None
    for c in contours:
        if cv2.contourArea(c) >= img_area * 0.10:
            best = c
            break

    if best is None:
        return img

    # 嘗試多邊形近似
    peri = cv2.arcLength(best, True)
    approx = cv2.approxPolyDP(best, 0.02 * peri, True)

    if len(approx) == 4:
        pts = approx.reshape(4, 2).astype("float32")
        return _perspective_transform(img, pts)
    else:
        x, y, w, h = cv2.boundingRect(best)
        # 加一點邊距
        pad = 10
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w_img, x + w + pad)
        y2 = min(h_img, y + h + pad)
        return img[y1:y2, x1:x2]
