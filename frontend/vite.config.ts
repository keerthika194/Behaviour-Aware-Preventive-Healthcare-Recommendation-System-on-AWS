import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    global: 'window', // Polyfill global for amazon-cognito-identity-js in browser environments
  },
  server: {
    port: 3000,
    host: true,
  },
})
