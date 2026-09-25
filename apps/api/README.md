# AMACTIVE API

API de controle de estoque e vendas (FastAPI). Ver `docs/SDD.md` na raiz do repositório para o desenho arquitetural completo antes de alterar qualquer coisa aqui.

## Estrutura (Clean Architecture por Bounded Context)

```
src/amactive/
├── main.py                # Entry point FastAPI — registra routers, exception handlers RFC 7807, /health
├── core/                  # Cross-cutting: config (env vars), segurança (JWT/bcrypt)
├── shared_kernel/          # Base ORM, sessão de banco, exceções de domínio base, paginação, dinheiro, ENUMs PG
├── scripts/                # apply_migrations.py — aplicador simples de migrations SQL puro
└── contexts/
    ├── catalogo_estoque/   # Produtos, Variantes, Estoque, Movimentações
    ├── vendas/              # Pedidos, Itens, Pagamentos — orquestra a baixa de estoque
    ├── cadastros/           # Clientes, Fornecedores
    ├── identidade/          # Usuário + login JWT (mínimo — ver TODOs em core/security.py)
    └── relatorios/          # Queries de leitura (dashboard, relatórios) — CQRS-lite, sem tabelas próprias
```

Cada contexto segue `domain/ → application/ → infrastructure/` (dependências sempre apontam para dentro). Ver `docs/SDD.md` §1.4.

## Rodando localmente

Via Docker Compose (recomendado — sobe API + Postgres e aplica as migrations automaticamente no start da API):

```bash
cp apps/api/.env.example apps/api/.env
docker compose up --build
```

- API: http://localhost:8000 (docs interativas em `/docs`, métricas em `/metrics`, health check em `/health`)
- O container da API aplica `migrations/*.up.sql` pendentes antes de subir o uvicorn (`docker-entrypoint.sh` → `python -m amactive.scripts.apply_migrations`), incluindo o seed de desenvolvimento (`000002_seed_dev.up.sql`).
- **Login de desenvolvimento**: `admin@amactive.dev` / `amactive123` (criado pelo seed — nunca aplicar esse seed em produção).

Sem Docker (Postgres já rodando localmente):

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate   # Linux/WSL (ver nota sobre Windows abaixo)
pip install -c constraints.txt -e ".[dev]"
cp .env.example .env
python -m amactive.scripts.apply_migrations   # aplica migrations/*.up.sql (roda a partir da raiz do repo)
uvicorn amactive.main:app --reload
```

### Dependências travadas (`constraints.txt`)

O `pyproject.toml` só declara limites inferiores (`>=`); quem fixa a versão
exata de cada pacote (runtime, transitivos e ferramentas de dev) é o
[`constraints.txt`](constraints.txt), usado pelo `Dockerfile`, pela Task
`python-test` do Tekton e pelo comando acima — o mesmo conjunto no CI, na
imagem de produção e no seu ambiente. Foi gerado a partir do que rodava em
produção em 2026-09-25.

- **Adicionou/alterou uma dependência no `pyproject.toml`?** Rode
  `./regenerar-constraints.sh` (Linux/WSL) e commite o `constraints.txt`. Um
  teste (`tests/unit/test_constraints_cobre_pyproject.py`) falha se alguma
  dependência declarada não estiver travada.
- **Quer atualizar as versões de propósito?** O mesmo script, que sobe tudo para
  o mais novo permitido pelo `pyproject.toml`, roda a suíte completa e mostra o
  que mudou — revise o diff antes de commitar.
- **Windows nativo:** o arquivo inclui pacotes só de Linux (`uvloop`,
  `httptools`, `watchfiles` do `uvicorn[standard]`); use WSL ou Docker.

## Testes

```bash
# Testes unitários (rápidos, sem banco — mocks/fakes)
pytest tests/unit -m unit

# Testes de integração (exigem Postgres real acessível)
# Por padrão apontam para postgresql+asyncpg://amactive:amactive@localhost:5432/amactive_test
# — cria o banco de teste e aplica as migrations automaticamente na primeira execução.
docker compose up -d db
export TEST_DATABASE_URL=postgresql+asyncpg://amactive:amactive@localhost:5432/amactive_test
pytest tests/integration -m integration

# Tudo, com cobertura
pytest --cov=src --cov-report=term-missing
```

## Status

Implementação funcional do MVP (Catálogo & Estoque, Vendas, Cadastros, Relatórios, Identidade mínima). Ver o resumo entregue pelo `dev-expert-fullcycle` para o que está pendente (ex.: RBAC por papel, testes de carga).
