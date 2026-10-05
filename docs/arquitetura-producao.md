# Arquitetura de produção — AMACTIVE

Status: **aprovada para implementação** (decisões de 2026-10).
Escopo: hospedagem de produção na AWS, domínio público, separação com o ambiente de desenvolvimento (lab) e plano de migração por fases.

Documentos relacionados: [SDD.md](./SDD.md) (§6 evolução, §7 riscos), [avaliacao-alternativas-canal-venda.md](./avaliacao-alternativas-canal-venda.md), [../infra/README.md](../infra/README.md) (operação do lab).

---

## 1. Decisões

| # | Tema | Decisão | Motivo |
|---|---|---|---|
| D1 | Provedor de produção | **AWS**, região **sa-east-1 (São Paulo)** | Dados de clientes no Brasil (LGPD) e latência baixa para a loja |
| D2 | Ambiente de desenvolvimento | **Lab K3s (`lab-k8s-01`) permanece como dev**, sem dados reais | Custo zero e iteração rápida; dados de produção nunca passam pelo lab |
| D3 | Modelo de implantação | **Opção D (híbrida)**: produção em serviços gerenciados AWS, lab em Kubernetes | Pouca operação de nós e patch; banco e backup gerenciados |
| D4 | Orçamento | Sem restrição de custo informada | Ainda assim, alarme de faturamento (AWS Budgets) é obrigatório |
| D5 | DNS | Domínio `amactive.com.br` delegado para a **Cloudflare** (a ser configurado) | WAF, rate limiting, Turnstile e Cloudflare Access ficam no mesmo lugar |
| D6 | Subdomínios | `app.amactive.com.br` (sistema administrativo, com Access) e `loja.amactive.com.br` (vitrine, pública) | Separação de superfície de ataque por hostname |

---

## 2. Arquitetura alvo

```
                    Internet
                       │
          ┌────────────▼────────────┐
          │   Cloudflare (DNS+WAF)  │
          │   - Access (app.*)      │
          │   - Turnstile / rate    │
          │     limit (loja/api)    │
          └────────────┬────────────┘
                       │  (só Cloudflare chega ao ALB)
┌──────────────────────▼───────────────────────────────────────┐
│ AWS sa-east-1 — VPC (2 AZs)                                   │
│                                                               │
│  Subnets públicas: ALB                                        │
│     ├─ app.amactive.com.br  ──► ECS: web (nginx) ──► api     │
│     └─ loja.amactive.com.br ──► ECS: loja (nginx) ──► api    │
│                                                               │
│  Subnets privadas (sem IP público):                          │
│     ECS Fargate: api (N tarefas), worker (1+ tarefas)        │
│     RDS PostgreSQL (Multi-AZ)                                 │
│                                                               │
│  Serviços regionais:                                          │
│     S3 (imagens de produto, privado) ◄── api                  │
│     ECR (imagens de container)                                │
│     Secrets Manager (segredos) · SSM Parameter Store (config) │
│     CloudWatch (logs, métricas, alarmes) · AWS Budgets        │
└───────────────────────────────────────────────────────────────┘

Lab (dev):  K3s + ArgoCD + Tekton + Harbor + Gitea  — sem acesso ao banco de produção
```

### 2.1 Serviços AWS

| Necessidade | Serviço | Observação |
|---|---|---|
| API FastAPI | **ECS Fargate**, serviço `amactive-api` | Atrás do ALB, health check em rota dedicada |
| Worker de integração (outbox) | **ECS Fargate**, serviço `amactive-worker` | Sempre ativo (mínimo 1 tarefa). Sem scale-to-zero |
| Web admin (SPA + nginx) | **ECS Fargate**, serviço `amactive-web` | Mesmo modelo de proxy `/api/` já validado no lab |
| Vitrine (SPA + nginx) | **ECS Fargate**, serviço `amactive-loja` | Build separado, sem telas administrativas (ver proposta da vitrine) |
| Balanceador | **ALB** (público, em subnets públicas) | Regras por host: `app.*` e `loja.*` |
| Banco | **RDS PostgreSQL**, Multi-AZ, backup automático com PITR | Retenção de backup: 14 dias (ajustável). Versão maior ou igual à do lab |
| Imagens de produto | **S3** privado + **CloudFront** (Origin Access Control) | Substitui o disco local (`LocalDiskArmazenamentoDeImagem`) por um adaptador novo |
| Registry | **ECR** (imagens com tag imutável) | Promoção por digest, ver §4 |
| Segredos | **Secrets Manager** | Injetados no ECS; nunca em repositório, nunca em variável em texto claro no task definition |
| Saída para internet (tarefas privadas) | **NAT Gateway** (1 por AZ) | Maior parcela surpresa de custo na AWS; monitorar |
| Logs e alarmes | **CloudWatch** | Alarmes: 5xx do ALB, CPU/memória do ECS, espaço e conexões do RDS, falha do worker |
| Governança | **AWS Organizations** (quando houver segunda conta), **IAM Identity Center**, MFA no root | Ver §5 |

