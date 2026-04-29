from app import create_app
from app.models import db, Employee, TravelRequest, TravelExpense

app = create_app()
with app.app_context():
    print("\n" + "="*50)
    print("【員工帳號列表】")
    users = Employee.query.all()
    for u in users:
        print(f"ID: {u.id} | 姓名: {u.name} | 編號: {u.email} | 角色: {u.role}")

    print("\n" + "="*50)
    print("【出差申請資料表 (travel_requests)】")
    requests = TravelRequest.query.all()
    if not requests:
        print("(目前沒有申請資料)")
    for r in requests:
        print(f"ID: {r.id} | 申請人ID: {r.employee_id} | 目的地: {r.destination} | 狀態: {r.status} | 風險: {r.risk_level}")

    print("\n" + "="*50)
    print("【報銷明細資料表 (travel_expenses)】")
    expenses = TravelExpense.query.all()
    if not expenses:
        print("(目前沒有報銷明細)")
    for e in expenses:
        print(f"ID: {e.id} | 申請ID: {e.request_id} | 類別: {e.expense_category} | 金額: {e.requested_amount}")
    print("="*50 + "\n")
