# Deploy — AMACTIVE

Manifestos e fluxo de deploy do AMACTIVE no cluster K3s `lab-k8s-01`, seguindo
exatamente o padrão já em produção pelo `amfit` e pelo `realtpmsys` no mesmo
cluster. Nada aqui foi aplicado no cluster real — ver "Passos manuais
pendentes" abaixo para a ordem exata do que falta.

## Topologia

| Componente | Endereço | Notas |
| --- | --- | --- |
| Imagem API | `harbor.lab.local/amactive/api:latest` | Build via Tekton + Harbor |
| Imagem Web | `harbor.lab.local/amactive/web:latest` | Build via Tekton + Harbor |
| Service API (MetalLB) | `192.168.1.212` | Confirmado e registrado no NetBox (2026-09-14) |
| Service Web (MetalLB) | `192.168.1.213` | Confirmado e registrado no NetBox (2026-09-14) |
| DNS | `api.amactive.local` / `app.amactive.local` | Adicionar no Pi-hole (passo 6) |
| Database | `postgresql.shared-infra.svc.cluster.local:5432/amactive` | **Ainda não provisionado** — ver passo 1 |
| Uploads (imagens de produto) | PVC `amactive-api-uploads` (local-path, 5Gi) | Substitui o volume Docker `amactive_uploads_data`; MinIO/S3 fica para uma etapa futura (decisão já confirmada, não migrar agora) |
| Node | worker com label `workload=cicd` | mesmo nodeSelector do amfit/realtpmsys |
| ArgoCD | `argocd.lab.local` | ns `cicd`, não `argocd` |

## Arquitetura dos manifestos

```text
infra/
├── k8s/                                 # ns amactive
│   ├── namespace.yaml
│   ├── rbac-tekton-rollout.yaml         # permite o pipeline reiniciar os Deployments
│   ├── sealedsecret.yaml.example        # TEMPLATE — pg-password + jwt-secret
│   ├── api/
│   │   ├── deployment.yaml              # 1 réplica, probes em /health, uid 1000
│   │   ├── service.yaml                 # LoadBalancer MetalLB 192.168.1.212
│   │   ├── pvc.yaml                     # amactive-api-uploads (5Gi, local-path)
│   │   └── migrations-configmap.yaml    # conteúdo de migrations/*.up.sql (ver nota abaixo)
│   └── web/
│       ├── deployment.yaml              # SPA Vite servida por nginx-unprivileged
│       └── service.yaml                 # LoadBalancer MetalLB 192.168.1.213
├── tekton/                              # ns cicd — pipelines de build
│   ├── serviceaccount.yaml              # tekton-amactive + RBAC namespaced + cluster
│   ├── task-kaniko.yaml                 # amactive-kaniko-build-push (suporta --build-arg)
│   ├── task-python-test.yaml            # ruff + mypy + pytest -m unit
│   ├── pipeline-api.yaml                # git-clone -> python-test -> kaniko -> rollout-restart
│   ├── pipeline-web.yaml                # git-clone -> kaniko (VITE_API_URL) -> rollout-restart
│   ├── triggers.yaml                    # TriggerBinding + Template (2 PipelineRuns) + Trigger + EventListener
│   ├── sealedsecret-webhook.yaml.example  # TEMPLATE — HMAC do webhook Gitea
│   ├── pipelinerun-api-manual.yaml.example
│   └── pipelinerun-web-manual.yaml.example
└── argocd/
    ├── application.yaml                 # infra/k8s -> ns amactive
    └── application-tekton.yaml          # infra/tekton -> ns cicd
```

**Nota sobre `migrations-configmap.yaml`**: o `Dockerfile` de `apps/api`
(build context = `apps/api/`) não inclui o diretório `migrations/` (vive na
raiz do monorepo). Em `docker-compose` isso é resolvido com um bind mount
(`./migrations:/app/migrations:ro`); em k8s não há bind mount de host
possível, então o mesmo efeito é obtido via ConfigMap montado read-only.
**Toda nova migration precisa ser copiada manualmente para esse ConfigMap**
— não há automação disso hoje. `000002_seed_dev.up.sql` foi
intencionalmente omitido (cria um usuário ADMIN com senha fraca conhecida,
o próprio arquivo diz "NUNCA aplicar em produção").

