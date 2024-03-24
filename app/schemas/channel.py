from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ChannelCreate(BaseModel):
    name: str


class ChannelUpdate(BaseModel):
    id: int
    name: str


class ChannelDelete(BaseModel):
    id: int
