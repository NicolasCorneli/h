# Salão em Dia

Aplicativo para profissionais de beleza: carteira de clientes, agenda, histórico de
atendimentos e simulação capilar por IA, com o consentimento de imagem de cada cliente
(LGPD) como regra do servidor. Projeto do TCC *Aplicativo Mobile com Inteligência
Artificial para Simulação Capilar e Gestão de Clientes em Serviços de Beleza* (Sistemas de
Informação, Faculdade Antônio Meneghetti).

O nome interno do aplicativo e de alguns identificadores (pasta `espelho/`, banco
`espelho`) é **Espelho**, o nome do protótipo.

## Arquitetura

```
 celular (Expo / React Native) ─┐
                                 ├─ HTTPS ─▶ Caddy (site + /api) ─▶ API FastAPI ─▶ PostgreSQL 16
 navegador (site estático, web) ─┘                                      │
                                                                        ├─▶ imagens: volume local ou S3/MinIO
                                                                        └─▶ simulação: provedor local (fake) ou Replicate
```

| Parte | Pasta | Tecnologia |
| --- | --- | --- |
| Aplicativo (celular e navegador) | [`espelho/`](espelho) | React Native 0.86, Expo SDK 57, expo-router, TypeScript estrito |
| API | [`backend/`](backend) | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 |
| Imagens | disco (volume) ou S3/MinIO/Supabase | servidas só por URL assinada de 10 minutos |
| Simulação | `fake` (local, sem custo, sem IA) ou Replicate (`flux-kontext-apps/change-haircut`) | a chave fica só no servidor |
| Autenticação | JWT (acesso 30 min, renovação 30 dias) com revogação por conta; bcrypt; Google opcional | |
| Infraestrutura | Docker, `docker-compose.yml` (aplicação inteira: banco, API e site com HTTPS), GitHub Actions (`.github/workflows/ci.yml`) | |

Camadas da API: rotas (`app/api/v1`) → serviços (`app/services`) → consultas
(`app/repositories`) → modelos (`app/models`). Toda consulta a dado de cliente filtra pelo
profissional autenticado; o consentimento é imutável e versionado no banco (gatilhos).
Detalhes: [`docs/DOCUMENTACAO-BACKEND.md`](docs/DOCUMENTACAO-BACKEND.md) e
[`docs/DECISOES_TECNICAS.md`](docs/DECISOES_TECNICAS.md).

## Pré-requisitos

- Python 3.11 (o mesmo da imagem Docker) e PostgreSQL 16, ou Docker com Compose v2;
- Node 22 e npm;
- para as baterias de navegador: Chromium (Playwright).

## Desenvolvimento local

```bash
# Banco (uma vez)
createuser -P espelho                # senha: espelho (ou ajuste DATABASE_URL)
createdb -O espelho espelho
createdb -O espelho espelho_test     # usado só pelos testes, que o apagam a cada execução

# API
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt  # execução + ferramentas de teste
cp .env.example .env                 # preencha JWT_SECRET (32+ caracteres)
alembic upgrade head                 # cria/atualiza o banco
python -m app.seed                   # contas de demonstração (recusado em produção)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Aplicativo, em outro terminal
cd espelho
npm ci
npx expo start --web                 # ou `npx expo start` para o celular (Expo Go)
```

Com Docker, a API e o banco de desenvolvimento sobem com `docker compose up --build`
dentro de `backend/` (migrations e dados de demonstração automáticos). Contas de
demonstração e todas as variáveis: [`backend/README.md`](backend/README.md).

### Banco de dados e migrations

O banco nasce e evolui só pelas migrations do Alembic (`backend/migrations/versions`);
nenhum `create_all()`. `alembic upgrade head` aplica o que falta e é seguro com várias
instâncias ao mesmo tempo (trava no banco). `alembic check` confere se os modelos e as
migrations coincidem (roda no `qa.sh` e na CI).

## Testes

```bash
./qa.sh              # API (pytest com PostgreSQL real e cobertura), migrations x modelos,
                     # tipos e lint do app, testes de unidade, busca de travessões
./qa.sh --interface  # + 11 baterias de navegador (API e `expo start --web` no ar)
./qa.sh --tudo       # + auditoria de dependências (pip-audit e npm audit)
```

