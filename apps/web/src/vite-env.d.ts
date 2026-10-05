/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  /** `loja` no build da vitrine (ver .env.loja); ausente no sistema administrativo. */
  readonly VITE_APP?: string
  /** Número do WhatsApp da loja, só dígitos com DDI. */
  readonly VITE_WHATSAPP_LOJA?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
