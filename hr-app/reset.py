import sys
import importlib.util
from app.models import db, Employee

spec = importlib.util.spec_from_file_location("hr_app_module", "app.py")
hr_app = importlib.util.module_from_spec(spec)
sys.modules["hr_app_module"] = hr_app
spec.loader.exec_module(hr_app)

app = hr_app.create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    
    admin = Employee(name='Admin Test', email='admin@hr.com', department='HR', role='Manager')
    admin.set_password('password123')
    db.session.add(admin)
    
    user = Employee(name='大雄', email='user@hr.com', department='IT', role='Employee')
    user.set_password('password123')
    db.session.add(user)
    
    db.session.commit()
    print("Database completely reset and seeded with users!")
