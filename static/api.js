class API {
    static uploadFiles(messageId, files, cb) {
        let formData = new FormData()
        formData.append('message_id', messageId)
        for (const file of files)
            formData.append('files', file)
        fetch('/uploadFiles', {
            method: 'POST',
            body: formData
        }).then(resp => {
            if (resp.ok)
                return resp.json()
            throw new Error(`Upload error: ${resp.status}`)
        }).then(_ => {
            cb()
        }).catch((err) => {
            alert(err)
        })
    }
}