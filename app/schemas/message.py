from pydantic import BaseModel, Field, ConfigDict

from typing import Optional
from datetime import datetime

from .user import UserRead
from .attachment import AttachmentRead


class MessageReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user: UserRead
    content: str


class GetMessages(BaseModel):
    channel_id: int
    offset: int = Field(default=0)  # 0 = latest message
    limit: int = Field(default=50)


class MessageCreate(BaseModel):
    channel_id: int
    content: str
    attachments: Optional[list[str]] = None
    referenced_msg_id: Optional[int] = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    channel_id: int
    referenced_msg: Optional[MessageReference] = None
    content: str
    user: UserRead
    attachments: list[AttachmentRead]


class MessageUpdate(BaseModel):
    id: int
    content: Optional[str]


class MessageDelete(BaseModel):
    id: int
