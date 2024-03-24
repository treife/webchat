from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


engine = create_engine('sqlite:///./db.sqlite', connect_args={'check_same_thread': False})
DbSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = DbSession()
    try:
        yield db
    finally:
        db.close()
