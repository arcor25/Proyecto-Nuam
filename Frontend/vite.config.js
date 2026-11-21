import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Las llamadas a /api/... se reenvían al backend Django (evita problemas de CORS en desarrollo)
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
