class Message {
    constructor(obj, clientsideInfo) {
        this.id = obj['id']
        this.created_at = obj['created_at']
        this.updated_at = obj['updated_at']
        this.channel_id = obj['channel_id']
        this.content = obj['content']
        this.user = obj['user']
        this.attachments = obj['attachments']
        this.referenced_msg = obj['referenced_msg']

        this.clientsideInfo = clientsideInfo
    }
}

class UIManager {
    constructor() {
        this.initialized = false
    }

    templSubst(templId, context, contextUnsafe={}) {
        const inst = document.createElement('div')
        inst.append(document.getElementById(templId).content.cloneNode(true))
        for (const [ident, text] of Object.entries(context)) {
            const el = inst.getElementsByClassName(ident)
            for (const e of el)
                e.innerText = text
        }
        for (const [ident, text] of Object.entries(contextUnsafe)) {
            const el = inst.getElementsByClassName(ident)
            for (const e of el)
                e.innerHTML = text
        }
        return inst
    }

    updateChannelList(channels) {
        const channelList = document.getElementById('channel-list')
        const updated = channelList.cloneNode(true)
        updated.innerHTML = ''
        for (const chan of channels) {
            const entry = this.templSubst('channel-btn-templ', {name: chan.name})
            const chanBtn = entry.getElementsByClassName('channel-btn')[0]
            chanBtn.setAttribute('data-id', chan.id.toString())
            chanBtn.setAttribute('onclick', `Controller.setCurChannel(this.getAttribute('data-id'))`)
            updated.appendChild(entry)
        }

        channelList.parentElement.replaceChild(updated, channelList)
    }

    setChannelAsCurrent(id) {
        document.getElementById('channel-list')
            .querySelector(`button[data-id="${id}"]`)
            .classList.add('channel-btn-cur')
    }
    removeChannelAsCurrent(id) {
        document.getElementById('channel-list')
            .querySelector(`button[data-id="${id}"]`)
            .classList.remove('channel-btn-cur')
    }

    updateSelfInfo(user) {
        const nickname = document.getElementById('me-nickname')
        nickname.innerText = user['nickname']
        if (user['is_admin']) {
            nickname.style.color = 'red'
        }
        else {
            nickname.style.color = 'antiquewhite'
        }

        document.getElementById('me-avatar').src = user['avatar_url']
    }

    _wrapDate1Dy(isoString) {
        const now = new Date()
        const date = new Date(isoString)
        if (Math.round(now - date) / (1000 * 3600 * 24) < 1)
            return date.toLocaleTimeString()
        return date.toLocaleString()
    }

    _createMessageElement(msg) {
        const elem = this.templSubst('message-list-entry-templ', {
            'msg-author-name': msg.user.nickname,
            'msg-content': msg['content']
        })

        const msgContainer = elem.getElementsByClassName('msg-container')[0]

        if (msg.clientsideInfo.mentionsMe) {
            msgContainer.classList.add('mentions-me')
            msgContainer.getElementsByClassName('ref-msg-container')[0].classList.add('mentions-me')
        }

        msgContainer.setAttribute('data-id', msg.id)

        elem.getElementsByClassName('msg-author-avatar')[0].setAttribute('src', msg.user.avatar_url)
        elem.getElementsByClassName('msg-created-at')[0].innerText = this._wrapDate1Dy(msg.created_at)
        if (msg.updated_at)
            elem.getElementsByClassName('msg-updated-at')[0].innerText =
                `Edited: ${this._wrapDate1Dy(msg.updated_at)}`

        if (msg.user.is_admin)
            elem.getElementsByClassName('msg-author-name')[0].style.color = 'red'
        else
            elem.getElementsByClassName('msg-author-name')[0].style.color = 'antiquewhite'
        // Enable allowed actions
        const actions = elem.getElementsByClassName('msg-actions')[0]
        if (msg.user.id === State.me.value.id)
            actions.getElementsByClassName('edit')[0].style.display = 'inline-block'
        if (msg.user.id === State.me.value.id || State.me.value.is_admin)
            actions.getElementsByClassName('delete')[0].style.display = 'inline-block'

        const attachmentsContainer = document.createElement('div')
        attachmentsContainer.classList.add('attachments-container')
        for (const attch of msg.attachments) {
            const storageKey = attch['storage_key']
            const filename = attch['filename']
            const url = `/uploads/${storageKey}`

            const pastLastDot = filename.lastIndexOf('.') + 1
            const naiveExt = pastLastDot == 0 ? '' : filename.slice(pastLastDot).toLowerCase()

            const a = document.createElement('a')
            if (['png', 'gif', 'jpg', 'jpeg', 'svg', 'tiff'].indexOf(naiveExt) != -1) {
                a.setAttribute('target', '_blank') // Open in a new tab
                a.href = url + '?preview=1'

                const preview = document.createElement('img')
                preview.classList.add('image-preview')
                preview.src = url

                a.appendChild(preview)
                attachmentsContainer.appendChild(a)
            }
            else {
                a.href = url
                a.style.userSelect = 'none'
                a.style.textDecoration = 'none'
                a.innerText = '📁'
                a.style.fontSize = '48px'

                attachmentsContainer.appendChild(a)
            }
        }
        msgContainer.appendChild(attachmentsContainer)

        const ref_msg = msg['referenced_msg']
        if (ref_msg) {
            const nicknameTag = elem.getElementsByClassName('ref-msg-nickname')[0]
            nicknameTag.src = ref_msg.user.nickname
            if (ref_msg.user.is_admin)
                nicknameTag.style.color = 'red'
            elem.getElementsByClassName('ref-msg-avatar')[0].src = ref_msg.user.avatar_url
            elem.getElementsByClassName('ref-msg-nickname')[0].innerText = ref_msg.user.nickname + ': '
            elem.getElementsByClassName('ref-msg-content')[0].innerText = this._wrapSingleLine(ref_msg.content)

            const container = elem.getElementsByClassName('ref-msg-container')[0]
            container.style.display = 'block'
            container.onclick = () => {
                UI.jumpToMessage(ref_msg.id)
                UI.highlightMessage(ref_msg.id)
            }
        }

        return elem
    }

