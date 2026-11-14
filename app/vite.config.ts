import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// During development (npm run dev), API calls go to the Python server on port 8000.
export default defineConfig({
  plugins: [react()],
  // The map outlines are bundled in, so the single chunk is large (~1.4 MB); fine for a local tool.
  build: { chunkSizeWarningLimit: 2000 },
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
