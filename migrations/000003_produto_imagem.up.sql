-- AMACTIVE — Imagens de produto (galeria por cor)
-- Ver docs/data-model.md § Decisões de Modelagem para a justificativa de
-- vincular a imagem à COR (não à variante tamanho+cor): uma foto de produto
-- não muda por tamanho, apenas por cor.
-- Convenção: forward-only, nunca editar após aplicado em ambiente compartilhado.

BEGIN;

-- ─────────────────────────────────────────────────────────────
-- Catálogo & Estoque
-- ─────────────────────────────────────────────────────────────
CREATE TABLE produto_imagem (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    produto_id   uuid NOT NULL REFERENCES produto(id) ON DELETE CASCADE,
    -- Mesma convenção de produto_variante.cor: texto livre, sem tabela/enum
    -- de cores separada. A validação de que a cor informada aqui de fato
    -- existe entre as variantes do produto é responsabilidade da camada de
    -- aplicação (não é uma FK possível, pois `cor` não é chave em
    -- produto_variante).
    cor          varchar(50) NOT NULL,
    -- Caminho relativo do arquivo em disco (volume Docker local nesta fase,
    -- não S3), ex: /media/produtos/{produto_id}/{uuid}.jpg
    url          varchar(500) NOT NULL,
    ordem        smallint NOT NULL DEFAULT 0 CHECK (ordem >= 0),
    principal    boolean NOT NULL DEFAULT false,
    criado_em    timestamptz NOT NULL DEFAULT now()
);

-- Galeria de uma cor de um produto (padrão de acesso dominante: listar todas
-- as imagens de produto_id+cor, ordenadas por `ordem` na aplicação).
CREATE INDEX idx_produto_imagem_produto_cor ON produto_imagem(produto_id, cor);

-- No máximo uma imagem principal (capa) por produto+cor. Índice único
-- parcial em vez de trigger: a constraint é puramente estática (não depende
-- de agregação nem de lógica condicional além do próprio filtro), então o
-- Postgres já garante a exclusão mútua na própria instrução INSERT/UPDATE.
CREATE UNIQUE INDEX uq_produto_imagem_principal_por_cor
    ON produto_imagem(produto_id, cor)
    WHERE principal = true;

COMMIT;