**Nota sobre a imagem web**: `apps/web/Dockerfile` e `apps/web/nginx.conf`
são novos (não existiam antes desta tarefa) — necessários porque não havia
Dockerfile para o frontend Vite. Usa `nginxinc/nginx-unprivileged` em vez do
padrão node-distroless do amfit-web/realtpmsys-web porque o app é uma SPA
pura (sem SSR) — ver justificativa completa no próprio Dockerfile.

## Passos manuais pendentes (ordem recomendada)

Nenhum destes passos foi executado — todos exigem acesso real ao cluster,
ao Harbor, ao Gitea ou ao NetBox, que esta tarefa não tem.

### 1. Provisionar o banco no Postgres compartilhado

O Postgres de `shared-infra` já hospeda `realtpmsys` e `amfit`, provisionados
via ConfigMap `postgresql-initdb` (repo `infra-lab`,
`kubernetes/shared-infra/postgresql/configmap.yaml`) + Secret
`postgresql-secret`. **Esta tarefa não editou o repo `infra-lab`** — os
comandos abaixo replicam manualmente o mesmo efeito para `amactive`, a
rodar via `kubectl exec` no pod `postgresql-0` (ou aplicando o equivalente
no `infra-lab`, preferível para manter o provisionamento declarativo e
sobreviver a um reboot do pod):

```bash
# Gerar uma senha forte para o usuário amactive
AMACTIVE_PASSWORD="$(openssl rand -base64 24)"
echo "$AMACTIVE_PASSWORD"   # guardar — vai para o SealedSecret no passo 2

kubectl exec -n shared-infra postgresql-0 -- psql -v ON_ERROR_STOP=1 \
  --username postgres --dbname postgres <<EOSQL
CREATE USER amactive WITH PASSWORD '${AMACTIVE_PASSWORD}';
CREATE DATABASE amactive OWNER amactive;
EOSQL

kubectl exec -n shared-infra postgresql-0 -- psql -v ON_ERROR_STOP=1 \
  --username postgres --dbname amactive <<EOSQL
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO amactive;
EOSQL
```

Se preferir manter o provisionamento declarativo (recomendado, mesmo padrão
de `amfit`/`realtpmsys`): adicionar o bloco `amactive` equivalente em
`infra-lab/kubernetes/shared-infra/postgresql/configmap.yaml` e a chave
`AMACTIVE_PASSWORD` no Secret `postgresql-secret`, fora do escopo desta
tarefa (repositório diferente).

### 2. Selar os Secrets (kubeseal)

Dois SealedSecrets ficam pendentes, cada um com instruções completas no
próprio arquivo `.example`:

- [`k8s/sealedsecret.yaml.example`](k8s/sealedsecret.yaml.example) —
  `pg-password` (senha gerada no passo 1) + `jwt-secret` (gerar com
  `openssl rand -base64 48`, nunca reaproveitar o default
  `change-me-in-env` de `apps/api/.env.example`).
- [`tekton/sealedsecret-webhook.yaml.example`](tekton/sealedsecret-webhook.yaml.example) —
  HMAC do webhook do Gitea.

Os arquivos finais devem ser `k8s/sealedsecret.yaml` e
`tekton/sealedsecret-webhook.yaml` — commitar **apenas** depois de selados
de verdade com `kubeseal` (chave pública do controller deste cluster).

### 3. Garantir `harbor-pull-secret` no namespace `amactive`

```bash
kubectl create namespace amactive --dry-run=client -o yaml | kubectl apply -f -
kubectl get secret harbor-creds -n cicd -o yaml \
  | sed 's/namespace: cicd/namespace: amactive/' \
  | sed 's/name: harbor-creds/name: harbor-pull-secret/' \
  | kubectl apply -f -
```

### 4. Criar as credenciais do Tekton no ns `cicd`

```bash
# Robot account do Harbor com push+pull em amactive/* (criar no Harbor antes)
kubectl create secret docker-registry harbor-push-amactive \
  --docker-server=harbor.lab.local \
  --docker-username='robot$amactive+tekton-pusher' \
  --docker-password='<HARBOR_ROBOT_TOKEN>' \
  -n cicd

# Secret HMAC do webhook — se optar por criar imperativamente em vez do
# SealedSecret do passo 2:
WEBHOOK_TOKEN="$(openssl rand -hex 32)"
kubectl create secret generic gitea-webhook-secret-amactive \
  --from-literal=secretToken="$WEBHOOK_TOKEN" \
  -n cicd
```

