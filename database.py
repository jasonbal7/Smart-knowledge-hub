from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Database URL pointing to a local SQLite file named 'app.db'
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"


# Create the SQLAlchemy engine
# check_same_thread=False' is needed specifically for SQLite in FastAPI
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})


# Create a SessionLocal class for database conversations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our ORM models
Base = declarative_base()

# Dependency helper to get a DB session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()