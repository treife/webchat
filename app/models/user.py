from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    login = Column(String, nullable=False, unique=True)
    nickname = Column(String, nullable=False)
    is_admin = Column(Boolean, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    avatar_url = Column(String, default="static/defaultAvatar.png")
    password = Column(String, nullable=False)
    password_salt = Column(String, nullable=False)