Os testes da API usam o banco de `TEST_DATABASE_URL` (padrão `espelho_test`) e se recusam a
rodar num banco cujo nome não termine em `_test`, porque o apagam a cada execução.
A integração com a Replicate é testada contra um servidor que imita o protocolo dela
(`backend/tests/mock_provedor_ia.py`), sem custo. Detalhes em
[`backend/README.md`](backend/README.md#testes) e
[`espelho/e2e/README.md`](espelho/e2e/README.md).

## Produção com Docker

A aplicação inteira (banco, migrações, API e site com HTTPS automático) sobe pelo
`docker-compose.yml` da raiz:

```bash
cp .env.example .env      # preencha DOMINIO, POSTGRES_PASSWORD, JWT_SECRET (e a Replicate)
docker compose up -d --build --wait
```

O site fica em `https://DOMINIO` e a API em `https://DOMINIO/api`. Para testar na própria
máquina, use `DOMINIO=localhost` (certificado local; o navegador avisa). O aplicativo de
celular é gerado pelo EAS Build com `EXPO_PUBLIC_API_URL=https://DOMINIO`. Passo a passo,
backup e rollback: [`DEPLOY.md`](DEPLOY.md).

## Integrações externas

| Serviço | Para quê | Sem ele |
| --- | --- | --- |
| Replicate (`AI_PROVIDER=replicate`, `AI_API_KEY`) | gerar a simulação | o provedor `fake` gera uma imagem recolorida com o aviso "simulação local, sem IA" |
| Google OAuth (`GOOGLE_CLIENT_IDS`, `EXPO_PUBLIC_GOOGLE_*`) | "Entrar com Google" | o botão não aparece; e-mail e senha seguem funcionando |
| S3/MinIO/Supabase (`STORAGE_DRIVER=s3`) | guardar as imagens fora do servidor | as imagens ficam no volume local |

Guias: [`docs/GUIA_LOGIN_GOOGLE.md`](docs/GUIA_LOGIN_GOOGLE.md) e a seção "Para usar o
provedor de IA de verdade" de [`backend/README.md`](backend/README.md).

## Problemas comuns

| Sintoma | Causa provável e solução |
| --- | --- |
| A API não sobe: `JWT_SECRET precisa ter ao menos 32 caracteres` | Preencha `JWT_SECRET` no `.env` |
| A API não sobe em produção citando `URL_PUBLICA`, `DATABASE_URL` ou `MODO_DEMO` | Proteções de produção; ver [`DEPLOY.md`](DEPLOY.md) |
| Log `BANCO DESATUALIZADO` e `/api/v1/saude` responde 503 | Rode `alembic upgrade head` |
| `pytest` recusa rodar citando `_test` | `TEST_DATABASE_URL` aponta para um banco que não é de teste |
| O celular mostra "Sem conexão" no desenvolvimento | API iniciada sem `--host 0.0.0.0`, ou firewall bloqueando a porta 8000 |
| O app de produção diz que foi gerado sem o endereço do servidor | Gere o build com `EXPO_PUBLIC_API_URL` |
| Imagens com "Imagem indisponível" | Arquivo ausente no storage (pasta `backend/dados` não acompanhou o banco) |
| `429 tentativas_demais` no login | 10 falhas em 5 minutos do mesmo endereço; espere ou reinicie a API no desenvolvimento |
| Build Docker falha com erro de certificado no `pip` ou no `npm` | Rede com proxy que inspeciona TLS: entregue a CA ao build (`--secret id=ca,src=<ca.crt>`; ver os Dockerfiles) |
| `docker compose up` diz que falta `DOMINIO`, `POSTGRES_PASSWORD` ou `JWT_SECRET` | Copie `.env.example` para `.env` na raiz e preencha |
| O navegador acusa certificado inválido em produção | DNS do domínio ainda não aponta para o servidor, ou portas 80/443 fechadas; veja `docker compose logs web` |

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [`DEPLOY.md`](DEPLOY.md) | Implantação em produção, HTTPS, backup, restauração e rollback |
| [`RELATORIO_REVISAO_E_DEPLOY.md`](RELATORIO_REVISAO_E_DEPLOY.md) | Revisão técnica mais recente: problemas, correções, testes e prontidão |
| [`backend/README.md`](backend/README.md) | Execução, configuração, rotas e testes da API |
| [`docs/DECISOES_TECNICAS.md`](docs/DECISOES_TECNICAS.md) | Decisões que o código precisa manter |
| [`docs/DOCUMENTACAO-BACKEND.md`](docs/DOCUMENTACAO-BACKEND.md) | Arquitetura do servidor, modelo de dados e LGPD |
| [`docs/DOCUMENTACAO.md`](docs/DOCUMENTACAO.md) | Telas, decisões de design e acessibilidade do aplicativo |
| [`docs/GUIA_LOGIN_GOOGLE.md`](docs/GUIA_LOGIN_GOOGLE.md) | Credenciais do "Entrar com Google" |
| [`espelho/e2e/README.md`](espelho/e2e/README.md) | Baterias de navegador |
| [`docs/historico/`](docs/historico) | Relatórios das etapas anteriores (registro histórico) |

O projeto começou como protótipo no Claude Design: a conversa está em [`chats/`](chats) e o
protótipo, com o PDF do pré-projeto, em [`project/`](project). São referência histórica; o
aplicativo real é o de `espelho/`.
