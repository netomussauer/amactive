-- AMACTIVE — Integração de Canais: Nuvemshop (Fase 1)
-- Ver docs/design-integracao-nuvemshop.md §6 para o modelo lógico completo
-- (este arquivo é a tradução física, sem nenhuma decisão de design nova) e
-- docs/data-model.md para as convenções gerais de modelagem já fixadas.
-- Convenção: forward-only, nunca editar após aplicado em ambiente compartilhado.
--
-- ATENÇÃO — pré-condição manual antes de aplicar em qualquer ambiente com
-- dados reais (dev compartilhado, staging, produção): a constraint
-- `uq_cliente_email_nao_nulo` (seção "Cadastros" abaixo) exige que não haja
-- e-mails duplicados hoje em `cliente`. Rode ANTES de aplicar esta migration:
--
--   SELECT email, count(*)
--   FROM cliente
--   WHERE email IS NOT NULL
--   GROUP BY email
--   HAVING count(*) > 1;
--
-- Se a consulta retornar alguma linha, resolva a duplicidade (limpeza de
-- dados) antes de prosseguir — a migration falhará com violação de
-- constraint única caso contrário. Esta migration foi validada apenas
-- contra um banco de teste vazio (schema das migrations 000001-000004
-- aplicado, sem dados de `cliente`); não foi possível rodar esta checagem
-- contra a base real de dev/staging/produção do projeto a partir deste
-- ambiente de execução — o `data-expert` não teve acesso a essas bases.

BEGIN;

-- ─────────────────────────────────────────────────────────────
-- Enums novos
-- ─────────────────────────────────────────────────────────────
CREATE TYPE canal_integracao         AS ENUM ('NUVEMSHOP');
CREATE TYPE status_webhook_evento    AS ENUM ('PENDENTE', 'PROCESSADO', 'ERRO', 'CONFLITO_MANUAL');
CREATE TYPE status_outbox            AS ENUM ('PENDENTE', 'ENVIADO', 'ERRO');
CREATE TYPE operacao_catalogo_outbox AS ENUM ('CRIAR', 'ATUALIZAR');

-- Vocabulário de `vendas` (não de `integracao_canais`, ver docs/design-
-- integracao-nuvemshop.md §2.3 — cada contexto nomeia/versiona seu próprio
-- enum mesmo compartilhando o valor literal "NUVEMSHOP" com canal_integracao).
CREATE TYPE origem_canal_pedido      AS ENUM ('PDV', 'NUVEMSHOP');

-- Vocabulário de `cadastros`, mesma nuance acima.
CREATE TYPE origem_cadastro_cliente  AS ENUM ('MANUAL', 'NUVEMSHOP');

-- Alteração aditiva a um enum já existente (docs/design-integracao-
-- nuvemshop.md §3.1, §6.1): um pedido Nuvemshop chega já pago via checkout
-- do canal, sem forma de pagamento física do MVP — não destrutiva.
-- `ALTER TYPE ... ADD VALUE` é seguro dentro do mesmo bloco de transação
-- desta migration (suportado desde o Postgres 12; validado empiricamente
-- contra Postgres 16.15 nesta auditoria) DESDE QUE o novo valor não seja
-- referenciado (INSERT/UPDATE/comparação) na mesma transação em que foi
-- adicionado — não é o caso aqui: nenhuma linha desta migration usa
-- 'NUVEMSHOP' como forma_pagamento, o valor só passa a ser usado pela
-- aplicação em transações futuras. Por isso não precisa de um statement
-- isolado fora desta transação.
ALTER TYPE forma_pagamento ADD VALUE 'NUVEMSHOP';

