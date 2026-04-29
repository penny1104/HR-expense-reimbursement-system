from app import create_app
from app.models import db, Employee

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    
    # 主管 (Manager)
    mgr = Employee(name='主管甲', email='0000001m', department='管理部', role='Manager')
    mgr.set_password('password123')
    db.session.add(mgr)
    
    # 員工 (Employee)
    emp = Employee(name='員工乙', email='0000001s', department='技術部', role='Employee')
    emp.set_password('password123')
    db.session.add(emp)
    
    # 會計 (Accountant)
    acc = Employee(name='會計丙', email='0000001a', department='財務部', role='Accountant')
    acc.set_password('password123')
    db.session.add(acc)
    
    db.session.commit()
    print("Database completely reset and seeded with users!")
