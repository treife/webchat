from sqlalchemy import Column, ForeignKey, String, Integer, DateTime
from sqlalchemy import func
from sqlalchemy.orm import relationship, Mapped

from .database import Base


class Attachment(Base):
    __tablename__ = 'attachment'

    id = Column(Integer, primary_key=True)
    storage_key = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    message_id = Column(Integer, ForeignKey('message.id'), nullable=False)
    message = relationship('Message', back_populates='attachments')
    filename = Column(String, nullable=False)