-- ─────────────────────────────────────────────────────────────
-- Integração de Canais — bounded context `integracao_canais`
-- Ver docs/design-integracao-nuvemshop.md §2.4/§6.2-§6.6 para a motivação
-- de cada tabela.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE webhook_evento (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    canal                canal_integracao NOT NULL,
    -- Construído pela aplicação como "{canal}:{tipo_evento}:{id_recurso_externo}"
    -- (ver §2.4) — não é o "id" cru do payload sozinho, para que eventos
    -- diferentes sobre o mesmo recurso não colidam na UNIQUE abaixo.
    evento_externo_id    varchar(255) NOT NULL UNIQUE,
    tipo_evento          varchar(50) NOT NULL,
    id_recurso_externo   varchar(100) NOT NULL,
    payload_bruto        jsonb NOT NULL,
    status               status_webhook_evento NOT NULL DEFAULT 'PENDENTE',
    tentativas           integer NOT NULL DEFAULT 0,
    erro_detalhe         text,
    recebido_em          timestamptz NOT NULL DEFAULT now(),
    processado_em        timestamptz
);

-- Leitura do worker: próximo lote pendente/em retry, mais antigo primeiro.
CREATE INDEX idx_webhook_evento_fila ON webhook_evento(status, recebido_em)
    WHERE status IN ('PENDENTE', 'ERRO');

-- Fila de conflito manual (§5.4) — parcial, mantém o índice minúsculo.
CREATE INDEX idx_webhook_evento_conflito ON webhook_evento(status)
    WHERE status = 'CONFLITO_MANUAL';

CREATE TABLE mapeamento_variante_canal (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- ON DELETE RESTRICT: histórico de integração nunca pode ficar órfão,
    -- mesmo motivo de item_pedido.variante_id (docs/data-model.md) —
    -- descontinuar uma variante usa ativo=false, não exclusão física.
    variante_id           uuid NOT NULL REFERENCES produto_variante(id) ON DELETE RESTRICT,
    canal                 canal_integracao NOT NULL,
    produto_externo_id    varchar(100) NOT NULL,
    variante_externo_id   varchar(100) NOT NULL,
    criado_em             timestamptz NOT NULL DEFAULT now(),
    atualizado_em         timestamptz,
    -- Uma variante AMACTIVE tem no máximo um mapeamento por canal.
    CONSTRAINT uq_mapeamento_variante_canal UNIQUE (variante_id, canal),
    -- Um variant_id da Nuvemshop nunca mapeia para duas variantes AMACTIVE
    -- diferentes — impede corrupção de estoque cruzado por bug de mapeamento.
    CONSTRAINT uq_mapeamento_canal_variante_externo UNIQUE (canal, variante_externo_id)
);

-- Consultas por produto (útil já na Fase 2, ao tratar product/updated).
CREATE INDEX idx_mapeamento_produto_externo ON mapeamento_variante_canal(produto_externo_id);

CREATE TRIGGER trg_mapeamento_variante_canal_atualizado
    BEFORE UPDATE ON mapeamento_variante_canal
    FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

