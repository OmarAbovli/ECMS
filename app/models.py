from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, Text, Date, Float
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# جدول الصفوف
class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)


# جدول المجموعات
class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    class_id = Column(Integer, ForeignKey("classes.id"))
    subscription_price = Column(Float, default=0.0)  # سعر الاشتراك الشهري


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(64), unique=True, index=True)   # الكود الفريد للباركود/RFID
    first_name = Column(String(100))
    last_name = Column(String(100), nullable=True)
    parent_name = Column(String(100), nullable=True)
    parent_phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)


class SessionAttendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    session_date = Column(DateTime, server_default=func.now())
    status = Column(String(20), default="present")  # present/absent/late
    score = Column(Float, nullable=True)
    recorded_by = Column(String(50), default="system")  # system/device/manual


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    amount = Column(Float, default=0.0)
    method = Column(String(50), default="cash")
    payment_date = Column(Date, server_default=func.current_date())
    note = Column(Text, nullable=True)


# جدول الكتب/المذكرات
class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, default=0.0)
    class_id = Column(Integer, ForeignKey("classes.id"))
    type = Column(String(50), default="book")  # book/memo/other


# جدول مشتريات الطالب من الكتب
class StudentBook(Base):
    __tablename__ = "student_books"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    buy_date = Column(DateTime, server_default=func.now())


# جدول الاختبارات/التسميع
class Test(Base):
    __tablename__ = "tests"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    max_score = Column(Float, default=100.0)
    test_date = Column(DateTime, server_default=func.now())


# نتائج الطالب في الاختبارات
class StudentTest(Base):
    __tablename__ = "student_tests"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    test_id = Column(Integer, ForeignKey("tests.id"))
    score = Column(Float, nullable=True)
    recorded_at = Column(DateTime, server_default=func.now())


# نفقات/فواتير الخزنة
class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    amount = Column(Float, default=0.0)
    expense_date = Column(Date, server_default=func.current_date())
    note = Column(Text, nullable=True)


# WhatsApp sessions and message logs
class WhatsAppSession(Base):
    __tablename__ = "wa_sessions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    connected = Column(Integer, default=0)  # 0 = false, 1 = true
    session_data = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class MessageLog(Base):
    __tablename__ = "message_logs"
    id = Column(Integer, primary_key=True, index=True)
    to_phone = Column(String(50))
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    content = Column(Text)
    status = Column(String(50), default="pending")
    error = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)


# Accounts to send from (represent WhatsApp accounts / sessions)
class WhatsAppAccount(Base):
    __tablename__ = 'wa_accounts'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=True)
    phone_number = Column(String(50), nullable=True)
    connected = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    # Optional WhatsApp Cloud API credentials for automatic sending
    phone_number_id = Column(String(120), nullable=True)
    access_token = Column(String(500), nullable=True)
    use_cloud_api = Column(Integer, default=0)
