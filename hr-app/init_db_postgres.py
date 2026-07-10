from app import create_app
from app.models import db, Employee, ReimbursementPolicy

app = create_app()

with app.app_context():
    try:
        print("正在建立 PostgreSQL 資料庫結構...")
        db.create_all()
        print("資料庫結構建立成功！")
        
        # Create Supervisor (主管)
        if not Employee.query.filter_by(email='0000001m').first():
            mgr = Employee(name='主管甲', email='0000001m', department='管理部', role='Manager')
            mgr.set_password('password123')
            db.session.add(mgr)
            print("已建立主管帳號 (0000001m)")
            
        # Create Employee (員工)
        if not Employee.query.filter_by(email='0000001s').first():
            user = Employee(name='員工乙', email='0000001s', department='技術部', role='Employee')
            user.set_password('password123')
            db.session.add(user)
            print("已建立員工帳號 (0000001s)")

        # Create Accountant (會計)
        if not Employee.query.filter_by(email='0000001a').first():
            acc = Employee(name='會計丙', email='0000001a', department='財務部', role='Accountant')
            acc.set_password('password123')
            db.session.add(acc)
            print("已建立會計帳號 (0000001a)")

        # Seed Reimbursement Policies (預設報銷政策)
        if not ReimbursementPolicy.query.first():
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
            print("已匯入預設報銷政策")
            
        db.session.commit()
        print("資料庫初始化完成！")
    except Exception as e:
        print(f"初始化資料庫發生錯誤: {e}")
