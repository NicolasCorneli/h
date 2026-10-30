# Relatório de revisão técnica e preparação para deploy — Salão em Dia

Revisão feita em 29/10/2026 num contêiner Linux (Python 3.11, Node 22, PostgreSQL 16,
Docker 29 com Compose v5, Chromium do Playwright), a partir do arquivo
`salaoemdia.zip` (archive do commit `9619ad3a`). O repositório de destino estava vazio; o
conteúdo do ZIP foi extraído para a raiz. O ZIP original ficou intacto. Todas as
alterações estão na área de trabalho, **sem commit e sem push**: as tentativas de commit
(no início e no fim) foram negadas pelo controle de permissões da sessão, de acordo com a
instrução de não commitar sem pedido explícito. Para separar o original da revisão ao
registrar, faça um primeiro commit com o conteúdo do ZIP e um segundo com a área de
trabalho atual. Nenhum pull request foi aberto e nada foi implantado.

Todos os números deste relatório vêm de comandos executados neste ambiente. O que não pôde
ser executado está marcado como BLOQUEADO ou NÃO EXECUTADO, com o motivo.

---

## A. Resumo executivo

**Estado inicial.** Um projeto maduro, com várias rodadas de QA anteriores: API FastAPI com
533 testes passando, aplicativo Expo sem erros de tipo, testes de unidade e 10 baterias de
navegador passando (linha de base reexecutada aqui, seção E). A prontidão para produção,
porém, tinha lacunas que os testes existentes não cobriam, porque eles rodam o código
diretamente (TestClient, Metro de desenvolvimento) e não o artefato que iria para produção.

**Principais problemas encontrados** (confirmados por reprodução, por teste que falha no
código original ou pela leitura do código; a seção C diz qual, em cada caso. O risco de
apagar um banco real, por exemplo, foi confirmado lendo o código, sem executar a perda):

1. **A suíte de testes podia apagar um banco real**: ela faz `downgrade base` no banco de
   `DATABASE_URL` herdado do terminal, e o próprio README orientava a definir essa variável.
2. **O aplicativo de produção não alcançaria a API**: sem `EXPO_PUBLIC_API_URL`, o build
   chamava `http://<domínio>:8000` na web e `http://espelho:8000` no celular.
3. **Imagens quebradas atrás de proxy**: as URLs assinadas eram montadas com o endereço
   interno da requisição (`http://api:8000`), bloqueado pelo navegador numa página https.
4. **Migrations concorrentes falhavam**: o entrypoint migrava a cada subida; com três
   instâncias simultâneas, duas caíram com `UniqueViolation`.
5. **Sessões impossíveis de revogar**: sem troca de senha e sem "sair de todos os
   aparelhos"; um token de renovação copiado valia 30 dias.
6. **Simulação presa para sempre** depois de um reinício no meio da geração (e impossível
   de excluir: 409).
7. **Assinatura das imagens no log de acesso** (credencial de acesso à foto de uma pessoa).
8. **Infraestrutura de produção inexistente ou insegura**: sem compose de produção, sem
   `.dockerignore` (o contexto de build levava `.env`, `.venv` e fotos de `dados/`),
   PostgreSQL de desenvolvimento publicado em todas as interfaces com senha conhecida,
   `/saude` respondendo 200 com o banco fora, cabeçalho `server: uvicorn` exposto, imagem
   com ferramentas de teste, sem CI, sem lint, sem `DEPLOY.md`.
9. Dependências do aplicativo **desalinhadas com o SDK do Expo** (o próprio Expo avisa que
   "pode não funcionar corretamente").
10. **Build web com a URL da API errada**: gerar o site logo depois de um build com outra
    URL reaproveitava o cache do Metro e embutia a URL anterior.
11. **`docker compose up` não subia a aplicação**: não havia compose na raiz, o site
    ficava fora do Docker e o HTTPS dependia de montar um proxy à parte.

**O que foi feito.** 29 correções (seção C), uma funcionalidade de segurança completa
(senha e sessões, da API à tela), infraestrutura de produção (Dockerfile endurecido,
`docker-compose.yml` que sobe a aplicação inteira com HTTPS automático, migrations em
serviço próprio com trava, sondas de vida e
prontidão, logs JSON com identificador de requisição, backup), CI no GitHub Actions, lint
no aplicativo, 34 testes novos no servidor, 1 bateria de navegador nova, documentação de
implantação e este relatório.

**Situação final.** 567 testes do servidor passando (cobertura 93%), modelos e migrations
idênticos (`alembic check`), 0 erros de tipo e 0 erros de lint no aplicativo, testes de
unidade passando, 15 rodadas finais de baterias de navegador sem falha (588 verificações,
140 delas contra o build web de produção), imagem Docker construída e a pilha de produção
validada de ponta a ponta num ambiente local (subida, fumaça funcional,
resiliência, backup e restauração, rollback). A aplicação inteira (banco, API e site com
HTTPS) sobe com `docker compose up -d --build --wait`, verificado do build ao navegador.
A integração com a Replicate foi testada pelo responsável do projeto (informado por ele;
nesta sessão ela foi exercitada contra um servidor que imita o protocolo).
Classificação: **PRONTO PARA DEPLOY CONDICIONAL** (seção L): faltam o domínio com o DNS
apontado (a primeira emissão real do certificado) e, à parte, o build do aplicativo de
celular para as lojas.

---

## B. Arquitetura identificada

