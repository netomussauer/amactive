# syntax=docker/dockerfile:1.7
#
# Dockerfile multi-stage do apps/web — build estático Vite (React + TS)
# servido por nginx.
#
# Por que nginx em vez do padrão node-distroless usado pelo amfit-web /
# realtpmsys-web (Next.js standalone): este app NÃO usa SSR — é uma SPA pura
# (`vite build` gera apenas HTML/JS/CSS estático em dist/, ver
# apps/web/package.json script "build": "tsc -b && vite build"). Rodar um
# runtime Node só para servir arquivos estáticos seria desperdício de
# recursos e superfície de ataque desnecessária; um servidor HTTP estático
# (nginx) é o padrão adequado para esse caso, mais leve e mais simples.
#
# Stages:
#   1. build   — node:20-alpine, `npm ci` + `vite build` -> dist/
#   2. runtime — nginxinc/nginx-unprivileged (nginx rodando como usuário não
#      -root de fábrica, uid 101, escutando em porta >1024 por padrão —
#      evita ter que reinventar essa configuração manualmente como seria
#      necessário com a imagem `nginx:alpine` oficial).

# ─── 1. Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# VITE_API_URL é embutida no bundle JS em BUILD TIME pelo Vite (import.meta.env)
# — não é uma env var de runtime como seria em um servidor Node/Next.js.
# O pipeline (infra/tekton/pipeline-web.yaml) a passa como --build-arg para o
# Kaniko. "/api" é RELATIVO à origem do navegador: o nginx deste mesmo
# container (nginx.conf, `location ^~ /api/`) repassa para a API dentro do
# cluster — mesmo bundle serve a LAN e o endereço público, sem CORS.
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ─── 2. Runtime ──────────────────────────────────────────────────────────
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=101:101 --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

# Imagem base já roda como uid 101 (usuário `nginx`) por padrão — sem USER
# explícito necessário, mas mantido aqui por clareza/auditoria.
USER 101

CMD ["nginx", "-g", "daemon off;"]