CREATE TABLE integracao_estoque_outbox (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- ON DELETE CASCADE (não RESTRICT): se a variante for fisicamente
    -- removida (caso raro sem histórico, mesmo padrão de estoque.variante_id
    -- em docs/data-model.md decisão #2), a fila de publicação associada
    -- perde o sentido.
    variante_id            uuid NOT NULL REFERENCES produto_variante(id) ON DELETE CASCADE,
    -- Snapshot do saldo absoluto no momento do enfileiramento — nunca um
    -- delta (§4.1/§4.3 do design).
    quantidade_publicada   integer NOT NULL,
    status                 status_outbox NOT NULL DEFAULT 'PENDENTE',
    tentativas             integer NOT NULL DEFAULT 0,
    proxima_tentativa_em   timestamptz,
    erro_detalhe           text,
    criado_em              timestamptz NOT NULL DEFAULT now(),
    processado_em          timestamptz
);

-- Leitura do worker: próximo lote pendente/em retry já elegível.
CREATE INDEX idx_estoque_outbox_fila ON integracao_estoque_outbox(status, proxima_tentativa_em)
    WHERE status IN ('PENDENTE', 'ERRO');

-- Suporta a query de coalescing DISTINCT ON (variante_id) ... ORDER BY
-- variante_id, criado_em DESC (§4.2 do design).
CREATE INDEX idx_estoque_outbox_coalescing ON integracao_estoque_outbox(variante_id, criado_em DESC);

CREATE TABLE integracao_catalogo_outbox (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- ON DELETE CASCADE: mesmo raciocínio de integracao_estoque_outbox acima.
    produto_id             uuid NOT NULL REFERENCES produto(id) ON DELETE CASCADE,
    operacao               operacao_catalogo_outbox NOT NULL,
    status                 status_outbox NOT NULL DEFAULT 'PENDENTE',
    tentativas             integer NOT NULL DEFAULT 0,
    proxima_tentativa_em   timestamptz,
    erro_detalhe           text,
    criado_em              timestamptz NOT NULL DEFAULT now(),
    processado_em          timestamptz
);

CREATE INDEX idx_catalogo_outbox_fila ON integracao_catalogo_outbox(status, proxima_tentativa_em)
    WHERE status IN ('PENDENTE', 'ERRO');

CREATE INDEX idx_catalogo_outbox_coalescing ON integracao_catalogo_outbox(produto_id, criado_em DESC);

CREATE TABLE credencial_canal (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Uma única loja por canal na Fase 1 (§6.6 do design).
    canal                    canal_integracao NOT NULL UNIQUE,
    store_id                 varchar(50) NOT NULL,
    -- Nome deliberado (não "access_token"/"client_secret" sozinhos): deixa
    -- explícito no próprio schema que o valor nunca é texto puro — ver
    -- docs/design-integracao-nuvemshop.md §6.6. Cifrado via pgp_sym_encrypt
    -- (extensão pgcrypto, já habilitada em migrations/000001), chave vinda
    -- de variável de ambiente da aplicação, nunca armazenada no banco.
    access_token_cifrado     bytea NOT NULL,
    client_secret_cifrado    bytea NOT NULL,
    criado_em                timestamptz NOT NULL DEFAULT now(),
    atualizado_em            timestamptz
);

CREATE TRIGGER trg_credencial_canal_atualizada
    BEFORE UPDATE ON credencial_canal
    FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- ─────────────────────────────────────────────────────────────
-- Outbox transacional — trigger de banco, não evento de domínio in-process
-- Ver docs/design-integracao-nuvemshop.md §4.1 para a justificativa
-- arquitetural completa (garantia transacional real: a escrita do outbox
-- acontece na mesma transação da mudança de estado que ela representa,
-- porque é disparada pelo mesmo UPDATE/INSERT que já existe hoje).
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_enfileirar_outbox_estoque() RETURNS trigger AS $$
BEGIN
    INSERT INTO integracao_estoque_outbox (variante_id, quantidade_publicada)
    VALUES (NEW.variante_id, NEW.quantidade);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Dispara na mesma transação do UPDATE feito por
-- fn_aplicar_movimentacao_estoque (migrations/000001) — nunca é a aplicação
-- Python quem publica este evento.
CREATE TRIGGER trg_estoque_enfileira_outbox
    AFTER UPDATE ON estoque
    FOR EACH ROW
    WHEN (OLD.quantidade IS DISTINCT FROM NEW.quantidade)
    EXECUTE FUNCTION fn_enfileirar_outbox_estoque();

CREATE OR REPLACE FUNCTION fn_enfileirar_outbox_catalogo() RETURNS trigger AS $$
BEGIN
    INSERT INTO integracao_catalogo_outbox (produto_id, operacao)
    VALUES (
        NEW.id,
        (CASE WHEN TG_OP = 'INSERT' THEN 'CRIAR' ELSE 'ATUALIZAR' END)::operacao_catalogo_outbox
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_produto_enfileira_outbox
    AFTER INSERT OR UPDATE ON produto
    FOR EACH ROW EXECUTE FUNCTION fn_enfileirar_outbox_catalogo();

-- Granularidade do outbox é o produto, não a variante (§2.4 do design: a
-- Nuvemshop modela variante como sub-recurso do produto) — este trigger
-- enfileira o produto_id PAI sempre que uma variante é criada/alterada.
-- produto_variante sempre é criada depois de produto já existir (endpoint
-- POST /produtos/{id}/variantes), então a operação enfileirada é sempre
-- ATUALIZAR (o CRIAR já foi enfileirado pela criação do produto em si).
CREATE OR REPLACE FUNCTION fn_enfileirar_outbox_catalogo_variante() RETURNS trigger AS $$
BEGIN
    INSERT INTO integracao_catalogo_outbox (produto_id, operacao)
    VALUES (NEW.produto_id, 'ATUALIZAR');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_variante_enfileira_outbox
    AFTER INSERT OR UPDATE ON produto_variante
    FOR EACH ROW EXECUTE FUNCTION fn_enfileirar_outbox_catalogo_variante();

-- Mesmo raciocínio acima para a galeria de imagens (produto_imagem, já
-- existente desde migrations/000003) — inclui DELETE (remoção de uma foto
-- também precisa republicar o produto), usando OLD.produto_id nesse caso
-- porque NEW não existe em um DELETE.
CREATE OR REPLACE FUNCTION fn_enfileirar_outbox_catalogo_imagem() RETURNS trigger AS $$
BEGIN
    INSERT INTO integracao_catalogo_outbox (produto_id, operacao)
    VALUES (COALESCE(NEW.produto_id, OLD.produto_id), 'ATUALIZAR');
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_imagem_enfileira_outbox
    AFTER INSERT OR UPDATE OR DELETE ON produto_imagem
    FOR EACH ROW EXECUTE FUNCTION fn_enfileirar_outbox_catalogo_imagem();

-- ─────────────────────────────────────────────────────────────
-- Vendas — mudanças aditivas em `pedido` (docs/design-integracao-
-- nuvemshop.md §3.1/§6.7)
-- ─────────────────────────────────────────────────────────────
ALTER TABLE pedido
    ADD COLUMN origem_canal      origem_canal_pedido NOT NULL DEFAULT 'PDV',
    ADD COLUMN pedido_externo_id varchar(100);

-- Defesa em profundidade contra duplicidade de pedido externo (§3.1): não é
-- UNIQUE de tabela simples porque precisa do filtro parcial (múltiplos
-- pedidos PDV com pedido_externo_id NULL não podem colidir entre si).
CREATE UNIQUE INDEX uq_pedido_origem_canal_externo
    ON pedido (origem_canal, pedido_externo_id)
    WHERE pedido_externo_id IS NOT NULL;

-- Pequeno e parcial (exclui o caso dominante PDV) — relatórios por canal,
-- extensão natural e barata de Relatórios, fora do escopo desta fase.
CREATE INDEX idx_pedido_origem_canal ON pedido (origem_canal)
    WHERE origem_canal <> 'PDV';

-- ─────────────────────────────────────────────────────────────
-- Cadastros — mudanças aditivas em `cliente` (docs/design-integracao-
-- nuvemshop.md §3.3/§6.7)
-- ─────────────────────────────────────────────────────────────
ALTER TABLE cliente
    ADD COLUMN cliente_externo_id varchar(100),
    ADD COLUMN origem_cadastro    origem_cadastro_cliente NOT NULL DEFAULT 'MANUAL';

CREATE UNIQUE INDEX uq_cliente_origem_cadastro_externo
    ON cliente (origem_cadastro, cliente_externo_id)
    WHERE cliente_externo_id IS NOT NULL;

-- Necessária para o upsert_por_email (§3.3) ser atômico via
-- INSERT ... ON CONFLICT (email) DO UPDATE — ON CONFLICT exige uma
-- constraint/índice único na coluna de conflito. VER O AVISO NO TOPO DESTE
-- ARQUIVO: requer ausência de e-mails duplicados na base antes de aplicar.
CREATE UNIQUE INDEX uq_cliente_email_nao_nulo
    ON cliente (email)
    WHERE email IS NOT NULL;

COMMIT;
