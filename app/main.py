import secrets
import datetime
import aiofiles
import os
import pathlib
import mimetypes
from uuid import uuid4
from typing import Annotated, Optional

import pydantic
from argon2 import PasswordHasher
from fastapi import FastAPI, Cookie, Form, Depends, Request, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from starlette.endpoints import WebSocketEndpoint
import starlette.status as status
from starlette.websockets import WebSocket
from starlette.routing import WebSocketRoute

from . import schemas
from . import models
from . import schemas
from . import sessionutils
from . import textutils


models.init()


app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')


@app.get('/')
async def index(session_id: Annotated[str | None, Cookie()] = None,
                db: models.OrmSession = Depends(models.get_db)):
    try:
        sessionutils.verify_session(db, session_id)
    except HTTPException:
        return RedirectResponse('/signIn', status.HTTP_302_FOUND)
    return FileResponse('html/chat.html')


@app.get('/signIn')
async def sign_in_get(request: Request, session_id: Annotated[str | None, Cookie()] = None,
                      db: models.OrmSession = Depends(models.get_db)):
    try:
        sessionutils.verify_session(db, session_id)
    except HTTPException as e:
        return templates.TemplateResponse(request=request, name='signIn.html', context={
            'initialForm': 'showSignInForm()'
        })
    return RedirectResponse("/", status.HTTP_302_FOUND)


@app.post('/signIn')
async def sign_in_post(login: Annotated[str, Form()], password: Annotated[str, Form()],
                       request: Request, db: models.OrmSession = Depends(models.get_db)):
    user = db.query(models.User).filter(models.User.login == login).first()
    if not user:
        return templates.TemplateResponse(request=request, name='signIn.html', context={
            'initialForm': 'showSignInForm({"error": "Incorrect username or password"})'
        })

    try:
        ph = PasswordHasher()
        ph.verify(user.password, password + user.password_salt)
    except:
        return templates.TemplateResponse(request=request, name='signIn.html', context={
            'initialForm': 'showSignInForm({"error": "Incorrect username or password"})'
        })

    if user.is_banned:
        return templates.TemplateResponse(request=request, name='signIn.html', context={
            'initialForm': 'showSignInForm({"error": "You are banned"})'
        })

    session = sessionutils.create_session(db, user.id)
    db.add(session)
    db.commit()

    resp = RedirectResponse('/', status.HTTP_302_FOUND)
    resp.set_cookie('session_id', session.token)
    return resp


@app.post('/signUp')
async def sign_up_post(login: Annotated[str, Form()],
                       nickname: Annotated[str, Form()],
                       password: Annotated[str, Form()],
                       master_password: Annotated[str, Form()],
                       request: Request, db: models.OrmSession = Depends(models.get_db)):
    ph = PasswordHasher()
    cur_master_passwd = models.util.get_config_entry(db, 'master_password').value
    try:
        ph.verify(cur_master_passwd, master_password)
    except Exception as e:
        return templates.TemplateResponse(request=request, name='signIn.html', context={
            'initialForm': 'showSignUpForm({"error": "You are not permitted"})'
        })

    existing_user = db.query(models.User).filter(models.User.login == login).first()
    if existing_user:
        return templates.TemplateResponse(request=request, name='signIn.html', context={
            'initialForm': 'showSignUpForm({"error": "Your login was taken"})'
        })

    salt = secrets.token_urlsafe(16)
    passwd_hash = ph.hash(password + salt)

    is_first_to_register = models.util.get_user_by_id(db, 1) is None
    user = models.User(login=login, nickname=nickname, password=passwd_hash, password_salt=salt,
                       is_admin=is_first_to_register, avatar_url='static/defaultAvatar.png')
    db.add(user)
    db.commit()
    db.refresh(user)

    session = sessionutils.create_session(db, user.id)
    db.add(session)
    db.commit()

    resp = RedirectResponse('/', status.HTTP_302_FOUND)
    resp.set_cookie('session_id', session.token)
    return resp


@app.get('/signOut')
async def sign_out(session_id: Annotated[str | None, Cookie()] = None,
                   db: models.OrmSession = Depends(models.get_db)):
    session = sessionutils.verify_session(db, session_id)
    db.delete(session)
    db.commit()

    resp = RedirectResponse('/signIn', status.HTTP_302_FOUND)
    resp.delete_cookie('session_id')
    return resp


def get_uploads_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent / 'uploads'


