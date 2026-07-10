from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Employee, TravelRequest, TravelExpense, ReimbursementPolicy, db
from datetime import datetime
from app.chatbot import match_faq

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
            
        db.session.commit()
        return "資料庫已初始化。測試帳號：主管 (0000001m), 員工 (0000001s), 會計 (0000001a)，密碼皆為 'password123'。預設報銷規則已匯入。"
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
        pending_approvals = TravelRequest.query.filter(
            TravelRequest.status.in_(['TravelPendingAccounting', 'ExpensePendingAccounting'])
        ).all()
    
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
            draft_req.money = est_accommodation + est_transportation + est_meals + est_misc
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
                money=est_accommodation + est_transportation + est_meals + est_misc,
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
        categories = request.form.getlist('expense_category[]')
        dates = request.form.getlist('expense_date[]')
        expense_names = request.form.getlist('expense_name[]')
        has_tax_ids = request.form.getlist('has_tax_id[]')
        receipt_types = request.form.getlist('receipt_type[]')
        expense_locations = request.form.getlist('expense_location[]')
        amounts = request.form.getlist('requested_amount[]')
        notes = request.form.getlist('expense_note[]')
        
        # 1. 檢查同單重複項目
        valid_items = []
        for i in range(len(categories)):
            if i < len(dates) and i < len(amounts) and dates[i].strip() and amounts[i].strip():
                try:
                    valid_items.append((dates[i].strip(), float(amounts[i])))
                except ValueError:
                    pass
                    
        if len(valid_items) != len(set(valid_items)):
            flash('報銷失敗！明細中含有相同日期與金額的重複項目，一律不得申報報銷。', 'danger')
            return redirect(url_for('main.expense_report', app_id=app_id))
            
        # 2. 檢查與資料庫中其他出差報銷相同之項目
        for dt, amt in valid_items:
            try:
                date_val = datetime.strptime(dt, '%Y-%m-%d').date()
                exists_in_db = TravelExpense.query.filter(
                    TravelExpense.request_id != app_id,
                    TravelExpense.expense_date == date_val,
                    TravelExpense.requested_amount == amt
                ).first() is not None
                if exists_in_db:
                    flash(f'報銷失敗！單據（日期：{dt}，金額：NT$ {amt:,.0f}）已在資料庫中報銷過，一律不得重複報銷。', 'danger')
                    return redirect(url_for('main.expense_report', app_id=app_id))
            except Exception as e:
                pass

        # Clear old expenses if this is a resubmission
        TravelExpense.query.filter_by(request_id=app_id).delete()
        dates = request.form.getlist('expense_date[]')
        expense_names = request.form.getlist('expense_name[]')
        has_tax_ids = request.form.getlist('has_tax_id[]')
        receipt_types = request.form.getlist('receipt_type[]')
        expense_locations = request.form.getlist('expense_location[]')
        amounts = request.form.getlist('requested_amount[]')
        notes = request.form.getlist('expense_note[]')
        
        # 讀取 OCR 隱藏快取與已存在憑證路徑
        ocr_dates = request.form.getlist('ocr_date[]')
        ocr_categories = request.form.getlist('ocr_category[]')
        ocr_expense_names = request.form.getlist('ocr_expense_name[]')
        ocr_amounts = request.form.getlist('ocr_amount[]')
        ocr_receipt_types = request.form.getlist('ocr_receipt_type[]')
        ocr_tax_id_numbers = request.form.getlist('ocr_tax_id_number[]')
        ocr_expense_locations = request.form.getlist('ocr_expense_location[]')
        is_receipt_user_uploaded_list = request.form.getlist('is_receipt_user_uploaded[]')
        existing_receipt_paths = request.form.getlist('existing_receipt_path[]')
        
        receipt_files = request.files.getlist('row_receipt[]')
        
        import os
        from flask import current_app
        import uuid
        
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        
        total_amount = 0
        act_accommodation = 0.0
        act_transportation = 0.0
        act_meals = 0.0
        act_misc = 0.0
        location_discrepancy = 0
        limit_violations = 0
        
        # 從資料庫動態讀取政策
        db_policies = ReimbursementPolicy.query.all()

        for i in range(len(categories)):
            try:
                date_val = datetime.strptime(dates[i], '%Y-%m-%d').date()
                amount_val = float(amounts[i])
                location_val = expense_locations[i] if i < len(expense_locations) else ""
                name_val = expense_names[i] if i < len(expense_names) else ""
                tax_id_input = has_tax_ids[i].strip() if i < len(has_tax_ids) else ""
                has_tax_id_val = False
                tax_id_number_val = None
                if tax_id_input and tax_id_input.lower() not in ["no", "無", "false", ""]:
                    import re
                    digits = re.sub(r'\D', '', tax_id_input)
                    if len(digits) == 8:
                        has_tax_id_val = True
                        tax_id_number_val = digits
                    else:
                        has_tax_id_val = True
                        tax_id_number_val = tax_id_input if tax_id_input != 'yes' else None
                
                receipt_type_val = receipt_types[i] if i < len(receipt_types) else "收據"
                note_val = notes[i] if i < len(notes) else ""
                
                # 處理憑證實體檔案上傳與儲存
                receipt_path_val = ""
                uploaded_file = receipt_files[i] if i < len(receipt_files) else None
                if uploaded_file and uploaded_file.filename != '':
                    ext = os.path.splitext(uploaded_file.filename)[1]
                    unique_filename = f"receipt_{app_id}_{i}_{uuid.uuid4().hex}{ext}"
                    save_path = os.path.join(uploads_dir, unique_filename)
                    uploaded_file.save(save_path)
                    receipt_path_val = f"/static/uploads/{unique_filename}"
                elif i < len(existing_receipt_paths) and existing_receipt_paths[i].strip():
                    receipt_path_val = existing_receipt_paths[i].strip()
                
                # 處理隱藏 OCR 欄位快取
                ocr_date_val = None
                if i < len(ocr_dates) and ocr_dates[i].strip():
                    try:
                        ocr_date_val = datetime.strptime(ocr_dates[i].strip(), '%Y-%m-%d').date()
                    except:
                        pass
                
                ocr_category_val = ocr_categories[i] if i < len(ocr_categories) else None
                ocr_expense_name_val = ocr_expense_names[i] if i < len(ocr_expense_names) else None
                ocr_amount_val = float(ocr_amounts[i]) if (i < len(ocr_amounts) and ocr_amounts[i]) else 0.0
                ocr_receipt_type_val = ocr_receipt_types[i] if i < len(ocr_receipt_types) else None
                ocr_tax_id_number_val = ocr_tax_id_numbers[i] if i < len(ocr_tax_id_numbers) else None
                ocr_expense_location_val = ocr_expense_locations[i] if i < len(ocr_expense_locations) else None
                is_user_uploaded_val = (is_receipt_user_uploaded_list[i] == 'true') if i < len(is_receipt_user_uploaded_list) else False
                
                expense = TravelExpense(
                    request_id=app_id,
                    expense_date=date_val,
                    expense_category=categories[i],
                    expense_name=name_val,
                    has_tax_id=has_tax_id_val,
                    tax_id_number=tax_id_number_val,
                    receipt_type=receipt_type_val,
                    expense_location=location_val,
                    requested_amount=amount_val,
                    expense_note=note_val,
                    receipt_path=receipt_path_val,
                    
                    ocr_date=ocr_date_val,
                    ocr_category=ocr_category_val,
                    ocr_expense_name=ocr_expense_name_val,
                    ocr_amount=ocr_amount_val,
                    ocr_receipt_type=ocr_receipt_type_val,
                    ocr_tax_id_number=ocr_tax_id_number_val,
                    ocr_expense_location=ocr_expense_location_val,
                    is_receipt_user_uploaded=is_user_uploaded_val
                )
                db.session.add(expense)
                
                total_amount += amount_val
                
                # Accumulate category totals
                cat = categories[i]
                if cat == '住宿費':
                    act_accommodation += amount_val
                elif cat == '交通費':
                    act_transportation += amount_val
                elif '伙食費' in cat:
                    act_meals += amount_val
                elif cat == '雜費':
                    act_misc += amount_val
                
                # 動態比對資料庫政策
                violation = False
                
                # 篩選匹配類別的政策
                matched_policies = []
                item_lower = name_val.lower()
                location_lower = location_val.lower()
                
                if cat == '交通費':
                    if '計程車' in item_lower or 'taxi' in item_lower or '計程車' in location_lower or 'taxi' in location_lower:
                        matched_policies = [p for p in db_policies if p.category == '計程車']
                    else:
                        matched_policies = [p for p in db_policies if p.category == '交通費']
                elif cat == '伙食費':
                    if '早餐' in item_lower or 'breakfast' in item_lower:
                        matched_policies = [p for p in db_policies if p.category == '伙食費 (早餐)']
                    elif '午餐' in item_lower or 'lunch' in item_lower or '便當' in item_lower or '飯' in item_lower:
                        matched_policies = [p for p in db_policies if p.category == '伙食費 (午餐)']
                    elif '晚餐' in item_lower or 'dinner' in item_lower:
                        matched_policies = [p for p in db_policies if p.category == '伙食費 (晚餐)']
                    else:
                        matched_policies = [p for p in db_policies if p.category == '伙食費 (午餐)']
                else:
                    matched_policies = [p for p in db_policies if p.category == cat]
                
                limit = None
                for p in matched_policies:
                    # 檢查政策日期範圍
                    if p.start_date and date_val < p.start_date:
                        continue
                    if p.end_date and date_val > p.end_date:
                        continue
                    
                    # 檢查平假日類型
                    if p.day_type == 'weekday':
                        if date_val.weekday() < 5: # 週一至週五
                            limit = p.amount_limit
                            break
                    elif p.day_type == 'weekend':
                        if date_val.weekday() >= 5: # 週六、週日
                            limit = p.amount_limit
                            break
                    elif p.day_type == 'any':
                        limit = p.amount_limit
                        break
                
                if limit is not None and amount_val > limit:
                    if not note_val or len(note_val.strip()) < 2:
                        limit_violations += 1
 
                # 地點符合性校驗 (是否在核准目的地內)
                approved_dests = [d.strip() for d in req.destination.split(',') if d.strip()]
                if location_val and location_val not in approved_dests:
                    location_discrepancy += 1
            except Exception as e:
                pass 

        # 讀取並儲存預算不符說明
        req.acc_mismatch_explanation = request.form.get('mismatch_explanation_accommodation', '').strip() or None
        req.trans_mismatch_explanation = request.form.get('mismatch_explanation_transportation', '').strip() or None
        req.meals_mismatch_explanation = request.form.get('mismatch_explanation_meals', '').strip() or None
        req.misc_mismatch_explanation = request.form.get('mismatch_explanation_misc', '').strip() or None

        # 新的風險判定模型 (符合任一則為 High)
        has_risk = False
        risk_reasons = []

        # 1. 實際金額與申請預算細目不符 (預算風險)
        has_mismatch = False
        mismatch_categories = []
        if abs(act_accommodation - req.est_accommodation) > 0.01:
            has_mismatch = True
            mismatch_categories.append("住宿費")
        if abs(act_transportation - req.est_transportation) > 0.01:
            has_mismatch = True
            mismatch_categories.append("交通費")
        if abs(act_meals - req.est_meals) > 0.01:
            has_mismatch = True
            mismatch_categories.append("伙食費")
        if abs(act_misc - req.est_misc) > 0.01:
            has_mismatch = True
            mismatch_categories.append("雜費")
            
        if has_mismatch:
            has_risk = True
            risk_reasons.append("實際報銷與原預算細目不符(" + "、".join(mismatch_categories) + ")")

        # 2. 超額且無說明 (由 limit_violations 判定)
        if limit_violations > 0:
            has_risk = True
            risk_reasons.append("單項支出超額且未填寫合理解釋理由")

        # 3. 地點明顯不合理 (由 location_discrepancy 判定)
        if location_discrepancy > 0:
            has_risk = True
            risk_reasons.append("報銷項目地點與出差地不符")

        # 4. 重複報銷 (偵測同日期/同金額項目)
        if len(amounts) != len(set(zip(dates, amounts))):
            has_risk = True
            risk_reasons.append("疑似重複報銷項目")

        # 5. 統一編號與公司統編 58711014 不符
        tax_id_mismatch = 0
        for i in range(len(categories)):
            tax_id_input = has_tax_ids[i].strip() if i < len(has_tax_ids) else ""
            if tax_id_input and tax_id_input.lower() not in ["no", "無", "false", ""]:
                import re
                digits = re.sub(r'\D', '', tax_id_input)
                if digits != "58711014":
                    tax_id_mismatch += 1

        if tax_id_mismatch > 0:
            has_risk = True
            risk_reasons.append("統一編號與公司統編(58711014)不符")

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
        
    # GET: 載入報銷單政策清單傳給前端
    policies = ReimbursementPolicy.query.all()
    policies_data = []
    for p in policies:
        policies_data.append({
            'category': p.category,
            'amount_limit': p.amount_limit,
            'day_type': p.day_type,
            'start_date': p.start_date.isoformat() if p.start_date else None,
            'end_date': p.end_date.isoformat() if p.end_date else None,
            'description': p.description
        })
    import json
    policies_json = json.dumps(policies_data)
    
    return render_template('expense_report.html', app_id=app_id, req=req, policies=policies, policies_json=policies_json)


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
        # Accountants review pre-trip budget and final reimbursement
        pending_items = TravelRequest.query.filter(
            TravelRequest.status.in_(['TravelPendingAccounting', 'ExpensePendingAccounting'])
        ).all()
    
    return render_template('approvals.html', pending_items=pending_items)

