-- AMACTIVE — Rollback da vitrine: reserva de estoque e pedido sem operador (000008)
--
-- ABORTA se existir pedido da vitrine ainda sem operador (usuario_id NULL):
-- após reverter, esses pedidos ficariam inválidos. O operador decide antes
-- (cancelar/reclassificar) e repete o rollback.

BEGIN;

DO $$
DECLARE
    total_sem_usuario bigint;
BEGIN
    SELECT count(*) INTO total_sem_usuario FROM pedido WHERE usuario_id IS NULL;
    IF total_sem_usuario > 0 THEN
        RAISE EXCEPTION
            'Rollback 000008 abortado: existem % pedido(s) sem usuario_id (vitrine). '
            'Cancele ou reclassifique esses pedidos antes de reverter esta migration.',
            total_sem_usuario;
    END IF;
END
$$;

DROP INDEX IF EXISTS idx_reserva_estoque_variante;
DROP TABLE IF EXISTS reserva_estoque;

ALTER TABLE pedido DROP CONSTRAINT IF EXISTS chk_pedido_reserva_so_pendente;
ALTER TABLE pedido DROP COLUMN IF EXISTS reservado_ate;

ALTER TABLE pedido DROP CONSTRAINT IF EXISTS chk_pedido_usuario_obrigatorio;
ALTER TABLE pedido ALTER COLUMN usuario_id SET NOT NULL;

COMMIT;
