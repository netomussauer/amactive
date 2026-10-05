-- AMACTIVE — Novo canal de origem de pedido: VITRINE (loja online)
-- Contexto: a vitrine pública registra pedidos feitos pelo cliente final, que
-- são fechados depois pela equipe via WhatsApp. Ver docs/vitrine-online.md.
-- Convenção: forward-only, nunca editar após aplicado em ambiente compartilhado.
--
-- Mesmo precedente de migrations/000006: `ALTER TYPE ... ADD VALUE` dentro de
-- transação é aceito (Postgres >= 12) desde que o valor novo NÃO seja
-- referenciado na mesma transação. Por isso o uso de 'VITRINE' (CHECK em
-- migrations/000008) fica em arquivo separado, aplicado em transação própria.

BEGIN;

ALTER TYPE origem_canal_pedido ADD VALUE IF NOT EXISTS 'VITRINE';

COMMIT;
