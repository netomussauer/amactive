import { useEffect, useState } from 'react'

// Debounce de 300ms recomendado em docs/frontend-architecture.md §6 para
// campos de busca (produtos, clientes, fornecedores, estoque por SKU).
export function useDebounce<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timeout = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timeout)
  }, [value, delayMs])

  return debounced
}
