# AMACTIVE API

API de controle de estoque e vendas (FastAPI). Ver `docs/SDD.md` na raiz do repositório para o desenho arquitetural completo antes de implementar qualquer coisa aqui.

## Estrutura (Clean Architecture por Bounded Context)

```
src/amactive/
├── main.py                # Entry point FastAPI — registra routers de cada contexto
├── core/                  # Cross-cutting: config, segurança, exceções
├── shared_kernel/          # Base ORM, sessão de banco, value objects compartilhados
└── contexts/
    ├── catalogo_estoque/   # Produtos, Variantes, Estoque, Movimentações
    ├── vendas/              # Pedidos, Itens, Pagamentos
    ├── cadastros/           # Clientes, Fornecedores
    ├── identidade/          # Usuários, Autenticação (JWT)
    └── relatorios/          # Queries de leitura (dashboard, relatórios)
```

Cada contexto segue `domain/ → application/ → infrastructure/` (dependências sempre apontam para dentro). Ver `docs/SDD.md` §1.4.

## Rodando localmente

Via Docker Compose (recomendado — ver `docker-compose.yml` na raiz):

```bash
docker compose up --build
```

Sem Docker (desenvolvimento local com Postgres já rodando):

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate   # ou .venv\Scripts\activate no Windows
pip install -e ".[dev]"
cp .env.example .env
uvicorn amactive.main:app --reload
```

API disponível em `http://localhost:8000`. Documentação interativa em `http://localhost:8000/docs`.

## Status

Scaffold de arquitetura — sem regras de negócio implementadas ainda. Próximo passo: `dev-expert-fullcycle` implementa os casos de uso de cada contexto seguindo `docs/openapi.yaml` como contrato.