    replaceMessageView(messages) {
        const list = document.getElementById('message-list')
        const newList = list.cloneNode(true)
        newList.innerHTML = ''
        for (const msg of messages)
            newList.appendChild(this._createMessageElement(msg))
        list.parentNode.replaceChild(newList, list)
        newList.scrollTo(0, newList.scrollHeight)
    }

    prependMessages(messages) {
        const list = document.getElementById('message-list')
        for (const msg of messages.reverse())
            list.prepend(this._createMessageElement(msg))
        this.jumpToMessage(messages[0].id)
    }

    appendMessage(msg) {
        const list = document.getElementById('message-list')
        const updateScroll = (list.scrollHeight - list.offsetHeight) - list.scrollTop <= 1
        list.appendChild(this._createMessageElement(msg))
        if (updateScroll)
            list.scrollTo(0, list.scrollHeight)
    }

    deleteMessage(id) {
        const list = document.getElementById('message-list')
        const entry = list.querySelector(`div[data-id="${id}"]`)
        if (!entry)
            return
        entry.parentNode.removeChild(entry)
    }

    updateMessage(msg) {
        const list = document.getElementById('message-list')
        const entry = list.querySelector(`div[data-id="${msg.id}"]`)
        const newEntry = this._createMessageElement(msg)
        entry.parentNode.replaceChild(newEntry, entry)
    }

    jumpToMessage(id) {
        const list = document.getElementById('message-list')
        const entry = list.querySelector(`div[data-id="${id}"]`)
        if (!entry) {
            alert('Message not in cache')
            return
        }
        entry.scrollIntoView()
    }

    highlightMessage(id) {
        const list = document.getElementById('message-list')
        const entry = list.querySelector(`div[data-id="${id}"]`)
        entry.animate([
            {backgroundColor: '#888888'},
            {backgroundColor: '#666666'}
        ],{
            easing: 'ease-in-out',
            duration: 500
        })
    }

    _wrapSingleLine(text) {
        const lf = text.search('\n')
        if (lf != -1)
            return text.slice(0, lf)
        return text;
    }

    showInputStatusBar(mode, content) {
        const statusBar = document.getElementById('message-input-status-bar')
        statusBar.style.display = 'inline-block'

        statusBar.getElementsByClassName('info')[0].innerText = mode
        statusBar.getElementsByClassName('content')[0].innerText = this._wrapSingleLine(content)

        return statusBar
    }

    hideInputStatusBar() {
        const statusBar = document.getElementById('message-input-status-bar')
        statusBar.style.display = 'none'
    }

    enterMsgEditMode(msg) {
        const list = document.getElementById('message-list')
        const entry = list.querySelector(`div[data-id="${msg.id}"]`)

        const statusBar = this.showInputStatusBar('Editing: ', this._wrapSingleLine(msg.content))
        statusBar.onclick = () => {
            UI.jumpToMessage(msg.id)
            UI.highlightMessage(msg.id)
        }

        const textarea = document.getElementById('message-input')
        textarea.value = msg.content
        textarea.focus()
    }

