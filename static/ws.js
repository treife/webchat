class WSClient {
    constructor(onOpen, onMessage, onClose, onError) {
        const proto = window.location.protocol === 'https' ? 'wss' : 'ws'
        this.socket = new WebSocket(proto + '://' + window.location.host + '/ws')

        this.socket.addEventListener('open', _ => onOpen(this))
        this.socket.addEventListener('message', ev => onMessage(this, JSON.parse(ev.data)))
        this.socket.addEventListener('close', _ => onClose(this))
        this.socket.addEventListener('error', ev => onError(this, ev))
    }

    close() {
        this.socket.close()
    }

    send(reqType, data={}, reqId=null) {
        data['type'] = reqType
        if (reqId)
            data['reqId'] = reqId
        this.socket.send(JSON.stringify(data))
    }

    getChannels() { this.send('getChannels') }
    createChannel(name) { this.send('createChannel', {name: name}) }
    updateChannel(id, name) { this.send('updateChannel', {id: id, name: name}) }
    deleteChannel(id) { this.send('deleteChannel', {id: id}) }

    getMe() { this.send('getMe') }

    getMessages(channelId, offset=0, limit=50) {
        this.send('getMessages', {
            channel_id: channelId,
            offset: offset,
            limit: limit
        })
    }

    createMessage(message, reqId=null) { this.send('createMessage', message, reqId) }

    deleteMessage(id) { this.send('deleteMessage', { id: id }) }
    updateMessage(message) { this.send('updateMessage', message) }
}