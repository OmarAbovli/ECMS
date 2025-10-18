import os
from fastapi import FastAPI, Request, Form, Query, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# استبدال relative imports بـ absolute
from .models import Base
from . import crud, models

print("LOADED main.py")

DATABASE_URL = "sqlite:///./center.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# create tables if not exists
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
app.mount("/static", StaticFiles(directory=os.path.dirname(__file__) + "/static"), name="static")

# Dependency to get the DB session
from sqlalchemy.orm import Session # Import Session for type hinting
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Redirect root to dashboard
@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

# ---------------------- API: ADD CLASS ----------------------
@app.post("/api/classes")
async def api_add_class(name: str = Form(...), db: Session = Depends(get_db)):
    from .models import Class
    new_class = Class(name=name)
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return {"ok": True, "id": new_class.id, "name": new_class.name}

# ---------------------- API: CHANGE STUDENT GROUP ----------------------
@app.post("/api/student/change_group")
async def api_change_student_group(student_id: int = Form(...), group_id: int = Form(...), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return {"ok": False, "error": "الطالب غير موجود"}
    student.group_id = group_id
    db.commit()
    return {"ok": True}

# ---------------------- API: UPDATE GROUP NAME ----------------------
@app.post("/api/groups/update")
async def api_update_group_name(group_id: int = Form(...), name: str = Form(...), db: Session = Depends(get_db)):
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return {"ok": False, "error": "المجموعة غير موجودة"}
    group.name = name
    db.commit()
    return {"ok": True}


# ---------------------- API: ADD GROUP & GROUP STUDENTS ----------------------
@app.post("/api/groups")
async def api_add_group(
    name: str = Form(...),
    class_id: int = Form(...),
    subscription_price: float = Form(...),
    db: Session = Depends(get_db)
):
    from .models import Group
    group = Group(name=name, class_id=class_id, subscription_price=subscription_price)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"ok": True, "id": group.id}

@app.get("/api/group_students")
async def api_group_students(group_id: int, db: Session = Depends(get_db)):
    students = db.query(models.Student).filter(models.Student.group_id == group_id).all()
    result = [{"id": s.id, "uuid": s.uuid, "first_name": s.first_name, "last_name": s.last_name} for s in students]
    return result

# ---------------------- GROUPS PAGE ----------------------
@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("groups.html", {"request": request})

# ---------------------- API: CLASSES & GROUPS ----------------------
@app.get("/api/classes")
async def api_get_classes(db: Session = Depends(get_db)):
    classes = crud.get_all_classes(db)
    return [{"id": c.id, "name": c.name} for c in classes]

@app.get("/api/groups")
async def api_get_groups(class_id: int = Query(None), db: Session = Depends(get_db)):
    groups = crud.get_all_groups(db, class_id)
    return [{"id": g.id, "name": g.name, "class_id": g.class_id} for g in groups]

# ---------------------- API: BOOKS ----------------------
@app.post("/api/books")
async def api_add_book(name: str = Form(...), price: float = Form(...), class_id: int = Form(...), type: str = Form("book"), db: Session = Depends(get_db)):
    from .models import Book
    book = Book(name=name, price=price, class_id=class_id, type=type)
    db.add(book)
    db.commit()
    db.refresh(book)
    return {"ok": True, "id": book.id}


@app.get("/api/books")
async def api_get_books(class_id: int = Query(None), db: Session = Depends(get_db)):
    from .models import Book
    q = db.query(Book)
    if class_id:
        q = q.filter(Book.class_id == class_id)
    books = q.order_by(Book.id.asc()).all()
    return [{"id": b.id, "name": b.name, "price": b.price, "type": b.type, "class_id": b.class_id} for b in books]


@app.post("/api/student/buy_book")
async def api_student_buy_book(student_id: int = Form(...), book_id: int = Form(...), db: Session = Depends(get_db)):
    from .models import StudentBook
    sb = StudentBook(student_id=student_id, book_id=book_id)
    db.add(sb)
    db.commit()
    return {"ok": True}


@app.get("/api/student/{student_id}/books")
async def api_get_student_books(student_id: int, db: Session = Depends(get_db)):
    # join student_books with books to return book info + buy date
    from .models import StudentBook, Book
    q = db.query(StudentBook, Book).join(Book, StudentBook.book_id == Book.id).filter(StudentBook.student_id == student_id).order_by(StudentBook.buy_date.desc()).all()
    result = []
    for sb, b in q:
        result.append({
            "id": b.id,
            "name": b.name,
            "price": b.price,
            "type": b.type,
            "buy_date": sb.buy_date.isoformat() if sb.buy_date is not None else None
        })
    return result


