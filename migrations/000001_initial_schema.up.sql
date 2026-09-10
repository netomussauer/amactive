-- AMACTIVE — Schema inicial (MVP)
-- Ver docs/data-model.md para o diagrama ERD e justificativas de modelagem.
-- Convenção: forward-only, nunca editar após aplicado em ambiente compartilhado.

BEGIN;

-- Extensões
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- busca textual (nome de produto)

-- Enums
CREATE TYPE papel_usuario       AS ENUM ('ADMIN', 'VENDEDOR', 'ESTOQUISTA');
CREATE TYPE tipo_movimentacao   AS ENUM ('ENTRADA', 'SAIDA', 'AJUSTE');
CREATE TYPE status_pedido       AS ENUM ('PENDENTE', 'CONFIRMADO', 'CANCELADO');
CREATE TYPE forma_pagamento     AS ENUM ('DINHEIRO', 'PIX', 'CARTAO_DEBITO', 'CARTAO_CREDITO');

-- ─────────────────────────────────────────────────────────────
-- Identidade & Acesso
-- ─────────────────────────────────────────────────────────────
CREATE TABLE usuario (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            varchar(150) NOT NULL,
    email           varchar(255) NOT NULL UNIQUE,
    senha_hash      varchar(255) NOT NULL,
    papel           papel_usuario NOT NULL DEFAULT 'VENDEDOR',
    ativo           boolean NOT NULL DEFAULT true,
    criado_em       timestamptz NOT NULL DEFAULT now(),
    atualizado_em   timestamptz
);

-- ─────────────────────────────────────────────────────────────
-- Cadastros (Master Data)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE cliente (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                 varchar(150) NOT NULL,
    cpf_cnpj             varchar(20) UNIQUE,
    email                varchar(255),
    telefone             varchar(20),
    endereco_logradouro  varchar(255),
    endereco_cidade      varchar(100),
    endereco_uf          char(2),
    endereco_cep         varchar(10),
    ativo                boolean NOT NULL DEFAULT true,
    criado_em            timestamptz NOT NULL DEFAULT now(),
    atualizado_em        timestamptz
);

CREATE TABLE fornecedor (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    razao_social         varchar(150) NOT NULL,
    nome_fantasia        varchar(150),
    cnpj                 varchar(20) UNIQUE,
    email                varchar(255),
    telefone             varchar(20),
    endereco_logradouro  varchar(255),
    endereco_cidade      varchar(100),
    endereco_uf          char(2),
    endereco_cep         varchar(10),
    ativo                boolean NOT NULL DEFAULT true,
    criado_em            timestamptz NOT NULL DEFAULT now(),
    atualizado_em        timestamptz
);