    leaveMsgEditMode() {
        this.hideInputStatusBar()

        const textarea = document.getElementById('message-input')
        textarea.value = ''
    }

    enterReplyMode(msg) {
        const list = document.getElementById('message-list')
        const entry = list.querySelector(`div[data-id="${msg.id}"]`)

        const statusBar = document.getElementById('message-input-status-bar')
        statusBar.style.display = 'inline-block'

        statusBar.getElementsByClassName('info')[0].innerText = 'Replying to: '
        statusBar.getElementsByClassName('content')[0].innerText = this._wrapSingleLine(msg.content)

        statusBar.onclick = () => {
            UI.jumpToMessage(msg.id)
            UI.highlightMessage(msg.id)
        }

        const textarea = document.getElementById('message-input')
        textarea.focus()
    }
}

UI = new UIManager()

class PendingUpload {
    constructor(reqId, files) {
        // reqId - unique ID to track the message the files are to be attached to
        this.reqId = reqId
        this.files = files
    }
}

const MESSAGE_PAGINATION = 50

class StateClass {
    constructor() {
        this.curChannelId = {
            value: null,
            update: id => {
                if (this.curChannelId.value)
                    UI.removeChannelAsCurrent(this.curChannelId.value)
                this.curChannelId.value = id
                UI.setChannelAsCurrent(this.curChannelId.value)
            }
        }

        this.channelList = {
            value: null,
            update: channels => {
                this.channelList.value = channels
                UI.updateChannelList(this.channelList.value)
            }
        }

        this.messageList = {
            value: null,
            update: messages => {
                this.messageList.value = messages
                UI.replaceMessageView(this.messageList.value)
            },
            append: message => {
                this.messageList.value.push(message)
                UI.appendMessage(this.messageList.value.at(-1))
            },
            prepend: messages => {
                this.messageList.value.unshift(...messages)
                UI.prependMessages(messages)
            },
            delete: id => {
                this.messageList.value = this.messageList.value.filter(x => x.id !== id)
                UI.deleteMessage(id)
            },
            updateMessage: msg => {
                this.messageList.value = this.messageList.value.map(x => x.id === msg.id ? msg : x)
            }
        }

        this.me = {
            value: null,
            update: me => {
                this.me.value = me
                UI.updateSelfInfo(this.me.value)
            }
        }

        this.editedMessage = {
            value: null,
            update: id => {
                this.editedMessage.value = id
                if (this.editedMessage.value === null)
                    UI.leaveMsgEditMode()
                else {
                    const msg = this.messageList.value.find(x => x.id === id)
                    UI.enterMsgEditMode(msg)
                }
            }
        }

        this.replyingTo = {
            value: null,
            update: id => {
                this.replyingTo.value = id
                if (this.replyingTo.value === null)
                    UI.hideInputStatusBar()
                else {
                    const msg = this.messageList.value.find(x => x.id === id)
                    UI.enterReplyMode(msg)
                }
            }
        }

        this.pendingUpload = {
            value: null,
            update: (val) => this.pendingUpload.value = val
        }

        this.fetchMessagesOffset = {
            value: 0,
            update: (offset) => this.fetchMessagesOffset.value = offset,
            pageUp: () => this.fetchMessagesOffset.value = this.fetchMessagesOffset.value + MESSAGE_PAGINATION,
            pageDown: () => this.fetchMessagesOffset.value = Math.max(0, this.fetchMessagesOffset.value - MESSAGE_PAGINATION)
        }
    }
}

State = new StateClass()

class ControllerClass {
    signOut() {
        websocket.close()
        window.location.href = '/signOut'
    }

    setCurChannel(id) {
        State.editedMessage.update(null)
        State.curChannelId.update(id)
        State.fetchMessagesOffset.update(0)
        websocket.getMessages(id)
    }

    messageInputOnKeydown(ev) {
        const input = document.getElementById('message-input')
        if (ev.keyCode === 13 && !ev.shiftKey) {
            if (input.value.length === 0) {
                ev.preventDefault()
                return
            }

            if (State.editedMessage.value !== null) {
                const editedMsg = State.messageList.value.find(msg => msg.id === State.editedMessage.value)
                websocket.updateMessage({
                    id: editedMsg.id,
                    content: input.value
                })
                State.editedMessage.update(null)
                input.value = ''
            }
            else {
                websocket.createMessage({
                    channel_id: State.curChannelId.value,
                    content: input.value,
                    referenced_msg_id: State.replyingTo.value
                })
                if (State.replyingTo.value)
                    State.replyingTo.update(null)
                input.value = ''
            }
            ev.preventDefault()
        }
        else if (ev.keyCode === 27) {
            // ESC
            // Leave edit / reply mode
            if (State.editedMessage.value !== null)
                State.editedMessage.update(null)
            else if (State.replyingTo.value !== null)
                State.replyingTo.update(null)
            ev.preventDefault()
        }
    }