### 5. Confirmar/reservar os IPs no NetBox — feito (2026-09-14)

`192.168.1.212` (API) e `192.168.1.213` (Web) já estavam em uso real pelo
MetalLB (services aplicados e respondendo) sem conflito com nenhum IP
existente no NetBox (checado via API — nenhuma das duas faixas aparecia
registrada; amfit/realtpmsys nunca haviam sido registrados no NetBox
apesar de também estarem ativos, então a ausência de registro não indica
disponibilidade por si só, mas a checagem confirmou que ninguém mais
reivindica esses dois endereços). Registrados como
`ipam.ip-addresses` (`192.168.1.212/27` — "MetalLB — AMACTIVE API",
`192.168.1.213/27` — "MetalLB — AMACTIVE Web"), mesmo padrão de descrição
usado pelos demais IPs MetalLB do lab (Gitea `.200`, Harbor `.201`, ArgoCD
`.202`, Tekton EventListener `.203`, Grafana `.210`).

### 6. DNS no Pi-hole

Adicionar em `infra-lab/kubernetes/network-services/pihole/configmap-records.yaml`
(repo `infra-lab`, fora do escopo desta tarefa):

```text
# AMACTIVE
address=/api.amactive.local/192.168.1.212
address=/app.amactive.local/192.168.1.213
```

Aplicar e reiniciar o Pi-hole (`kubectl apply` + `kubectl rollout restart
deployment/pihole -n network-services`).

### 7. Build + push manual da primeira imagem (antes do Tekton rodar)

```bash
# API — contexto apps/api (ver infra/tekton/pipeline-api.yaml)
docker build -t harbor.lab.local/amactive/api:latest ./apps/api
docker login harbor.lab.local
docker push harbor.lab.local/amactive/api:latest

# Web — contexto apps/web, build-arg com a URL pública real da API
docker build -t harbor.lab.local/amactive/web:latest \
  --build-arg VITE_API_URL=http://api.amactive.local:8000 \
  ./apps/web
docker push harbor.lab.local/amactive/web:latest
```

### 8. Registrar as Applications no ArgoCD

```bash
kubectl apply -f infra/argocd/application.yaml
kubectl apply -f infra/argocd/application-tekton.yaml
```

### 9. Configurar o webhook no Gitea

Repositório `labadmin/amactive` → Settings → Webhooks → Add Webhook →
Gitea. Target URL = endpoint exposto do `el-amactive-event-listener`
(mesma ressalva do amfit: o Service é `ClusterIP` por padrão — usar
port-forward para teste rápido, ou IngressRoute Traefik dedicado para uso
contínuo). Secret = o mesmo `$WEBHOOK_TOKEN` do passo 4/2. Branch filter =
`main`.

### 10. Criar o primeiro usuário ADMIN

A migration `000002_seed_dev.up.sql` (usuário `admin@amactive.dev` /
`amactive123`) foi **propositalmente omitida** do `migrations-configmap.yaml`
(senha fraca conhecida, o próprio arquivo diz "NUNCA aplicar em produção" —
ver nota acima). Sem ela, o ambiente sobe **sem nenhum usuário** — e como
`POST /usuarios` exige ser ADMIN, não há como sair desse estado pela API
(problema de ovo-e-galinha). Um script novo resolve isso uma única vez, via
`kubectl exec` no pod já rodando (depois do passo 8, com o pod saudável):

```bash
POD=$(kubectl get pod -n amactive -l app.kubernetes.io/name=amactive-api -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n amactive "$POD" -- env \
  BOOTSTRAP_ADMIN_EMAIL='admin@amactive.dev' \
  BOOTSTRAP_ADMIN_SENHA="$(openssl rand -base64 18)" \
  BOOTSTRAP_ADMIN_NOME='Administrador AMACTIVE' \
  python -m amactive.scripts.bootstrap_admin
```

**Anote a senha gerada antes de rodar o comando** (o `openssl rand` acima
some do histórico depois) — é a única vez que ela aparece em texto puro, em
nenhum lugar fica salva. O script (`apps/api/src/amactive/scripts/bootstrap_admin.py`)
só insere um usuário se a tabela `usuario` estiver vazia — seguro deixar na
imagem permanentemente, rodar de novo depois que já existe gente cadastrada
é um no-op (`[skip] já existem N usuário(s)...`).