| Camada | Tecnologia | Observação |
| --- | --- | --- |
| Aplicativo | React Native 0.86, Expo SDK 57, expo-router, TypeScript estrito | Web (react-native-web) e celular; estado em Context + `useReducer`; tokens no SecureStore (web: AsyncStorage) |
| API | Python 3.11, FastAPI 0.142, Pydantic 2, SQLAlchemy 2.1 | rotas → serviços → consultas → modelos; erros num formato único `{erro: {codigo, mensagem, detalhes}}` |
| Banco | PostgreSQL 16, Alembic (12 migrations) | gatilhos de imutabilidade em termos e consentimentos, índices únicos parciais, `CHECK`s de coerência |
| Imagens | disco local ou S3/MinIO/Supabase | binário fora do banco; entrega por URL assinada (HMAC, 10 min) |
| Simulação | provedor `fake` (local, sem IA) ou Replicate (FLUX Kontext) | tarefa em segundo plano; o app consulta o estado (202 + polling) |
| Autenticação | JWT HS256 (acesso 30 min, renovação 30 dias) + versão da sessão por conta; bcrypt; Google (ID token) opcional | |
| Infra | Dockerfiles (API e site), `docker-compose.yml` da raiz (aplicação inteira, com Caddy e HTTPS automático), `backend/docker-compose.yml` (dev), `.github/workflows/ci.yml` | o aplicativo não roda em contêiner (site estático e builds de loja) |

**Entidades:** usuários, identidades externas (Google), clientes, termos (versionados),
consentimentos (só inserção), ciências, imagens, simulações, atendimentos, agendamentos.

**Funcionalidades reais × simuladas:** todas as telas falam com a API real; o único serviço
simulado por padrão é o provedor de IA (`AI_PROVIDER=fake`), que marca a imagem como
"simulação local, sem IA". O contrato entre aplicativo e API foi conferido
automaticamente: as 52 rotas chamadas pelo aplicativo existem no OpenAPI do servidor, com
o mesmo método.

**Decisões arquiteturais mantidas:** sem fila externa para as simulações (tarefa em
segundo plano + consulta, suficiente para o porte), consentimento como regra do servidor,
exclusão física (LGPD art. 18). **Decisões novas** estão em
[`docs/DECISOES_TECNICAS.md`](docs/DECISOES_TECNICAS.md), seções 8 a 14.

---

## C. Problemas encontrados e correções

Severidade: **Crítica**, **Alta**, **Média**, **Baixa**. "Validação" diz como a correção foi
comprovada; os testes do servidor citados falham no código original (30 dos 34 testes
novos falham nele; os 4 restantes são de compatibilidade e de controle, seção E).

