from app import create_app
from app.models import Employee

app = create_app()
with app.app_context():
    users = Employee.query.all()
    print("目前資料庫中的帳號列表：")
    if not users:
        print(" -> (空空如也，請執行 python reset_db.py)")
    for u in users:
        print(f" - 姓名: {u.name}, 員工編號(Email): {u.email}, 角色: {u.role}")