# ---------------------- API: TESTS & RESULTS ----------------------
@app.post("/api/tests")
async def api_add_test(name: str = Form(...), class_id: int = Form(None), max_score: float = Form(100.0), db: Session = Depends(get_db)):
    from .models import Test
    t = Test(name=name, class_id=class_id, max_score=max_score)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"ok": True, "id": t.id}


@app.get("/api/tests")
async def api_get_tests(class_id: int = Query(None), db: Session = Depends(get_db)):
    from .models import Test
    q = db.query(Test)
    if class_id:
        q = q.filter(Test.class_id == class_id)
    tests = q.order_by(Test.test_date.desc()).all()
    return [{"id": t.id, "name": t.name, "max_score": t.max_score, "test_date": t.test_date.isoformat()} for t in tests]


@app.post("/api/student/add_result")
async def api_add_student_result(student_id: int = Form(...), test_id: int = Form(...), score: float = Form(...), db: Session = Depends(get_db)):
    from .models import StudentTest
    st = StudentTest(student_id=student_id, test_id=test_id, score=score)
    db.add(st)
    db.commit()
    return {"ok": True}


@app.get("/api/student/{student_id}/results")
async def api_get_student_results(student_id: int, db: Session = Depends(get_db)):
    from .models import StudentTest, Test
    q = db.query(StudentTest, Test).join(Test, StudentTest.test_id == Test.id).filter(StudentTest.student_id == student_id).order_by(StudentTest.recorded_at.desc()).all()
    res = []
    for st, t in q:
        res.append({"test_id": t.id, "test_name": t.name, "score": st.score, "max_score": t.max_score, "recorded_at": st.recorded_at.isoformat()})
    return res

# ---------------------- API ENDPOINTS ----------------------

@app.post("/api/students")
async def api_create_student(
    uuid: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(None),
    parent_name: str = Form(None),
    parent_phone: str = Form(None),
    class_id: int = Form(None),
    group_id: int = Form(None),
    db: Session = Depends(get_db)
):
    student = crud.create_student(db, uuid, first_name, last_name, parent_name, parent_phone, class_id, group_id)
    return {
        "id": student.id,
        "uuid": student.uuid
    }

@app.post("/api/scan")
async def api_scan(payload: dict, db: Session = Depends(get_db)):
    code = payload.get("code")
    student = crud.get_student_by_uuid(db, code)
    if not student:
        return JSONResponse({"error": "student_not_found"}, status_code=404)

    # --- NEW: Automatically mark attendance if not already marked for today ---
    from datetime import date # Import date for comparison
    new_attendance_record = None
    existing_attendance_today = db.query(models.SessionAttendance).filter(
        models.SessionAttendance.student_id == student.id,
        func.date(models.SessionAttendance.session_date) == date.today()
    ).first()

    if not existing_attendance_today:
        new_attendance_record = crud.mark_attendance(db, student.id, status="present", recorded_by="RFID_scan")
    # --- END NEW ---

    last_att = crud.get_last_attendance(db, student.id)
    pay_status = crud.get_payment_status(db, student.id)
    return {
        "student": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "uuid": student.uuid,
            "parent_phone": student.parent_phone,
            "class_id": student.class_id,
        },
        "last_attendance": str(last_att.session_date) if last_att else None,
        "payment_status": pay_status,
        "auto_marked_attendance": str(new_attendance_record.session_date) if new_attendance_record else None
    }


@app.get('/api/students/search')
async def api_search_students(q: str = Query(None), db: Session = Depends(get_db)):
    if not q:
        return []
    items = crud.search_students(db, q)
    res = []
    for s in items:
        class_name = None
        group_name = None
        if s.class_id:
            c = db.query(models.Class).filter(models.Class.id == s.class_id).first()
            if c: class_name = c.name
        if s.group_id:
            g = db.query(models.Group).filter(models.Group.id == s.group_id).first()
            if g: group_name = g.name
        res.append({
            "id": s.id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "uuid": s.uuid,
            "class_id": s.class_id,
            "class_name": class_name,
            "group_id": s.group_id,
            "group_name": group_name
        })
    return res

@app.post("/api/attendance")
async def api_attendance(code: str = Form(...), status: str = Form("present"), score: float = Form(None), db: Session = Depends(get_db)):
    student = crud.get_student_by_uuid(db, code)
    if not student:
        return JSONResponse({"error": "student_not_found"}, status_code=404)
    att = crud.mark_attendance(db, student.id, status=status, score=score)
    return {"ok": True, "attendance_id": att.id, "session_date": str(att.session_date)}

