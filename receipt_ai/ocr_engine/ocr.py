"""
OCR 客戶端 — 自動啟動並管理 OCR 子程序(ocr_worker.py),透過 stdin/stdout
管道溝通(不走 HTTP、不開 port)。

主程序(receipt_app env)綁 torch-gpu(YOLO)+tensorflow(分類器);
OCR 子程序(ocr_service env)綁 paddle-gpu。兩者分屬不同 process/環境,
徹底避開 torch 與 paddle 的 cuDNN DLL 衝突,兩邊都能用 GPU。

子程序在第一次呼叫時自動啟動,常駐於記憶體重複使用;程式結束時自動關閉。
OCR 子程序所用的 python 可用環境變數 OCR_PYTHON 覆寫。
"""
import os
import sys
import json
import atexit
import threading
import tempfile
import subprocess

import cv2

# OCR 子程序要用的 python(ocr_service 環境,內含 paddle-gpu)
def _find_ocr_python():
    env_py = os.environ.get("OCR_PYTHON")
    if env_py:
        return env_py
    user_profile = os.environ.get("USERPROFILE", "C:\\Users\\ACER")
    candidates = [
        r"D:\conda_envs\ocr_service\python.exe",
        os.path.join(user_profile, "miniconda3", "envs", "ocr_service", "python.exe"),
        os.path.join(user_profile, "anaconda3", "envs", "ocr_service", "python.exe"),
        r"C:\Users\ACER\miniconda3\envs\ocr_service\python.exe",
        r"C:\Users\ACER\anaconda3\envs\ocr_service\python.exe",
        r"D:\miniconda\envs\ocr_service\python.exe",
        r"D:\anaconda\envs\ocr_service\python.exe",
        r"C:\Users\TsutaCapybara\anaconda3\envs\ocr_service\python.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]  # fallback to first candidate if none exist

_OCR_PYTHON = _find_ocr_python()
_WORKER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ocr_worker.py")

_proc = None
_lock = threading.Lock()


def _start_worker():
    """啟動 OCR 子程序並等待它載入完模型(回報 ready)。"""
    if not os.path.exists(_OCR_PYTHON):
        raise RuntimeError(
            f"找不到 OCR 子程序的 python:\n    {_OCR_PYTHON}\n"
            f"請確認 ocr_service 環境存在,或設定環境變數 OCR_PYTHON 指向正確的 python.exe"
        )
    proc = subprocess.Popen(
        [_OCR_PYTHON, _WORKER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,   # 丟掉 paddle 的雜訊 log
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    # 等待 {"ready": true}(模型載入約十幾秒)
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("OCR 子程序啟動失敗(未回報 ready)")
    info = json.loads(line)
    if not info.get("ready"):
        raise RuntimeError(f"OCR 子程序回報異常: {info}")
    atexit.register(_shutdown)
    return proc


def _ensure_worker():
    global _proc
    if _proc is None or _proc.poll() is not None:
        _proc = _start_worker()
    return _proc


def _shutdown():
    global _proc
    if _proc is not None and _proc.poll() is None:
        try:
            _proc.stdin.write('{"cmd":"shutdown"}\n')
            _proc.stdin.flush()
            _proc.wait(timeout=5)
        except Exception:
            try:
                _proc.terminate()
            except Exception:
                pass
    _proc = None


def _request(cmd, img):
    """把影像寫到暫存檔,送一筆請求給子程序,讀回 JSON 結果。"""
    with _lock:
        proc = _ensure_worker()
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            cv2.imwrite(path, img)
            proc.stdin.write(json.dumps({"cmd": cmd, "path": path}) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass
        if not line:
            raise RuntimeError("OCR 子程序無回應(可能已崩潰)")
        res = json.loads(line)
        if isinstance(res, dict) and "error" in res:
            raise RuntimeError(f"OCR 子程序錯誤: {res['error']}")
        return res


def run_ocr(img):
    """全圖 OCR → {'texts': [...], 'ordered': [...]}"""
    return _request("ocr_raw", img)


def run_ocr_crop(crop):
    """YOLO 欄位裁切區 OCR → 合併文字字串"""
    if crop is None or crop.size == 0:
        return ""
    return _request("ocr_crop", crop).get("text", "")
