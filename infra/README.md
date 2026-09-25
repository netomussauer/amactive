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

## Acesso público ao sistema (web + API) com Cloudflare Access

**Arquitetura:** Internet → Cloudflare (TLS/WAF + **Access**) → `cloudflared`
(ns `edge`) → ingress-nginx interno → Ingress
[`web/ingress-public.yaml`](k8s/web/ingress-public.yaml) → Service `amactive-web`
→ nginx do web, que serve a SPA em `/` e repassa `/api/` para a API dentro do
cluster ([`apps/web/nginx.conf`](../apps/web/nginx.conf)). **Um único
hostname** — `amactive.amtech.app.br` — de propósito: o Access protege por
hostname e o navegador precisa do cookie dele em toda chamada; com a API em
outro hostname cada chamada XHR seria bloqueada. Mesma origem também elimina
CORS. O bundle chama a API em `/api` (`VITE_API_URL=/api`), então o mesmo
build funciona pela LAN (`http://192.168.1.213`) e pelo endereço público.

**Exceção consciente ao ADR-013 do `infra-lab`** ("nunca a aplicação inteira
nem painéis administrativos"): aqui o sistema inteiro fica alcançável pela
internet, por decisão do dono do projeto (acesso remoto da equipe). A
mitigação é a identidade do Cloudflare Access na frente. Sugere-se registrar
esta exceção no ADR-013 do `infra-lab` (repositório à parte).

**O que fica exposto por `/api/`** — lista de PERMISSÃO no nginx: `auth`,
`usuarios`, `categorias`, `produtos`, `variantes`, `estoque`, `pedidos`,
`clientes`, `fornecedores`, `dashboard`, `relatorios` e `media`. Tudo o mais
(`/docs`, `/redoc`, `/openapi.json`, `/metrics`, `/health`, o webhook da
Nuvemshop e qualquer rota nova) responde 404 do nginx. **Ao criar um router
novo na API, acrescentar o prefixo em `apps/web/nginx.conf`**, senão a tela
correspondente recebe 404.

### Ativar (nesta ordem — o Access vem ANTES do Ingress)

> **Os menus da Cloudflare mudam com frequência.** Os caminhos abaixo foram
> conferidos na documentação oficial em 2026-09-25 (fontes no fim desta
> seção). Se a tela divergir, valha a documentação atual, não este texto.

1. **Login por e-mail (pré-requisito).** *Zero Trust → Integrations →
   Identity providers → Add new identity provider → One-time PIN.*
   O PIN **não vem mais ativado por padrão**: organizações novas usam só o
   provedor "Cloudflare" (login com conta Cloudflare). Sem o PIN, colegas sem
   conta Cloudflare não conseguem entrar. Com ele, a pessoa digita o e-mail
   ("Send login code") e recebe um código de uso único, válido por 10 min.
2. **Política de acesso.** *Zero Trust → Access controls → Policies → Add a
   policy.* Campos: **Policy name** (ex.: `AMACTIVE - equipe`), **Action**:
   `Allow`, **Rules** → *Include* → seletor **Emails** → um e-mail por linha
   (ou **Emails ending in** para liberar um domínio inteiro), e
   **Session duration** (obrigatório e definido na política; ex.: 24h).
   Uma aplicação sem nenhuma política **nega todo mundo**.
3. **Aplicação.** *Zero Trust → Access controls → Applications → Create new
   application → Self-hosted and private → Add public hostname.* Hostname:
   `amactive.amtech.app.br` (subdomínio `amactive`, domínio `amtech.app.br` no
   seletor **Domain**, **sem path** — cobre o site inteiro). Em *Access
   policies*, adicione a política do passo 2 (existente ou crie ali mesmo) e,
   em *identity providers*, marque **One-time PIN**. Finalize com **Create**.
   (A documentação oficial não detalha os rótulos exatos dos campos
   subdomínio/path; se a tela pedir de outro jeito, o que importa é o
   hostname completo `amactive.amtech.app.br` sem restrição de caminho.)
4. **Web Analytics (opcional, cosmético).** O Web Analytics é injetado
   automaticamente em sites proxiados pela Cloudflare. Se estiver ligado para
   este hostname, o script dele é **bloqueado pela CSP do nginx** — só gera
   um erro no console, o sistema funciona igual. Para silenciar: *Cloudflare
   dashboard → Web Analytics → (o site) → Manage Site → Disable*. A doc não
   diz se isso vale para hostnames servidos via Tunnel; não é bloqueante.
5. **Prove que o Access está ativo antes de aplicar o Ingress:**
   `curl -sSI https://amactive.amtech.app.br/` deve responder `302` com
   `location:` para `*.cloudflareaccess.com/cdn-cgi/access/login/...`. Um
   `404` aqui significa que o Access **não** está protegendo o hostname (a
   resposta veio do ingress-nginx, que ainda não tem rota). Se não
   redirecionar, NÃO aplique o Ingress.
6. Commitar/dar push de `infra/k8s/web/ingress-public.yaml` (o ArgoCD aplica).
7. **Prove que sem credencial nada do AMACTIVE é servido:**

   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' https://amactive.amtech.app.br/api/produtos   # 302 (nunca 200/401 do AMACTIVE)
   curl -s https://amactive.amtech.app.br/ | grep -c AMACTIVE                              # 0
   ```

8. Logar pelo navegador (tela do Access → e-mail → código → tela de login do
   AMACTIVE) e conferir que as chamadas a `/api/*` funcionam (dashboard,
   produtos, upload de foto).

**Desativar:** remover `infra/k8s/web/ingress-public.yaml` e dar push (o ArgoCD
faz o prune); o acesso pela LAN não é afetado.

**Fontes dos menus da Cloudflare (conferidas em 2026-09-25):**
[aplicação self-hosted](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/),
[gerenciar políticas](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/policy-management/),
[políticas (seletores)](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/),
[One-time PIN](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/),
[Web Analytics](https://developers.cloudflare.com/web-analytics/get-started/).

### Riscos aceitos / pendências

- Os LoadBalancers da LAN (`192.168.1.212` API, `192.168.1.213` web) **não
  passam pelo Access** e o ns `amactive` não tem NetworkPolicy — a LAN é
  tratada como confiável (e o acesso pela LAN tem de continuar funcionando sem
  Cloudflare). O da API expõe `/docs`, `/metrics` e o webhook.
- Login sem lockout/rate limit por e-mail (só o tempo de resposta foi
  igualado, para não enumerar e-mails). Com o Access na frente só quem já está
  autorizado chega ao formulário; se o Access for removido, revisar isto antes.
- JWT de 8h em `localStorage`, sem revogação (mitigado pela CSP).
- O IP de origem visto pelo ingress-nginx atrás do túnel é forjável
  (`use-forwarded-headers` do edge, ver "Integração Nuvemshop") — por isso não
  há rate limit por IP no Ingress; o controle de acesso é o Access.

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

- `migrations-configmap.yaml` continua sincronizado à mão com
  `migrations/*.up.sql` — mas desde `test_migrations_configmap_espelho.py`
  (rodando de verdade em CI, ver `task-python-test.yaml`) uma divergência
  agora QUEBRA o build, em vez de silenciosamente ir parar em produção.
  Automatizar a geração do ConfigMap (ou reconsiderar mudar o build context
  do `Dockerfile` da API para incluir `migrations/` na imagem, como o
  `apps/web` do amfit faz) continua fora do escopo.
- Migrar armazenamento de imagens de produto para MinIO/S3 — decisão já
  tomada de NÃO fazer isso agora; o PVC local-path é a solução deste MVP.
# teste de webhook - 2026-09-14T18:40:42Z
# harbor project+robot configurados - 2026-09-14T18:54:43Z
