from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Employee, TravelRequest, TravelExpense, db
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = Employee.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid email or password, please try again.', 'danger')
            
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/init-db')
def init_db():
    try:
        db.create_all()
        # Create Supervisor (主管)
        if not Employee.query.filter_by(email='0000001m').first():
            mgr = Employee(name='主管甲', email='0000001m', department='管理部', role='Manager')
            mgr.set_password('password123')
            db.session.add(mgr)
            
        # Create Employee (員工)
        if not Employee.query.filter_by(email='0000001s').first():
            user = Employee(name='員工乙', email='0000001s', department='技術部', role='Employee')
            user.set_password('password123')
            db.session.add(user)

        # Create Accountant (會計)
        if not Employee.query.filter_by(email='0000001a').first():
            acc = Employee(name='會計丙', email='0000001a', department='財務部', role='Accountant')
            acc.set_password('password123')
            db.session.add(acc)
            
        db.session.commit()
        return "資料庫已初始化。測試帳號：主管 (0000001m), 員工 (0000001s), 會計 (0000001a)，密碼皆為 'password123'。"
    except Exception as e:
        return f"Error creating db: {e}"

@main.route('/dashboard')
@login_required
def dashboard():
    # Fetch all data needed for the integrated dashboard/hub
    returned_count = TravelRequest.query.filter_by(employee_id=current_user.id, status='Rejected').count()
    # Fetch pending approvals based on role
    pending_approvals = []
    if current_user.role == 'Manager':
        pending_approvals = TravelRequest.query.filter(
            TravelRequest.status.in_(['Pending', 'ExpensePendingManager'])
        ).all()
    elif current_user.role == 'Accountant':
        pending_approvals = TravelRequest.query.filter_by(status='ExpensePendingAccounting').all()
    
    # All requests for the user (to handle the hub logic on Home)
    requests = TravelRequest.query.filter_by(employee_id=current_user.id).order_by(TravelRequest.created_at.desc()).all()
    
    # ID of the most recent rejected request for deep linking
    first_rejected = TravelRequest.query.filter_by(employee_id=current_user.id, status='Rejected').order_by(TravelRequest.created_at.desc()).first()
    first_rejected_id = first_rejected.id if first_rejected else None

    # For a small "activity log" or summary
    recent_requests = requests[:5]
    
    return render_template('dashboard.html', 
                           returned_count=returned_count, 
                           first_rejected_id=first_rejected_id,
                           pending_approvals=pending_approvals,
                           recent_requests=recent_requests,
                           requests=requests)

@main.route('/travel_hub')
@login_required
def travel_hub():
    requests = TravelRequest.query.filter_by(employee_id=current_user.id).order_by(TravelRequest.created_at.desc()).all()
    return render_template('travel_hub.html', requests=requests)

