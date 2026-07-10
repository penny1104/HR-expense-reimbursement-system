import os
import shutil
from datetime import datetime, date
from app import create_app
from app.models import db, Employee, TravelRequest, TravelExpense

app = create_app()

with app.app_context():
    # 1. 建立上傳資料夾並拷貝樣品圖片
    uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        print(f"建立資料夾: {uploads_dir}")
        
    src_img_1 = r"d:\HR\hr-app\debug_images\1_original.jpg"
    src_img_2 = r"d:\HR\hr-app\app\static\images\HSR-6.png"
    
    dest_path_1 = os.path.join(uploads_dir, "receipt_sample_1.jpg")
    dest_path_2 = os.path.join(uploads_dir, "receipt_sample_2.jpg")
    dest_path_3 = os.path.join(uploads_dir, "receipt_sample_3.jpg")
    
    if os.path.exists(src_img_1):
        shutil.copy(src_img_1, dest_path_1)
        shutil.copy(src_img_1, dest_path_3)
        print("拷貝發票樣品圖完成")
    if os.path.exists(src_img_2):
        shutil.copy(src_img_2, dest_path_2)
        print("拷貝高鐵樣品圖完成")
        
    # 2. 清除之前的舊申請，避免衝突
    print("正在清空舊的出差與報銷資料...")
    TravelExpense.query.delete()
    TravelRequest.query.delete()
    
    # 3. 尋找員工帳號 (員工乙的 email 是 0000001s, ID 為 2)
    emp = Employee.query.filter_by(email="0000001s").first()
    if not emp:
        print("找不到員工乙 (0000001s)，請先運行 /init-db 初始化帳號")
        exit(1)
        
    print(f"找到員工: {emp.name} (ID: {emp.id})")
    
    # 4. 插入一筆已核准的出差申請 (新北市出差，預算總額 5,000 元)
    req = TravelRequest(
        id=1,
        employee_id=emp.id,
        destination="新北市",
        start_date=date(2026, 5, 25),
        end_date=date(2026, 5, 30),
        purpose="拜訪新北市重要客戶與技術交流",
        status="ExpensePendingManager", # 處於報銷待主管審核狀態
        est_accommodation=3000.0,
        est_transportation=1000.0,
        est_meals=500.0,
        est_misc=500.0,
        money=5000.0,
        risk_level="High",
        acc_mismatch_explanation="住宿天數與預期不同，實際花費超支",
        trans_mismatch_explanation="高鐵與計程車費超出預估的交通費上限",
        meals_mismatch_explanation="部分餐費由主辦方提供，無額外報銷項目",
        misc_mismatch_explanation="雜費實際支出少於預估"
    )
    db.session.add(req)
    db.session.commit()
    print("成功建立出差申請 (ID: 1)")
    
    # 5. 插入消費細目明細 (呈現修改過的藍框與違規紅框)
    # 明細 1：住宿費 - 超出出差申請的住宿預算 (3000)，觸發紅色 violation
    exp1 = TravelExpense(
        request_id=req.id,
        expense_date=date(2026, 5, 28),
        expense_category="住宿費",
        expense_name="馬可商旅",
        has_tax_id=True,
        tax_id_number="24510470",
        receipt_type="統一發票",
        expense_location="新北市",
        requested_amount=3800.0, # 填寫 3800，超出預算 3000，觸發違規紅框！
        expense_note="",
        receipt_path="/static/uploads/receipt_sample_1.jpg",
        
        # OCR 快取：完全一致，所以沒有藍框，只有預算超額的紅框！
        ocr_date=date(2026, 5, 28),
        ocr_category="住宿費",
        ocr_expense_name="馬可商旅",
        ocr_amount=3800.0,
        ocr_receipt_type="統一發票",
        ocr_tax_id_number="24510470",
        ocr_expense_location="新北市",
        is_receipt_user_uploaded=False
    )
    
    # 明細 2：雜費 - 手動修改了地點 (OCR 辨識是台北市，員工手動選取新北市以符合出差地) -> 觸發藍色 modified 框
    exp2 = TravelExpense(
        request_id=req.id,
        expense_date=date(2026, 5, 28),
        expense_category="雜費",
        expense_name="馬可先生麵包坊",
        has_tax_id=True,
        tax_id_number="24510470",
        receipt_type="統一發票",
        expense_location="新北市", # 員工手動選取新北市 (符合出差目的地，無紅框)
        requested_amount=314.0,
        receipt_path="/static/uploads/receipt_sample_2.jpg",
        
        ocr_date=date(2026, 5, 28),
        ocr_category="雜費",
        ocr_expense_name="馬可先生麵包坊",
        ocr_amount=314.0,
        ocr_receipt_type="統一發票",
        ocr_tax_id_number="24510470",
        ocr_expense_location="台北市", # 原始辨識為台北市，與員工填寫不符，觸發藍框！
        is_receipt_user_uploaded=False
    )
    
    # 明細 3：交通費 - 員工手動上傳憑證、手動修改了金額 (OCR 辨識 1000 元，員工手動改成 1200 元)
    # 並且金額 (1200) 超過交通費核准預算 (1000) -> 觸發金額紅框 + 金額藍框(在審核頁面優先呈現違規紅框) + 憑證上傳藍框
    exp3 = TravelExpense(
        request_id=req.id,
        expense_date=date(2026, 5, 28),
        expense_category="交通費",
        expense_name="計程車",
        has_tax_id=False,
        receipt_type="收據",
        expense_location="新北市",
        requested_amount=1200.0, # 填寫 1200，超出交通預算 1000，金額亮紅框！同時與 OCR 不符，是修改項目！
        receipt_path="/static/uploads/receipt_sample_3.jpg",
        
        ocr_date=date(2026, 5, 28),
        ocr_category="交通費",
        ocr_expense_name="計程車",
        ocr_amount=1000.0, # 原始辨識為 1000，金額手動修改！
        ocr_receipt_type="收據",
        ocr_expense_location="新北市",
        is_receipt_user_uploaded=True # 標記為手動上傳憑證，觸發藍色框標記！
    )
    
    db.session.add_all([exp1, exp2, exp3])
    db.session.commit()
    print("成功建立三筆報銷項目明細，包含藍框與紅框測試案例！")
    
    print("\n" + "="*50)
    print("資料庫 Seed 成功！")
    print("現在，您可以立即造訪以下網址測試：")
    print("1. 審核頁面 (主管端/會計端)： http://localhost:3000/review-expense/1")
    print("2. 簽核中心 (主管/會計首頁)： http://localhost:3000/approvals")
    print("3. 登入員工乙重新查看草稿狀態： http://localhost:3000/dashboard")
    print("="*50 + "\n")
