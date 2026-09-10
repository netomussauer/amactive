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
- Docker + Docker Compose
- Node.js 20+ e Python 3.12+ (apenas se for rodar fora de container)

### Via Docker Compose (recomendado)

```bash
cp apps/api/.env.example apps/api/.env
docker compose up --build
```

- API: http://localhost:8000 (docs interativas em `/docs`, métricas em `/metrics`, health check em `/health`)
- Postgres: `localhost:5432` (usuário/senha/banco: `amactive`)

Aplique as migrations iniciais (schema em `migrations/000001_initial_schema.up.sql`) com a ferramenta de migração definida pelo `data-expert` (ex: `golang-migrate` apontando para `DATABASE_URL`).

### Frontend (fora do Docker, nesta fase do MVP)

```bash
cd apps/web
cp .env.example .env
npm install
npm run dev
```

- Web: http://localhost:5173

## Status do Projeto

Fase atual: **arquitetura e scaffold**. Estrutura de pastas, contratos (`openapi.yaml`) e modelo de dados estão definidos; regras de negócio e telas ainda **não** foram implementadas.

Próximos passos:
1. `data-expert` — validar/ajustar o schema físico definitivo a partir de `docs/data-model.md` e das migrations iniciais em `migrations/`.
2. `dev-expert-fullcycle` — implementar os casos de uso e endpoints de cada bounded context (`apps/api/src/amactive/contexts/*`) seguindo `docs/openapi.yaml`.
3. `dev-expert-front` — implementar as telas do MVP em `apps/web/src/features/*` seguindo `docs/frontend-architecture.md`.
