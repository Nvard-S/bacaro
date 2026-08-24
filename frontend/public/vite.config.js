import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Dev-only: forward /api to the local backend so the browser only talks to
  // the Vite origin. In production VITE_API_BASE_URL points at the backend.
  server: {
    proxy: { '/api': 'http://localhost:5099' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './vitest.setup.js',
  },
})
