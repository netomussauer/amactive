# Vitrine online (loja pública)

Status: **construída e testada em desenvolvimento**. Ainda não implantada em produção.
Documentos relacionados: [arquitetura-producao.md](./arquitetura-producao.md) (hospedagem e domínio), [SDD.md](./SDD.md) §6 (evolução).

## 1. Escopo

Vitrine pública para o cliente final escolher peças, reservar e enviar o pedido. **Não há gateway de pagamento.** O pagamento é combinado pelo WhatsApp da loja e registrado pela equipe no sistema administrativo.

| Decisão | Escolha | Motivo |
|---|---|---|
| Pagamento | Fora do sistema (WhatsApp) | Sem gateway nesta fase |
| Login do cliente | Nenhum | Cliente final não se autentica; identificado por nome e telefone |
| Estoque | Reserva com prazo de 24h, baixa só na confirmação | Evita vender a mesma peça duas vezes sem baixar antes do pagamento |
| Origem do pedido | Novo canal `VITRINE` | Separa relatórios da loja online |
| Hostname (produção) | `loja.amactive.com.br`, sem Cloudflare Access | Superfície pública separada do admin (`app.`, com Access) |
| Build | Mesmo código-fonte, build separado (`npm run build:loja`) | O bundle público não contém telas administrativas |

## 2. Fluxo

1. O cliente navega pelo catálogo público (`GET /loja/produtos`) e monta o carrinho (guardado no navegador).
2. No checkout, informa nome e WhatsApp. `POST /loja/pedidos` cria o pedido **PENDENTE**, sem operador, e **reserva** as unidades por 24h. O estoque físico não muda.
3. A tela de confirmação oferece o botão "Enviar pedido pelo WhatsApp" (link `wa.me` com a mensagem pronta). Sem número configurado, oferece copiar a mensagem.
4. O cliente envia a mensagem. A equipe combina o pagamento pelo WhatsApp.
5. Na área administrativa, o detalhe do pedido da loja mostra **Confirmar pagamento** (`POST /pedidos/{id}/confirmar-pagamento`). Só nesse momento o estoque é baixado (movimentação `SAIDA`) e o pedido vira CONFIRMADO.
6. Se o pagamento não chegar, a equipe cancela (`PATCH /pedidos/{id}/cancelar`), que libera a reserva. Sem ação, a reserva expira sozinha.

## 3. Estoque e concorrência

- **Disponível = saldo físico (`estoque.quantidade`) − reservas vigentes.** Reserva vigente é de pedido PENDENTE com `reservado_ate` no futuro. O catálogo público e o checkout usam a mesma regra.
- O checkout trava a linha de `estoque` (`SELECT ... FOR UPDATE`) em ordem por `variante_id` antes de contar. Dois checkouts concorrentes da última unidade não passam os dois.
- A confirmação também trava as linhas antes de dar a baixa.
- A baixa continua passando só por `movimentacao_estoque` (o trigger aplica o delta). Nunca há `UPDATE` direto em `estoque`.
- **Expiração preguiçosa:** antes de cada checkout, pedidos com reserva vencida são cancelados e suas reservas removidas. Uma reserva vencida também deixa de contar na disponibilidade imediatamente. Confirmar um pedido com reserva vencida é recusado (`ReservaVencida`).

## 4. Contrato da API

Público (sem JWT), prefixo `/loja`:

| Método | Rota | Função |
|---|---|---|
| GET | `/loja/categorias` | Categorias ativas |
| GET | `/loja/produtos?page&per_page&categoria_id&q` | Produtos vendáveis (com ao menos uma variante ativa), com `disponivel` por variante |
| GET | `/loja/produtos/{id}` | Detalhe: variantes (cor, tamanho, preço cheio e promocional, disponível), imagens, descrição |
| POST | `/loja/pedidos` | Checkout: `{cliente:{nome,telefone}, observacao?, itens:[{variante_id,quantidade}]}` → 201 com `numero`, `valor_total`, `reservado_ate`, itens |

Campos que a vitrine **nunca** expõe: `preco_custo`, fornecedor, `estoque_minimo`, dados de outros clientes, id interno do pedido.

Administrativo (JWT, ADMIN/VENDEDOR):

