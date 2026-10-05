-- AMACTIVE — Rollback do canal de origem VITRINE (000007)
--
-- Mesma estratégia do rollback de 000006: o tipo `origem_canal_pedido` só é
-- usado pela coluna `pedido.origem_canal`, então é viável recriá-lo sem o
-- valor 'VITRINE'. ABORTA se existir pedido de vitrine — nunca apagamos nem
-- reclassificamos dados de venda silenciosamente.
--
-- ATENÇÃO — o rollback de 000008 precisa ser aplicado ANTES deste (o CHECK
-- que referencia 'VITRINE' e a reserva de estoque dependem do valor).
-- Reinicie a API/worker logo após aplicar (mesmo motivo de 000006.down).

BEGIN;

DO $$
DECLARE
    total_vitrine bigint;
BEGIN
    SELECT count(*) INTO total_vitrine FROM pedido WHERE origem_canal::text = 'VITRINE';
    IF total_vitrine > 0 THEN
        RAISE EXCEPTION
            'Rollback 000007 abortado: existem % pedido(s) com origem_canal = VITRINE. '
            'Cancele ou reclassifique esses pedidos antes de reverter esta migration.',
            total_vitrine;
    END IF;
END
$$;

DROP INDEX IF EXISTS idx_pedido_origem_canal;
DROP INDEX IF EXISTS uq_pedido_origem_canal_externo;

ALTER TYPE origem_canal_pedido RENAME TO origem_canal_pedido_antigo;
CREATE TYPE origem_canal_pedido AS ENUM ('PDV', 'NUVEMSHOP', 'WHATSAPP');

ALTER TABLE pedido ALTER COLUMN origem_canal DROP DEFAULT;
ALTER TABLE pedido
    ALTER COLUMN origem_canal TYPE origem_canal_pedido
    USING origem_canal::text::origem_canal_pedido;
ALTER TABLE pedido ALTER COLUMN origem_canal SET DEFAULT 'PDV';

DROP TYPE origem_canal_pedido_antigo;

CREATE UNIQUE INDEX uq_pedido_origem_canal_externo
    ON pedido (origem_canal, pedido_externo_id)
    WHERE pedido_externo_id IS NOT NULL;

CREATE INDEX idx_pedido_origem_canal ON pedido (origem_canal)
    WHERE origem_canal <> 'PDV';

COMMIT;
