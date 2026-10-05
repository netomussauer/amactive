-- AMACTIVE — Vitrine online: pedido sem operador + reserva de estoque com prazo
-- Ver docs/vitrine-online.md §Estoque.
--
-- 1. `pedido.usuario_id` deixa de ser obrigatório para pedidos da VITRINE
--    (cliente final não tem login). Os demais canais continuam exigindo operador.
-- 2. `pedido.reservado_ate`: prazo até o qual um pedido PENDENTE segura as
--    unidades que pediu. Após o prazo, a reserva deixa de contar para o saldo
--    disponível e o pedido é cancelado no próximo checkout (ver
--    ExpirarReservasVencidas no contexto Vendas).
-- 3. `reserva_estoque`: unidades reservadas por pedido. NUNCA altera
--    `estoque.quantidade` — a baixa real continua sendo só via
--    `movimentacao_estoque` (regra de ouro do docs/data-model.md), e acontece
--    apenas quando a equipe confirma o pagamento.
--
-- Convenção: forward-only, nunca editar após aplicado em ambiente compartilhado.

BEGIN;

ALTER TABLE pedido ALTER COLUMN usuario_id DROP NOT NULL;

ALTER TABLE pedido
    ADD CONSTRAINT chk_pedido_usuario_obrigatorio
    CHECK (usuario_id IS NOT NULL OR origem_canal = 'VITRINE');

ALTER TABLE pedido ADD COLUMN reservado_ate timestamptz;

-- Só pedido aguardando pagamento pode manter reserva ativa.
ALTER TABLE pedido
    ADD CONSTRAINT chk_pedido_reserva_so_pendente
    CHECK (reservado_ate IS NULL OR status = 'PENDENTE');

CREATE TABLE reserva_estoque (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id    uuid NOT NULL REFERENCES pedido(id) ON DELETE CASCADE,
    variante_id  uuid NOT NULL REFERENCES produto_variante(id) ON DELETE RESTRICT,
    quantidade   integer NOT NULL CHECK (quantidade > 0),
    criado_em    timestamptz NOT NULL DEFAULT now(),
    -- Uma linha por (pedido, variante): o checkout agrupa itens repetidos antes.
    CONSTRAINT uq_reserva_pedido_variante UNIQUE (pedido_id, variante_id)
);

-- Consulta quente: soma das reservas ativas por variante (checkout e catálogo).
CREATE INDEX idx_reserva_estoque_variante ON reserva_estoque (variante_id);

COMMIT;
