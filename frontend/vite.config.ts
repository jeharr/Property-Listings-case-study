import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const proxy = {
  '/api': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
}

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
  },
})
