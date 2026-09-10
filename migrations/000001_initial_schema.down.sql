-- AMACTIVE — Rollback do schema inicial (MVP)

BEGIN;

DROP VIEW IF EXISTS vw_giro_estoque;
DROP VIEW IF EXISTS vw_produtos_mais_vendidos;
DROP VIEW IF EXISTS vw_vendas_por_periodo;

DROP TABLE IF EXISTS pagamento_pedido;
DROP TABLE IF EXISTS item_pedido;

ALTER TABLE IF EXISTS movimentacao_estoque DROP CONSTRAINT IF EXISTS fk_movimentacao_pedido;

DROP TABLE IF EXISTS pedido;
DROP SEQUENCE IF EXISTS pedido_numero_seq;

DROP TABLE IF EXISTS movimentacao_estoque;
DROP TABLE IF EXISTS estoque;
DROP TABLE IF EXISTS produto_variante;
DROP TABLE IF EXISTS produto;
DROP TABLE IF EXISTS categoria;
DROP TABLE IF EXISTS fornecedor;
DROP TABLE IF EXISTS cliente;
DROP TABLE IF EXISTS usuario;

-- Funções de trigger (as triggers em si já foram removidas em cascata com
-- as tabelas acima; as funções são objetos independentes)
DROP FUNCTION IF EXISTS fn_aplicar_movimentacao_estoque();
DROP FUNCTION IF EXISTS fn_criar_estoque_inicial();
DROP FUNCTION IF EXISTS fn_atualizar_timestamp();

DROP TYPE IF EXISTS motivo_movimentacao;
DROP TYPE IF EXISTS forma_pagamento;
DROP TYPE IF EXISTS status_pedido;
DROP TYPE IF EXISTS tipo_movimentacao;
DROP TYPE IF EXISTS papel_usuario;

COMMIT;
