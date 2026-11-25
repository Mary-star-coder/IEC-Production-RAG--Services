
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Configure Vite for the React frontend application.
export default defineConfig({
  plugins: [react()],

  // Forward frontend API requests to the FastAPI backend.
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
