from app import create_app
from app.models import db, Employee, ReimbursementPolicy

app = create_app()
with app.app_context():
    print("正在清空並重建資料庫表...")
    db.drop_all()
    db.create_all()
    print("資料庫結構重建成功！")
    
    # 建立 主管 (Manager)
    mgr = Employee(name='主管甲', email='0000001m', department='管理部', role='Manager')
    mgr.set_password('password123')
    db.session.add(mgr)
    
    # 建立 員工 (Employee)
    emp = Employee(name='員工乙', email='0000001s', department='技術部', role='Employee')
    emp.set_password('password123')
    db.session.add(emp)
    
    # 建立 會計 (Accountant)
    acc = Employee(name='會計丙', email='0000001a', department='財務部', role='Accountant')
    acc.set_password('password123')
    db.session.add(acc)
    
    # 建立 系統管理員 (Admin)
    admin = Employee(name='系統管理員', email='admin', department='資訊部', role='Admin')
    admin.set_password('admin123')
    db.session.add(admin)
    
    # 匯入預設報銷政策規定
    default_policies = [
        ReimbursementPolicy(category='住宿費', amount_limit=3500.0, day_type='weekday', description='住宿費平日上限 $3,500/晚'),
        ReimbursementPolicy(category='住宿費', amount_limit=4500.0, day_type='weekend', description='住宿費假日上限 $4,500/晚'),
        ReimbursementPolicy(category='伙食費 (早餐)', amount_limit=75.0, day_type='any', description='伙食費 (早餐) 上限 $75/天'),
        ReimbursementPolicy(category='伙食費 (午餐)', amount_limit=150.0, day_type='any', description='伙食費 (午餐) 上限 $150/天'),
        ReimbursementPolicy(category='伙食費 (晚餐)', amount_limit=150.0, day_type='any', description='伙食費 (晚餐) 上限 $150/天'),
        ReimbursementPolicy(category='計程車', amount_limit=800.0, day_type='any', description='計程車單趟上限 $800'),
        ReimbursementPolicy(category='交通費', amount_limit=999999.0, day_type='any', description='交通費（一般交通核實報銷）'),
        ReimbursementPolicy(category='雜費', amount_limit=999999.0, day_type='any', description='雜費（核實報銷）')
    ]
    db.session.bulk_save_objects(default_policies)
    
    db.session.commit()
    print("資料庫已完全清空，並成功匯入初始帳號與預設政策規定！")
