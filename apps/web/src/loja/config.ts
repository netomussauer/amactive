// Configuração de build da vitrine (ver .env.loja).

/** WhatsApp que recebe os pedidos, só dígitos. Vazio = link de envio desabilitado. */
export const WHATSAPP_LOJA = (import.meta.env.VITE_WHATSAPP_LOJA ?? '').replace(/\D/g, '')
