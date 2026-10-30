#!/usr/bin/env bash
# Suíte de verificação do Espelho, em um comando.
#
#   ./qa.sh              back-end (testes com cobertura e migrations x modelos), tipos e lint do
#                        aplicativo, testes de unidade e busca de travessões
#   ./qa.sh --interface  acrescenta as baterias de navegador (precisa da API e do
#                        `expo start --web` no ar). A do Google roda só com
#                        GOOGLE_CLIENT_IDS e EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID definidos.
#   ./qa.sh --tudo       tudo acima, mais a auditoria de dependências
#
# Pré-requisitos: PostgreSQL acessível, banco `espelho_test` criado (ou outro cujo nome
# termine em `_test`, em TEST_DATABASE_URL) e `backend/.venv` com requirements-dev.txt
# instalado (ver backend/README.md). A suíte apaga o banco de teste a cada execução.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$RAIZ/backend/.venv/bin/python"
INTERFACE=0
AUDITORIA=0

for argumento in "$@"; do
  case "$argumento" in
    --interface) INTERFACE=1 ;;
    --tudo) INTERFACE=1; AUDITORIA=1 ;;
    --ajuda|-h) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "argumento desconhecido: $argumento"; exit 2 ;;
  esac
done

if [ ! -x "$PY" ]; then
  echo "ambiente Python não encontrado em backend/.venv — veja backend/README.md" >&2
  exit 1
fi

echo "━━ Back-end: testes e cobertura ━━"
cd "$RAIZ/backend"
"$PY" -m pytest --cov=app --cov-report=term-missing:skip-covered --cov-report=xml

echo
echo "━━ Banco: modelos e migrations coincidem ━━"
# O pytest deixou o banco de teste na última migration; qualquer diferença entre os
# modelos e o que as migrations criam aparece aqui.
DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://espelho:espelho@localhost:5432/espelho_test}" \
  JWT_SECRET="segredo-so-para-conferir-as-migrations-0000" "$PY" -m alembic check

echo
echo "━━ Aplicativo: verificação de tipos ━━"
(cd "$RAIZ/espelho" && npx tsc --noEmit --noUnusedLocals)

echo
echo "━━ Aplicativo: lint ━━"
(cd "$RAIZ/espelho" && npx eslint .)

echo
echo "━━ Aplicativo: duração, data inicial do agendamento, painel, busca, comparação, pedido e datas do calendário ━━"
(cd "$RAIZ/espelho" && node --experimental-strip-types --no-warnings testes/duracao.mjs)
(cd "$RAIZ/espelho" && TZ=America/Sao_Paulo node --experimental-strip-types --no-warnings testes/inicio-agendamento.mjs)
(cd "$RAIZ/espelho" && TZ=America/Sao_Paulo node --experimental-strip-types --no-warnings testes/painel.mjs)
(cd "$RAIZ/espelho" && node --experimental-strip-types --no-warnings testes/busca.mjs)
(cd "$RAIZ/espelho" && node --experimental-strip-types --no-warnings testes/comparacao.mjs)
(cd "$RAIZ/espelho" && node --experimental-strip-types --no-warnings --import ./testes/carregar-ts.mjs testes/pedido.mjs)
# Datas do calendário (nascimento): em dois fusos, para pegar deslocamento de dia.
for fuso in America/Sao_Paulo Asia/Tokyo; do
  (cd "$RAIZ/espelho" && TZ=$fuso node --experimental-strip-types --no-warnings \
    --import ./testes/carregar-ts.mjs testes/datas.mjs)
done

echo
echo "━━ Textos: travessões e meias-riscas na interface ━━"
"$PY" "$RAIZ/scripts/verificar_travessoes.py" "$RAIZ"

if [ "$INTERFACE" = "1" ]; then
  echo
  echo "━━ Dados de demonstração (o roteiro os altera; recriar deixa a execução repetível) ━━"
  cd "$RAIZ/backend"
  "$PY" -m app.seed --reset

  echo
  echo "━━ Interface: fluxo completo ━━"
  cd "$RAIZ/espelho"
  node e2e/fluxo-completo.mjs

  echo
  echo "━━ Interface: responsividade, acessibilidade e estados ━━"
  node e2e/qa-interface.mjs

  echo
  echo "━━ Interface: fluxos e ações desta etapa ━━"
  # A bateria anterior consome os dados de demonstração; recriar antes desta.
  (cd "$RAIZ/backend" && "$PY" -m app.seed --reset > /dev/null)
  cd "$RAIZ/espelho"
  node e2e/mudancas-interface.mjs

  echo
  echo "━━ Interface: agenda (editar, confirmar, cancelar, concluir, datas passadas) ━━"
  (cd "$RAIZ/backend" && "$PY" -m app.seed --reset > /dev/null)
  cd "$RAIZ/espelho"
  node e2e/agenda.mjs

  echo
  echo "━━ Interface: agendamentos, conclusão e atendimento avulso ━━"
  (cd "$RAIZ/backend" && "$PY" -m app.seed --reset > /dev/null)
  cd "$RAIZ/espelho"
  node e2e/atendimentos.mjs

  echo
  echo "━━ Interface: painel inicial e comparação de simulações ━━"
  (cd "$RAIZ/backend" && "$PY" -m app.seed --reset > /dev/null)
  cd "$RAIZ/espelho"
  node e2e/painel-e-comparacao.mjs

  echo
  echo "━━ Interface: fotos, câmera e enquadramento ━━"
  (cd "$RAIZ/backend" && "$PY" -m app.seed --reset > /dev/null)
  cd "$RAIZ/espelho"
  node e2e/fotos-e-camera.mjs

  echo
  echo "━━ Interface: etapa \"Estilo e cor\", revisão e geração ━━"
  (cd "$RAIZ/backend" && "$PY" -m app.seed --reset > /dev/null)
  cd "$RAIZ/espelho"
  node e2e/personalizacao.mjs

  echo
  echo "━━ Interface: todas as telas, contraste e largura ━━"
  (cd "$RAIZ/backend" && "$PY" -m app.seed --reset > /dev/null)
  cd "$RAIZ/espelho"
  node e2e/visual-contraste.mjs

  echo
  echo "━━ Interface: regressões da auditoria (sessão, nascimento, estado vazio, correção) ━━"
  cd "$RAIZ/espelho"
  node e2e/auditoria.mjs

  echo
  echo "━━ Interface: senha e sessões (trocar senha, sair de todos os aparelhos) ━━"
  # Por último: ela erra a senha de propósito, e o freio de login conta essas falhas.
  cd "$RAIZ/espelho"
  node e2e/seguranca.mjs

  if [ -n "${EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID:-}" ]; then
    echo
    echo "━━ Interface: Entrar com Google (sem conta real) ━━"
    (cd "$RAIZ/backend" && "$PY" -m app.seed --reset > /dev/null)
    GOOGLE_WEB_CLIENT_ID="$EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID" node e2e/google.mjs
  fi
fi

if [ "$AUDITORIA" = "1" ]; then
  echo
  echo "━━ Dependências: Python ━━"
  cd "$RAIZ/backend"
  "$PY" -m pip_audit -r requirements.txt --progress-spinner off || true

  echo
  echo "━━ Dependências: Node ━━"
  cd "$RAIZ/espelho"
  npm audit --omit=dev || true
fi

echo
echo "verificação concluída."
