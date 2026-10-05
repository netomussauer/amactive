// Configuração de build da vitrine (ver .env.loja).

/** Banner principal da vitrine (arte tratada, 1536 e 1920 px de largura). */
export const HERO_HOME = {
  src: '/brand/hero-home-1536.webp',
  srcSet: '/brand/hero-home-1536.webp 1536w, /brand/hero-home-1920.webp 1920w',
  largura: 1536,
  altura: 1024,
} as const

/** WhatsApp que recebe os pedidos, só dígitos. Vazio = link de envio desabilitado. */
export const WHATSAPP_LOJA = (import.meta.env.VITE_WHATSAPP_LOJA ?? '').replace(/\D/g, '')
