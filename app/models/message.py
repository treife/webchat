from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

from .database import Base
from .user import User
from .channel import Channel
from .attachment import Attachment


class Message(Base):
    __tablename__ = 'message'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    channel_id = Column(Integer, ForeignKey('channel.id'), nullable=False)
    channel: Mapped[Channel] = relationship()
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user: Mapped[User] = relationship()
    referenced_msg_id = Column(Integer, ForeignKey('message.id'), default=None)
    referenced_msg = relationship(lambda: Message, remote_side=id)
    content = Column(String)
    attachments: Mapped[List[Attachment]] = relationship(back_populates='message')
