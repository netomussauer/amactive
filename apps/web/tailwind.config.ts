import type { Config } from 'tailwindcss'

// Design Tokens documentados em docs/frontend-architecture.md §7 — nunca usar
// valores hex diretamente em componentes, sempre via var(--color-*) abaixo.
const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: 'var(--color-primary)',
        'primary-hover': 'var(--color-primary-hover)',
        'primary-subtle': 'var(--color-primary-subtle)',
        danger: 'var(--color-danger)',
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        'bg-subtle': 'var(--color-bg-subtle)',
        'text-muted': 'var(--color-text-muted)',
        status: {
          ok: 'var(--color-status-ok)',
          baixo: 'var(--color-status-baixo)',
          critico: 'var(--color-status-critico)',
          pendente: 'var(--color-status-pendente)',
          confirmado: 'var(--color-status-confirmado)',
          cancelado: 'var(--color-status-cancelado)',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        body: ['var(--font-body)'],
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        full: 'var(--radius-full)',
      },
    },
  },
  plugins: [],
}
export default config
