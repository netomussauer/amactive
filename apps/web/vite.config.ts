import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    // Em produção, o nginx repassa /api/ à API (mesma origem). Em dev, o mesmo
    // caminho relativo é encaminhado ao uvicorn local, sem CORS.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (caminho) => caminho.replace(/^\/api/, ''),
      },
    },
    // Polling em vez de eventos nativos do FS: necessário quando o dev
    // server roda dentro do WSL apontando para arquivos em /mnt/c/... (ou,
    // de forma equivalente, em qualquer bind mount tipo Docker/rede) —
    // mudanças feitas pelo lado Windows frequentemente não disparam
    // inotify no lado Linux, então o HMR fica "surdo" para elas mesmo com
    // o servidor rodando normalmente. Sem custo perceptível de CPU num
    // projeto deste tamanho.
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
  test: {
    environment: 'jsdom',
    globals: false,
    css: true,
    setupFiles: ['./src/shared/test-utils/setup.ts'],
  },
})