-- ─────────────────────────────────────────────────────────────
-- Catálogo & Estoque
-- ─────────────────────────────────────────────────────────────
CREATE TABLE categoria (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        varchar(100) NOT NULL UNIQUE,
    slug        varchar(100) NOT NULL UNIQUE,
    ativo       boolean NOT NULL DEFAULT true,
    criado_em   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE produto (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    categoria_id   uuid REFERENCES categoria(id) ON DELETE SET NULL,
    nome           varchar(200) NOT NULL,
    descricao      text,
    marca          varchar(100) NOT NULL DEFAULT 'AMACTIVE',
    ativo          boolean NOT NULL DEFAULT true,
    criado_em      timestamptz NOT NULL DEFAULT now(),
    atualizado_em  timestamptz,
    deletado_em    timestamptz
);

CREATE INDEX idx_produto_nome_trgm ON produto USING gin (nome gin_trgm_ops);
CREATE INDEX idx_produto_categoria ON produto(categoria_id);

CREATE TABLE produto_variante (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    produto_id     uuid NOT NULL REFERENCES produto(id) ON DELETE RESTRICT,
    sku            varchar(50) NOT NULL UNIQUE,
    tamanho        varchar(10) NOT NULL,   -- PP|P|M|G|GG ou numérico (ex: "38")
    cor            varchar(50) NOT NULL,
    preco_venda    decimal(10,2) NOT NULL CHECK (preco_venda >= 0),
    preco_custo    decimal(10,2) CHECK (preco_custo >= 0),
    ativo          boolean NOT NULL DEFAULT true,
    criado_em      timestamptz NOT NULL DEFAULT now(),
    atualizado_em  timestamptz
);

CREATE INDEX idx_variante_produto ON produto_variante(produto_id);

CREATE TABLE estoque (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    variante_id    uuid NOT NULL UNIQUE REFERENCES produto_variante(id) ON DELETE CASCADE,
    quantidade     integer NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
    estoque_minimo integer NOT NULL DEFAULT 5 CHECK (estoque_minimo >= 0),
    atualizado_em  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_estoque_baixo ON estoque(variante_id) WHERE quantidade <= estoque_minimo;

CREATE TABLE movimentacao_estoque (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    variante_id    uuid NOT NULL REFERENCES produto_variante(id) ON DELETE RESTRICT,
    tipo           tipo_movimentacao NOT NULL,
    quantidade     integer NOT NULL CHECK (quantidade <> 0),
    motivo         varchar(50) NOT NULL,   -- COMPRA|VENDA|AJUSTE_INVENTARIO|DEVOLUCAO|PERDA
    pedido_id      uuid,                   -- FK adicionada após criação de "pedido" (ver abaixo)
    fornecedor_id  uuid REFERENCES fornecedor(id) ON DELETE SET NULL,
    usuario_id     uuid NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
    criado_em      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_movimentacao_variante ON movimentacao_estoque(variante_id, criado_em DESC);

-- ─────────────────────────────────────────────────────────────
-- Vendas
-- ─────────────────────────────────────────────────────────────
CREATE TABLE pedido (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    numero         varchar(20) NOT NULL UNIQUE,
    cliente_id     uuid REFERENCES cliente(id) ON DELETE SET NULL,
    usuario_id     uuid NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
    status         status_pedido NOT NULL DEFAULT 'PENDENTE',
    subtotal       decimal(10,2) NOT NULL CHECK (subtotal >= 0),
    desconto       decimal(10,2) NOT NULL DEFAULT 0 CHECK (desconto >= 0),
    valor_total    decimal(10,2) NOT NULL CHECK (valor_total >= 0),
    observacao     text,
    criado_em      timestamptz NOT NULL DEFAULT now(),
    confirmado_em  timestamptz,
    cancelado_em   timestamptz
);

CREATE INDEX idx_pedido_status_criado ON pedido(status, criado_em DESC);
CREATE INDEX idx_pedido_cliente ON pedido(cliente_id);

-- FK tardia de movimentacao_estoque.pedido_id (pedido é criado depois na ordem do arquivo)
ALTER TABLE movimentacao_estoque
    ADD CONSTRAINT fk_movimentacao_pedido
    FOREIGN KEY (pedido_id) REFERENCES pedido(id) ON DELETE SET NULL;

CREATE TABLE item_pedido (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id       uuid NOT NULL REFERENCES pedido(id) ON DELETE CASCADE,
    variante_id     uuid NOT NULL REFERENCES produto_variante(id) ON DELETE RESTRICT,
    quantidade      integer NOT NULL CHECK (quantidade > 0),
    preco_unitario  decimal(10,2) NOT NULL CHECK (preco_unitario >= 0),
    desconto_item   decimal(10,2) NOT NULL DEFAULT 0 CHECK (desconto_item >= 0),
    subtotal        decimal(10,2) NOT NULL CHECK (subtotal >= 0)
);

CREATE INDEX idx_item_pedido_pedido ON item_pedido(pedido_id);
CREATE INDEX idx_item_pedido_variante ON item_pedido(variante_id);

CREATE TABLE pagamento_pedido (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id         uuid NOT NULL REFERENCES pedido(id) ON DELETE CASCADE,
    forma_pagamento   forma_pagamento NOT NULL,
    valor             decimal(10,2) NOT NULL CHECK (valor > 0),
    criado_em         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_pagamento_pedido ON pagamento_pedido(pedido_id);

-- ─────────────────────────────────────────────────────────────
-- Views de leitura — Relatórios & Dashboard (CQRS-lite, ver docs/SDD.md §1.5)
-- ─────────────────────────────────────────────────────────────
CREATE VIEW vw_vendas_por_periodo AS
SELECT
    date_trunc('day', p.confirmado_em) AS dia,
    COUNT(DISTINCT p.id)               AS total_pedidos,
    SUM(p.valor_total)                 AS faturamento
FROM pedido p
WHERE p.status = 'CONFIRMADO'
GROUP BY date_trunc('day', p.confirmado_em);

CREATE VIEW vw_produtos_mais_vendidos AS
SELECT
    ip.variante_id,
    pv.sku,
    pr.nome AS produto_nome,
    SUM(ip.quantidade)              AS quantidade_vendida,
    SUM(ip.subtotal)                AS faturamento
FROM item_pedido ip
JOIN pedido p             ON p.id = ip.pedido_id AND p.status = 'CONFIRMADO'
JOIN produto_variante pv  ON pv.id = ip.variante_id
JOIN produto pr           ON pr.id = pv.produto_id
GROUP BY ip.variante_id, pv.sku, pr.nome;

CREATE VIEW vw_giro_estoque AS
SELECT
    me.variante_id,
    pv.sku,
    SUM(CASE WHEN me.tipo = 'SAIDA' THEN me.quantidade ELSE 0 END) AS total_saidas,
    e.quantidade AS saldo_atual
FROM movimentacao_estoque me
JOIN produto_variante pv ON pv.id = me.variante_id
JOIN estoque e           ON e.variante_id = me.variante_id
GROUP BY me.variante_id, pv.sku, e.quantidade;

COMMIT;
