# Imagem da API. O aplicativo Expo fica fora do Docker (ver DEPLOY.md).
#
# Debian fixado (bookworm): numa troca de versão do Debian os nomes de pacotes do sistema
# mudam (libglib2.0-0 virou libglib2.0-0t64 no trixie) e o build quebraria sem aviso.
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libglib2.0-0 e libgomp1 são exigidas pelo OpenCV headless (detecção de rosto).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Só as dependências de execução: as de teste ficam em requirements-dev.txt.
# Atrás de um proxy que inspeciona TLS (rede corporativa), entregue a CA dele ao build,
# sem desligar a verificação de certificado:
#   docker build --secret id=ca,src=/caminho/da/ca.crt .
# Sem o secret, o pip usa os certificados públicos de sempre.
COPY requirements.txt .
RUN --mount=type=secret,id=ca,required=false \
    if [ -s /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi \
    && pip install -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY entrypoint.sh ./

# Usuário sem privilégios: o processo não precisa de root. O código fica do root (só
# leitura para o processo); só a pasta das imagens é dele.
RUN chmod 0755 entrypoint.sh \
    && useradd --create-home --uid 1000 espelho \
    && mkdir -p /app/dados/imagens \
    && chown -R espelho:espelho /app/dados
USER espelho

EXPOSE 8000

# Sonda de vida: o processo responde. A de prontidão (banco e migrations) é
# /api/v1/saude, usada pelo docker-compose e pelo balanceador.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/saude/vivo', timeout=4)"]

ENTRYPOINT ["./entrypoint.sh"]
# --proxy-headers: confia em X-Forwarded-For/Proto vindos dos endereços de
#   FORWARDED_ALLOW_IPS (padrão do uvicorn: só 127.0.0.1). É o que dá ao freio de login o
#   endereço real de quem chama, atrás do proxy.
# --no-access-log: o log de acesso é o da aplicação, que não escreve a query (nas imagens,
#   a query é a assinatura que abre a foto).
# --no-server-header: sem ele o uvicorn manda `server: uvicorn` junto do `server: espelho`
#   da aplicação, anunciando o servidor em uso.
# Processos: WEB_CONCURRENCY (padrão 1). Encerramento: UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log", "--no-server-header"]