### 11. Validar

```bash
kubectl get pods -n amactive
kubectl get svc -n amactive
curl http://api.amactive.local:8000/health

# Confirma que o admin criado no passo 10 loga de verdade:
curl -X POST http://api.amactive.local:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@amactive.dev","senha":"<senha-anotada-no-passo-10>"}'

curl http://app.amactive.local/
```

## Dry-run — status

Este ambiente de preparação não teve `kubectl`, `kubeconform`/`kubeval`,
`kube-score` nem `helm` disponíveis para rodar o dry-run real. Todos os
manifestos foram revisados manualmente (estrutura YAML, indentação,
referências cruzadas entre `Secret`/`ConfigMap`/`PVC` e os `Deployment`s) e
o `ConfigMap` de migrations foi gerado programaticamente a partir dos
arquivos reais em `migrations/*.up.sql` (não digitado à mão) para evitar
erro de transcrição. **O dry-run de verdade
(`kubectl apply --dry-run=client -f infra/k8s/`,
`kubectl apply --dry-run=server`, `kubectl diff`) fica pendente** para
quando alguém com acesso ao cluster (ou ao menos ao schema do K8s local)
rodar antes do primeiro apply real — não pule esse passo.

## Variáveis de ambiente (Deployment da API)

| Var | Origem | Notas |
| --- | --- | --- |
| `DATABASE_URL` | composta a partir de `PG_PASSWORD` (Secret) | `postgresql+asyncpg://amactive:****@postgresql.shared-infra/amactive` |
| `JWT_SECRET` | `amactive-secrets.jwt-secret` | Gerar com `openssl rand -base64 48` |
| `JWT_ALGORITHM` / `JWT_EXPIRES_MINUTES` | literal | `HS256` / `480` (mesmo default do `.env.example`) |
| `ENVIRONMENT` | literal | `production` — `settings.py` rejeita o `JWT_SECRET` default fora de `development` |
| `UPLOADS_DIR` | literal | `/app/uploads` (PVC `amactive-api-uploads`) |
| `CORS_ORIGINS` | literal | domínio do web (`app.amactive.local`) + IP do LoadBalancer como fallback enquanto o DNS não existe |

## Troubleshooting

**Pod em `CrashLoopBackOff`** → `kubectl logs -n amactive deploy/amactive-api`.
Causas prováveis:

- `ValueError: JWT_SECRET precisa ser definido...` — `ENVIRONMENT=production`
  mas o `amactive-secrets` ainda não foi selado de verdade (passo 2), ou o
  SealedSecret não decriptou (controller Sealed Secrets fora do ar).
- Falha ao aplicar migrations — checar se `amactive-api-migrations`
  (ConfigMap) está montado em `/app/migrations` e se o banco `amactive`
  existe (passo 1).
- `PermissionError` gravando em `/app/uploads` — conferir `fsGroup: 1000`
  no `securityContext` do pod e o `storageClassName` do PVC.

**Service sem `EXTERNAL-IP`** → IP fora do pool MetalLB ou já em uso —
conferir `kubectl logs -n metallb-system speaker-*` e o passo 5 (NetBox).

**`npm ci` falhando com `EAI_AGAIN` no build do web** → problema de DNS já
documentado pelo realtpmsys neste cluster — usar o `dnsConfig` de
`tekton/pipelinerun-web-manual.yaml.example` ao disparar manualmente.

## Integração Nuvemshop — EM ESPERA (exposição pública e ativação)

**Status: em espera.** Criar o app privado na Nuvemshop exige o plano Escala
(R$ 382–449/mês), acima do orçamento atual (loja no plano Essencial; ver
[`docs/avaliacao-alternativas-canal-venda.md`](../docs/avaliacao-alternativas-canal-venda.md)).
O código da Fase 1 continua na imagem, mas o worker está com `replicas: 0` e
**o Ingress público foi removido** (sem o webhook da Nuvemshop ele não tem
função e só aumentaria a superfície de ataque). Enquanto isso, os pedidos da
Nuvemshop e do WhatsApp são lançados manualmente no AMACTIVE, por canal.

