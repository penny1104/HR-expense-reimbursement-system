from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Employee(db.Model, UserMixin):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    role = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    requests = db.relationship('TravelRequest', backref='employee', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class TravelRequest(db.Model):
    __tablename__ = 'travel_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Draft') # Draft, Pending, Approved, Rejected, Reimbursed

    est_accommodation = db.Column(db.Float, default=0.0)
    est_transportation = db.Column(db.Float, default=0.0)
    est_meals = db.Column(db.Float, default=0.0)
    est_misc = db.Column(db.Float, default=0.0)

    # Added for risk assessment
    risk_level = db.Column(db.String(50)) # 'High' or 'Low'
    risk_score = db.Column(db.Float, default=0.0)
    
    # Reviewer's feedback
    review_comment = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expenses = db.relationship('TravelExpense', backref='request', lazy=True, cascade="all, delete-orphan")

class TravelExpense(db.Model):
    __tablename__ = 'travel_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('travel_requests.id'), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    expense_category = db.Column(db.String(100), nullable=False)
    expense_name = db.Column(db.String(200), nullable=False)
    requested_amount = db.Column(db.Float, nullable=False)
    reimbursement_days = db.Column(db.Integer)
    receipt_path = db.Column(db.String(255))
    expense_note = db.Column(db.Text) # For justifications of over-budget expenses
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
