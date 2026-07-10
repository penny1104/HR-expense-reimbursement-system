from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta

def get_taiwan_time():
    return datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)

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
    money = db.Column(db.Float, default=0.0)            # 差旅總金額 (估計預算總和)

    # Added for risk assessment
    risk_level = db.Column(db.String(50)) # 'High' or 'Low'
    risk_score = db.Column(db.Float, default=0.0)
    
    # Reviewer's feedback
    review_comment = db.Column(db.Text)

    # Mismatch explanations
    acc_mismatch_explanation = db.Column(db.Text)
    trans_mismatch_explanation = db.Column(db.Text)
    meals_mismatch_explanation = db.Column(db.Text)
    misc_mismatch_explanation = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=get_taiwan_time)

    expenses = db.relationship('TravelExpense', backref='request', lazy=True, cascade="all, delete-orphan")

class TravelExpense(db.Model):
    __tablename__ = 'travel_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('travel_requests.id'), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    expense_category = db.Column(db.String(100), nullable=False)
    expense_name = db.Column(db.String(200), nullable=False)     # 費用名稱 (例如午餐、高鐵票)
    has_tax_id = db.Column(db.Boolean, default=False)            # 是否有統一編號
    tax_id_number = db.Column(db.String(50))                     # 統一編號號碼
    receipt_type = db.Column(db.String(50), default='收據')      # 憑證類型 (收據/發票)
    expense_location = db.Column(db.String(200), nullable=False) # 地點
    requested_amount = db.Column(db.Float, nullable=False)
    reimbursement_days = db.Column(db.Integer)
    receipt_path = db.Column(db.String(255))
    expense_note = db.Column(db.Text) # For justifications of over-budget expenses
    
    ocr_date = db.Column(db.Date)
    ocr_category = db.Column(db.String(100))
    ocr_expense_name = db.Column(db.String(200))                 # OCR 費用名稱
    ocr_amount = db.Column(db.Float)
    ocr_receipt_type = db.Column(db.String(50))
    ocr_tax_id_number = db.Column(db.String(50))
    ocr_expense_location = db.Column(db.String(200))             # OCR 地點
    is_receipt_user_uploaded = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=get_taiwan_time)

class ReimbursementPolicy(db.Model):
    __tablename__ = 'reimbursement_policies'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)     # e.g., '住宿費', '伙食費 (早餐)', '計程車', etc.
    amount_limit = db.Column(db.Float, nullable=False)       # 金額上限
    day_type = db.Column(db.String(50), default='any')       # 'any', 'weekday', 'weekend'
    start_date = db.Column(db.Date, nullable=True)           # 生效日期起
    end_date = db.Column(db.Date, nullable=True)             # 生效日期迄
    description = db.Column(db.String(255))                  # 政策描述