### 2.2 Rede e borda

- **O ALB só aceita tráfego vindo da Cloudflare.** Sem essa trava, alguém descobre o DNS do ALB e contorna o Access e o WAF. Implementação: Security Group do ALB liberando apenas os IPs da Cloudflare, e/ou cabeçalho de origem validado no ALB (ou Authenticated Origin Pulls). Este é um requisito de segurança, não otimização.
- **Real IP**: com a Cloudflare na frente, o cliente real vem em `CF-Connecting-IP`. A API e o nginx devem usar esse cabeçalho (só quando a origem for a Cloudflare). Isso resolve a pendência de real-IP para rate limiting que estava adiada no lab.
- **Rate limiting** de `loja.*` e do checkout: primeiro na Cloudflare (regras de rate limit), depois na aplicação como segunda camada.
- **Access**: `app.amactive.com.br` exige login (e-mail corporativo ou OTP por e-mail). `loja.amactive.com.br` não tem Access.
- **HTTPS**: certificado público no ALB (ACM) e modo "Full (strict)" na Cloudflare.
- **Hostname de dev no lab** (`amactive.amtech.app.br`): mantido só para desenvolvimento. Nenhum dado real.

---

## 3. Dados

| Dado | Onde | Regra |
|---|---|---|
| Banco transacional | RDS PostgreSQL | Multi-AZ, PITR, criptografia em repouso (KMS), TLS obrigatório na conexão |
| Imagens de produto | S3 (privado) | Acesso só por CloudFront (OAC) e pela API; versionamento habilitado |
| Logs da aplicação | CloudWatch Logs | Retenção de 90 dias. **Nunca** logar CPF, telefone completo ou tokens |
| Backups | RDS automático + snapshot manual antes de cada cutover | Restauração testada antes do go-live (§6, fase F5) |

**LGPD** (dados de clientes: nome e telefone, com vitrine e pedidos):
- Registro das operações de tratamento, base legal e prazo de retenção a documentar antes do go-live (responsabilidade jurídica do negócio; a parte técnica está em §3).
- Política de privacidade e aviso no checkout da vitrine.
- Procedimento para exclusão e exportação de dados de um titular.

---

## 4. Entrega (CI/CD) e promoção

Princípio: **construir uma vez, promover o mesmo artefato**. A imagem que foi testada no lab é exatamente a que vai para produção, identificada pelo digest.

Fluxo proposto:

1. Push no Gitea do lab (fluxo já existente), que dispara o Tekton: testes, lint, build com kaniko.
2. A imagem vai para o Harbor do lab (dev) **e**, em uma etapa de promoção, para o **ECR** (produção), pelo mesmo digest.
3. Deploy de produção **manual**, com aprovação: nova task definition do ECS apontando para o digest, migration como tarefa única antes da troca, depois rolling update.
4. Smoke test automático após o deploy (health + uma rota de leitura).
5. Rollback: voltar a task definition para o digest anterior.

Credencial de promoção: a etapa do Tekton no lab precisa autenticar no ECR. Recomendação: **usuário IAM dedicado**, com permissão apenas de push no repositório ECR da aplicação, credencial armazenada como SealedSecret no lab e rotacionada a cada 90 dias. Alternativa melhor, a avaliar: GitHub Actions com OIDC para AWS (sem chave de longa duração), que exige o GitHub no caminho de produção. Decidir na fase F3.

IaC: **Terraform** em `infra/aws/` deste repositório, com estado remoto em S3 (locking nativo do S3). Ambientes separados por diretório e por conta (dev na lab, prod na AWS).

---

## 5. Conta AWS e segurança

Antes de qualquer recurso:
- Conta raiz com MFA (hardware ou passkey) e sem chaves de acesso.
- Usuário administrador via **IAM Identity Center** (não usar usuário IAM com chave de longa duração para o dia a dia).
- **AWS Budgets** com alerta em 50%, 80% e 100% de um teto mensal definido.
- **CloudTrail** habilitado na região e em todas as regiões, com trilha em bucket separado.
- **GuardDuty** habilitado (custo baixo, valor alto para este porte).
- Recomendado criar uma segunda conta (produção separada de administração) quando o time crescer; não é obrigatório agora.

Controles da aplicação já previstos que se mantêm: login com verificação de tempo constante, cabeçalhos de segurança no nginx, allow-list de rotas na borda, proteção de dados sensíveis em logs.

