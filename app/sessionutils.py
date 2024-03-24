import datetime
import secrets
from typing import Optional
from sqlalchemy.sql.functions import now
from fastapi import HTTPException
import starlette.status as status

from .models import Session, User, OrmSession


SESSION_DURATION = datetime.timedelta(minutes=45)


def create_session(db: OrmSession, user_id: int) -> Session:
    token = secrets.token_hex(16)
    expires_at = datetime.datetime.now() + SESSION_DURATION
    return Session(user_id=user_id, token=token, expires_at=expires_at)


def verify_session(db: OrmSession, token: str) -> Session:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    valid_session = db.query(Session).filter(Session.token == token).filter(Session.expires_at > now()).first()
    if not valid_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    return valid_session
