-- AMACTIVE — Novo canal de origem de pedido: WhatsApp
-- Contexto: a marca vende majoritariamente por WhatsApp e, enquanto a
-- integração automática com a Nuvemshop está em espera (plano sem acesso à
-- API), os pedidos de cada canal são registrados MANUALMENTE no AMACTIVE
-- (POST /pedidos com `origem_canal`), para que listagens/relatórios separem
-- os canais e o estoque baixe normalmente.
-- Convenção: forward-only, nunca editar após aplicado em ambiente compartilhado.
--
-- Mesmo precedente e mesma ressalva de migrations/000005: `ALTER TYPE ... ADD
-- VALUE` é aceito dentro de um bloco de transação (Postgres >= 12) DESDE QUE o
-- valor novo não seja referenciado (INSERT/UPDATE/comparação) na mesma
-- transação em que foi adicionado. Não é o caso aqui: nenhuma linha desta
-- migration usa 'WHATSAPP' — o valor só passa a ser usado pela aplicação em
-- transações futuras. Por isso não precisa de statement isolado fora do
-- BEGIN/COMMIT.
--
-- Nenhum índice precisa ser alterado: `uq_pedido_origem_canal_externo`
-- (origem_canal, pedido_externo_id) já se aplica a qualquer origem — o número
-- do pedido é único POR canal, então o mesmo número em canais diferentes é
-- permitido — e `idx_pedido_origem_canal` (parcial, `WHERE origem_canal <>
-- 'PDV'`) já cobre o novo valor.

BEGIN;

ALTER TYPE origem_canal_pedido ADD VALUE IF NOT EXISTS 'WHATSAPP';

COMMIT;
