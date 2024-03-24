from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    storage_key: str
    created_at: datetime
    message_id: int
    filename: str
