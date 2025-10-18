# إضافة بعض الصفوف والمجموعات الافتراضية عند أول تشغيل
from app.models import Base, Class, Group
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./center.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    # إضافة صفوف افتراضية إذا لم تكن موجودة
    if not db.query(Class).first():
        c1 = Class(name="الصف الأول")
        c2 = Class(name="الصف الثاني")
        c3 = Class(name="الصف الثالث")
        db.add_all([c1, c2, c3])
        db.commit()
    db.close()

if __name__ == "__main__":
    seed()
