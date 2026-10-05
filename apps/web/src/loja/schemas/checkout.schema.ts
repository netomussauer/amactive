import { z } from 'zod'

// Dados que o cliente final informa. Sem CPF nem e-mail: a identificação é
// só nome e telefone (ver docs/vitrine-online.md).

export const TELEFONE_MIN_DIGITOS = 10
export const TELEFONE_MAX_DIGITOS = 13

export const CheckoutFormSchema = z.object({
  nome: z
    .string()
    .trim()
    .min(2, 'Informe seu nome')
    .max(150, 'Use no máximo 150 caracteres'),
  telefone: z.string().refine((valor) => {
    const digitos = valor.replace(/\D/g, '')
    return digitos.length >= TELEFONE_MIN_DIGITOS && digitos.length <= TELEFONE_MAX_DIGITOS
  }, 'Informe um telefone com DDD, ex.: (11) 99999-9999'),
  observacao: z.string().max(500, 'Use no máximo 500 caracteres').optional(),
})

export type CheckoutFormValues = z.infer<typeof CheckoutFormSchema>
