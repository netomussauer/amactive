// Validação client-side do upload de imagem de produto — espelha as regras
// de docs/openapi.yaml (POST /produtos/{produtoId}/imagens): jpeg/png/webp,
// até 5MB. Roda antes de chamar a API para dar feedback imediato; o backend
// segue sendo a fonte de verdade (mensagem de erro do 422/413 é sempre
// exibida também, ver ImagemGaleriaCor.tsx).
export const TIPOS_IMAGEM_ACEITOS = ['image/jpeg', 'image/png', 'image/webp'] as const
export type TipoImagemAceito = (typeof TIPOS_IMAGEM_ACEITOS)[number]

export const TAMANHO_MAXIMO_IMAGEM_BYTES = 5 * 1024 * 1024 // 5MB

// Retorna a mensagem de erro amigável, ou null se o arquivo é válido.
export function validarArquivoImagem(arquivo: File): string | null {
  if (!TIPOS_IMAGEM_ACEITOS.includes(arquivo.type as TipoImagemAceito)) {
    return 'Formato inválido. Envie um arquivo JPEG, PNG ou WEBP.'
  }
  if (arquivo.size > TAMANHO_MAXIMO_IMAGEM_BYTES) {
    return 'Arquivo maior que 5MB. Escolha uma imagem menor.'
  }
  return null
}
