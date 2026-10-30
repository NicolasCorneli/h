#!/usr/bin/env bash
# Backup da implantação do docker-compose.yml: banco e imagens, com data no nome.
#
#   ./scripts/backup_producao.sh [pasta-de-destino]       (padrão: ./backups)
#
# Variáveis opcionais: COMPOSE_ARQUIVO (padrão docker-compose.yml), ENV_ARQUIVO
# (padrão .env) e COMPOSE_PROJETO (o nome do projeto, se a implantação usar -p).
#
# Gera dois arquivos, que precisam ser guardados juntos e FORA deste servidor:
#   banco-AAAAmmdd-HHMMSS.dump      pg_dump em formato custom (pg_restore)
#   imagens-AAAAmmdd-HHMMSS.tar.gz  as fotos (só com STORAGE_DRIVER=local; com S3, o
#                                   backup das imagens é o versionamento/replicação do bucket)
#
# Os arquivos contêm dados pessoais (cadastro de clientes e fotos de rosto): guarde-os
# criptografados e com acesso restrito. A restauração está em DEPLOY.md.
set -euo pipefail

DESTINO="${1:-./backups}"
COMPOSE_ARQUIVO="${COMPOSE_ARQUIVO:-docker-compose.yml}"
ENV_ARQUIVO="${ENV_ARQUIVO:-.env}"
MARCA="$(date -u +%Y%m%d-%H%M%S)"

compose=(docker compose -f "$COMPOSE_ARQUIVO" --env-file "$ENV_ARQUIVO")
if [ -n "${COMPOSE_PROJETO:-}" ]; then
  compose+=(-p "$COMPOSE_PROJETO")
fi

mkdir -p "$DESTINO"
chmod 700 "$DESTINO"
umask 077

echo "banco → $DESTINO/banco-$MARCA.dump"
"${compose[@]}" exec -T db pg_dump -U espelho -d espelho --format=custom --no-owner \
  > "$DESTINO/banco-$MARCA.dump.parcial"
mv "$DESTINO/banco-$MARCA.dump.parcial" "$DESTINO/banco-$MARCA.dump"

if "${compose[@]}" exec -T api sh -c 'test -d /app/dados/imagens'; then
  echo "imagens → $DESTINO/imagens-$MARCA.tar.gz"
  "${compose[@]}" exec -T api tar czf - -C /app/dados imagens \
    > "$DESTINO/imagens-$MARCA.tar.gz.parcial"
  mv "$DESTINO/imagens-$MARCA.tar.gz.parcial" "$DESTINO/imagens-$MARCA.tar.gz"
fi

# Confere que o dump é legível antes de dizer que deu certo.
"${compose[@]}" exec -T db pg_restore --list < "$DESTINO/banco-$MARCA.dump" > /dev/null
echo "backup concluído: $(ls -1 "$DESTINO" | grep -c "$MARCA") arquivo(s) com a marca $MARCA"
