import { HERO_HOME } from '../config'

// Banner principal da vitrine (arte oficial da coleção, tratada — ver
// apps/web/public/brand/hero-home-*.webp). O botão "CONHEÇA A COLEÇÃO" já vem
// impresso na própria arte, então o banner inteiro leva à coleção (âncora).
export function HeroBanner() {
  return (
    <a
      href="#colecao"
      className="block overflow-hidden rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      aria-label="Ir para a coleção"
    >
      <img
        src={HERO_HOME.src}
        srcSet={HERO_HOME.srcSet}
        sizes="(min-width: 1280px) 1152px, 100vw"
        width={HERO_HOME.largura}
        height={HERO_HOME.altura}
        alt="SEU RITMO. SEU ESTILO. Activewear para te acompanhar dentro e fora do treino."
        fetchPriority="high"
        className="h-auto w-full"
      />
    </a>
  )
}
