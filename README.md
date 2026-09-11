# AMACTIVE — Sistema de Controle de Estoque e Vendas

Sistema interno de gestão para a **AMACTIVE**, marca de roupas esportivas femininas (moda fitness). Controla catálogo/estoque, vendas (PDV/pedidos), clientes, fornecedores e relatórios/dashboard. Uso interno — sem emissão fiscal (NF-e/NFC-e) e sem gateway de pagamento real nesta fase (ver `docs/SDD.md` para os pontos de extensão futuros).

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + FastAPI (Clean Architecture por Bounded Context) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS (SPA) |
| Banco de dados | PostgreSQL 16 |
| Data fetching (web) | TanStack Query + Zod |
| Migrations | SQL puro versionado (`migrations/NNNNNN_nome.up.sql` / `.down.sql`) |
| Ambiente local | Docker Compose (API + Postgres) |

## Documentação

Antes de implementar qualquer coisa, leia:

- [`docs/SDD.md`](./docs/SDD.md) — System Design Document: bounded contexts, decisões arquiteturais (ADRs), stack, resiliência, plano de evolução.
- [`docs/data-model.md`](./docs/data-model.md) — modelagem de dados (ERD completo, decisões de schema, índices).
- [`docs/openapi.yaml`](./docs/openapi.yaml) — contrato OpenAPI 3.0 de todos os endpoints do MVP.
- [`docs/frontend-architecture.md`](./docs/frontend-architecture.md) — arquitetura de frontend (feature-based), sitemap, user flows, design tokens.

## Estrutura do Repositório

```
amactive/
├── apps/
│   ├── api/          # Backend FastAPI (Clean Architecture por contexto)
│   └── web/           # Frontend React + TS + Vite (feature-based)
├── docs/               # SDD, data-model, openapi.yaml, frontend-architecture
├── migrations/         # Migrations SQL versionadas (up/down)
└── docker-compose.yml
```

## Rodando localmente

### Pré-requisitos
- Docker + Docker Compose v2 (`docker compose`, plugin — não o `docker-compose` v1 legado)
- Node.js 20+ (para o frontend, que roda fora de container nesta fase)
- Python 3.12+ apenas se for rodar a API fora de container (não é necessário para o fluxo abaixo)

### Passo 1 — Backend (API + Postgres) via Docker Compose

```bash
# 1. Crie o .env da API a partir do exemplo (obrigatório — o compose falha
#    sem esse arquivo, pois o serviço `api` usa `env_file: ./apps/api/.env`).
#    Os valores padrão do .env.example já funcionam para uso local sem
#    edição nenhuma.
cp apps/api/.env.example apps/api/.env

# 2. (Opcional) valide o compose antes de subir — bom hábito antes de
#    qualquer `up`/`build`, principalmente após editar docker-compose.yml.
docker compose config --quiet

# 3. Build + subida dos serviços `db` (Postgres 16) e `api` (FastAPI)
docker compose up --build
```

- API: http://localhost:8000 (docs interativas em `/docs`, métricas em `/metrics`, health check em `/health`)
- Postgres: `localhost:5432` (usuário/senha/banco padrão: `amactive` — sobrescrevível via um `.env` na raiz do repo com `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`, lido automaticamente pelo `docker compose`)

O container da API aplica automaticamente as migrations pendentes (`migrations/*.up.sql`, incluindo o seed de desenvolvimento) antes de subir — ver `apps/api/src/amactive/scripts/apply_migrations.py` e `apps/api/docker-entrypoint.sh`. Login de desenvolvimento (seed): `admin@amactive.dev` / `amactive123`.

Aguarde os dois serviços ficarem `healthy` (`docker compose ps`) antes de usar a API — `api` só sobe de fato depois que `db` responde ao seu healthcheck, e o próprio `api` também expõe um healthcheck em `/health`. Para derrubar a stack: `docker compose down` (adicione `-v` **apenas** se quiser apagar também os dados do Postgres — isso destrói o volume `amactive_db_data`).

Teste rápido da API sem o frontend:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@amactive.dev", "senha": "amactive123"}'
```

(Confirme o nome exato dos campos do payload em `docs/openapi.yaml` caso a chamada acima retorne 422 — o exemplo usa `email`/`senha`.)

### Passo 2 — Frontend (fora do Docker, nesta fase do MVP)

O frontend não está containerizado de propósito nesta fase do MVP (feedback rápido com Vite + HMR); ver `docs/SDD.md` para o ADR correspondente.

```bash
cd apps/web
cp .env.example .env
npm install
npm run dev
```

- Web: http://localhost:5173 (`VITE_API_URL` em `apps/web/.env` aponta para `http://localhost:8000`, a API rodando via Docker Compose acima)

A API libera CORS para `http://localhost:5173` por padrão (`CORS_ORIGINS` em `apps/api/.env` — ver `apps/api/.env.example`), então o login pela UI funciona sem configuração extra. Se o frontend rodar em outra porta/host, ajuste `CORS_ORIGINS` de acordo.

### Passo 3 — Login e primeiro fluxo de teste

1. Acesse http://localhost:5173 e faça login com `admin@amactive.dev` / `amactive123` (usuário seed criado pela migration `migrations/000002_seed_dev.up.sql`).
2. Ponto de partida sugerido para explorar o sistema: **PDV** (`/vendas/pdv`), onde é possível buscar um produto/variante já semeado, montar um carrinho e finalizar um pedido — isso exercita catálogo, baixa de estoque atômica e o fluxo de vendas de ponta a ponta.
3. Outras áreas: `Produtos` (catálogo/estoque), `Pedidos` (histórico de vendas), `Relatórios`/`Dashboard`.

## Status do Projeto

Backend (`apps/api`) implementado: Catálogo & Estoque, Vendas (incluindo a baixa de estoque atômica via trigger de banco), Cadastros e Relatórios estão funcionais end-to-end contra `docs/openapi.yaml`. Identidade & Acesso é um login JWT mínimo (ver TODOs em `apps/api/src/amactive/core/security.py`). Ver `apps/api/README.md` para como rodar e testar.

Próximos passos:
1. `dev-expert-front` — implementar as telas do MVP em `apps/web/src/features/*` seguindo `docs/frontend-architecture.md`, consumindo a API já implementada.
2. RBAC por papel (ADMIN/VENDEDOR/ESTOQUISTA) no backend, hoje apenas autenticação (qualquer usuário logado acessa qualquer endpoint protegido).
