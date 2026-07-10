import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

# 載入環境變數
load_dotenv()

class TravelExpenseDB:
    def __init__(self, db_name="hr_db"):
        """初始化資料庫連線"""
        self.db_name = db_name
        self.init_database()

    def _get_connection(self):
        """建立 PostgreSQL 資料庫連線"""
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", self.db_name),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "your_password_here"),
            cursor_factory=RealDictCursor
        )

    def init_database(self):
        """確認與 PostgreSQL 資料庫連線正常"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            print(f"【系統通知】成功連線至 PostgreSQL 資料庫 '{self.db_name}'！")
        except Exception as e:
            print(f"【系統通知】無法連線到 PostgreSQL，請確認資料庫是否啟動或帳密設定正確。錯誤訊息: {e}")

    def authenticate_user(self, username, password):
        """驗證使用者登入 (僅允許 Admin 管理員登入資料庫後台)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # 尋找使用者
            cursor.execute("SELECT id, name as username, password, role FROM employees WHERE email = %s", (username,))
            user = cursor.fetchone()
            
            # 驗證密碼且限制角色必須為 Admin
            if user and user['role'] == 'Admin' and check_password_hash(user['password'], password):
                return {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"]
                }
            return None
        except Exception as e:
            print("登入驗證錯誤:", e)
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
                
    def insert_travel_request(self, expected_amount, expected_location, expected_date, submitter_id=2):
        """新增差旅前申請單 (相容模式，將資料寫入 hr-app 的 travel_requests)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 解析日期格式 "YYYY-MM-DD"
            try:
                from datetime import datetime
                if " 至 " in expected_date:
                    start_str, end_str = expected_date.split(" 至 ")
                else:
                    start_str = expected_date
                    end_str = expected_date
                start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
                end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d').date()
            except:
                from datetime import date
                start_date = date.today()
                end_date = date.today()
                
            cursor.execute('''
                INSERT INTO travel_requests (employee_id, destination, start_date, end_date, purpose, est_accommodation, est_transportation, est_meals, est_misc, status)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 0, 'Pending')
                RETURNING id
            ''', (submitter_id, expected_location, start_date, end_date, '由後台直接建立的出差申請', expected_amount))
            request_id = cursor.fetchone()['id']
            conn.commit()
            return {"success": True, "id": request_id}
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def evaluate_risk(self, amount, expected_amount, location, expected_location, date, expected_date, tax_id, company_limit=10000, company_tax_id="12345678"):
        """
        核心功能：風險評級引擎
        規則：時間比對、地點比對、金額比對。全部符合才為低風險。
        """
        reasons = []
        
        # 1. 檢查統編
        if tax_id != company_tax_id:
            reasons.append("統編與公司不符")
            
        # 2. 檢查時間 (支援 "YYYY-MM-DD" 在 "YYYY-MM-DD 至 YYYY-MM-DD" 範圍內)
        is_date_valid = False
        if " 至 " in expected_date:
            try:
                start_date, end_date = expected_date.split(" 至 ")
                if start_date.strip() <= date <= end_date.strip():
                    is_date_valid = True
            except:
                pass
        else:
            if date == expected_date:
                is_date_valid = True
                
        if not is_date_valid:
            reasons.append(f"實際時間 ({date}) 與事前申請的時間範圍 ({expected_date}) 不符")
            
        # 3. 檢查地點 (檢查實際地點是否為預期目的地之子字串或相等)
        if expected_location not in location and location not in expected_location:
            reasons.append(f"實際地點 ({location}) 與事前申請的地點 ({expected_location}) 不符")
            
        # 4. 檢查金額
        if amount > expected_amount:
            reasons.append(f"實際金額 ({amount}元) 超過事前申請的預估金額 ({expected_amount}元)")
        if amount > company_limit:
            reasons.append(f"實際金額 ({amount}元) 超過公司規定上限 ({company_limit}元)")
            
        if len(reasons) > 0:
            return "High", "、".join(reasons)
        
        return "Low", "符合差旅前申請預算、地點與公司政策"

    def insert_ocr_and_risk(self, request_id, amount, date_str, location, tax_id, submitter_id=2, transport_amount=0, food_amount=0, accommodation_amount=0, misc_amount=0):
        """
        將 OCR 資料與風險寫入 hr-app 的 travel_expenses 中
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 1. 取得事前申請單資料
            cursor.execute('''
                SELECT (est_accommodation + est_transportation + est_meals + est_misc) as expected_amount,
                       destination as expected_location,
                       CONCAT(start_date, ' 至 ', end_date) as expected_date
                FROM travel_requests 
                WHERE id = %s
            ''', (request_id,))
            req_data = cursor.fetchone()
            
            if not req_data:
                return {"success": False, "error": f"找不到編號為 {request_id} 的差旅前申請單"}
                
            expected_amount = req_data['expected_amount'] or 0
            expected_location = req_data['expected_location']
            expected_date = req_data['expected_date']
            
            # 1.5 檢查是否為重複報銷單據
            cursor.execute('''
                SELECT id FROM travel_expenses
                WHERE request_id != %s AND expense_date = %s AND requested_amount = %s
                LIMIT 1
            ''', (request_id, date_str, amount))
            dup_record = cursor.fetchone()
            if dup_record:
                return {"success": False, "error": f"此單據（日期：{date_str}，金額：{amount}）已存在於系統資料庫中，一律不能重複報銷"}
            
            # 2. 執行風險評級
            risk_level, risk_reason = self.evaluate_risk(amount, expected_amount, location, expected_location, date_str, expected_date, tax_id)
            
            # 決定費用類別 (預設若沒傳入明細金額，以總金額決定類別)
            category = "雜費"
            if accommodation_amount > 0 or "飯店" in location or "旅館" in location or "住宿" in location:
                category = "住宿費"
                accommodation_amount = amount if accommodation_amount == 0 else accommodation_amount
            elif transport_amount > 0 or "車" in location or "捷運" in location or "高鐵" in location or "交通" in location:
                category = "交通費"
                transport_amount = amount if transport_amount == 0 else transport_amount
            elif food_amount > 0 or "餐" in location or "伙食" in location or "飯" in location:
                category = "伙食費"
                food_amount = amount if food_amount == 0 else food_amount
            else:
                misc_amount = amount if misc_amount == 0 else misc_amount
                
            cursor.execute('''
                INSERT INTO travel_expenses (
                    request_id, expense_date, expense_category, expense_name, 
                    has_tax_id, tax_id_number, receipt_type, expense_location, 
                    requested_amount, ocr_date, ocr_category, ocr_expense_name, 
                    ocr_amount, ocr_receipt_type, ocr_tax_id_number, ocr_expense_location, 
                    is_receipt_user_uploaded, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
            ''', (
                request_id, date_str, category, "由後台 API 上傳項目",
                True if tax_id else False, tax_id, "發票" if tax_id else "收據", location,
                amount, date_str, category, "由後台 API 上傳項目",
                amount, "發票" if tax_id else "收據", tax_id, location,
                False
            ))
            
            record_id = cursor.fetchone()['id']
            
            # 4. 更新 travel_requests 的風險結果與狀態
            cursor.execute('''
                UPDATE travel_requests
                SET risk_level = %s,
                    risk_score = %s,
                    review_comment = %s,
                    status = %s
                WHERE id = %s
            ''', (
                risk_level, 
                90 if risk_level == 'High' else 10,
                risk_reason, 
                'ExpensePendingManager' if risk_level == 'High' else 'ExpensePendingAccounting',
                request_id
            ))
            
            conn.commit()
            
            return {
                "success": True,
                "id": record_id,
                "risk_level": risk_level,
                "risk_reason": risk_reason
            }
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_all_records(self):
        """查詢所有報銷明細（對應到 travel_expenses）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.id, u.name as submitter_name,
                       e.expense_date, e.expense_category, e.expense_name,
                       e.requested_amount, e.receipt_path, e.created_at,
                       e.receipt_type, e.tax_id_number, e.expense_location,
                       e.expense_date as ocr_date,
                       e.expense_location as ocr_location,
                       e.tax_id_number as ocr_tax_id,
                       e.requested_amount as ocr_amount,
                       t.risk_level,
                       t.review_comment as risk_reason,
                       t.status,
                       e.request_id,
                       t.destination,
                       t.money as expected_amount,
                       CASE WHEN e.expense_category = '交通費' THEN e.requested_amount ELSE 0 END as transport_amount,
                       CASE WHEN e.expense_category = '伙食費' THEN e.requested_amount ELSE 0 END as food_amount,
                       CASE WHEN e.expense_category = '住宿費' THEN e.requested_amount ELSE 0 END as accommodation_amount,
                       CASE WHEN e.expense_category = '雜費' THEN e.requested_amount ELSE 0 END as misc_amount
                FROM travel_expenses e
                LEFT JOIN travel_requests t ON e.request_id = t.id
                LEFT JOIN employees u ON t.employee_id = u.id
                ORDER BY e.created_at DESC
            ''')
            records = cursor.fetchall()
            return records
        except Exception as e:
            print("查詢錯誤:", e)
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_records_by_user(self, user_id):
        """查詢特定員工的報銷紀錄"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.id, u.name as submitter_name,
                       e.expense_date, e.expense_category, e.expense_name,
                       e.requested_amount, e.receipt_path, e.created_at,
                       e.receipt_type, e.tax_id_number, e.expense_location,
                       e.expense_date as ocr_date,
                       e.expense_location as ocr_location,
                       e.tax_id_number as ocr_tax_id,
                       e.requested_amount as ocr_amount,
                       t.risk_level,
                       t.review_comment as risk_reason,
                       t.status,
                       e.request_id,
                       t.destination,
                       t.money as expected_amount,
                       CASE WHEN e.expense_category = '交通費' THEN e.requested_amount ELSE 0 END as transport_amount,
                       CASE WHEN e.expense_category = '伙食費' THEN e.requested_amount ELSE 0 END as food_amount,
                       CASE WHEN e.expense_category = '住宿費' THEN e.requested_amount ELSE 0 END as accommodation_amount,
                       CASE WHEN e.expense_category = '雜費' THEN e.requested_amount ELSE 0 END as misc_amount
                FROM travel_expenses e
                LEFT JOIN travel_requests t ON e.request_id = t.id
                LEFT JOIN employees u ON t.employee_id = u.id
                WHERE t.employee_id = %s
                ORDER BY e.created_at DESC
            ''', (user_id,))
            records = cursor.fetchall()
            return records
        except Exception as e:
            print("查詢錯誤:", e)
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_all_employees(self):
        """查詢所有員工資訊（對應到 employees）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, department, role, email, password FROM employees ORDER BY id ASC")
            employees = cursor.fetchall()
            return employees
        except Exception as e:
            print("查詢員工錯誤:", e)
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_all_travel_requests(self):
        """查詢所有事前申請單（對應到 travel_requests）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.employee_id, u.name as submitter_name, 
                       t.destination, t.start_date, t.end_date, t.purpose,
                       t.est_accommodation, t.est_transportation, t.est_meals, t.est_misc,
                       t.money, t.status, t.created_at
                FROM travel_requests t
                LEFT JOIN employees u ON t.employee_id = u.id
                ORDER BY t.created_at DESC
            ''')
            requests = cursor.fetchall()
            return requests
        except Exception as e:
            print("查詢錯誤:", e)
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_travel_requests_by_user(self, user_id):
        """查詢特定員工的事前申請單"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.employee_id, u.name as submitter_name, 
                       t.destination, t.start_date, t.end_date, t.purpose,
                       t.est_accommodation, t.est_transportation, t.est_meals, t.est_misc,
                       t.money, t.status, t.created_at
                FROM travel_requests t
                LEFT JOIN employees u ON t.employee_id = u.id
                WHERE t.employee_id = %s
                ORDER BY t.created_at DESC
            ''', (user_id,))
            requests = cursor.fetchall()
            return requests
        except Exception as e:
            print("查詢錯誤:", e)
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def update_status(self, request_id, new_status):
        """供主管或會計審核時，更新審批進度 (直接更新 request_id)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            status_map = {
                '主管核准': 'ExpensePendingAccounting',
                '會計核准': 'Reimbursed',
                '主管駁回': 'Rejected',
                '會計駁回': 'Rejected'
            }
            db_status = status_map.get(new_status, 'Rejected')
            cursor.execute('''
                UPDATE travel_requests 
                SET status = %s 
                WHERE id = %s
            ''', (db_status, request_id))
            conn.commit()
            return True
        except Exception as e:
            print("更新狀態出錯:", e)
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

# ─── 本地測試程式碼 ───
if __name__ == "__main__":
    db = TravelExpenseDB("hr_db")
    print("本機測試成功。")