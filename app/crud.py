from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from . import models, utils
from datetime import date, datetime

def create_student(db: Session, uuid_code: str, first_name: str, last_name: str=None, parent_name: str=None, parent_phone: str=None, class_id: int=None, group_id: int=None):
    # The uuid_code is now passed from the RFID card reader instead of being generated.
    # uuid_code = utils.generate_uuid()
    student = models.Student(
        uuid=uuid_code.strip(), # Ensure no leading/trailing whitespace
        first_name=first_name,
        last_name=last_name,
        parent_name=parent_name,
        parent_phone=parent_phone,
        class_id=class_id,
        group_id=group_id
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    utils.generate_code128_image(student.uuid)
    utils.generate_qr_image(student.uuid)
    return student

# جلب كل الصفوف
def get_all_classes(db: Session):
    return db.query(models.Class).order_by(models.Class.id.asc()).all()

# جلب كل المجموعات (مع إمكانية التصفية حسب الصف)
def get_all_groups(db: Session, class_id: int = None):
    q = db.query(models.Group)
    if class_id:
        q = q.filter(models.Group.class_id == class_id)
    return q.order_by(models.Group.id.asc()).all()

def get_student_by_uuid(db: Session, uuid_code: str):
    return db.query(models.Student).filter(models.Student.uuid == uuid_code).first()

def get_last_attendance(db: Session, student_id: int):
    return db.query(models.SessionAttendance)\
        .filter(models.SessionAttendance.student_id == student_id)\
        .order_by(models.SessionAttendance.session_date.desc())\
        .first()

def mark_attendance(db: Session, student_id: int, status="present", score=None, recorded_by="system"):
    att = models.SessionAttendance(
        student_id=student_id,
        session_date=datetime.now(),
        status=status,
        score=score,
        recorded_by=recorded_by
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att

def add_payment(db: Session, student_id: int, amount: float, method="cash", note=None):
    p = models.Payment(
        student_id=student_id,
        amount=amount,
        method=method,
        payment_date=date.today(),
        note=note
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

def get_payment_status(db: Session, student_id: int):
    # بسيط: نجيب اخر دفعة ونحسب الفرق بالأيام
    last = db.query(models.Payment)\
        .filter(models.Payment.student_id == student_id)\
        .order_by(models.Payment.payment_date.desc())\
        .first()
    if not last:
        return {"status": "no_payment", "days_since": None}
    days = (date.today() - last.payment_date).days
    state = "green" if days < 25 else ("yellow" if days <= 30 else "red")
    return {"status": state, "days_since": days, "last_paid_date": str(last.payment_date)}

# ---------------------- NEW FUNCTION ----------------------
def get_all_students(db: Session):
    """
    ترجع كل الطلاب بالترتيب حسب ID
    """
    return db.query(models.Student).order_by(models.Student.id.asc()).all()


def search_students(db: Session, q: str):
    """
    Search students by first name, last name, or uuid (case-insensitive, partial match).
    """
    if not q:
        return []
    pattern = f"%{q}%"
    return db.query(models.Student).filter(
        (models.Student.first_name.ilike(pattern)) |
        (models.Student.last_name.ilike(pattern)) |
        (models.Student.uuid.ilike(pattern))
    ).order_by(models.Student.id.asc()).all()

def delete_student(db: Session, student_id: int) -> bool:
    """
    Deletes a student and all their associated records.
    """
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return False

    # Delete associated records first to avoid foreign key constraint errors
    db.query(models.SessionAttendance).filter(models.SessionAttendance.student_id == student_id).delete(synchronize_session=False)
    db.query(models.Payment).filter(models.Payment.student_id == student_id).delete(synchronize_session=False)
    db.query(models.StudentBook).filter(models.StudentBook.student_id == student_id).delete(synchronize_session=False)
    db.query(models.StudentTest).filter(models.StudentTest.student_id == student_id).delete(synchronize_session=False)

    # For MessageLog, set student_id to null instead of deleting the log
    db.query(models.MessageLog).filter(models.MessageLog.student_id == student_id).update({"student_id": None})

    # Now delete the student
    db.delete(student)
    db.commit()
    return True


def get_treasury_summary(db: Session):
    """
    Returns a summary of incomes (payments + book sales) grouped by class and group,
    and total incomes, total expenses, and balance.
    """
    # إجمالي الدفعات
    total_payments = db.query(models.Payment).with_entities(func.coalesce(func.sum(models.Payment.amount), 0.0)).scalar() or 0.0
    # إجمالي مبيعات الكتب (join student_books -> books)
    total_book_sales = 0.0
    sb_q = db.query(models.StudentBook, models.Book).join(models.Book, models.StudentBook.book_id == models.Book.id).all()
    for sb, b in sb_q:
        total_book_sales += (b.price or 0.0)

    total_income = (total_payments or 0.0) + (total_book_sales or 0.0)

    # إجمالي المصروفات
    total_expenses = db.query(models.Expense).with_entities(func.coalesce(func.sum(models.Expense.amount), 0.0)).scalar() or 0.0

    # تجميع حسب صف ومجموعة: نحتاج مجموع الدفعات لكل طالب ثم جمعها حسب الصف/المجموعة
    class_group_income = {}
    payments = db.query(models.Payment, models.Student).join(models.Student, models.Payment.student_id == models.Student.id).all()
    for p, s in payments:
        cls = s.class_id or 0
        grp = s.group_id or 0
        key = (cls, grp)
        class_group_income.setdefault(key, 0.0)
        class_group_income[key] += (p.amount or 0.0)

    # include book sales per student's class/group (approximate by student association)
    sb_items = db.query(models.StudentBook, models.Book, models.Student).join(models.Book, models.StudentBook.book_id == models.Book.id).join(models.Student, models.StudentBook.student_id == models.Student.id).all()
    for sb, b, s in sb_items:
        cls = s.class_id or 0
        grp = s.group_id or 0
        key = (cls, grp)
        class_group_income.setdefault(key, 0.0)
        class_group_income[key] += (b.price or 0.0)

    # convert grouping into nested dict {class_id: {group_id: amount}}
    by_class = {}
    for (cls, grp), amt in class_group_income.items():
        by_class.setdefault(cls, {})[grp] = round(amt, 2)

    return {
        "total_income": round(total_income, 2),
        "total_payments": round(total_payments, 2),
        "total_book_sales": round(total_book_sales, 2),
        "total_expenses": round(total_expenses, 2),
        "balance": round((total_income or 0.0) - (total_expenses or 0.0), 2),
        "by_class": by_class
    }


def add_expense(db: Session, title: str, amount: float, note: str = None):
    e = models.Expense(title=title, amount=amount, note=note)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def list_expenses(db: Session, limit: int = 100):
    return db.query(models.Expense).order_by(models.Expense.expense_date.desc()).limit(limit).all()



def generate_student_report(db: Session, student_id: int) -> str:
    from datetime import timedelta

    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return "لم يتم العثور على الطالب."

    # 1. Student name
    student_name = f"{student.first_name} {student.last_name or ''}".strip()

    # 2. Last attendance date and time
    last_attendance = get_last_attendance(db, student_id)
    last_attendance_str = str(last_attendance.session_date) if last_attendance else "لا يوجد تسجيل حضور"

    # 3. Last 2 test scores
    last_2_tests = db.query(models.StudentTest, models.Test)\
        .join(models.Test, models.StudentTest.test_id == models.Test.id)\
        .filter(models.StudentTest.student_id == student_id)\
        .order_by(models.StudentTest.recorded_at.desc())\
        .limit(2).all()
    
    tests_scores_str = ""
    if last_2_tests:
        for st, t in last_2_tests:
            tests_scores_str += f'{t.name}: {st.score}/{t.max_score}\n'
    else:
        tests_scores_str = "لا توجد درجات مسجلة"

    # 4. Payment status and next payment date
    payment_info = get_payment_status(db, student_id)
    last_payment_date_str = ""
    next_payment_date_str = ""
    if payment_info['status'] == 'no_payment':
        last_payment_date_str = "لا توجد دفعات مسجلة"
        next_payment_date_str = "غير محدد"
    else:
        last_payment_date = datetime.strptime(payment_info['last_paid_date'], '%Y-%m-%d').date()
        last_payment_date_str = str(last_payment_date)
        next_payment_date = last_payment_date + timedelta(days=30)
        next_payment_date_str = str(next_payment_date)

    # Construct the report message
    report = f"""السلام عليكم، هذا بخصوص {student_name}. آخر حضور: {last_attendance_str}. درجات التسميع والاختبارات
{tests_scores_str}
حالة الدفع: {last_payment_date_str}. موعد الدفع القادم: {next_payment_date_str}
"""
    return report

# WhatsApp sessions and logs
def create_wa_session(db: Session, name: str = None, session_data: str = None):
    s = models.WhatsAppSession(name=name, session_data=session_data, connected=0)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def set_wa_session_connected(db: Session, session_id: int, connected: bool, session_data: str = None):
    s = db.query(models.WhatsAppSession).filter(models.WhatsAppSession.id == session_id).first()
    if not s: return None
    s.connected = 1 if connected else 0
    if session_data is not None: s.session_data = session_data
    db.commit()
    db.refresh(s)
    return s

def list_wa_sessions(db: Session):
    return db.query(models.WhatsAppSession).order_by(models.WhatsAppSession.created_at.desc()).all()

def log_message(db: Session, to_phone: str, content: str, student_id: int = None, status: str = 'pending', error: str = None):
    m = models.MessageLog(to_phone=to_phone, content=content, student_id=student_id, status=status, error=error)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m

def list_message_logs(db: Session, limit: int = 200):
    return db.query(models.MessageLog).order_by(models.MessageLog.sent_at.desc()).limit(limit).all()


def create_wa_account(db: Session, name: str = None, phone_number: str = None, phone_number_id: str = None, access_token: str = None, use_cloud_api: int = 0):
    a = models.WhatsAppAccount(name=name, phone_number=phone_number, connected=0,
                              phone_number_id=phone_number_id, access_token=access_token,
                              use_cloud_api=use_cloud_api)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a

def list_wa_accounts(db: Session):
    return db.query(models.WhatsAppAccount).order_by(models.WhatsAppAccount.created_at.desc()).all()

def delete_wa_account(db: Session, account_id: int):
    a = db.query(models.WhatsAppAccount).filter(models.WhatsAppAccount.id == account_id).first()
    if not a: return False
    db.delete(a)
    db.commit()
    return True


def send_via_whatsapp_cloud(db: Session, account_id: int, to_phone: str, message: str, student_id: int = None):
    """Send a text message via WhatsApp Cloud API using stored credentials.
    This is a best-effort helper; network errors are caught and logged in MessageLog.
    """
    import requests

    acc = db.query(models.WhatsAppAccount).filter(models.WhatsAppAccount.id == account_id).first()
    if not acc or not acc.access_token or not acc.phone_number_id:
        return log_message(db, to_phone=to_phone, content=message, student_id=student_id, status='failed', error='missing_credentials')

    url = f"https://graph.facebook.com/v17.0/{acc.phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {acc.access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': to_phone,
        'type': 'text',
        'text': {'body': message}
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code in (200, 201):
            # mark as sent
            return log_message(db, to_phone=to_phone, content=message, student_id=student_id, status='sent', error=None)
        else:
            return log_message(db, to_phone=to_phone, content=message, student_id=student_id, status='failed', error=r.text)
    except Exception as e:
        return log_message(db, to_phone=to_phone, content=message, student_id=student_id, status='failed', error=str(e))


def send_via_whatsapp_web(db: Session, to_phone: str, message: str, student_id: int = None):
    """Attempt to send via WhatsApp Web automation (Playwright/pywhatkit)."""
    try:
        from .wa_web import send_via_web_best_effort
    except Exception as e:
        return log_message(db, to_phone=to_phone, content=message, student_id=student_id, status='failed', error=f'wa_web_not_available:{e}')

    res = send_via_web_best_effort(to_phone, message)
    if res.get('ok'):
        return log_message(db, to_phone=to_phone, content=message, student_id=student_id, status='sent', error=None)
    else:
        return log_message(db, to_phone=to_phone, content=message, student_id=student_id, status='failed', error=res.get('error'))
