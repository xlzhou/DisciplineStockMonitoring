from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./discipline_stock.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_stock_columns():
    with engine.connect() as connection:
        result = connection.execute(text("PRAGMA table_info(stocks)"))
        existing = {row[1] for row in result}
        if "avg_entry_price" not in existing:
            connection.execute(text("ALTER TABLE stocks ADD COLUMN avg_entry_price REAL"))
        if "position_qty" not in existing:
            connection.execute(text("ALTER TABLE stocks ADD COLUMN position_qty INTEGER"))
