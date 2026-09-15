-- AMACTIVE — Rollback da integração de canais (Nuvemshop, Fase 1)
--
-- LIMITAÇÃO CONHECIDA E ACEITA: o Postgres não suporta `ALTER TYPE ... DROP
-- VALUE` — o valor 'NUVEMSHOP' adicionado a `forma_pagamento` pelo
-- `.up.sql` permanece no tipo mesmo após este rollback (removê-lo exigiria
-- recriar o tipo inteiro e todas as colunas/tabelas que o usam, uma
-- operação destrutiva desproporcional para um rollback de desenvolvimento).
-- Isso é consistente com a própria natureza "aditiva, não destrutiva" dessa
-- alteração documentada em docs/design-integracao-nuvemshop.md §6.1.

BEGIN;

-- ─────────────────────────────────────────────────────────────
-- Cadastros — reverte mudanças em `cliente`
-- ─────────────────────────────────────────────────────────────
DROP INDEX IF EXISTS uq_cliente_email_nao_nulo;
DROP INDEX IF EXISTS uq_cliente_origem_cadastro_externo;

ALTER TABLE cliente DROP COLUMN IF EXISTS origem_cadastro;
ALTER TABLE cliente DROP COLUMN IF EXISTS cliente_externo_id;

-- ─────────────────────────────────────────────────────────────
-- Vendas — reverte mudanças em `pedido`
-- ─────────────────────────────────────────────────────────────
DROP INDEX IF EXISTS idx_pedido_origem_canal;
DROP INDEX IF EXISTS uq_pedido_origem_canal_externo;

ALTER TABLE pedido DROP COLUMN IF EXISTS pedido_externo_id;
ALTER TABLE pedido DROP COLUMN IF EXISTS origem_canal;

-- ─────────────────────────────────────────────────────────────
-- Triggers/funções de outbox (as triggers em si já seriam removidas em
-- cascata com as tabelas de origem abaixo caso as tabelas fossem droppadas
-- primeiro, mas aqui a origem — estoque/produto/produto_variante/
-- produto_imagem — não é droppada nesta migration, então elas precisam ser
-- removidas explicitamente antes das funções que referenciam)
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_imagem_enfileira_outbox ON produto_imagem;
DROP TRIGGER IF EXISTS trg_variante_enfileira_outbox ON produto_variante;
DROP TRIGGER IF EXISTS trg_produto_enfileira_outbox ON produto;
DROP TRIGGER IF EXISTS trg_estoque_enfileira_outbox ON estoque;

DROP FUNCTION IF EXISTS fn_enfileirar_outbox_catalogo_imagem();
DROP FUNCTION IF EXISTS fn_enfileirar_outbox_catalogo_variante();
DROP FUNCTION IF EXISTS fn_enfileirar_outbox_catalogo();
DROP FUNCTION IF EXISTS fn_enfileirar_outbox_estoque();

-- ─────────────────────────────────────────────────────────────
-- Integração de Canais — tabelas (as triggers próprias dessas tabelas,
-- trg_mapeamento_variante_canal_atualizado e trg_credencial_canal_atualizada,
-- são removidas em cascata junto com as tabelas)
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS credencial_canal;
DROP TABLE IF EXISTS integracao_catalogo_outbox;
DROP TABLE IF EXISTS integracao_estoque_outbox;
DROP TABLE IF EXISTS mapeamento_variante_canal;
DROP TABLE IF EXISTS webhook_evento;

-- ─────────────────────────────────────────────────────────────
-- Enums (forma_pagamento NÃO é removido — ver aviso no topo deste arquivo)
-- ─────────────────────────────────────────────────────────────
DROP TYPE IF EXISTS origem_cadastro_cliente;
DROP TYPE IF EXISTS origem_canal_pedido;
DROP TYPE IF EXISTS operacao_catalogo_outbox;
DROP TYPE IF EXISTS status_outbox;
DROP TYPE IF EXISTS status_webhook_evento;
DROP TYPE IF EXISTS canal_integracao;

COMMIT;
