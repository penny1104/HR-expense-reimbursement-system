"""
收據類型分類器 — 判別「電子發票」或「手寫收據」。

使用 Teachable Machine 匯出的 Keras 模型 (keras_model.h5)。
輸入 224x224x3,正規化到 [-1, 1]。
labels.txt: "0 electronic_receipt" / "1 handwritten_receipt"
"""
import os
import cv2
import numpy as np

_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
_H5_PATH = os.path.join(_MODEL_DIR, "keras_model.h5")
_LABELS_PATH = os.path.join(_MODEL_DIR, "labels.txt")

_model = None
_labels = None


def _load_labels():
    """讀 labels.txt → {index: 'electronic'|'handwritten'}"""
    mapping = {}
    with open(_LABELS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, name = line.split(maxsplit=1)
            # electronic_receipt → electronic;handwritten_receipt → handwritten
            simple = "electronic" if "electronic" in name.lower() else "handwritten"
            mapping[int(idx)] = simple
    return mapping


def _get_keras():
    """優先用 tf_keras(Keras 2 舊版 API,Teachable Machine 模型原生相容);
    退而求其次用 tensorflow.keras / keras。"""
    try:
        import tf_keras as keras
        return keras
    except Exception:
        pass
    try:
        from tensorflow import keras
        return keras
    except Exception:
        import keras
        return keras


def _patched_dw(keras):
    """Teachable Machine 的 .h5 帶有新版 keras 不認的 DepthwiseConv2D 'groups' 參數,
    用子類別把它吃掉。"""
    DepthwiseConv2D = keras.layers.DepthwiseConv2D

    class PatchedDepthwiseConv2D(DepthwiseConv2D):
        def __init__(self, *args, **kwargs):
            kwargs.pop("groups", None)
            super().__init__(*args, **kwargs)

    return {"DepthwiseConv2D": PatchedDepthwiseConv2D}


def _ascii_safe_path(path):
    """TensorFlow 在含中文/非 ASCII 路徑下讀 .h5 會 UnicodeDecodeError,
    若偵測到非 ASCII 就複製到暫存的純英文路徑。"""
    try:
        path.encode("ascii")
        return path
    except UnicodeEncodeError:
        import tempfile, shutil
        tmp = os.path.join(tempfile.gettempdir(), "receipt_classifier.h5")
        if not os.path.exists(tmp) or os.path.getsize(tmp) != os.path.getsize(path):
            shutil.copy2(path, tmp)
        return tmp


def _load():
    global _model, _labels
    if _model is not None:
        return
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    keras = _get_keras()
    h5_path = _ascii_safe_path(_H5_PATH)
    _model = keras.models.load_model(
        h5_path, compile=False, custom_objects=_patched_dw(keras)
    )
    _labels = _load_labels()


def classify_receipt(img):
    """
    回傳 (receipt_type, confidence)
      receipt_type: 'electronic' | 'handwritten'
      confidence:   float 0~1
    若模型載入或推論失敗,回傳 (None, 0.0),呼叫端可退回文字判斷。
    """
    try:
        _load()
    except Exception as e:
        print(f"[classifier] 載入失敗,改用文字判斷: {e}")
        return None, 0.0

    try:
        # 預處理:BGR→RGB、resize 224、正規化 [-1,1]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA)
        arr = resized.astype(np.float32)
        arr = (arr / 127.5) - 1.0
        arr = np.expand_dims(arr, axis=0)

        preds = _model.predict(arr, verbose=0)[0]
        idx = int(np.argmax(preds))
        return _labels.get(idx, "handwritten"), float(preds[idx])
    except Exception as e:
        print(f"[classifier] 推論失敗,改用文字判斷: {e}")
        return None, 0.0