@app.post('/uploadFiles')
async def upload_files(message_id: Annotated[int, Form()], files: list[UploadFile],
                       session_id: Annotated[str | None, Cookie()] = None,
                       db: models.OrmSession = Depends(models.get_db)):
    session = sessionutils.verify_session(db, session_id)
    msg = db.query(models.Message).filter(models.Message.id == message_id).first()
    if not msg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Message not found')
    if msg.user_id != session.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Operation not permitted')

    attachments = []
    for entry in files:
        try:
            _, ext = os.path.splitext(entry.filename)
            unique_id = uuid4().hex
            attachment = models.Attachment(storage_key=unique_id + ext,
                                           message_id=message_id,
                                           filename=entry.filename)

            path = get_uploads_path() / attachment.storage_key
            async with aiofiles.open(path, 'wb') as f:
                while data := await entry.read(1024 * 1024):
                    await f.write(data)

            db.add(attachment)
            db.commit()
            db.refresh(attachment)
            attachments.append(attachment)
        except Exception:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                 detail='There was an error uploading {}'.format(entry.filename))
    return [schemas.AttachmentRead.parse_obj(x) for x in attachments]


@app.get('/uploads/{storage_key}')
async def uploads_get(storage_key: str, request: Request, preview: bool = False,
                      session_id: Annotated[str | None, Cookie()] = None,
                      db: models.OrmSession = Depends(models.get_db)):
    sessionutils.verify_session(db, session_id)

    path = get_uploads_path() / storage_key
    if not os.path.exists(path):
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    desc = db.query(models.Attachment).filter(models.Attachment.storage_key == storage_key).first()
    guessed_media_type = mimetypes.guess_type(desc.filename)[0] or 'application/octet-stream'

    if preview and guessed_media_type.split('/')[0] == 'image':
        url = str(request.url)
        qm_pos = url.find('?')
        url_no_qs = url[:qm_pos if qm_pos != -1 else None]
        return templates.TemplateResponse(request=request, name='imagePreview.html', context={"url": url_no_qs})
    return FileResponse(path, filename=desc.filename, media_type=guessed_media_type)


