#!/bin/sh
# Prepara o banco e sobe a API. `create_all()` não é usado em lugar nenhum: o banco é
# sempre construído pelas migrations, do zero se necessário.
#
#   MIGRAR_AO_SUBIR=true   (padrão) aplica `alembic upgrade head` antes de subir. Várias
#                          instâncias ao mesmo tempo são seguras: as migrations esperam
#                          uma trava no banco (ver migrations/env.py). Em produção, o
#                          docker-compose.yml da raiz roda as migrations num serviço à parte
#                          e liga a API com MIGRAR_AO_SUBIR=false.
#   SEED_AO_SUBIR=true     cria os dados de demonstração. Nunca em produção.
set -eu

if [ "${MIGRAR_AO_SUBIR:-true}" = "true" ]; then
  echo "aplicando migrations..."
  alembic upgrade head
fi

# Dados de demonstração têm senha publicada: nunca em produção (o próprio seed também se
# recusa, mas aqui a mensagem fica clara no log do contêiner).
if [ "${SEED_AO_SUBIR:-false}" = "true" ]; then
  if [ "${AMBIENTE:-desenvolvimento}" = "producao" ]; then
    echo "SEED_AO_SUBIR ignorado: AMBIENTE=producao"
  else
    echo "populando dados de demonstração..."
    # O seed recusa recriar dados que já existem; isso não impede a API de subir.
    python -m app.seed || echo "seed não aplicado (veja a mensagem acima); seguindo"
  fi
fi

exec "$@"