| ID | Problema | Sev. | Causa | Impacto | Solução | Validação |
| --- | --- | --- | --- | --- | --- | --- |
| RV-01 | A suíte de testes apagaria o banco de `DATABASE_URL` exportado no terminal | Alta | `conftest.py` usava `setdefault(DATABASE_URL)` e a sessão de testes faz `downgrade base` + `TRUNCATE` | Perda total de dados de quem rodasse os testes com o terminal apontado para dev/produção | `TEST_DATABASE_URL` própria; `DATABASE_URL` herdada é ignorada; banco cujo nome não termina em `_test` é recusado | `test_testes_se_recusam_a_rodar_fora_de_um_banco_de_teste` |
| RV-02 | Build de produção do app sem `EXPO_PUBLIC_API_URL` chamava `http://<site>:8000` (web) e `http://espelho:8000` (celular) | Alta | descoberta do Metro aplicada também fora do desenvolvimento | App publicado sem conexão com o servidor | Produção web: mesma origem do site; produção nativa sem URL: erro explícito `servidor_nao_configurado`; desenvolvimento inalterado | Build web sem a variável (nenhuma referência a `localhost:8000`) e baterias contra ele (seção E, E2E-13) |
| RV-03 | URLs de imagem com host/esquema internos atrás de proxy | Alta | URL montada de `request.base_url` | Fotos não carregam em produção (conteúdo misto, ATS) | `URL_PUBLICA` (obrigatória em produção, https) | `test_url_da_imagem_usa_a_url_publica`; fumaça de produção (URL `https://api...`) |
| RV-04 | Migrations simultâneas quebravam | Alta | sem trava; o entrypoint migra a cada subida | Réplicas caindo na implantação | advisory lock em `migrations/env.py`; serviço `migrar` único no compose de produção | 3 processos simultâneos: antes 2 falhas `UniqueViolation`, depois 0 |
| RV-05 | Tokens não revogáveis; sem troca de senha | Alta | JWT sem estado | Token copiado valia 30 dias; senha vazada sem remédio | `usuarios.versao_sessao` + claim `sv`; `POST /usuarios/me/senha`; `DELETE /usuarios/me/sessoes`; tela "Senha e sessões" | 8 testes do servidor; bateria `seguranca.mjs` (13 verificações); fumaça de produção |
| RV-06 | Produção podia subir com banco de desenvolvimento, CORS `*` ou sem URL pública | Média | validação só de `MODO_DEMO` | Configuração insegura passando despercebida | Recusa na inicialização; avisos para escolhas arriscadas (provedor `fake`, origens http, storage local) | 6 testes de configuração; log de avisos no contêiner |
| RV-07 | Simulação presa em "processando" para sempre após reinício | Média | expiração só na inicialização, para as com mais de 5 min | Histórico com geração eterna; exclusão impossível (409) | Expiração por conta ao listar/consultar/excluir, num `UPDATE` atômico condicionado ao status | 2 testes |
| RV-08 | Freio de login atrás de proxy contava todos como um só endereço | Média | uvicorn sem confiar nos cabeçalhos do proxy | Um usuário bloqueava todos, ou o freio não freava | `--proxy-headers` + `FORWARDED_ALLOW_IPS` (porta só em 127.0.0.1) | Fumaça de produção: IP com 10 erros → 429; outro IP → 200 |
| RV-09 | Memória do freio de login crescia sem limite | Média | uma entrada por endereço, nunca removida | Consumo crescente; vetor de exaustão com muitos IPs | Remoção das entradas sem falha e faxina acima de 10 mil origens | 2 testes |
| RV-10 | Falha transitória na consulta da Replicate perdia geração já paga | Média | consulta e download sem nova tentativa | Crédito gasto sem resultado | Até 3 tentativas só nas leituras idempotentes (5xx, 429, rede); criação nunca repetida | 4 testes com o servidor que imita a Replicate (cenários novos) |
| RV-11 | Uma falha de rede durante a espera encerrava a espera no app | Média | qualquer erro saía do laço de consulta | "Falhou" na tela embora a simulação concluísse | Tolera 5 falhas de conexão seguidas; erros do servidor continuam encerrando | Tipos, lint e baterias de simulação; **sem teste dedicado** (pendência K-09) |
| RV-12 | S3/MinIO fora do ar respondia 500; falha parcial ao apagar ignorada; sem tempo limite | Média | exceções do botocore sem tratamento; `delete_objects` devolve erros no corpo | Erro genérico; fotos permaneciam no bucket após pedido de eliminação (LGPD) | `ErroDeArmazenamento` → 503; falha parcial levanta erro; tempos limite e retentativas do botocore | 3 testes |
| RV-13 | Foto de 50 MP decodificada inteira antes de checar o lado máximo | Média | conferência de dimensão depois do `convert` | ~150 MB de RAM por requisição | Dimensões lidas do cabeçalho antes de decodificar (foto e enquadramento) | Teste com espião do `convert` |
| RV-14 | Assinatura das imagens gravada no log de acesso | Média | log do uvicorn escreve a query | Credencial de acesso à foto exposta a quem lê logs | Log de acesso da aplicação, sem query; `--no-access-log` | Teste; contêiner: 0 ocorrências de `?t=` nos logs |
| RV-15 | `/saude` respondia 200 com o banco fora | Média | sem código de status | Balanceador mandaria tráfego para instância quebrada | `/saude` 503 quando não pronta; `/saude/vivo` para vida | 3 testes; contêiner com o banco parado: 503/200 |
| RV-16 | Dependências do app desalinhadas com o SDK 57 | Média | versões abaixo das esperadas (`expo-camera`, `expo-image-manipulator`, `expo-image-picker`, `expo-router`) | Comportamento nativo imprevisível | `npx expo install --fix` (só patches do SDK 57; `datetimepicker` na versão do SDK e plugin registrado) | `expo install --check`: "Dependencies are up to date"; tipos, lint, unidade e 11 baterias |
| RV-17 | Contexto de build Docker levava `.env`, `.venv` e `dados/` (fotos) | Média | sem `.dockerignore` | Segredos e dados pessoais enviados ao daemon/cache de build | `.dockerignore` | Inspeção da imagem: só `app`, `migrations`, `alembic.ini`, `entrypoint.sh` |
| RV-18 | Compose de desenvolvimento publicava o PostgreSQL em todas as interfaces com senha conhecida | Média | `ports: 5432:5432` | Banco exposto na rede local | Publicado só em `127.0.0.1`; `JWT_SECRET` exigido com mensagem | Compose de desenvolvimento subido e testado |
| RV-19 | Sem configuração de produção para o Docker | Média | só existia o compose de desenvolvimento (com `MODO_DEMO=true`) | Implantação improvisada | Compose de produção (hoje `docker-compose.yml` da raiz, ver RV-29): banco sem porta, segredos obrigatórios, migrations à parte, `read_only`, `cap_drop`, `no-new-privileges`, healthcheck de prontidão, encerramento de 160 s, rotação de logs | Subida real, fumaça (14/14), resiliência, backup/restauração e rollback (seção F) |
| RV-20 | Cabeçalho `server: uvicorn` junto do `server: espelho` | Baixa | uvicorn acrescenta o próprio | Anuncia o servidor em uso | `--no-server-header` | `curl -I` no contêiner: um só `server` (achado só no contêiner) |
| RV-21 | Duas linhas de log do Alembic a cada sonda de prontidão | Baixa | `MigrationContext` em nível INFO | Log poluído a cada 15 s | Logger do Alembic em WARNING na API; versão do código lida uma vez | Logs do contêiner: 0 linhas |
| RV-22 | Faltavam índices em consultas por conta e chaves estrangeiras | Baixa | o PostgreSQL não indexa FK sozinho | Varredura completa na cota de simulações, no histórico da conta e nas exclusões em cascata | Migration `f3a8d6e2b571` (7 índices) | `alembic check` sem diferença |
| RV-23 | Imagem de produção com `pytest`, Debian não fixado, sem `HEALTHCHECK`, código gravável pelo processo | Baixa | Dockerfile de desenvolvimento | Imagem maior, build frágil a troca do Debian | `requirements-dev.txt`; `python:3.11-slim-bookworm`; `HEALTHCHECK`; código do root, só `dados/` do usuário 1000 | Inspeção da imagem |
| RV-24 | Pool de conexões sem configuração | Baixa | padrões do SQLAlchemy | Conexões ociosas derrubadas por firewalls | `BANCO_POOL*`, `pool_recycle=1800` | Suíte e pilha de produção |
| RV-25 | Sem lint no aplicativo; 1 reatribuição de propriedade | Baixa | ESLint nunca configurado | Regras de hooks não verificadas | ESLint do Expo (flat config); correção; 2 regras do React Compiler como aviso (justificado) | `npx eslint .`: 0 erros |
| RV-26 | Sem CI | Baixa | — | Regressões só descobertas à mão | GitHub Actions: backend, aplicativo, imagem + compose de produção | `actionlint` 1.7.12 sem apontamentos; comandos executados localmente; **não executado no GitHub** |
| RV-27 | Documentação desatualizada ou dispersa | Baixa | 9 relatórios na raiz; README afirmava teto de simulações em memória (é no banco) | Instruções erradas | README, `DEPLOY.md`, `.env.example`, `backend/README.md`, decisões técnicas; relatórios antigos em `docs/historico/` | Revisão manual dos links |
| RV-28 | Build web com a URL da API **de um build anterior** | Alta | o Metro guarda em cache os módulos já com as `EXPO_PUBLIC_*` embutidas; `expo export` sem `--clear` reaproveita | Site publicado chamando o servidor errado (ex.: o de homologação) | `npm run build:web` sempre com `--clear`; CI e `DEPLOY.md` usam o script | Reproduzido (build com URL B saiu com a URL A); com `--clear`, sai a URL pedida; `qa-interface` no build corrigido: 44/0 |
| RV-29 | `docker compose up` não subia a aplicação | Alta | não havia `docker-compose.yml` na raiz (o comando nem encontrava configuração); o site ficava fora do Docker; o compose de produção exigia montar um proxy com HTTPS à parte | Deploy dependia de montagem manual de proxy, certificado e site | `docker-compose.yml` na raiz com o serviço `web` (Caddy): site compilado dentro do Docker, `/api/` encaminhado, HTTPS automático (Let's Encrypt), API e banco sem porta publicada; `URL_PUBLICA`/`CORS_ORIGENS` derivadas de `DOMINIO` | `docker compose build --no-cache` e `up --wait` (4 serviços prontos); site, rotas internas, API e cabeçalhos pelo HTTPS; fumaça 12/12; baterias 29/0 e 13/0 pelo HTTPS; dados e certificado mantidos ao recriar (T-42 a T-49) |

Achado no ambiente de verificação, não no projeto: o Metro deste contêiner não percebe
alterações de arquivo (o bundle servido continuava com o código antigo). Foi descoberto
durante a verificação da tela nova e contornado reiniciando o Metro antes de cada rodada;
a rodada final de baterias foi feita com o bundle conferido.

---

## D. Arquivos alterados

**Criados**

| Arquivo | Por quê |
| --- | --- |
| `DEPLOY.md`, `.env.example`, `RELATORIO_REVISAO_E_DEPLOY.md` | Implantação, variáveis de produção e este relatório |
| `docker-compose.yml` (raiz) | A aplicação inteira: banco, migrações, API e site com HTTPS (RV-19, RV-29) |
| `espelho/Dockerfile`, `espelho/Caddyfile`, `espelho/.dockerignore` | Site compilado no Docker e servido pelo Caddy, que encaminha `/api/` e cuida do HTTPS (RV-29) |
| `.gitattributes` | Fim de linha LF nos scripts e arquivos usados nos contêineres (clones no Windows não quebram o `entrypoint.sh`) |
| `.github/workflows/ci.yml` | CI (RV-26) |
| `scripts/backup_producao.sh` | Backup do banco e das imagens, com conferência do dump |
| `backend/.dockerignore`, `backend/requirements-dev.txt` | RV-17, RV-23 |
| `backend/app/core/registro.py` | Logs (texto/JSON) com identificador da requisição |
| `backend/migrations/versions/e1b4c7d29a50_versao_da_sessao.py` | RV-05 |
| `backend/migrations/versions/f3a8d6e2b571_indices_de_desempenho.py` | RV-22 |
| `backend/tests/test_producao_e_operacao.py` | 30 testes de regressão desta revisão |
| `espelho/app/seguranca.tsx` | Tela "Senha e sessões" (RV-05) |
| `espelho/e2e/seguranca.mjs` | Bateria de navegador da tela nova |
| `espelho/eslint.config.js` | RV-25 |

**Modificados (principais)**

| Arquivo | Mudança |
| --- | --- |
| `backend/app/core/config.py` | `URL_PUBLICA`, logs, pool; recusas e avisos de produção (RV-03, RV-06) |
| `backend/app/main.py` | Middleware de identificação e log de acesso; sondas de vida/prontidão; 503 de storage (RV-14, RV-15, RV-12) |
| `backend/app/core/security.py`, `dependencies.py`, `services/auth.py`, `api/v1/usuarios.py`, `schemas/auth.py`, `models/usuario.py` | Versão da sessão, troca de senha, sair de todos (RV-05) |
| `backend/app/core/protecoes.py` | Faxina do freio, rota de senha limitada (RV-09) |
| `backend/app/services/storage/*.py` | `ErroDeArmazenamento`, tempos limite, falha parcial (RV-12) |
| `backend/app/services/ai/replicate.py` | Leituras repetidas (RV-10) |
| `backend/app/services/simulacao.py`, `api/v1/simulacoes.py`, `api/v1/clientes.py` | Expiração das presas (RV-07) |
| `backend/app/services/validacao_foto.py` | Recusa pelo cabeçalho (RV-13) |
| `backend/app/services/imagens.py` | URL pública (RV-03) |
| `backend/app/db/session.py`, `db/versao.py`, `models/*.py` | Pool; versão do código em cache; índices declarados |
| `backend/migrations/env.py` | Trava das migrations (RV-04) |
| `backend/Dockerfile`, `entrypoint.sh`, `docker-compose.yml`, `requirements.txt`, `.env.example` | RV-17, RV-18, RV-20, RV-23 |
| `backend/tests/conftest.py` | RV-01 |
| `backend/tests/mock_provedor_ia.py`, `test_simulacao_com_mock_ia.py` | 3 cenários e 4 testes de leituras instáveis |
| `backend/tests/test_auditoria_regressao.py`, `test_seguranca_aplicacao.py` | `URL_PUBLICA` nos testes que montam produção (exigência nova; o que verificam não mudou) |
| `espelho/src/services/api/cliente.ts`, `api/index.ts`, `src/data/store.tsx` | RV-02, RV-11, chamadas de senha e sessões |
| `espelho/app/(tabs)/perfil.tsx`, `src/components/Basicos.tsx` | Entrada "Senha e sessões"; correção do lint |
| `espelho/package.json`, `package-lock.json`, `app.json` | SDK alinhado (RV-16), ESLint, scripts `lint` e `build:web` |
| `espelho/e2e/visual-contraste.mjs` | Tela nova na bateria de contraste |
| `qa.sh` | Lint, `alembic check`, bateria nova, `pip-audit -r requirements.txt` |
| `README.md`, `backend/README.md`, `docs/DECISOES_TECNICAS.md`, `espelho/e2e/README.md`, `espelho/.env.example`, `.gitignore` | Documentação (RV-27); `.gitignore` cobre `.env.*` e backups |

**Movidos (sem alteração de conteúdo, só links):** `DOCUMENTACAO*.md` para `docs/`; os seis
relatórios de etapas anteriores para `docs/historico/`. **Removidos:** nenhum.

---

## E. Testes realizados

| ID | Teste | Comando ou método | Resultado | Evidência ou observação |
| --- | --- | --- | --- | --- |
| T-01 | Linha de base do servidor (código original) | `pytest` (PostgreSQL real) | PASSOU | 533 aprovados, 0 falhas, 4min23s |
| T-02 | Linha de base do app: tipos | `tsc --noEmit --noUnusedLocals` | PASSOU | 0 erros |
| T-03 | Linha de base do app: testes de unidade | `node testes/*.mjs` (2 fusos nas datas) | PASSOU | 150 verificações, 0 falhas |
| T-04 | Linha de base: 10 baterias de navegador (código original) | Playwright/Chromium contra API + `expo start --web` | PASSOU | 0 falhas em todas; contraste: 0 textos abaixo do mínimo, 0 telas com rolagem horizontal |
| T-05 | Contrato app × API | script que cruza as chamadas de `src/services/api/index.ts` com o OpenAPI | PASSOU | 52 rotas usadas, 0 inexistentes |
| T-06 | Modelos × migrations | `alembic check` | PASSOU | "No new upgrade operations detected" (antes e depois das migrations novas) |
| T-07 | Downgrade/upgrade completo | sessão de testes (`downgrade base` → `upgrade head`) | PASSOU | executado em toda rodada do pytest |
| T-08 | Suíte final do servidor | `pytest --cov=app` | PASSOU | 567 aprovados, 0 falhas, cobertura 93%, 5min17s |
| T-09 | Testes novos contra o código original | os 34 testes novos rodando sobre a cópia original | PASSOU | 30 falham no original (defeitos reais); 4 passam por serem de compatibilidade/controle |
| T-10 | Migrations concorrentes | 3 × `alembic upgrade head` simultâneos num banco vazio | PASSOU | com trava: 1 aplicou 12, 2 esperaram, 0 erros; sem trava (original): 2 `UniqueViolation` |
| T-11 | Auditoria de dependências Python | `pip-audit -r requirements.txt` | PASSOU | "No known vulnerabilities found" |
| T-12 | Auditoria de dependências do app | `npm audit --omit=dev` | FALHOU | 12 avisos (6 altos, 6 baixos), 0 críticos; antes 16. Análise na seção H e pendência K-05 |
| T-13 | Tipos do app (final) | `tsc --noEmit --noUnusedLocals` | PASSOU | 0 erros |
| T-14 | Lint do app | `npx eslint .` | PASSOU | 0 erros, 18 avisos (regras do React Compiler, rebaixadas com justificativa) |
| T-15 | Testes de unidade do app (final) | os mesmos de T-03 | PASSOU | 150 verificações, 0 falhas |
| T-16 | Alinhamento com o SDK | `npx expo install --check` | PASSOU | "Dependencies are up to date" (no original: 4 desatualizadas) |
| T-17 | Build web de produção | `npm run build:web` | PASSOU | bundle de 1,6 MB; nenhum segredo (só nomes de variáveis em textos de ajuda); código de desenvolvimento (`localhost:8000`) eliminado do pacote sem a variável |
| T-18 | Textos sem travessão | `scripts/verificar_travessoes.py` | PASSOU | 0 ocorrências |
| T-19 | Build da imagem Docker | `docker build --secret id=ca,...` | PASSOU | usuário 1000, código só leitura, sem `pytest`, sem `.env`, OpenCV 4.14 importa |
| T-20 | Compose de produção (versão só com banco e API, antes do RV-29): subida | `docker compose up -d --wait` | PASSOU | `db` saudável → `migrar` (12 migrations, exit 0) → `api` saudável |
| T-21 | Produção: cabeçalhos e superfície | `curl` | PASSOU | HSTS presente, `/docs` e `/openapi.json` 404, `/saude` só `{ok, ambiente}`, um cabeçalho `server` |
| T-22 | Produção: fumaça funcional | script com 14 verificações (cadastro, cliente, consentimento, foto, simulação, troca de senha, freio por IP real, exclusão da conta) | PASSOU | 14/14 |
| T-23 | Produção: logs | `docker logs` | PASSOU | JSON por linha com `requisicao`; 0 assinaturas `?t=`; avisos de produção presentes |
| T-24 | Produção: queda do processo | SIGTERM no PID 1 do contêiner | PASSOU | reiniciado (`RestartCount=1`), saudável |
| T-25 | Produção: banco fora do ar | `compose stop db` | PASSOU | prontidão 503, vida 200; com o banco de volta, 200 sem reiniciar a API |
| T-26 | Produção: persistência | `compose down` (sem `-v`) e `up` | PASSOU | conta criada antes entra depois; `migrar` sem migration nova |
| T-27 | Backup | `scripts/backup_producao.sh` | PASSOU | dump + tar gerados, dump conferido com `pg_restore --list` |
| T-28 | Restauração em banco separado | `pg_restore` em `espelho_restauracao` | PASSOU | contagens idênticas em 7 tabelas; versão `f3a8d6e2b571`; 3 gatilhos; 3 imagens no tar = 3 no volume |
| T-29 | Restauração por cima (procedimento do DEPLOY.md) | `dropdb`/`createdb`/`pg_restore` + tar, na pilha de teste | PASSOU | usuário criado depois do backup sumiu (3 → 2); conta do backup entra. O passo "esvaziar o volume de imagens" **não foi executado** (bloqueado pela proteção contra remoções do ambiente) |
| T-30 | Rollback do código | `VERSAO=anterior up -d --no-build api` e volta | PASSOU | contêiner trocou de imagem e ficou saudável nas duas direções |
| T-31 | Código anterior sobre o banco migrado | API original (do ZIP) contra banco com as migrations novas | PASSOU | 7/7 (cadastro, renovação, consentimento, simulação, histórico, exclusão); 0 tracebacks |
| T-32 | Compose de desenvolvimento | `backend/docker-compose.yml` | PASSOU | migrations + seed + modo demo; sem `JWT_SECRET`, a interpolação falha com a mensagem |
| T-33 | Workflow da CI | `actionlint .github/workflows/ci.yml`; fumaça `up -d --wait` com `.env` gerado, localmente | PASSOU | 0 apontamentos; o workflow em si **não rodou no GitHub** (sem push) |
| T-34 | Build sem a CA (caminho fora deste ambiente) | `docker build --no-cache` sem `--secret` | PASSOU | o passo roda normalmente e o `pip` usa os certificados públicos (aqui falha só pelo proxy deste ambiente, como esperado). Primeira tentativa bloqueada por 429 do Docker Hub |
| T-35 | Bateria nova `seguranca.mjs` | Playwright | PASSOU | 13/13 |
| T-41 | Verificação completa, um comando | `./qa.sh` (código final) | PASSOU | exit 0: 567 testes (93%), `alembic check` sem diferenças, tipos 0 erros, lint 0 erros, unidade 150/150, 0 travessões |
| T-42 | Compose da raiz: build do zero | `docker compose build --no-cache` (CA deste ambiente por override) | PASSOU | imagens da API e do site construídas (site: 86 MB) |
| T-43 | Compose da raiz: subida | `docker compose up -d --wait` com `DOMINIO=localhost` | PASSOU | `db` → `migrar` (exit 0) → `api` → `web`, todos saudáveis |
| T-44 | Site e API pelo HTTPS do Caddy | `curl --cacert` (CA local do Caddy) | PASSOU | site 200; rota interna 200 (fallback); HTTP → HTTPS 308; `/api/v1/saude` 200; HSTS; sem cabeçalho `Server`; pacotes com cache imutável, `index.html` sem cache |
| T-45 | Fumaça funcional pelo Caddy | script de fumaça | PASSOU | 12/12 (cadastro, foto, URL pública `https://localhost/...`, simulação, troca de senha, exclusão da conta) |
| T-46 | Freio de login atrás do Caddy | `X-Forwarded-For` forjado e origem real diferente | PASSOU | forjado: 429 (o Caddy descarta o cabeçalho do cliente); outro endereço real: 200 |
| T-47 | Baterias de navegador pelo HTTPS (modo produção) | `auditoria.mjs`, `seguranca.mjs` com `APP_URL=https://localhost` | PASSOU | 29/0 e 13/0 |
| T-48 | Persistência ao recriar | `docker compose down` e `up` | PASSOU | contas mantidas; mesmo certificado |
| T-49 | Backup com o compose novo | `scripts/backup_producao.sh` | PASSOU | dump + tar gerados e conferidos |
| E2E | Regressão final das 11 baterias | ver tabela abaixo | ver abaixo | |
| T-36 | Provedor de IA real (Replicate) | — | BLOQUEADO nesta sessão | sem credencial aqui. **Testado pelo responsável do projeto** (informado por ele, não verificado nesta sessão); aqui, exercitado contra servidor que imita o protocolo |
| T-37 | Login com Google real | — | BLOQUEADO | sem credenciais OAuth; `google.mjs` não executada |
| T-38 | Aparelho físico / build de loja | — | BLOQUEADO | sem aparelho e sem conta EAS |
| T-39 | HTTPS com certificado público | — | NÃO EXECUTADO | sem domínio. O HTTPS do Caddy foi testado com a CA local dele (T-44); a emissão pelo Let's Encrypt depende do DNS apontado |
| T-40 | CI no GitHub | — | NÃO EXECUTADO | nada foi enviado ao repositório remoto |

**Baterias de navegador, rodada final** (código final, bundle conferido):

| Bateria | Alvo | Verificações | Falhas | Observação |
| --- | --- | ---: | ---: | --- |
| `fluxo-completo` | desenvolvimento (Metro) | 54 | 0 | 0 erros de console |
| `qa-interface` | desenvolvimento | 44 | 0 | 390/768/1280 px, teclado, alvos de toque, API derrubada |
| `mudancas-interface` | desenvolvimento | 42 | 0 | |
| `agenda` | desenvolvimento | 27 | 0 | |
| `atendimentos` | desenvolvimento | 49 | 0 | |
| `painel-e-comparacao` | desenvolvimento | 48 | 0 | |
| `fotos-e-camera` | desenvolvimento | 28 | 0 | |
| `personalizacao` | desenvolvimento | 66 | 0 | |
| `visual-contraste` | desenvolvimento | 48 | 0 | 24 telas × 2 larguras; 0 textos abaixo do contraste, 0 rolagens horizontais |
| `auditoria` | desenvolvimento | 29 | 0 | |
| `seguranca` (nova) | desenvolvimento | 13 | 0 | |
| **Subtotal** | | **448** | **0** | |
| `fluxo-completo` | **build de produção**, domínio único (site + `/api` no mesmo endereço) | 54 | 0 | sem `EXPO_PUBLIC_API_URL`: a API pela própria origem (RV-02) |
| `auditoria` | build de produção, domínio único | 29 | 0 | abre rotas internas direto: exercita o fallback de SPA |
| `seguranca` | build de produção, domínio único | 13 | 0 | |
| `qa-interface` | **build de produção**, dois domínios (`EXPO_PUBLIC_API_URL`) | 44 | 0 | primeira tentativa: 2 falhas, causadas pelo cache de build (RV-28); depois da correção, 0 |
| **Total** | | **588** | **0** | `google.mjs` não executada (T-37) |

---

## F. Build e inicialização

| Etapa | Comando | Resultado |
| --- | --- | --- |
| Dependências Python | `pip install -r requirements-dev.txt` (Python 3.11) | ok |
| Dependências Node | `npm ci` | ok |
| Testes do servidor | `pytest --cov=app` | 567 aprovados, 93% |
| Migrations × modelos | `alembic check` | sem diferenças |
| Tipos | `tsc --noEmit --noUnusedLocals` | 0 erros |
| Lint | `npx eslint .` | 0 erros, 18 avisos |
| Build web | `npm run build:web` (`expo export --platform web --clear`) | bundle de 1,6 MB; a URL embutida conferida no pacote |
| Imagem | `docker build` | 789 MB (OpenCV, numpy, boto3) |
| Subida da aplicação | `docker compose up -d --build --wait` (raiz) | 4 serviços prontos; site e API pelo HTTPS |
| Subida de desenvolvimento | `docker compose up` em `backend/` | api saudável, seed criado |

A API recusa subir sem `JWT_SECRET` (32+), e em produção sem `URL_PUBLICA` https, com o
banco de desenvolvimento, com `MODO_DEMO=true` ou com `CORS_ORIGENS=*`.

---

## G. Banco de dados

**Alterações de esquema** (duas migrations, ambas aditivas e reversíveis):

- `e1b4c7d29a50` — `usuarios.versao_sessao INTEGER NOT NULL DEFAULT 0`. Linhas existentes
  ficam com 0; tokens antigos (sem `sv`) valem como 0. Volta: remove a coluna.
- `f3a8d6e2b571` — 7 índices: `simulacoes (usuario_id, criado_em)`, `(img_entrada_id)`,
  `(img_saida_id)`, `atendimentos (usuario_id, data_servico)`, `(simulacao_id)`,
  `agendamentos (cliente_id)`, `imagens (usuario_id)`. Volta: remove os índices.

**Persistência e integridade:** a suíte do servidor roda em PostgreSQL real com os
gatilhos; a pilha de produção manteve os dados entre `down`/`up`; backup e restauração
foram conferidos por contagem (T-27 a T-29).

**Riscos de compatibilidade:** o código anterior funciona com o banco migrado (T-31), então
o rollback do código não exige rollback do esquema. `CREATE INDEX` segura as gravações da
tabela enquanto roda (segundos no porte atual; em tabelas grandes, usar `CONCURRENTLY`
numa migration futura). A trava das migrations usa a chave fixa `7342195001` de
`pg_advisory_lock`; outro sistema no mesmo banco não pode usar a mesma chave.

---

## H. Segurança

**Verificado:** isolamento entre contas (suíte existente, 23+ rotas), consentimento como
controle de acesso, segredos fora do código e do Git (varredura de padrões de chave: nada),
chave do provedor nunca no app (bundle conferido), cabeçalhos de segurança, CORS, documentação
fechada em produção, mensagens de erro sem detalhe interno, validação de imagem (formato
real, bomba de descompressão, agora também dimensão pelo cabeçalho), limites de corpo,
freio de tentativas (agora também na troca de senha e com o IP real atrás do proxy),
revogação de sessões, logs sem credenciais, contêiner sem privilégios.

**Corrigido nesta revisão:** RV-01, RV-03, RV-05, RV-06, RV-08, RV-09, RV-12 (eliminação
parcial no bucket), RV-13, RV-14, RV-17, RV-18, RV-20.

**Dependências:** Python sem vulnerabilidades conhecidas. Node (`npm audit --omit=dev`):
12 avisos, 0 críticos. Quase todos estão nas ferramentas de build do Expo (`@expo/cli`,
`@expo/config`, `zod` e `deepmerge` usados pela CLI), que não entram no pacote do aplicativo.
O único em código que entra no pacote é `decode-uri-component` (via `query-string` do
`expo-router`): negação de serviço ao decodificar um endereço malformado, no aparelho de quem
abre o link. A correção exige o `expo-router` 58 (próximo SDK). A CI bloqueia só avisos
críticos.

**Riscos residuais:** ver pendências K-01 a K-12. Em destaque: recuperação de senha por
e-mail inexistente; freio de login em memória por processo; tokens na web guardados no
`localStorage` (risco de XSS; não há CSP definida para o site); URL de imagem é credencial
portadora por 10 minutos (limitação do `<Image>` do React Native).

**LGPD (sem afirmar conformidade jurídica):** consentimento versionado e imutável,
exigência de responsável para menores, exclusão física de imagens, de cliente e de conta,
minimização (EXIF removido), fotos fora de URL pública, backups com aviso de dados
pessoais. Falta uma revisão jurídica, a política de retenção dos backups e um meio de
exportar os dados de um cliente (portabilidade, art. 18, V).

---

## I. Configuração de produção

Variáveis: [`.env.example`](.env.example) (produção, com descrições) e
`backend/.env.example` (desenvolvimento). Obrigatórias: `DOMINIO`, `POSTGRES_PASSWORD` e
`JWT_SECRET`; para a simulação real, `AI_PROVIDER=replicate` e `AI_API_KEY`. `URL_PUBLICA`
e `CORS_ORIGENS` derivam de `DOMINIO`. Componentes (todos no `docker-compose.yml` da raiz):
`db`, `migrar` (uma execução por subida), `api` e `web` (Caddy: site, `/api/` e HTTPS).
Fora do Docker: os builds de loja do aplicativo. Integrações opcionais: Google OAuth
(`GOOGLE_CLIENT_IDS` + `EXPO_PUBLIC_GOOGLE_*`) e S3 (`STORAGE_*`).

## J. Processo de deploy

Preparado e documentado em [`DEPLOY.md`](DEPLOY.md): servidor com Docker, DNS do domínio
apontado, portas 80/443, `.env` e `docker compose up -d --build --wait`; conferência
pós-deploy; atualização com backup prévio e etiqueta de versão; backup diário,
restauração e rollback (código por etiqueta; esquema compatível com a versão anterior);
build do aplicativo de celular pelo EAS. Partes que dependem de escolhas externas estão
marcadas como **[decisão externa]**. Nenhum deploy real foi feito e nenhuma
infraestrutura externa foi tocada.

---

## K. Pendências

| ID | Pendência | Sev. | Impacto | Por que ficou | Próxima ação |
| --- | --- | --- | --- | --- | --- |
| K-01 | Provedor de IA real não verificado **nesta sessão** | Baixa | testado pelo responsável do projeto (informado); aqui só contra o servidor que imita a Replicate | sem credencial nesta sessão | Depois do deploy: `docker compose exec api python -m app.diagnostico_ia` e uma simulação real |
| K-02 | Aplicativo nativo sem build de loja e sem teste em aparelho | Alta | envio de foto no celular (FormData do SDK 57) nunca visto num aparelho; sem `eas.json` | sem conta EAS e sem aparelho | `eas build:configure`, build de homologação com `EXPO_PUBLIC_API_URL` https, roteiro de fumaça no aparelho |
| K-03 | Primeira emissão real do certificado | Média | HTTPS automático pelo Caddy testado com certificado local; o do Let's Encrypt depende do DNS | sem domínio nesta sessão | Apontar o DNS, subir e conferir (`DEPLOY.md` §5) |
| K-04 | Login com Google real | Média | implementado e testado com tokens forjados | sem credenciais OAuth | `docs/GUIA_LOGIN_GOOGLE.md` e `e2e/google.mjs` |
| K-05 | 12 avisos do `npm audit` (6 altos) | Média | ferramentas de build e `decode-uri-component` no `expo-router` | correção exige o SDK 58 | Atualizar o SDK do Expo e repetir as baterias |
| K-06 | Recuperação de senha por e-mail | Média | quem esquece a senha perde o acesso | exige provedor de e-mail | Escolher provedor e implementar fluxo com token de uso único |
| K-07 | Freio de login em memória, por processo | Baixa | com várias instâncias, cada uma conta em separado | depende da topologia | Limite no proxy de borda ou Redis |
| K-08 | CI não executada no GitHub | Baixa | o workflow só foi validado por partes, localmente | nada foi enviado ao remoto | Enviar a branch e acompanhar a primeira execução |
| K-09 | Tolerância de rede na espera da simulação sem teste dedicado | Baixa | coberta só por tipos e baterias gerais | exige simular queda de rede no meio do polling | Bateria com `page.route` derrubando consultas |
| K-10 | (resolvida) Build sem a CA | — | verificado em T-34 | — | — |
| K-11 | Destino e retenção de backups, monitoramento | Média | backup só local sem destino externo | decisão de infraestrutura | Definir destino criptografado e verificador externo de `/api/v1/saude` |
| K-12 | Exportação dos dados de um cliente, CSP no site, paginação, avisos de lint do React Compiler, espaços nas pontas da senha | Baixa | melhorias conhecidas | fora do escopo seguro desta revisão | Planejar em versões seguintes |

---

## L. Classificação final de prontidão

### **PRONTO PARA DEPLOY CONDICIONAL**

**Por quê:** as verificações técnicas foram satisfatórias — 567 testes do servidor,
migrations idênticas aos modelos, tipos e lint, 11 baterias de navegador (4 também contra o
build web de produção), e a aplicação inteira subindo pelo `docker compose` do zero:
build, subida ordenada, site e API pelo HTTPS do Caddy, fumaça funcional, baterias de
navegador em modo produção, resiliência, persistência, backup e restauração, rollback. A
integração com a Replicate, que era a principal lacuna, foi testada pelo responsável do
projeto.

**Condições** (externas ou operacionais, documentadas):

1. um domínio com o DNS apontado para o servidor e as portas 80/443 abertas, e a
   conferência da primeira emissão do certificado (K-03);
2. o destino externo dos backups e um monitor de `/api/v1/saude` (K-11);
3. à parte do deploy do site e da API: o build do aplicativo de celular para as lojas e o
   teste num aparelho (K-02), antes de distribuir o app.

**Para "pronto para produção no escopo validado":** cumprir as condições 1 e 2 e repetir a
conferência do `DEPLOY.md` §5 no servidor. Nenhum defeito conhecido de código bloqueia.