@main.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    # Load draft mode if draft_id is passed
    draft_id = request.args.get('draft_id')
    draft_req = None
    if draft_id:
        draft_req = TravelRequest.query.get(draft_id)
        if not draft_req or draft_req.employee_id != current_user.id:
            flash("找不到該草稿或無權存取", "danger")
            return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action') # draft or submit
        destinations = request.form.getlist('destination')
        destination = ", ".join([d for d in destinations if d.strip()])
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        purpose = request.form.get('purpose')
        
        est_accommodation = float(request.form.get('est_accommodation') or 0)
        est_transportation = float(request.form.get('est_transportation') or 0)
        est_meals = float(request.form.get('est_meals') or 0)
        est_misc = float(request.form.get('est_misc') or 0)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except:
            flash("Invalid date format", "danger")
            return redirect(url_for('main.apply', draft_id=draft_id) if draft_id else url_for('main.apply'))
        
        status = 'Draft' if action == 'draft' else 'Pending'
        msg = '草稿已存檔' if action == 'draft' else '出差申請已送出，等待主管審核'

        # Risk assessment for estimates
        from datetime import timedelta
        weekdays, weekends = 0, 0
        curr = start_date
        while curr < end_date:
            if curr.weekday() >= 4: # Fri=4, Sat=5
                weekends += 1
            else:
                weekdays += 1
            curr += timedelta(days=1)
        
        days_total = (end_date - start_date).days + 1
        acc_limit = weekdays * 3500 + weekends * 4500
        meal_limit = days_total * 375
        
        # Calculate risk score for Travel Request
        risk_score = 0
        if est_accommodation > acc_limit and acc_limit > 0:
            risk_score += 30
        if est_meals > meal_limit and meal_limit > 0:
            risk_score += 20
        
        risk_level = 'High' if risk_score >= 30 else 'Low'

        if draft_req:
            # Update existing
            draft_req.destination = destination
            draft_req.start_date = start_date
            draft_req.end_date = end_date
            draft_req.purpose = purpose
            draft_req.status = status
            draft_req.est_accommodation = est_accommodation
            draft_req.est_transportation = est_transportation
            draft_req.est_meals = est_meals
            draft_req.est_misc = est_misc
            draft_req.risk_score = risk_score
            draft_req.risk_level = risk_level
            
            # Clear comment only on re-submission, not on saving draft
            if action == 'submit':
                draft_req.review_comment = None
        else:
            # Create new
            new_req = TravelRequest(
                employee_id=current_user.id,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                purpose=purpose,
                status=status,
                est_accommodation=est_accommodation,
                est_transportation=est_transportation,
                est_meals=est_meals,
                est_misc=est_misc,
                risk_score=risk_score,
                risk_level=risk_level
            )
            db.session.add(new_req)
            
        db.session.commit()
        flash(msg, 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('apply.html', draft_id=draft_id, draft_req=draft_req)

@main.route('/expense-report/<int:app_id>', methods=['GET', 'POST'])
@login_required
def expense_report(app_id):
    req = TravelRequest.query.get_or_404(app_id)
    # Allow if Approved OR if Rejected but has previously submitted expenses (resubmission)
    can_access = req.status == 'Approved' or (req.status == 'Rejected' and req.expenses)
    
    if req.employee_id != current_user.id or not can_access:
        flash('無效的操作', 'danger')
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        # Clear old expenses if this is a resubmission
        TravelExpense.query.filter_by(request_id=app_id).delete()
        
        categories = request.form.getlist('expense_category[]')
        dates = request.form.getlist('expense_date[]')
        names = request.form.getlist('expense_name[]')
        amounts = request.form.getlist('requested_amount[]')
        notes = request.form.getlist('expense_note[]')
        
        total_amount = 0
        location_discrepancy = 0
        limit_violations = 0
        
        LIMITS = {
            '住宿費': { 'weekday': 3500, 'weekend': 4500 },
            '伙食費 (早餐)': 75,
            '伙食費 (午餐)': 150,
            '伙食費 (晚餐)': 150,
            '計程車': 800
        }

        for i in range(len(categories)):
            try:
                date_val = datetime.strptime(dates[i], '%Y-%m-%d').date()
                amount_val = float(amounts[i])
                name_val = names[i]
                note_val = notes[i] if i < len(notes) else ""
                
                expense = TravelExpense(
                    request_id=app_id,
                    expense_date=date_val,
                    expense_category=categories[i],
                    expense_name=name_val,
                    requested_amount=amount_val,
                    expense_note=note_val
                )
                db.session.add(expense)
                
                total_amount += amount_val
                
                # Check limits for risk scoring
                cat = categories[i]
                violation = False
                if cat == '住宿費':
                    limit = LIMITS['住宿費']['weekend'] if date_val.weekday() >= 5 else LIMITS['住宿費']['weekday']
                    if amount_val > limit: violation = True
                elif cat in LIMITS:
                    if amount_val > LIMITS[cat]: violation = True
                elif cat == '交通費' and ('計程車' in name_val or 'Taxi' in name_val):
                    if amount_val > LIMITS['計程車']: violation = True
                
                if violation:
                    limit_violations += 1
                    # Additional risk if no note provided for over-limit item
                    if not note_val or len(note_val.strip()) < 2:
                        limit_violations += 1 

                # Mock location risk
                if req.destination[0:2] not in name_val and len(name_val) > 2:
                    location_discrepancy += 1
            except Exception as e:
                pass 

        # 新的風險判定模型 (符合任一則為 High)
        has_risk = False
        risk_reasons = []

        # 1. 實際總金額 > 申請總金額
        est_total = (req.est_accommodation + req.est_transportation + req.est_meals + req.est_misc)
        if total_amount > est_total:
            has_risk = True
            risk_reasons.append("實際總額超過申請預算")

        # 2. 超過公司規範 (由 limit_violations 判定)
        if limit_violations > 0:
            has_risk = True
            risk_reasons.append("單項支出超過公司限額")

        # 3. 憑證缺失 (檢查是否有上傳全域憑證)
        receipt_file = request.files.get('receipt_global')
        if not receipt_file or receipt_file.filename == '':
            has_risk = True
            risk_reasons.append("憑證佐證缺失")

        # 4. 地點明顯不合理 (由 location_discrepancy 判定)
        if location_discrepancy > 0:
            has_risk = True
            risk_reasons.append("報銷項目地點與出差地不符")

        # 5. 類別與申請不符 (簡單檢查：如果原申請某項為0但在報銷出現)
        # 例如原申請無住宿費，但報銷有住宿費
        actual_cats = set(categories)
        if '住宿費' in actual_cats and req.est_accommodation == 0:
            has_risk = True
            risk_reasons.append("報銷類別與原申請不符 (住宿費)")

        # (Condition 6: 重複報銷 - 此處暫以模擬判定，實務上需檢查資料庫歷史)
        # mock: 如果金額完全一樣且日期一樣，視為重複 (簡化版)
        if len(amounts) != len(set(zip(dates, amounts))):
            has_risk = True
            risk_reasons.append("疑似重複報銷項目")

        if has_risk:
            req.risk_level = 'High'
            req.status = 'ExpensePendingManager'
            req.risk_score = 90 # 固定高分
            reason_str = "、".join(risk_reasons)
            flash(f'報銷單已送出！系統判定為【高風險】({reason_str})，已提交主管審核。', 'warning')
        else:
            req.risk_level = 'Low'
            req.status = 'ExpensePendingAccounting'
            req.risk_score = 10 # 固定低分
            flash('報銷單已送出！系統判定為【低風險】，已直接跳過主管，提交會計審核。', 'success')

        db.session.commit()
        return redirect(url_for('main.progress'))
        
    return render_template('expense_report.html', app_id=app_id, req=req)

@main.route('/progress')
@login_required
def progress():
    requests = TravelRequest.query.filter_by(employee_id=current_user.id).order_by(TravelRequest.created_at.desc()).all()
    return render_template('progress.html', requests=requests)

@main.route('/approvals')
@login_required
def approvals():
    if current_user.role not in ['Manager', 'Accountant']:
        flash('無權限訪問', 'danger')
        return redirect(url_for('main.dashboard'))
    
    pending_items = []
    if current_user.role == 'Manager':
        # Managers review travel requests (Pending) and high-risk expense reports (ExpensePendingManager)
        pending_items = TravelRequest.query.filter(
            TravelRequest.status.in_(['Pending', 'ExpensePendingManager'])
        ).all()
    elif current_user.role == 'Accountant':
        # Accountants review only items ready for final reimbursement
        pending_items = TravelRequest.query.filter_by(status='ExpensePendingAccounting').all()
    
    return render_template('approvals.html', pending_items=pending_items)

@main.route('/review-travel/<int:req_id>')
@login_required
def review_travel(req_id):
    req = TravelRequest.query.get_or_404(req_id)
    # Allow the manager to review, but also allow the owner of the request to view it (read-only)
    if current_user.role != 'Manager' and req.employee_id != current_user.id:
        flash('無權限訪問', 'danger')
        return redirect(url_for('main.dashboard'))
    if req.status != 'Pending':
        flash('該案件目前不處於待簽核狀態', 'info')
        return redirect(url_for('main.approvals'))
        
    return render_template('review_travel.html', req=req)

@main.route('/review-expense/<int:req_id>')
@login_required
def review_expense(req_id):
    req = TravelRequest.query.get_or_404(req_id)
    
    # Allow Managers, Accountants, and the OWNER to view.
    is_authorized = (current_user.role in ['Manager', 'Accountant']) or (req.employee_id == current_user.id)
    
    if not is_authorized:
        flash('無權限訪問', 'danger')
        return redirect(url_for('main.dashboard'))
        
    # Validation logic for reviewers (Accountant/Manager)
    if current_user.role == 'Manager' and req.status != 'ExpensePendingManager' and req.employee_id != current_user.id:
        flash('該報銷單無需主管簽核', 'info')
        return redirect(url_for('main.approvals'))
    if current_user.role == 'Accountant' and req.status != 'ExpensePendingAccounting' and req.employee_id != current_user.id:
        flash('該報銷單無需會計審核', 'info')
        return redirect(url_for('main.approvals'))
        
    return render_template('review_expense.html', req=req)

@main.route('/process-review/<int:req_id>', methods=['POST'])
@login_required
def process_review(req_id):
    action = request.form.get('action') # approve, reject
    comment = request.form.get('review_comment', '').strip()
    req = TravelRequest.query.get_or_404(req_id)
    
    if action == 'approve':
        req.review_comment = comment # Optionally save comment on approval too
        if req.status == 'Pending' and current_user.role == 'Manager':
            req.status = 'Approved'
            flash('出差申請已核准', 'success')
        elif req.status == 'ExpensePendingManager' and current_user.role == 'Manager':
            req.status = 'ExpensePendingAccounting'
            flash('報銷單（主管部分）已核准，移交會計審核', 'success')
        elif req.status == 'ExpensePendingAccounting' and current_user.role == 'Accountant':
            req.status = 'Reimbursed'
            flash('報銷單審核通過，已完成撥款程序', 'success')
        else:
            flash('非法操作', 'danger')
    elif action == 'reject':
        if not comment:
            flash('退回案件時必須填寫審核意見（原因）', 'danger')
            return redirect(url_for('main.review_travel', req_id=req.id) if req.status == 'Pending' else url_for('main.review_expense', req_id=req.id))
        
        req.status = 'Rejected'
        req.review_comment = comment
        flash('案件已被駁回，並已記錄原因', 'warning')
    
    db.session.commit()
    return redirect(url_for('main.approvals'))

@main.route('/history')
@login_required
def history():
    # Show closed requests for current user (Reimbursed, Rejected)
    requests = TravelRequest.query.filter(
        TravelRequest.employee_id == current_user.id,
        TravelRequest.status.in_(['Reimbursed', 'Rejected'])
    ).order_by(TravelRequest.created_at.desc()).all()
    
    return render_template('history.html', requests=requests)

@main.route('/receipts')
@login_required
def receipts():
    # Show all expense items (receipts) for the current user
    # We join TravelRequest to filter by the current employee
    receipts = db.session.query(TravelExpense).join(TravelRequest).filter(
        TravelRequest.employee_id == current_user.id
    ).order_by(TravelExpense.expense_date.desc()).all()
    
    return render_template('receipts.html', receipts=receipts)

@main.route('/delete-request/<int:req_id>', methods=['POST'])
@login_required
def delete_request(req_id):
    req = TravelRequest.query.get_or_404(req_id)
    if req.employee_id != current_user.id:
        flash('您無權刪除此案件', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if req.status not in ['Draft', 'Rejected', 'Pending']:
        flash('只有草稿、等待審核或已被退回的案件可以刪除', 'danger')
        return redirect(url_for('main.dashboard'))
    
    db.session.delete(req)
    db.session.commit()
    flash('案件已成功刪除', 'success')
    return redirect(url_for('main.dashboard'))

