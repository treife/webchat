from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from .database import Base


class Session(Base):
    __tablename__ = 'session'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    token = Column(String, nullable=False)