class WSEndpoint(WebSocketEndpoint):
    encoding = 'json'

    _clients = []

    class HandlerException(Exception):
        pass

    async def emit(self, event: str, data: dict, targeted_data: Optional[dict] = {}):
        for client in self._clients:
            additional_data = {}
            for target, tdata in targeted_data.items():
                if client is target:
                    additional_data = tdata
            await client.send_json(jsonable_encoder({'event': event, **data, **additional_data}))

    async def on_connect(self, websocket: WebSocket) -> None:
        self._clients.append(websocket)
        await websocket.accept()

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        self._clients.remove(websocket)

    async def on_receive(self, websocket: WebSocket, data: dict) -> None:
        # TODO: Refactor into shorter functions
        db = models.DbSession()
        try:
            try:
                session_id = websocket.cookies['session_id']
            except KeyError:
                raise self.HandlerException('You are not authorized')

            try:
                session = sessionutils.verify_session(db, session_id)
            except HTTPException:
                raise self.HandlerException('You are not authorized')

            user = models.util.get_user_by_id(db, session.user_id)
            if user.is_banned:
                raise self.HandlerException('You are banned')

            try:
                req_type = data['type']
                req_id = data.get('reqId', None)
            except KeyError:
                raise self.HandlerException('Malformed JSON')

            async def reply(event: str, resp):
                resp = {'event': event, **resp}
                if req_id:
                    resp['reqId'] = req_id
                await websocket.send_json(jsonable_encoder(resp))

            def get_channels():
                chans = db.query(models.Channel).all()
                resp_chans = [{'name': ch.name, 'id': ch.id} for ch in chans]
                return resp_chans

            match req_type:
                case 'getChannels':
                    await reply('channels', {'channels': get_channels()})
                case 'deleteChannel':
                    if not user.is_admin:
                        raise self.HandlerException('Operation not permitted')
                    try:
                        req = schemas.ChannelDelete.parse_obj(data)
                    except pydantic.ValidationError:
                        raise self.HandlerException('Malformed request data')
                    chan = db.query(models.Channel).filter(models.Channel.id == req.id).first()
                    if not chan:
                        raise self.HandlerException('Invalid channel ID')
                    db.delete(chan)
                    db.commit()
                    await self.emit('channels', {'channels': get_channels()})
                case 'createChannel':
                    if not user.is_admin:
                        raise self.HandlerException('Operation not permitted')
                    try:
                        req = schemas.ChannelCreate.parse_obj(data)
                    except pydantic.ValidationError:
                        raise self.HandlerException('Malformed request data')
                    chan = models.Channel(name=req.name)
                    db.add(chan)
                    db.commit()
                    await self.emit('channels', {'channels': get_channels()})
                case 'updateChannel':
                    if not user.is_admin:
                        raise self.HandlerException('Operation not permitted')
                    try:
                        req = schemas.ChannelUpdate.parse_obj(data)
                    except pydantic.ValidationError:
                        raise self.HandlerException('Malformed request data')
                    chan = db.query(models.Channel).filter(models.Channel.id == req.id).first()
                    if not chan:
                        raise self.HandlerException('Invalid channel ID')
                    chan.name = req.name
                    db.commit()
                    await self.emit('channels', {'channels': get_channels()})
                case 'getMe':
                    await reply('me', {
                        'id': user.id,
                        'is_admin': user.is_admin,
                        'nickname': user.nickname,
                        'avatar_url': user.avatar_url
                    })
                case 'getMessages':
                    try:
                        req = schemas.GetMessages.parse_obj(data)
                    except pydantic.ValidationError:
                        raise self.HandlerException('Malformed request data')
                    messages = models.util.get_messages(db, req.channel_id, req.offset, req.limit)
                    messages_resp = [schemas.MessageRead.model_validate(x) for x in messages]
                    await reply('messages', {'messages': messages_resp})
                case 'createMessage':
                    try:
                        req = schemas.MessageCreate.parse_obj(data)
                    except pydantic.ValidationError:
                        raise self.HandlerException('Malformed request data')
                    msg_ref_id = None
                    if req.referenced_msg_id is not None:
                        refd_msg = db.query(models.Message).filter(models.Message.id == req.referenced_msg_id).first()
                        if not refd_msg:
                            raise self.HandlerException('Invalid message reference')
                        msg_ref_id = refd_msg.id
                    try:
                        safe_content = textutils.process_message_content(req.content)
                    except textutils.InvalidMessageContent as e:
                        raise self.HandlerException(e.args[0])
                    msg = models.Message(channel_id=req.channel_id, user_id=user.id, content=safe_content,
                                         referenced_msg_id=msg_ref_id)
                    db.add(msg)
                    db.commit()
                    db.refresh(msg)
                    req_tag_for_creator = {}
                    if req_id:
                        req_tag_for_creator[websocket] = {'reqId': req_id}
                    await self.emit('messageCreate', {'message': schemas.MessageRead.model_validate(msg)},
                                    req_tag_for_creator)
                case 'deleteMessage':
                    try:
                        req = schemas.MessageDelete.parse_obj(data)
                    except pydantic.ValidationError:
                        raise self.HandlerException('Malformed request data')
                    msg = db.query(models.Message).filter(models.Message.id == req.id).first()
                    if not user.is_admin and msg.user.id != user.id:
                        raise self.HandlerException('Operation not permitted')
                    db.delete(msg)
                    db.commit()
                    await self.emit('messageDelete', {'message': req})
                case 'updateMessage':
                    try:
                        req = schemas.MessageUpdate.parse_obj(data)
                    except pydantic.ValidationError:
                        raise self.HandlerException('Malformed request data')
                    msg = db.query(models.Message).filter(models.Message.id == req.id).first()
                    if msg.user.id != user.id:
                        raise self.HandlerException('Operation not permitted')
                    # "Touch" a message if the new content is null
                    # Used to emit a message update when an attachment is uploaded
                    if req.content is None:
                        await self.emit('messageUpdate', {'message': schemas.MessageRead.model_validate(msg)})
                        return
                    try:
                        safe_content = textutils.process_message_content(req.content)
                    except textutils.InvalidMessageContent as e:
                        raise self.HandlerException(e.args[0])
                    msg.content = safe_content
                    db.commit()
                    db.refresh(msg)
                    await self.emit('messageUpdate', {'message': schemas.MessageRead.model_validate(msg)})

        except self.HandlerException as e:
            await websocket.send_json({'event': 'error', 'error': e.args[0]})
        finally:
            db.close()



app.add_websocket_route('/ws', WebSocketRoute('/ws', WSEndpoint))
