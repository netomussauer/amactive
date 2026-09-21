-- AMACTIVE — Rollback do canal de origem WhatsApp (000006)
--
-- O Postgres não suporta `ALTER TYPE ... DROP VALUE`. Estratégia deste
-- rollback (diferente do no-op documentado em 000005.down, onde remover o
-- valor exigiria recriar um tipo usado por várias tabelas): aqui o tipo
-- `origem_canal_pedido` só é usado por UMA coluna (`pedido.origem_canal`),
-- então é viável recriá-lo sem o valor 'WHATSAPP':
--
--   1. ABORTA com erro claro se existir algum pedido com origem 'WHATSAPP'
--      (remover o valor destruiria/invalidaria esses pedidos — nunca
--      convertemos nem apagamos dados de venda silenciosamente; o operador
--      decide o que fazer com eles antes de repetir o rollback);
--   2. renomeia o tipo antigo, cria o tipo novo com ('PDV', 'NUVEMSHOP'),
--      converte a coluna via texto e descarta o tipo antigo;
--   3. recria os dois índices parciais que dependem da coluna (índices
--      precisam ser removidos antes de trocar o tipo da coluna, pois o
--      predicado `origem_canal <> 'PDV'` referencia o tipo).
--
-- Custo: `ALTER COLUMN ... TYPE` reescreve a tabela `pedido` sob lock
-- ACCESS EXCLUSIVE — aceitável para rollback manual em desenvolvimento/lab;
-- em produção com tabela grande, planeje janela de manutenção.
--
-- ATENÇÃO — reinicie a API (e qualquer worker) logo após aplicar este rollback:
-- o tipo é recriado com outro OID, e conexões já abertas (pool do asyncpg) têm
-- prepared statements em cache que referenciam o tipo antigo e falham com
-- "cache lookup failed for type" até a conexão ser refeita. Validado
-- empiricamente em tests/integration/test_migration_origem_canal_whatsapp.py.
--
-- Idempotente: reexecutar sem o valor 'WHATSAPP' presente apenas recria o
-- tipo/índices com o mesmo resultado final.

BEGIN;

DO $$
DECLARE
    total_whatsapp bigint;
BEGIN
    -- Comparação via texto (e não pelo literal do enum) para que a checagem
    -- também funcione se o valor 'WHATSAPP' já não existir no tipo.
    SELECT count(*) INTO total_whatsapp FROM pedido WHERE origem_canal::text = 'WHATSAPP';
    IF total_whatsapp > 0 THEN
        RAISE EXCEPTION
            'Rollback 000006 abortado: existem % pedido(s) com origem_canal = WHATSAPP. '
            'Remova ou reclassifique esses pedidos antes de reverter esta migration.',
            total_whatsapp;
    END IF;
END
$$;

DROP INDEX IF EXISTS idx_pedido_origem_canal;
DROP INDEX IF EXISTS uq_pedido_origem_canal_externo;

ALTER TYPE origem_canal_pedido RENAME TO origem_canal_pedido_antigo;
CREATE TYPE origem_canal_pedido AS ENUM ('PDV', 'NUVEMSHOP');

ALTER TABLE pedido ALTER COLUMN origem_canal DROP DEFAULT;
ALTER TABLE pedido
    ALTER COLUMN origem_canal TYPE origem_canal_pedido
    USING origem_canal::text::origem_canal_pedido;
ALTER TABLE pedido ALTER COLUMN origem_canal SET DEFAULT 'PDV';

DROP TYPE origem_canal_pedido_antigo;

-- Mesmas definições de migrations/000005_integracao_nuvemshop.up.sql.
CREATE UNIQUE INDEX uq_pedido_origem_canal_externo
    ON pedido (origem_canal, pedido_externo_id)
    WHERE pedido_externo_id IS NOT NULL;

CREATE INDEX idx_pedido_origem_canal ON pedido (origem_canal)
    WHERE origem_canal <> 'PDV';

COMMIT;