@main.route('/review-travel/<int:req_id>')
@login_required
def review_travel(req_id):
    req = TravelRequest.query.get_or_404(req_id)
    # Allow Managers, Accountants, and the OWNER to view.
    is_authorized = (current_user.role in ['Manager', 'Accountant']) or (req.employee_id == current_user.id)
    if not is_authorized:
        flash('無權限訪問', 'danger')
        return redirect(url_for('main.dashboard'))
        
    # Validation logic for reviewers (Accountant/Manager)
    if current_user.role == 'Manager' and req.status != 'Pending' and req.employee_id != current_user.id:
        flash('該差旅申請無需主管簽核', 'info')
        return redirect(url_for('main.approvals'))
    if current_user.role == 'Accountant' and req.status != 'TravelPendingAccounting' and req.employee_id != current_user.id:
        flash('該差旅申請無需會計審核', 'info')
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
        
    # 預先計算並繫結每筆消費的超額、政策警告與預算限制
    db_policies = ReimbursementPolicy.query.all()
    for exp in req.expenses:
        cat = exp.expense_category
        name_val = exp.expense_name or ""
        location_val = exp.expense_location or ""
        date_val = exp.expense_date
        
        # 1. 估算預算限制
        category_budget = 0.0
        if cat == '住宿費':
            category_budget = req.est_accommodation or 0.0
        elif cat == '交通費':
            category_budget = req.est_transportation or 0.0
        elif '伙食費' in cat:
            category_budget = req.est_meals or 0.0
        elif cat == '雜費':
            category_budget = req.est_misc or 0.0
            
        exp.category_budget = category_budget
        exp.is_over_budget = exp.requested_amount > category_budget
        
        # 2. 公司限額政策限制匹配
        matched_policies = []
        item_lower = name_val.lower()
        location_lower = location_val.lower()
        
        if cat == '交通費':
            if '計程車' in item_lower or 'taxi' in item_lower or '計程車' in location_lower or 'taxi' in location_lower:
                matched_policies = [p for p in db_policies if p.category == '計程車']
            else:
                matched_policies = [p for p in db_policies if p.category == '交通費']
        elif cat == '伙食費':
            if '早餐' in item_lower or 'breakfast' in item_lower:
                matched_policies = [p for p in db_policies if p.category == '伙食費 (早餐)']
            elif '午餐' in item_lower or 'lunch' in item_lower or '便當' in item_lower or '飯' in item_lower:
                matched_policies = [p for p in db_policies if p.category == '伙食費 (午餐)']
            elif '晚餐' in item_lower or 'dinner' in item_lower:
                matched_policies = [p for p in db_policies if p.category == '伙食費 (晚餐)']
            else:
                matched_policies = [p for p in db_policies if p.category == '伙食費 (午餐)']
        else:
            matched_policies = [p for p in db_policies if p.category == cat]
            
        limit = None
        limit_desc = "金額限制"
        for p in matched_policies:
            if p.start_date and date_val < p.start_date:
                continue
            if p.end_date and date_val > p.end_date:
                continue
            
            if p.day_type == 'weekday':
                if date_val.weekday() < 5:
                    limit = p.amount_limit
                    limit_desc = p.description or f"平日上限 ${limit:,.0f}"
                    break
            elif p.day_type == 'weekend':
                if date_val.weekday() >= 5:
                    limit = p.amount_limit
                    limit_desc = p.description or f"假日上限 ${limit:,.0f}"
                    break
            elif p.day_type == 'any':
                limit = p.amount_limit
                limit_desc = p.description or f"上限 ${limit:,.0f}"
                break
                
        exp.company_limit = limit
        exp.limit_description = limit_desc
        exp.is_over_company_limit = (limit is not None and exp.requested_amount > limit)
        exp.is_amt_violation = exp.is_over_budget or exp.is_over_company_limit
        
        # 3. 超額警告提示文字組裝
        if exp.is_over_company_limit:
            exp.limit_warning_text = f"已超過{limit_desc}，請填寫說明"
        elif exp.is_over_budget:
            exp.limit_warning_text = f"已超過該類別出差預算上限 ${category_budget:,.0f}，請填寫說明"
        else:
            exp.limit_warning_text = ""
            
    # 重新計算系統風險評估原因 (不需要資料庫變更即可動態顯示)
    risk_reasons = []
    
    # 1. 實際金額與申請預算細目不符 (預算風險)
    act_accommodation = sum(e.requested_amount for e in req.expenses if e.expense_category == '住宿費')
    act_transportation = sum(e.requested_amount for e in req.expenses if e.expense_category == '交通費')
    act_meals = sum(e.requested_amount for e in req.expenses if '伙食費' in e.expense_category)
    act_misc = sum(e.requested_amount for e in req.expenses if e.expense_category == '雜費')
    
    mismatch_categories = []
    if abs(act_accommodation - (req.est_accommodation or 0.0)) > 0.01:
        mismatch_categories.append("住宿費")
    if abs(act_transportation - (req.est_transportation or 0.0)) > 0.01:
        mismatch_categories.append("交通費")
    if abs(act_meals - (req.est_meals or 0.0)) > 0.01:
        mismatch_categories.append("伙食費")
    if abs(act_misc - (req.est_misc or 0.0)) > 0.01:
        mismatch_categories.append("雜費")
        
    if mismatch_categories:
        risk_reasons.append("實際報銷與原預算細目不符(" + "、".join(mismatch_categories) + ")")
        
    # 2. 超額且無說明
    limit_violations = 0
    for exp in req.expenses:
        if exp.is_over_company_limit:
            if not exp.expense_note or len(exp.expense_note.strip()) < 2:
                limit_violations += 1
    if limit_violations > 0:
        risk_reasons.append("單項支出超額且未填寫合理解釋理由")
        
    # 3. 地點明顯不合理
    location_discrepancy = 0
    approved_dests = [d.strip() for d in req.destination.split(',') if d.strip()]
    for exp in req.expenses:
        if exp.expense_location and exp.expense_location not in approved_dests:
            location_discrepancy += 1
    if location_discrepancy > 0:
        risk_reasons.append("報銷項目地點與出差地不符")
        
    # 4. 重複報銷 (偵測同日期/同金額項目)
    seen_pairs = set()
    has_dup = False
    for exp in req.expenses:
        pair = (exp.expense_date, exp.requested_amount)
        if pair in seen_pairs:
            has_dup = True
        seen_pairs.add(pair)
    if has_dup:
        risk_reasons.append("疑似重複報銷項目")
            
    return render_template('review_expense.html', req=req, risk_reasons=risk_reasons)

