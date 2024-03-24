from sqlalchemy import Column, Integer, String
from .database import Base


class Channel(Base):
    __tablename__ = 'channel'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
