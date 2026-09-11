-- AMACTIVE — Rollback do desconto promocional por produto

BEGIN;

ALTER TABLE produto
    DROP CONSTRAINT IF EXISTS chk_produto_desconto_percentual;

ALTER TABLE produto
    DROP COLUMN IF EXISTS desconto_percentual;

COMMIT;
