// Configuração de build da vitrine (ver .env.loja).

/** Foto da modelo do banner principal (asset separado; o texto é renderizado no site). */
export const HERO_MODELO = {
  src: '/brand/hero-modelo.webp',
  largura: 855,
  altura: 1280,
} as const

/** WhatsApp que recebe os pedidos, só dígitos. Vazio = link de envio desabilitado. */
export const WHATSAPP_LOJA = (import.meta.env.VITE_WHATSAPP_LOJA ?? '').replace(/\D/g, '')
