import os
from app import create_app
from app.models import db, TravelRequest, TravelExpense

app = create_app()

with app.app_context():
    # 1. 取得差旅申請單號 TQ000001 (即 ID = 1)
    req = TravelRequest.query.get(1)
    if not req:
        print("找不到差旅申請單號 TQ000001 (ID: 1)")
        exit(1)
        
    print(f"找到差旅申請單：TQ000001 (ID: {req.id}) | 目前狀態: {req.status}")
    
    # 2. 取得關聯的報銷明細並刪除實體檔案
    expenses = TravelExpense.query.filter_by(request_id=req.id).all()
    if expenses:
        print(f"正在清理報銷細目明細 (共 {len(expenses)} 筆)...")
        for exp in expenses:
            print(f" - 刪除細目 ID: {exp.id} | 類別: {exp.expense_category} | 金額: {exp.requested_amount}")
            if exp.receipt_path:
                # 取得實體路徑
                relative_path = exp.receipt_path.lstrip('/')
                absolute_path = os.path.join(app.root_path, relative_path)
                if os.path.exists(absolute_path):
                    try:
                        os.remove(absolute_path)
                        print(f"   -> 成功刪除憑證檔案: {absolute_path}")
                    except Exception as e:
                        print(f"   -> 刪除檔案失敗: {absolute_path}，錯誤: {e}")
                else:
                    print(f"   -> 檔案不存在於本機路徑: {absolute_path}")
                    
        # 3. 從資料庫刪除所有關聯的 TravelExpense 記錄
        TravelExpense.query.filter_by(request_id=req.id).delete()
        print("資料庫中的報銷細目明細已成功刪除！")
    else:
        print("此差旅單目前沒有關聯的報銷明細。")
        
    # 4. 重置 TravelRequest 的狀態為 'Approved' (已核准出差狀態，可重新申請報銷)
    # 並清除相關風險等級與主管審核評語
    req.status = 'Approved'
    req.risk_level = 'Low'
    req.risk_score = 0.0
    req.review_comment = None
    
    db.session.commit()
    print("差旅申請單狀態已重置為：'Approved' (已核准，待填寫報銷)！")
    print("\n" + "="*50)
    print("差旅單 TQ000001 之報銷單已成功完全刪除！")
    print("="*50 + "\n")
