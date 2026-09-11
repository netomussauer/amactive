import { toDecimalString } from '@/shared/lib/format'

// Calcula o `desconto_item` a ser enviado em POST /pedidos (ver
// docs/openapi.yaml ItemPedidoRequest.desconto_item) para uma variante com
// desconto promocional ativo. O `preco_promocional` já vem pronto da API
// (calculado pelo backend) — aqui só multiplicamos a diferença unitária pela
// quantidade, nunca recalculamos o percentual em si.
export function calcularDescontoItem(
  precoUnitario: string,
  precoPromocional: string | null | undefined,
  quantidade: number,
): string {
  if (!precoPromocional) return '0.00'

  const diferencaUnitaria = Number(precoUnitario) - Number(precoPromocional)
  if (!(diferencaUnitaria > 0)) return '0.00'

  return toDecimalString(diferencaUnitaria * quantidade)
}