@main.route('/process-review/<int:req_id>', methods=['POST'])
@login_required
def process_review(req_id):
    action = request.form.get('action') # approve, reject
    comment = request.form.get('review_comment', '').strip()
    req = TravelRequest.query.get_or_404(req_id)
    
    if action == 'approve':
        req.review_comment = comment # Optionally save comment on approval too
        if req.status == 'Pending' and current_user.role == 'Manager':
            req.status = 'TravelPendingAccounting'
            flash('出差申請主管簽核通過，移交會計審核', 'success')
        elif req.status == 'TravelPendingAccounting' and current_user.role == 'Accountant':
            req.status = 'Approved'
            flash('出差申請會計審核通過，已最終核准', 'success')
        elif req.status == 'ExpensePendingManager' and current_user.role == 'Manager':
            req.status = 'ExpensePendingAccounting'
            flash('報銷單（主管部分）已核准，移交會計審核', 'success')
        elif req.status == 'ExpensePendingAccounting' and current_user.role == 'Accountant':
            req.status = 'Reimbursed'
            flash('報銷單審核通過，出納撥款中', 'success')
        else:
            flash('非法操作', 'danger')
    elif action == 'reject':
        if not comment:
            flash('退回案件時必須填寫審核意見（原因）', 'danger')
            return redirect(url_for('main.review_travel', req_id=req.id) if req.status in ['Pending', 'TravelPendingAccounting'] else url_for('main.review_expense', req_id=req.id))
        
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
    
    if req.status not in ['Draft', 'Rejected', 'Pending', 'TravelPendingAccounting']:
        flash('只有草稿、等待審核或已被退回的案件可以刪除', 'danger')
        return redirect(url_for('main.dashboard'))
    
    db.session.delete(req)
    db.session.commit()
    flash('案件已成功刪除', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/api/ocr-scan', methods=['POST'])
@login_required
def ocr_scan():
    import requests
    import os
    import uuid
    from flask import current_app
    
    if 'image' not in request.files:
        return {'error': '沒有上傳檔案'}, 400
        
    file = request.files['image']
    if file.filename == '':
        return {'error': '沒有選擇檔案'}, 400

    file_content = file.read()
    
    # 預先將檔案儲存至本機 static/uploads，避免後端因為 file input 被清空而收不到檔案
    uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        
    ext = os.path.splitext(file.filename)[1]
    if not ext:
        ext = '.jpg'
    unique_filename = f"receipt_ocr_{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(uploads_dir, unique_filename)
    
    try:
        with open(save_path, 'wb') as f:
            f.write(file_content)
        file_path = f"/static/uploads/{unique_filename}"
    except Exception as e:
        print(f"[OCR] 儲存本機檔案失敗: {e}")
        file_path = None

    try:
        # 將檔案轉發至 OCR 微服務 (提高逾時時間至 180 秒以容納大圖及 CPU 運算)
        files = {'image': (file.filename, file_content, file.mimetype)}
        response = requests.post('http://127.0.0.1:5000/ocr', files=files, timeout=180)
        
        if response.status_code != 200:
            print(f"[OCR] 辨識微服務回傳錯誤代碼: {response.status_code}")
            ret = {'error': f'辨識服務異常 (狀態碼 {response.status_code})'}
            if file_path:
                ret['file_path'] = file_path
            return ret, 500
            
        result = response.json()
        if file_path:
            result['file_path'] = file_path
        return result
    except requests.exceptions.RequestException as e:
        print(f"[OCR] 連線微服務發生異常: {e}")
        ret = {'error': f'無法連線至 AI 辨識服務，請確認 OCR 微服務是否已啟動（使用 GPU）。異常詳情: {e}'}
        if file_path:
            ret['file_path'] = file_path
        return ret, 503

@main.route('/api/check-duplicate-receipt', methods=['GET'])
@login_required
def check_duplicate_receipt():
    date_str = request.args.get('date')
    amount_str = request.args.get('amount')
    exclude_request_id = request.args.get('exclude_request_id', type=int)
    
    if not date_str or not amount_str:
        return jsonify({'error': '缺少必要參數'}), 400
        
    try:
        date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
        amount_val = float(amount_str)
    except Exception as e:
        return jsonify({'error': '參數格式錯誤'}), 400
        
    query = TravelExpense.query.filter(
        TravelExpense.expense_date == date_val,
        TravelExpense.requested_amount == amount_val
    )
    
    if exclude_request_id:
        query = query.filter(TravelExpense.request_id != exclude_request_id)
        
    exists = query.first() is not None
    return jsonify({'duplicate': exists})

@main.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot_api():
    data = request.json or {}
    message = data.get('message', '').strip()
    
    # Retrieve current category context from session to enable multi-turn context boosting
    session_context = session.get('chatbot_context')
    
    # Run the matching algorithm
    result = match_faq(message, session_context)
    
    # Save the updated context back to session
    session['chatbot_context'] = result.get('context')
    
    return jsonify({
        'answer': result.get('answer'),
        'suggestions': result.get('suggestions', [])
    })