| Método | Rota | Função |
|---|---|---|
| POST | `/pedidos/{id}/confirmar-pagamento` | Confirma o pagamento (`pagamentos` com soma igual ao total), libera a reserva e dá a baixa |

`POST /pedidos` (registro manual do PDV) **recusa** `origem_canal=VITRINE`: pularia reserva e confirmação.

Preço e desconto são sempre recalculados no backend. O desconto promocional do produto (`desconto_percentual`) vira `desconto_item`. O cliente nunca envia valor.

## 5. Dados

Migrations (forward-only, espelhadas no ConfigMap de produção):

- `000007_origem_canal_vitrine`: novo valor `VITRINE` no enum de origem.
- `000008_vitrine_reserva_estoque`: `pedido.usuario_id` passa a aceitar nulo **só** para VITRINE (CHECK no banco); `pedido.reservado_ate` (CHECK: só PENDENTE tem reserva); tabela `reserva_estoque`.

Ciclo up → down → up verificado em banco descartável.

## 6. Frontend

- Mesmo código de `apps/web`. `VITE_APP=loja` (em `.env.loja`) seleciona a vitrine em `src/main.tsx`.
- `npm run build:loja` gera `dist-loja/`. Verificado: o bundle da vitrine não contém telas administrativas, e o build administrativo não contém a vitrine (controle positivo confirmado).
- Variáveis de build: `VITE_API_URL=/api` (mesma origem, sem CORS) e `VITE_WHATSAPP_LOJA` (só dígitos com DDI, definido por ambiente).
- Em desenvolvimento, `/api` é encaminhado ao uvicorn em `localhost:8000` pelo proxy do Vite.
- Carrinho em zustand, persistido em localStorage. Schemas Zod em todas as respostas da API.
- Área administrativa: `usuario_id` nulo tratado (a listagem quebraria sem isso); canal "Loja online" nos rótulos e badges, mas fora das opções de registro manual.

## 7. Testes

- Backend: 280 testes passando (152 unitários, 128 de integração). Inclui fakes das regras da vitrine, Postgres real (reserva, baixa, catálogo público) e HTTP ponta a ponta (checkout → confirmação → disponibilidade).
- Frontend: 256 testes passando. Inclui carrinho, mensagem do WhatsApp, contrato dos schemas e a confirmação de pagamento no admin.

## 8. Pendências para produção (bloqueantes)

1. **Proteção contra abuso no `POST /loja/pedidos`**: não implementado. Rate limit por IP (regras da Cloudflare, com `CF-Connecting-IP`) e Cloudflare Turnstile no checkout. Um checkout é um pedido real que prende estoque.
2. **Nginx do host `loja.`**: allow-list apenas de `/api/loja/` e de `/loja`-assets. Hoje o nginx da imagem atende o admin. Entra na fase F3 da arquitetura de produção.
3. **Número do WhatsApp da loja**: `VITE_WHATSAPP_LOJA` precisa de valor no build de produção.
4. **Aviso de privacidade e base legal (LGPD)** no checkout, antes de coletar nome e telefone.

## 9. Limitações conhecidas (aceitas nesta fase)

- **Venda no balcão (PDV) não respeita reservas.** O PDV baixa do saldo físico. Se vender unidades reservadas, a confirmação da vitrine falha com "estoque insuficiente" e a equipe precisa cancelar o pedido da loja. Corrigir exige o PDV checar `saldo − reservas`.
- **Expiração sem job agendado.** Pedidos vencidos só são cancelados no próximo checkout. Na lista administrativa podem aparecer como PENDENTE por mais tempo. Recomendado: job periódico no worker (fase F4).
- **Cliente deduplicado por telefone sem restrição de unicidade no banco.** Duas requisições simultâneas do mesmo número podem criar dois cadastros. Efeito limitado (cadastro duplicado, não estoque).
- **Confirmação com um único pagamento** (valor total, uma forma). Pagamento misto na vitrine fica para depois.
- **Carrinho local com preço visto.** O total exibido pode diferir do cobrado se o preço mudar; o backend recalcula e a mensagem de WhatsApp usa o valor do próprio pedido criado.
- **Pedido após a reserva expirar**: o cliente precisa refazer o checkout. A tela não avisa isso antecipadamente.
