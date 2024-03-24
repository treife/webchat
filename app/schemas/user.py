from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    is_admin: bool
    is_banned: bool
    avatar_url: str


class UserUpdate(BaseModel):
    id: int
    nickname: Optional[str] = None
    is_admin: Optional[bool] = None
    is_banned: Optional[bool] = None
    avatar_url: Optional[str] = None


class UserDelete(BaseModel):
    id: int
