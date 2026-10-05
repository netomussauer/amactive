import { ArrowRight, ArrowUpDown, Dumbbell, Heart, Leaf } from 'lucide-react'
import { HERO_MODELO } from '../config'

// Banner principal da vitrine, montado a partir de elementos separados:
//   - foto da modelo (asset próprio, proporção original, sem recorte);
//   - logotipo (asset próprio, public/brand/amactive-logo-white.png);
//   - título, subtítulo, botão e benefícios: texto real do site (acessível e
//     editável), não imagem.
// Desktop: texto à esquerda e foto inteira à direita. Celular: foto em cima.

const BENEFICIOS = [
  { icone: Leaf, texto: 'Tecnologia e conforto' },
  { icone: ArrowUpDown, texto: 'Respirabilidade e leveza' },
  { icone: Dumbbell, texto: 'Performance que move' },
  { icone: Heart, texto: 'Feito para você' },
]

export function HeroBanner() {
  return (
    <section
      aria-labelledby="hero-titulo"
      className="grid overflow-hidden rounded-xl bg-blue-900 text-white md:grid-cols-2"
    >
      <div className="order-first md:order-none">
        <img
          src={HERO_MODELO.src}
          srcSet={HERO_MODELO.srcSet}
          sizes="(min-width: 768px) 50vw, 100vw"
          width={HERO_MODELO.largura}
          height={HERO_MODELO.altura}
          alt="Modelo praticando corrida, vestindo a coleção AMACTIVE"
          fetchPriority="high"
          className="h-auto w-full object-cover"
        />
      </div>

      <div className="flex flex-col justify-between gap-8 p-6 md:p-12">
        <img
          src="/brand/amactive-logo-white.png"
          alt="AMACTIVE"
          className="h-14 w-auto self-start md:h-16"
        />

        <div className="flex flex-col gap-4">
          <h1 id="hero-titulo" className="font-sans text-4xl font-bold leading-tight md:text-5xl">
            SEU RITMO.
            <span className="block text-blue-200">SEU ESTILO.</span>
          </h1>
          <p className="max-w-md text-base text-blue-100">
            Activewear para te acompanhar dentro e fora do treino.
          </p>
          <a
            href="#colecao"
            className="inline-flex w-fit items-center gap-2 rounded-md bg-blue-600 px-6 py-3 text-sm font-semibold uppercase tracking-wide text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-900"
          >
            Conheça a coleção
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </a>
        </div>

        <ul className="grid grid-cols-2 gap-4 text-xs text-blue-100">
          {BENEFICIOS.map(({ icone: Icone, texto }) => (
            <li key={texto} className="flex items-center gap-2">
              <Icone className="h-5 w-5 shrink-0 text-blue-200" aria-hidden="true" />
              <span>{texto}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
