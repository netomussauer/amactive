import { z } from 'zod'

// Espelha components.schemas.Pagination do docs/openapi.yaml
export const PaginationSchema = z.object({
  total: z.number(),
  page: z.number(),
  per_page: z.number(),
})
export type Pagination = z.infer<typeof PaginationSchema>

export function paginatedResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    data: z.array(itemSchema),
    pagination: PaginationSchema,
  })
}

export function listResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    data: z.array(itemSchema),
  })
}

export type ListFilter = {
  page?: number
  per_page?: number
}
