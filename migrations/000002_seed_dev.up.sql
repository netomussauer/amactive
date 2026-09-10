-- AMACTIVE — Seed de desenvolvimento (NUNCA aplicar em produção)
-- Cria um usuário ADMIN para permitir o primeiro login local via
-- POST /auth/login (ver apps/api/README.md — credenciais de desenvolvimento).
-- Convenção: seeds ficam em migrations separadas do DDL do schema
-- (ver docs/data-model.md § Estratégia de Migração).

BEGIN;

INSERT INTO usuario (id, nome, email, senha_hash, papel, ativo)
VALUES (
    gen_random_uuid(),
    'Administrador AMACTIVE',
    'admin@amactive.dev',
    -- pgcrypto gera um hash bcrypt ($2a$) compatível com o `bcrypt` do Python
    -- (verificado via bcrypt.checkpw em amactive.core.security).
    crypt('amactive123', gen_salt('bf')),
    'ADMIN',
    true
)
ON CONFLICT (email) DO NOTHING;

COMMIT;