@app.post("/api/payment")
async def api_payment(code: str = Form(...), amount: float = Form(...), method: str = Form("cash"), note: str = Form(None), db: Session = Depends(get_db)):
    student = crud.get_student_by_uuid(db, code)
    if not student:
        return JSONResponse({"error": "student_not_found"}, status_code=404)
    p = crud.add_payment(db, student.id, amount, method=method, note=note)
    return {"ok": True, "payment_id": p.id}

# ---------------------- PAGES ----------------------

@app.get("/scanner", response_class=HTMLResponse)
async def scanner_page(request: Request):
    return templates.TemplateResponse("scanner.html", {"request": request})

@app.get("/student/{code}", response_class=HTMLResponse)
async def student_card(request: Request, code: str, db: Session = Depends(get_db)):
    student = crud.get_student_by_uuid(db, code)
    if not student:
        return Response("Student not found", status_code=404)
    last_att = crud.get_last_attendance(db, student.id)
    pay_status = crud.get_payment_status(db, student.id)
    group = None
    group_price = None
    if student.group_id:
        group = db.query(models.Group).filter(models.Group.id == student.group_id).first()
        if group:
            group_price = group.subscription_price
    return templates.TemplateResponse("student_card.html", {
        "request": request,
        "student": student,
        "last_attendance": last_att,
        "payment_status": pay_status,
        "group_price": group_price
    })

@app.post("/api/student/{student_id}/delete")
async def api_delete_student(student_id: int, db: Session = Depends(get_db)):
    try:
        success = crud.delete_student(db, student_id)
        if not success:
            return JSONResponse({"ok": False, "error": "student_not_found"}, status_code=404)
        return {"ok": True}
    except Exception as e:
        db.rollback()
        return JSONResponse({"ok": False, "error": f"database_error: {str(e)}"}, status_code=500)


# ---------------------- ADMIN DASHBOARD ----------------------

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    students = crud.get_all_students(db)   # لازم تكون عامل دالة في crud ترجع كل الطلاب
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "students": students
    })

# ---------------------- CENTER DASHBOARD ----------------------
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ---------------------- TREASURY (الخزنة) ----------------------
@app.get('/api/treasury/summary')
async def api_treasury_summary(db: Session = Depends(get_db)):
    summary = crud.get_treasury_summary(db)
    return summary


@app.post('/api/treasury/expense')
async def api_add_expense(title: str = Form(...), amount: float = Form(...), note: str = Form(None), db: Session = Depends(get_db)):
    e = crud.add_expense(db, title, amount, note=note)
    return {"ok": True, "id": e.id}


@app.get('/api/treasury/expenses')
async def api_list_expenses(limit: int = Query(100), db: Session = Depends(get_db)):
    items = crud.list_expenses(db, limit=limit)
    return [{"id": i.id, "title": i.title, "amount": i.amount, "date": str(i.expense_date), "note": i.note} for i in items]


# ---------------------- WhatsApp Integration (lightweight) ----------------------
@app.post('/api/wa/session')
async def api_create_wa_session(name: str = Form(None), db: Session = Depends(get_db)):
    s = crud.create_wa_session(db, name=name)
    # For now return session id; front-end will call /api/wa/session/{id}/qr to get QR
    return {"ok": True, "id": s.id}


@app.get('/api/wa/sessions')
async def api_list_wa_sessions(db: Session = Depends(get_db)):
    items = crud.list_wa_sessions(db)
    return [{"id": i.id, "name": i.name, "connected": bool(i.connected), "created_at": str(i.created_at)} for i in items]


@app.get('/api/wa/session/{session_id}/qr')
async def api_get_wa_qr(session_id: int, db: Session = Depends(get_db)):
    s = db.query(models.WhatsAppSession).filter(models.WhatsAppSession.id == session_id).first()
    if not s:
        return JSONResponse({'error':'not_found'}, status_code=404)
    # In a real integration we'd return the QR image data; here return a placeholder text instructing user to scan WhatsApp Web
    return {"ok": True, "qr_hint": "افتح واتساب ويب او استخدم التطبيق لمسح الكيو آر المعروض هنا عبر تكامل خارجي"}


