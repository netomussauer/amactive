import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles/tokens.css'

// Duas aplicações, um mesmo código-fonte. `VITE_APP=loja` (build da vitrine,
// `npm run build:loja`) seleciona a loja online; no build padrão, o sistema
// administrativo. O import dinâmico com condição constante faz o bundler
// descartar a aplicação não usada — a vitrine público nunca contém as telas
// administrativas. Ver docs/vitrine-online.md.
const aplicacao =
  import.meta.env.VITE_APP === 'loja' ? import('./loja/LojaApp') : import('./App')

aplicacao.then(({ default: App }) => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
})
