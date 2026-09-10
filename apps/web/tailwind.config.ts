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
        bg: 'var(--color-bg)',
        'bg-subtle': 'var(--color-bg-subtle)',
        text: 'var(--color-text)',
        'text-muted': 'var(--color-text-muted)',
        border: 'var(--color-border)',
        // Primitivos expostos para casos que precisam de um degrade dentro da
        // própria paleta da marca (ex: hover states, ícones secundários) —
        // sempre via token, nunca hex literal nas classes.
        coral: {
          50: 'var(--color-coral-50)',
          400: 'var(--color-coral-400)',
          500: 'var(--color-coral-500)',
          600: 'var(--color-coral-600)',
          700: 'var(--color-coral-700)',
        },
        graphite: {
          50: 'var(--color-graphite-50)',
          200: 'var(--color-graphite-200)',
          500: 'var(--color-graphite-500)',
          800: 'var(--color-graphite-800)',
          900: 'var(--color-graphite-900)',
        },
        status: {
          ok: 'var(--color-status-ok)',
          baixo: 'var(--color-status-baixo)',
          critico: 'var(--color-status-critico)',
          pendente: 'var(--color-status-pendente)',
          confirmado: 'var(--color-status-confirmado)',
          cancelado: 'var(--color-status-cancelado)',
        },
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
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
