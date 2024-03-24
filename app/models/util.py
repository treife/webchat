from sqlalchemy.orm import Session as OrmSession

from .user import User
from .config import Config
from .message import Message
from .attachment import Attachment


def get_user_by_id(db: OrmSession, id: int):
    return db.query(User).filter(User.id == id).first()


def get_config_entry(db: OrmSession, key: str):
    return db.query(Config).filter(Config.key == key).first()


def get_messages(db: OrmSession, chan_id: int, offset: int, limit: int):
    count = db.query(Message).filter(Message.channel_id == chan_id).count()
    calc_offset = count - offset - limit
    cut_offset = max(0, calc_offset)
    calc_limit = limit
    if calc_offset < 0:
        calc_limit -= abs(calc_offset)
    if calc_limit <= 0:
        return []
    return (db.query(Message).filter(Message.channel_id == chan_id)
            .offset(cut_offset).limit(calc_limit)
            .all())


def get_attachments_by_msg_id(db: OrmSession, msg_id: int):
    return db.query(Attachment).filter(Attachment.message_id == msg_id).all()
