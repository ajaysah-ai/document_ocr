import axios from 'axios'

const client = axios.create({ baseURL: '/api', timeout: 180000 })

export async function getHealth() {
    const { data } = await client.get('/health')
    return data
}

export async function uploadDocument(file) {
    const formData = new FormData()
    formData.append('file', file)
        // Intentionally NO Content-Type header: the browser must set
        // multipart/form-data including the boundary parameter.
    const { data } = await client.post('/ocr', formData)
    return data
}