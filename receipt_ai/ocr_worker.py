"""
OCR worker — 由主程序自動以「子程序」啟動(ocr_service env, paddle-gpu)。
透過 stdin/stdout 管道與主程序溝通(不走 HTTP / 不開 port)。

為什麼獨立子程序:torch(YOLO) 與 paddle(OCR) 綁不同版本 cuDNN,同一個
Windows process 內會 DLL 衝突。拆成子程序,本檔只 import paddle、不碰 torch,
即可讓 OCR 在 GPU 上跑,與主程序的 YOLO GPU 並行而互不干擾。

協定(每行一個 JSON):
  收(stdin):  {"cmd":"ocr_raw","path":"<img>"} / {"cmd":"ocr_crop","path":"<img>"} / {"cmd":"shutdown"}
  回(stdout): {"texts":[...],"ordered":[...]}  /  {"text":"..."}

重點:PaddleOCR 會把模型載入等雜訊印到 stdout,會污染 JSON 協定。
啟動時先把 fd1(stdout) 重導到 stderr,另存一份原始 stdout 專供協定輸出。
"""
import os
import sys
import json

# ── 先把所有函式庫的 stdout 雜訊趕到 stderr,保留乾淨的協定通道 ──
_PROTOCOL_FD = os.dup(1)          # 複製一份原始 stdout(連到主程序的管道)
os.dup2(2, 1)                     # fd1 → stderr,之後任何函式庫印到 stdout 都進 stderr
_protocol = os.fdopen(_PROTOCOL_FD, "w", encoding="utf-8")
sys.stdout = sys.stderr           # Python 層的 print 也導到 stderr
try:
    sys.stdin.reconfigure(encoding="utf-8")
except Exception:
    pass

os.environ["FLAGS_log_level"] = "3"
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ["GLOG_minloglevel"] = "3"

import cv2
import numpy as np
from paddleocr import PaddleOCR


def _pick_device():
    try:
        import paddle
        if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
            return "gpu"
    except Exception:
        pass
    return "cpu"


_DEVICE = _pick_device()
ocr = PaddleOCR(use_angle_cls=True, lang="ch", device=_DEVICE, enable_mkldnn=False)


# ============ 影像前處理(與原始 OCR 完全一致) ============
def _upscale(img, target_min=1200):
    h, w = img.shape[:2]
    short = min(h, w)
    if short < target_min:
        scale = target_min / short
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    return img


def _safe_resize(img, max_side=2400):
    h, w = img.shape[:2]
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    return img


def _preprocess_for_handwriting(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=15, templateWindowSize=7, searchWindowSize=21)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 15
    )
    return thresh


def _preprocess_sharp(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    _, thresh = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _parse_ocr_result(result):
    texts = []
    for res in result:
        if not res:
            continue
        if isinstance(res, dict) and "rec_texts" in res:
            for t in res["rec_texts"]:
                if t and t.strip():
                    texts.append(t.strip())
        elif isinstance(res, list):
            for item in res:
                if isinstance(item, list) and len(item) >= 2:
                    text_info = item[1]
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 1:
                        t = text_info[0]
                        if t and t.strip():
                            texts.append(t.strip())
    return texts


# ============ OCR 核心(邏輯與原始一致) ============
def run_ocr(img):
    img = _upscale(img, target_min=1200)
    img = _safe_resize(img, max_side=2400)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh_hw = _preprocess_for_handwriting(img)
    thresh_sharp = _preprocess_sharp(img)

    versions = [img, gray, thresh_hw, thresh_sharp]
    ordered = []
    all_results = []

    for i, v in enumerate(versions):
        if len(v.shape) == 2:
            v = cv2.cvtColor(v, cv2.COLOR_GRAY2BGR)
        try:
            result = ocr.predict(v)
            texts = _parse_ocr_result(result)
            all_results.extend(texts)
            if i == 0:
                ordered = texts
        except Exception:
            continue

    seen = {}
    for t in all_results:
        seen[t] = seen.get(t, 0) + 1
    deduped = sorted(seen.keys(), key=lambda x: -seen[x])
    return {"texts": deduped, "ordered": ordered}


def run_ocr_crop(crop):
    if crop is None or crop.size == 0:
        return ""
    crop = _upscale(crop, target_min=320)
    crop = _safe_resize(crop, max_side=1600)

    versions = [crop, _preprocess_sharp(crop)]
    texts = []
    for v in versions:
        if len(v.shape) == 2:
            v = cv2.cvtColor(v, cv2.COLOR_GRAY2BGR)
        try:
            result = ocr.predict(v)
            texts.extend(_parse_ocr_result(result))
        except Exception:
            continue
    seen = set()
    out = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return " ".join(out)


def _send(obj):
    _protocol.write(json.dumps(obj, ensure_ascii=False) + "\n")
    _protocol.flush()


def main():
    # 通知主程序:模型已載入、可開始服務
    _send({"ready": True, "device": _DEVICE})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            _send({"error": "bad json"})
            continue

        cmd = req.get("cmd")
        if cmd == "shutdown":
            break

        try:
            img = cv2.imread(req["path"])
            if cmd == "ocr_raw":
                _send(run_ocr(img))
            elif cmd == "ocr_crop":
                _send({"text": run_ocr_crop(img)})
            else:
                _send({"error": f"unknown cmd: {cmd}"})
        except Exception as e:
            _send({"error": str(e)})


if __name__ == "__main__":
    main()
