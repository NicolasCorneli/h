# Site do Salão em Dia (versão web do aplicativo) servido pelo Caddy.
#
# O Caddy entrega o site, encaminha /api/ para a API e obtém o certificado HTTPS sozinho
# (Let's Encrypt) para o domínio de DOMINIO. Site e API no mesmo domínio: o build não
# precisa de EXPO_PUBLIC_API_URL (o site usa a própria origem) e não há CORS.

# --- Build do site estático ------------------------------------------------------------
FROM node:22-bookworm-slim AS build

ENV CI=1 \
    EXPO_NO_TELEMETRY=1 \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    NPM_CONFIG_UPDATE_NOTIFIER=false

WORKDIR /app

# Atrás de um proxy que inspeciona TLS (rede corporativa), entregue a CA dele ao build,
# sem desligar a verificação de certificado:
#   docker build --secret id=ca,src=/caminho/da/ca.crt .
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=ca,required=false \
    if [ -s /run/secrets/ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca; fi \
    && npm ci --no-audit --no-fund

COPY . .

# Vazio: o site chama a API na própria origem (/api). Só defina para hospedar a API em
# outro domínio.
ARG EXPO_PUBLIC_API_URL=
ARG EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=
ENV EXPO_PUBLIC_API_URL=$EXPO_PUBLIC_API_URL \
    EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=$EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID

# `build:web` limpa o cache do Metro: as EXPO_PUBLIC_* entram no pacote nesta etapa.
RUN npm run build:web

# --- Servidor --------------------------------------------------------------------------
FROM caddy:2.10-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv

# 80 (HTTP, redireciona para HTTPS e responde ao desafio do Let's Encrypt) e 443.
EXPOSE 80 443 443/udp

# A API de administração do Caddy escuta só em 127.0.0.1:2019, dentro do contêiner.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:2019/config/"]
