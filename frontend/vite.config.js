import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            // Dev-only proxy so the browser talks to FastAPI same-origin.
            '/api': { target: 'https://document-ocr-53qt.onrender.com', changeOrigin: true },
        },
    },
})