    deleteMessage(ev) {
        // TODO: Dynamically generate the callback
        const id = ev.target.parentNode.parentNode.getAttribute('data-id')
        websocket.deleteMessage(parseInt(id))
    }

    editMessage(ev) {
        // TODO: Dynamically generate the callback
        const id = parseInt(ev.target.parentNode.parentNode.getAttribute('data-id'))
        State.editedMessage.update(id)
    }

    updateMessage(msg) {
        if (State.curChannelId.value == msg.channel_id) {
            State.messageList.updateMessage(msg)
            UI.updateMessage(msg)
        }
    }

    showFileUploadDialog() {
        const input = document.getElementById('upload-files-hdn')
        input.click()
    }

    fileUploadOnChange(input) {
        const files = input.files
        if (!files.length)
            return

        State.pendingUpload.update(new PendingUpload('uploadTarget', files))

        const msgInput = document.getElementById('message-input')

        const content = msgInput.value || '🡇'
        websocket.createMessage({
            channel_id: State.curChannelId.value,
            content: content,
            referenced_msg_id: State.replyingTo.value
        }, State.pendingUpload.value.reqId)

        if (State.replyingTo.value !== null)
            State.replyingTo.update(null)
        msgInput.value = ''
    }

    setReplyingTo(ev) {
        const id = ev.target.parentNode.parentNode.getAttribute('data-id')
        State.replyingTo.update(parseInt(id))
    }

    setNormalMode(ev) {
        if (ev.target.id === 'message-input-status-bar-exit' || ev.target.tagName === 'A') {
            State.editedMessage.update(null)
            State.replyingTo.update(null)
            UI.hideInputStatusBar()
            ev.stopPropagation()
        }
    }

    messageListOnScroll(list) {
        const hitBottom = (list.scrollHeight - list.offsetHeight) - list.scrollTop <= 1
        const hitTop = list.scrollTop === 0
        if (hitTop) {
            State.fetchMessagesOffset.pageUp()
            websocket.getMessages(State.curChannelId.value, State.fetchMessagesOffset.value)
        }
        // else if (hitBottom && State.fetchMessagesOffset.value > 0) {
        //     websocket.getMessages(State.curChannelId.value, State.fetchMessagesOffset.value)
        //     State.fetchMessagesOffset.pageDown()
        // }
    }
}

Controller = new ControllerClass()

function messagePayloadToClientModel(msg) {
    const mentionsMe = (msg.content.search(State.me.value.nickname) !== -1) ||
        msg.referenced_msg?.user.id === State.me.value.id
    const clientsideInfo = {
        mentionsMe: mentionsMe
    }
    return new Message(msg, clientsideInfo)
}

function wsOnOpen(ws) {
    ws.getMe()
    ws.getChannels()
}
function wsOnMessage(ws, data) {
    switch (data['event']) {
        case 'me':
            State.me.update(data)
            break
        case 'channels':
            State.channelList.update(data['channels'])
            State.curChannelId.update(State.curChannelId.value ?? State.channelList.value[0].id)
            if (!this.initialized)
                ws.getMessages(data['channels'][0].id)
            break
        case 'messages':
            const messages = data['messages'].map(msg => messagePayloadToClientModel(msg))
            if (State.fetchMessagesOffset.value > 0)
                State.messageList.prepend(messages)
            else
                State.messageList.update(messages)
            break
        case 'messageCreate':
            const msg = data['message']
            if ('reqId' in data && data['reqId'] === State.pendingUpload.value?.reqId) {
                API.uploadFiles(msg.id, State.pendingUpload.value.files, () => {
                    State.pendingUpload.update(null)
                    // 'Touch' the message to propagate an update event with the attachments
                    ws.updateMessage({id: msg.id, content: null})
                })
            }
            State.messageList.append(messagePayloadToClientModel(msg))
            break
        case 'messageDelete':
            State.messageList.delete(data['message']['id'])
            break
        case 'messageUpdate':
            Controller.updateMessage(messagePayloadToClientModel(data['message']))
            break
        default:
            console.log(`[WS] Unknown event: ${data['event']}`)
            console.log(data)
            break
    }
}
function wsOnClose(ws) {}
function wsOnError(ws, error) {
    console.log('WebSocket error:', error)

    alert('WebSocket connection was closed')
    window.location.reload()
}

const websocket = new WSClient(wsOnOpen, wsOnMessage, wsOnClose, wsOnError)

