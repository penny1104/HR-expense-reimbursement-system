from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
import os
from risk_db import TravelExpenseDB

app = Flask(__name__)
# 設定 Secret Key 以啟用 Session
app.secret_key = os.getenv("SECRET_KEY", "super_secret_dev_key")

# 初始化資料庫管理器
db_manager = TravelExpenseDB(os.getenv("DB_NAME", "travel_expense"))

@app.route('/', methods=['GET'])
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db_manager.authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('帳號或密碼錯誤，請重試', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/ocr-upload', methods=['POST'])
def ocr_upload():
    data = request.json
    
    required_fields = ['request_id', 'amount', 'date', 'location']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"status": "error", "message": "OCR 資料欄位不完整，必須包含 request_id, amount, date, location"}), 400
    
    request_id = int(data['request_id'])
    amount = int(data['amount'])
    transport_amount = int(data.get('transport_amount', 0))
    food_amount = int(data.get('food_amount', 0))
    accommodation_amount = int(data.get('accommodation_amount', 0))
    misc_amount = int(data.get('misc_amount', 0))
    date_str = data['date']
    location = data['location']
    tax_id = data.get('tax_id', '')
    submitter_id = data.get('submitter_id', 1)
    
    result = db_manager.insert_ocr_and_risk(
        request_id=request_id,
        amount=amount, 
        date_str=date_str, 
        location=location, 
        tax_id=tax_id,
        submitter_id=submitter_id,
        transport_amount=transport_amount,
        food_amount=food_amount,
        accommodation_amount=accommodation_amount,
        misc_amount=misc_amount
    )
    
    if result.get("success"):
        return jsonify({
            "status": "success",
            "message": "OCR 資料已處理並成功寫入資料庫",
            "record_id": result["id"],
            "risk_level": result["risk_level"],
            "risk_reason": result["risk_reason"]
        }), 201
    else:
        return jsonify({"status": "error", "message": result.get("error", "未知錯誤")}), 500

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    role = session.get('role')
    user_id = session.get('user_id')
    
    # 依據身分讀取資料
    if role == 'Employee':
        records = db_manager.get_records_by_user(user_id)
        travel_requests = db_manager.get_travel_requests_by_user(user_id)
        employees = []
    else:
        records = db_manager.get_all_records()
        travel_requests = db_manager.get_all_travel_requests()
        employees = db_manager.get_all_employees()
        
    # 將費用明細 (records) 依據 request_id 分組，重組成「報銷單」
    reports_dict = {}
    for r in records:
        req_id = r['request_id']
        if not req_id:
            continue
        if req_id not in reports_dict:
            reports_dict[req_id] = {
                'request_id': req_id,
                'submitter_name': r['submitter_name'],
                'destination': r['destination'],
                'status': r['status'],
                'risk_level': r['risk_level'],
                'risk_reason': r['risk_reason'],
                'created_at': r['created_at'],
                'total_amount': 0.0,
                'expenses': []
            }
        reports_dict[req_id]['total_amount'] += r['requested_amount'] or 0.0
        reports_dict[req_id]['expenses'].append(r)
        
    expense_reports = list(reports_dict.values())
    expense_reports.sort(key=lambda x: x['request_id'], reverse=True)
        
    return render_template('dashboard.html', 
                           records=records, 
                           expense_reports=expense_reports,
                           travel_requests=travel_requests, 
                           employees=employees, 
                           role=role, 
                           username=session.get('username'))

@app.route('/dashboard/update_status/<int:request_id>', methods=['POST'])
def update_status(request_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    role = session.get('role')
    if role not in ['Manager', 'Accountant']:
        flash('權限不足', 'danger')
        return redirect(url_for('dashboard'))
        
    action = request.form.get('action')
    if action in ['approve', 'reject']:
        if action == 'approve':
            status_text = f"{'主管' if role == 'Manager' else '會計'}核准"
        else:
            status_text = f"{'主管' if role == 'Manager' else '會計'}駁回"
            
        db_manager.update_status(request_id, status_text)
            
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
