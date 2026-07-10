import os
import sys
import subprocess
import atexit
from app import create_app

app = create_app()

subprocesses = []

def cleanup_subprocesses():
    for p in subprocesses:
        try:
            p.terminate()
            p.wait(timeout=2)
        except:
            pass

if __name__ == '__main__':
    # 僅在主 Flask 進程啟動時執行，避免 Flask debug 模式的 reloader 觸發二次啟動
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("\n" + "="*70)
        print("  正在自動連帶啟動 Companion 服務 (AI 憑證辨識 & 風控審計)...")
        print("="*70)
        
        # 1. 啟動 AI 憑證辨識服務 (Port 5000)
        receipt_python = r"D:\conda_envs\receipt_app\python.exe"
        receipt_script = r"D:\HR\receipt_ai\app.py"
        if os.path.exists(receipt_python):
            try:
                p1 = subprocess.Popen([receipt_python, receipt_script], cwd=r"D:\HR\receipt_ai")
                subprocesses.append(p1)
                print("  [OK] AI 憑證辨識服務已啟動 (Port 5000)...")
            except Exception as e:
                print(f"  [Error] AI 憑證辨識服務啟動失敗: {e}")
        else:
            print("  [Warning] 找不到 D:\\conda_envs\\receipt_app 虛擬環境，跳過 AI 服務啟動")

        # 2. 啟動 風控審計服務 (Port 5001)
        sq_script = r"D:\HR\sq-risk\app.py"
        try:
            p2 = subprocess.Popen(["python", sq_script], cwd=r"D:\HR\sq-risk")
            subprocesses.append(p2)
            print("  [OK] 風控審計服務已啟動 (Port 5001)...")
        except Exception as e:
            print(f"  [Error] 風控審計服務啟動失敗: {e}")
            
        print("="*70 + "\n")
        
        # 註冊當主應用程式關閉時，乾淨地結束子進程
        atexit.register(cleanup_subprocesses)

    app.run(debug=True, port=3000)
