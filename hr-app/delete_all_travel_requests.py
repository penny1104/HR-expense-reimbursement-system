import os
import shutil
from app import create_app
from app.models import db, TravelRequest, TravelExpense

app = create_app()

with app.app_context():
    print("="*50)
    print("【開始執行資料庫完整清理】")
    
    # 1. 取得所有報銷細目明細，並刪除實體檔案
    expenses = TravelExpense.query.all()
    if expenses:
        print(f"找到共 {len(expenses)} 筆報銷明細，正在清理對應的憑證實體檔案...")
        for exp in expenses:
            if exp.receipt_path:
                # 取得實體路徑
                relative_path = exp.receipt_path.lstrip('/')
                absolute_path = os.path.join(app.root_path, relative_path)
                if os.path.exists(absolute_path):
                    try:
                        os.remove(absolute_path)
                        print(f" -> 成功刪除憑證檔案: {absolute_path}")
                    except Exception as e:
                        print(f" -> 刪除檔案失敗: {absolute_path}，錯誤: {e}")
                else:
                    print(f" -> 憑證檔案不存在於本機 (可能已被手動刪除): {absolute_path}")
        
        # 刪除 TravelExpense 資料庫記錄
        num_deleted_expenses = TravelExpense.query.delete()
        print(f"資料庫共刪除 {num_deleted_expenses} 筆 `travel_expenses` 記錄。")
    else:
        print("資料庫中無任何報銷明細。")
        
    # 2. 刪除 TravelRequest 資料庫記錄 (包括 TQ000001, TQ000002 等)
    requests = TravelRequest.query.all()
    if requests:
        print(f"找到共 {len(requests)} 筆出差申請單，正在自資料庫中刪除...")
        for r in requests:
            print(f" - 刪除出差單 ID: {r.id} | 單號: TQ{r.id:06d} | 目的地: {r.destination} | 狀態: {r.status}")
        
        num_deleted_requests = TravelRequest.query.delete()
        print(f"資料庫共刪除 {num_deleted_requests} 筆 `travel_requests` 記錄。")
    else:
        print("資料庫中無任何出差申請記錄。")
        
    # 3. 額外清理 uploads 資料夾中的殘留暫存檔案
    uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
    if os.path.exists(uploads_dir):
        print("\n檢查並清理 static/uploads 下可能殘留的其它隨機暫存憑證圖檔...")
        files_deleted = 0
        for filename in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    files_deleted += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    files_deleted += 1
            except Exception as e:
                print(f"無法刪除檔案 {file_path}，錯誤: {e}")
        print(f"共成功清除 uploads 資料夾下 {files_deleted} 個殘留暫存檔。")
        
    db.session.commit()
    print("\n資料庫變更已順利 Commit 提交完成！")
    print("="*50 + "\n")
    print("出差申請與報銷明細資料已全部成功刪除！現已完全清空！")
    print("="*50 + "\n")
