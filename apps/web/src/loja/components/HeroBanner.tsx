import { ArrowRight, ArrowUpDown, Dumbbell, Heart, Leaf } from 'lucide-react'
import { HERO_MODELO } from '../config'

// Banner principal da vitrine: a foto da modelo INTEIRA (sem recorte), com
// logotipo, título, subtítulo, botão e benefícios sobrepostos por cima.
//
//   - Desktop: a foto fica alinhada à direita, com a altura do banner (corpo
//     inteiro visível). As laterais que sobram são preenchidas pela própria
//     foto, ampliada e desfocada ao fundo, e o texto fica sobre a área à
//     esquerda, com um degradê para legibilidade.
//   - Celular: a foto define a altura e o texto fica sobre a parte inferior,
//     com degradê vertical.
//
// Todo o texto é HTML real (acessível e editável), não parte da imagem.

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
      className="relative isolate overflow-hidden rounded-xl bg-blue-900 text-white md:h-[min(90vh,820px)]"
    >
      {/* Fundo (só desktop): a mesma foto, ampliada e desfocada, preenche as laterais. */}
      <img
        src={HERO_MODELO.srcFundo}
        alt=""
        aria-hidden="true"
        className="absolute inset-0 -z-10 hidden h-full w-full scale-110 object-cover opacity-50 blur-2xl md:block"
      />

      {/* Foto inteira. No celular define a altura do banner; no desktop fica à direita, na altura total. */}
      <img
        src={HERO_MODELO.src}
        srcSet={HERO_MODELO.srcSet}
        sizes="(min-width: 768px) 60vw, 100vw"
        width={HERO_MODELO.largura}
        height={HERO_MODELO.altura}
        alt="Modelo praticando corrida, vestindo a coleção AMACTIVE"
        fetchPriority="high"
        className="block h-auto w-full md:absolute md:right-0 md:top-0 md:h-full md:w-auto"
      />

      {/* Degradê de leitura: vertical no celular, da esquerda no desktop. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-gradient-to-t from-blue-900 via-blue-900/60 via-40% to-transparent md:bg-gradient-to-r md:from-blue-900 md:via-blue-900/75 md:via-45% md:to-transparent"
      />

      {/* Conteúdo sobreposto. */}
      <div className="absolute inset-0 flex flex-col justify-between gap-8 p-6 md:w-[55%] md:p-12">
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