**Para reativar a exposição pública** (ADR-013 do `infra-lab`): Internet →
Cloudflare → `cloudflared` (ns `edge`, túnel outbound) → ingress-nginx
interno → Ingress `amactive-api-public`. O manifest foi removido no commit
que fecha a exposição; para recuperá-lo:
`git show 3f07544:infra/k8s/api/ingress-public.yaml > infra/k8s/api/ingress-public.yaml`.
Ele expõe só a rota exata
`POST https://amactive.amtech.app.br/integracoes/nuvemshop/webhooks`
(`pathType: Exact`; `/docs`, `/metrics`, `/auth/login` etc. respondem 404 nesse
hostname e seguem só na LAN). A barreira de aplicação é o HMAC-SHA256 do
corpo (`x-linkedstore-hmac-sha256`).

**Worker**: [`worker/deployment.yaml`](k8s/worker/deployment.yaml) — mesma
imagem da API, `python -m amactive.scripts.run_worker`. Está com
`replicas: 0` até a credencial existir (sem ela o processo sai com erro por
design). O pipeline `amactive-build-api` reinicia API **e** worker a cada
build.

**Ativar** (nesta ordem; nenhum segredo entra no Git nem no histórico do
shell — `read -s` não ecoa):

```bash
# 1. Usuário de sistema que assina pedidos importados (idempotente)
kubectl exec -n amactive deploy/amactive-api -- \
  python -m amactive.scripts.bootstrap_usuario_integracao

# 2. Credencial do app privado da Nuvemshop (cifrada no banco via pgcrypto).
#    A chave de cifragem já está no ambiente do pod (secret amactive-secrets).
read -rp  'STORE_ID: ' STORE_ID
read -rsp 'Access token: ' NS_TOKEN; echo
read -rsp 'Client secret: ' NS_SECRET; echo
kubectl exec -n amactive deploy/amactive-api -- env \
  STORE_ID="$STORE_ID" NUVEMSHOP_ACCESS_TOKEN="$NS_TOKEN" \
  NUVEMSHOP_CLIENT_SECRET="$NS_SECRET" \
  python -m amactive.scripts.configurar_credencial_nuvemshop
unset NS_TOKEN NS_SECRET

# 3. Ligar o worker: trocar `replicas: 0` por `replicas: 1` em
#    infra/k8s/worker/deployment.yaml e dar push (GitOps — `kubectl scale`
#    direto é revertido pelo selfHeal do ArgoCD).

# 4. Registrar o webhook na Nuvemshop (evento order/paid) apontando para a
#    URL pública acima — POST /webhooks da API da Nuvemshop, com o mesmo
#    access token (fora do escopo Python, design §9 item 9).
```

O endpoint cacheia a credencial por 30s: após rotacioná-la, a nova vale em
até esse tempo. Se o webhook responder 401 depois de configurado, confira
que `STORE_ID` é exatamente o `store_id` que a Nuvemshop envia no payload.

## Próximos passos (fora do escopo desta tarefa)

- Observabilidade da integração: as métricas do worker (fila de outbox,
  conflitos manuais) vivem no processo do worker, que ainda não expõe
  `/metrics`; e não há `ServiceMonitor` para o amactive (nem para a API).

- Path filtering no interceptor `cel` de `triggers.yaml`: hoje qualquer
  push em `main` dispara os dois pipelines (api + web), mesmo que só um
  tenha mudado — mesma limitação aceita pelo amfit/realtpmsys hoje.
- Lint/test no pipeline do web (`npm run lint` / `vitest`) — omitido por
  paridade com o `amfit-build-web`, que também não roda.
- Automatizar a sincronização de `migrations-configmap.yaml` com
  `migrations/*.up.sql` (hoje manual) — ou reconsiderar mudar o build
  context do `Dockerfile` da API para a raiz do monorepo, incluindo
  `migrations/` na imagem (como o `apps/web` do amfit faz, contexto "." +
  dockerfile em subdiretório) — decisão explicitamente adiada nesta tarefa
  para não alterar o `docker-compose.yml`/`Dockerfile` já validados
  localmente.
- Migrar armazenamento de imagens de produto para MinIO/S3 — decisão já
  tomada de NÃO fazer isso agora; o PVC local-path é a solução deste MVP.
# teste de webhook - 2026-09-14T18:40:42Z
# harbor project+robot configurados - 2026-09-14T18:54:43Z
