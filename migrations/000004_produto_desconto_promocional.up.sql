-- AMACTIVE — Desconto promocional por produto
-- Ver docs/data-model.md § Decisões de Modelagem para a justificativa de
-- usar um único campo NULL-ável (sem coluna boolean separada) para
-- representar "sem promoção ativa".
-- Convenção: forward-only, nunca editar após aplicado em ambiente compartilhado.

BEGIN;

-- ─────────────────────────────────────────────────────────────
-- Catálogo & Estoque
-- ─────────────────────────────────────────────────────────────
-- NULL = sem promoção ativa no momento (não usamos uma coluna boolean
-- separada tipo `em_promocao` — o próprio valor NULL já é inequívoco e
-- evita o estado inconsistente "em_promocao=true, desconto_percentual=NULL").
ALTER TABLE produto
    ADD COLUMN desconto_percentual decimal(5,2)
        CONSTRAINT chk_produto_desconto_percentual
        CHECK (desconto_percentual IS NULL OR (desconto_percentual > 0 AND desconto_percentual <= 100));

COMMIT;