@app.post('/api/wa/send_report')
async def api_send_report(student_id: int = Form(None), group_id: int = Form(None), send_mode: str = Form(None), db: Session = Depends(get_db)):
    # If student_id provided, send to that student's parent phone
    sent = []
    if student_id:
        student = db.query(models.Student).filter(models.Student.id == student_id).first()
        if not student:
            return JSONResponse({"ok": False, "error": "student_not_found"}, status_code=404)
        phone = (student.parent_phone or '').strip()
        
        # Generate the report message
        report_message = crud.generate_student_report(db, student_id)

        # determine mode: explicit send_mode='auto' forces auto, otherwise try auto if account enabled
        use_auto = (send_mode == 'auto')
        acc = db.query(models.WhatsAppAccount).filter(models.WhatsAppAccount.use_cloud_api == 1).first()
        if use_auto and not acc:
            return JSONResponse({"ok": False, "error": "no_auto_account_configured"}, status_code=400)
        if acc and (use_auto or acc):
            # if acc exists and either user asked for auto or it's available, use it
            log = crud.send_via_whatsapp_cloud(db, acc.id, phone, report_message, student_id=student.id)
            return {"ok": True, "log_id": log.id, "to": phone, "auto_sent": log.status == 'sent'}
        # if user requested web automation explicitly or cloud not configured, try web automation
        if send_mode == 'web' or (send_mode == 'auto' and not acc):
            log = crud.send_via_whatsapp_web(db, phone, report_message, student_id=student.id)
            return {"ok": True, "log_id": log.id, "to": phone, "auto_sent": log.status == 'sent'}
        else:
            log = crud.log_message(db, phone, report_message, student_id=student.id)
            return {"ok": True, "log_id": log.id, "to": phone, "auto_sent": False}

    # if group_id provided, send to members of that group
    if group_id:
        students = db.query(models.Student).filter(models.Student.group_id == group_id).all()
        # try to find a cloud-enabled account
        acc = db.query(models.WhatsAppAccount).filter(models.WhatsAppAccount.use_cloud_api == 1).first()
        use_auto = (send_mode == 'auto')
        count = 0
        for s in students:
            phone = (s.parent_phone or '').strip()
            
            # Generate the report message for each student
            report_message = crud.generate_student_report(db, s.id)

            if acc and (use_auto or acc):
                crud.send_via_whatsapp_cloud(db, acc.id, phone, report_message, student_id=s.id)
            else:
                # if user asked explicitly for web automation, attempt it
                if send_mode == 'web' or (send_mode == 'auto' and not acc):
                    crud.send_via_whatsapp_web(db, phone, report_message, student_id=s.id)
                else:
                    crud.log_message(db, phone, report_message, student_id=s.id)
            count += 1
        return {"ok": True, "sent": count, "auto_sent": bool(acc and use_auto)}

    return JSONResponse({"ok": False, "error": "no_target"}, status_code=400)


@app.get('/api/wa/logs')
async def api_wa_logs(limit: int = Query(200), db: Session = Depends(get_db)):
    items = crud.list_message_logs(db, limit=limit)
    return [{"id": i.id, "to": i.to_phone, "student_id": i.student_id, "content": i.content, "status": i.status, "error": i.error, "sent_at": str(i.sent_at) if i.sent_at else None} for i in items]


# WA accounts CRUD
@app.post('/api/wa/accounts')
async def api_create_wa_account(
    name: str = Form(None),
    phone_number: str = Form(None),
    phone_number_id: str = Form(None),
    access_token: str = Form(None),
    use_cloud_api: int = Form(0),
    db: Session = Depends(get_db)
):
    a = crud.create_wa_account(db, name=name, phone_number=phone_number, phone_number_id=phone_number_id, access_token=access_token, use_cloud_api=use_cloud_api)
    return {"ok": True, "id": a.id}


@app.get('/api/wa/accounts')
async def api_list_wa_accounts(db: Session = Depends(get_db)):
    items = crud.list_wa_accounts(db)
    return [{"id": i.id, "name": i.name, "phone_number": i.phone_number, "connected": bool(i.connected), "created_at": str(i.created_at), "phone_number_id": i.phone_number_id, "use_cloud_api": bool(i.use_cloud_api)} for i in items]


@app.post('/api/wa/accounts/{account_id}/delete')
async def api_delete_wa_account(account_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_wa_account(db, account_id)
    return {"ok": bool(ok)}


@app.get('/wa', response_class=HTMLResponse)
async def wa_page(request: Request):
    return templates.TemplateResponse('wa.html', {"request": request})


@app.post('/api/wa/send_via_web')
async def api_wa_send_via_web(phone: str = Form(...), message: str = Form(...), db: Session = Depends(get_db)):
    # use web automation helper
    log = crud.send_via_whatsapp_web(db, phone, message)
    return {"ok": True, "log_id": log.id, "status": log.status, "error": log.error}
