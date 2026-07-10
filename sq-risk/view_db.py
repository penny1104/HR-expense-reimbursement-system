"""查看 PostgreSQL 資料庫內容的小工具"""
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

# 載入環境變數
load_dotenv()

db_name = sys.argv[1] if len(sys.argv) > 1 else os.getenv("DB_NAME", "hr_db")

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=db_name,
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "your_password_here"),
        cursor_factory=RealDictCursor
    )
    cursor = conn.cursor()
    
    # 查看差旅申請單
    print(f"=== 資料庫: {db_name} | 事前申請單列表 ===\n")
    cursor.execute("SELECT * FROM travel_requests ORDER BY created_at DESC")
    requests = cursor.fetchall()
    for req in requests:
        print(f"  申請單 ID: {req['id']} | 員工 ID: {req['employee_id']} | 預估金額: {req['money']} 元 | 預估時間: {req['start_date']} 至 {req['end_date']}")
    print("\n" + "="*50 + "\n")

    # 查看報銷單
    cursor.execute("""
        SELECT e.id, e.request_id, e.ocr_amount, e.ocr_date, 
               e.ocr_expense_location as ocr_location, e.ocr_tax_id_number as ocr_tax_id,
               t.risk_level, t.review_comment as risk_reason, t.status
        FROM travel_expenses e
        LEFT JOIN travel_requests t ON e.request_id = t.id
        ORDER BY e.created_at DESC
    """)
    rows = cursor.fetchall()
    print(f"=== 報銷單紀錄 | 共 {len(rows)} 筆紀錄 ===\n")
    for r in rows:
        print(f"  報銷單 ID: {r['id']}")
        print(f"  對應申請單 ID: {r['request_id']}")
        print(f"  實際金額: {r['ocr_amount']} 元")
        print(f"  日期: {r['ocr_date']}")
        print(f"  地點: {r['ocr_location']}")
        print(f"  統編: {r['ocr_tax_id']}")
        print(f"  風險: {r['risk_level']}")
        print(f"  原因: {r['risk_reason']}")
        print(f"  狀態: {r['status']}")
        print("  " + "-" * 40)

    cursor.close()
    conn.close()
except Exception as e:
    print("無法連線到 PostgreSQL 或讀取資料，錯誤訊息：", e)