---

## 6. Plano de migração por fase

Cada fase tem um **critério de saída**. Não se avança sem ele.

| Fase | Entrega | Critério de saída |
|---|---|---|
| **F0 — Preparação** | Conta AWS criada com MFA, Identity Center, Budgets, CloudTrail, GuardDuty. DNS de `amactive.com.br` delegado para a Cloudflare. Bucket de estado do Terraform | Acesso administrativo testado; alarme de faturamento disparando em teste; `dig` mostra os NS da Cloudflare |
| **F1 — Fundação** | Terraform: VPC (2 AZs), subnets, ALB, ECR, RDS (Multi-AZ), S3, CloudFront, Secrets Manager, CloudWatch, Security Groups, trava de origem para a Cloudflare | `terraform plan` limpo; RDS e S3 acessíveis só pela rede privada; ALB inacessível diretamente pela internet |
| **F2 — Código** | Adaptador S3 para `ArmazenamentoDeImagemPort` com teste de integração; job de migration separado do boot; rota de health; leitura de real IP via `CF-Connecting-IP`; worker como serviço próprio; configuração 100% por variável de ambiente | Testes de unidade e integração passando; build de imagem reproduzível (digest) |
| **F3 — Pipeline** | Promoção Tekton → ECR por digest; deploy ECS com aprovação manual; smoke test; rollback testado | Deploy e rollback executados em produção sem dados reais, com registro no runbook |
| **F4 — Operação** | Alarmes ativos, runbook de incidentes, teste de restauração do RDS a partir de snapshot, procedimento de LGPD | Restauração concluída dentro do tempo-alvo documentado; alarmes testados com disparo real |
| **F5 — Carga inicial** | Exportação do dado do lab (se houver dado real), restauração no RDS, cópia das imagens para o S3, conferência de contagens | Contagens de tabelas e de imagens batendo com a origem; amostra funcional validada pelo negócio |
| **F6 — Cutover** | Registro DNS de `app.` e `loja.` apontando para o ALB via Cloudflare; Access configurado; janela combinada; plano de volta (DNS para o estado anterior) | Smoke test verde nos dois hostnames; Access exigindo login no admin; ALB inacessível diretamente |
| **F7 — Pós go-live** | Desativar acesso público de dev no lab; revisão de custos após 30 dias | Lab sem exposição pública; custo real comparado ao previsto |

A vitrine (`loja.`) entra em produção com a feature, não antes. Antes disso, o hostname existe com uma página de manutenção.

---

## 7. Riscos

| Risco | Mitigação |
|---|---|
| ALB acessível direto, contornando Access e WAF | Trava de origem para a Cloudflare (§2.2), com teste automatizado de conectividade |
| Pedidos de vitrine travam estoque (ver proposta da vitrine) | Reserva com expiração, decidida antes da fase de código da vitrine |
| Credencial de promoção do lab vazar | Permissão mínima no ECR, rotação a cada 90 dias, alerta no CloudTrail para uso fora do horário |
| NAT Gateway elevando custo sem aviso | Alarme de tráfego de saída e revisão mensal |
| Migration quebrar produção | Migration como tarefa única, com snapshot antes e teste em cópia da base |
| Perda de dados | Multi-AZ, PITR e restauração testada na F4 |
| Dado de produção no lab | Proibido por política; o lab usa apenas dados fictícios |

---

## 8. Pendências (decisões ou ações a fechar)

- [ ] Criação da conta AWS (ação do responsável) e definição do e-mail do root.
- [ ] Teto mensal do AWS Budgets.
- [ ] Configuração da delegação DNS do `amactive.com.br` para a Cloudflare.
- [ ] Número de WhatsApp da loja (para o checkout da vitrine).
- [ ] Confirmar se o banco do lab contém dado real de operação. Se sim, a F5 é obrigatória; se não, a produção começa do zero.
- [ ] Escolha da credencial de promoção (usuário IAM com rotação vs. GitHub Actions OIDC), na F3.
- [ ] Hostname para mídia (`midia.amactive.com.br` ou outro), se o CloudFront tiver domínio próprio.
- [ ] Revisão jurídica da base legal e da política de privacidade (LGPD).
- [ ] Decisão de estratégia de reserva de estoque da vitrine (A, B ou C da proposta anterior).

---

## 9. Fora de escopo deste documento

- Detalhes da vitrine (modelo de dados, endpoints e telas): tratados na proposta da vitrine.
- Fiscal, gateway de pagamento e multi-loja: itens de evolução do SDD §6, sem mudança de decisão aqui.
- Operação do lab: [../infra/README.md](../infra/README.md).
