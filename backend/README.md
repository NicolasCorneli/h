# Espelho — API

Back-end do aplicativo Espelho: simulação capilar por IA e gestão de clientes para
profissionais de beleza. FastAPI + PostgreSQL + storage de objetos + provedor externo de
inteligência artificial.

Este arquivo é o manual de operação. A documentação acadêmica — arquitetura, modelo de
dados, decisões e rastreabilidade com os requisitos do TCC — está em
[`../DOCUMENTACAO-BACKEND.md`](../docs/DOCUMENTACAO-BACKEND.md).

---

## Como executar

### Com Docker (um comando)

```bash
cd backend
cp .env.example .env
# gere o segredo dos tokens e coloque em JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up --build
```

Este compose é o de **desenvolvimento** (modo demonstração, contas de teste, banco com
senha conhecida). Para produção, use `../docker-compose.yml` e siga
[`../DEPLOY.md`](../DEPLOY.md).

Sobe `db` (PostgreSQL 16) e `api` (FastAPI). As migrations rodam sozinhas na partida e,
com `SEED_AO_SUBIR=true`, os dados de demonstração são criados. A API fica em
<http://localhost:8000> e a documentação interativa em <http://localhost:8000/docs>.

O **aplicativo Expo fica fora do Docker**, de propósito: para rodar no celular ele precisa
do Metro bundler na mesma rede do aparelho, o que dentro de contêiner exigiria rede em
modo host e configuração extra sem ganho nenhum para o desenvolvimento.

### Sem Docker

Requer Python 3.11+ e um PostgreSQL 16 acessível.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt                    # execução + testes (a imagem usa só requirements.txt)

cp .env.example .env                                   # preencha JWT_SECRET e DATABASE_URL

alembic upgrade head        # cria o banco do zero, inclusive os termos publicados
python -m app.seed          # dados de demonstração (opcional, mas recomendado)

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` é necessário para o celular alcançar a API pela rede local.

### Aplicativo

```bash
cd ../espelho
npm install
npx expo start
```

O aplicativo descobre a API sozinho: usa o endereço do Metro bundler com a porta 8000
(`http://<ip-do-computador>:8000`). Para apontar para outro servidor, defina
`EXPO_PUBLIC_API_URL` antes de iniciar:

```bash
EXPO_PUBLIC_API_URL=https://api.exemplo.com npx expo start
```

### Contas de demonstração

Criadas por `python -m app.seed` (dados fictícios):

| Conta | E-mail | Senha |
| --- | --- | --- |
| Principal (7 clientes, 5 simulações) | `carolina@salaoexemplo.com.br` | `espelho-demo-2026` |
| Segunda conta (prova o isolamento) | `diego@salaoexemplo.com.br` | `espelho-demo-2026` |

Cenários de consentimento prontos: aceito, pendente, recusado, aceito em versão anterior,
revogado e menor de idade com responsável.

`python -m app.seed --reset` apaga e recria.

---

## Configuração

Tudo por variável de ambiente; `.env.example` lista todas. As que importam:

| Variável | Para quê | Padrão |
| --- | --- | --- |
| `DATABASE_URL` | conexão com o PostgreSQL | `postgresql+psycopg://espelho:espelho@localhost:5432/espelho` |
| `JWT_SECRET` | assina tokens e URLs de imagem. **Obrigatória**, mínimo 32 caracteres | — |
| `JWT_MINUTOS_ACCESS` / `JWT_DIAS_REFRESH` | validade dos tokens | 30 min / 30 dias |
| `CORS_ORIGENS` | origens autorizadas, separadas por vírgula | `http://localhost:8081,http://localhost:19006` |
| `STORAGE_DRIVER` | `local` (disco) ou `s3` (S3, MinIO, Supabase) | `local` |
| `STORAGE_DIR` | pasta do driver local | `./dados/imagens` |
| `STORAGE_URL`, `STORAGE_BUCKET`, `STORAGE_KEY`, `STORAGE_SECRET`, `STORAGE_REGIAO` | driver S3 | — |
| `AI_PROVIDER` | `fake` (local, sem custo) ou `replicate` | `fake` |
| `AI_API_KEY` | credencial do provedor. **Nunca vai para o aplicativo** | — |
| `AI_MODELO` | modelo principal: pedidos que batem com os exemplos da tela, com as opções fechadas `haircut` e `hair_color` | `flux-kontext-apps/change-haircut` |
| `AI_MODELO_TEXTO` | descrição livre de corte e cor (`prompt` + `input_image`). Vazio: só os exemplos | `black-forest-labs/flux-kontext-pro` |
| `AI_INSTRUCAO_IDIOMA` | `pt_com_termos` (descrição em português mais os termos em inglês) ou `pt` | `pt_com_termos` |
| `AI_TIMEOUT_S` | tempo limite da geração (recomendado 120 com o provedor real) | 60 s |
| `AI_LIMITE_DATA_URI_KB` | até este tamanho a foto vai como data URI; acima, pela API de arquivos (apagada depois) | 1024 |
| `AI_LADO_MAXIMO_ENVIO` | lado maior das imagens enviadas ao modelo | 1536 px |
| `AI_CACHE_ESQUEMA_MIN` | validade do schema lido de cada modelo | 60 min |
| `AI_BASE_URL` | endereço do provedor. Existe para os testes apontarem para um servidor de mentira e exercitarem o cliente real sem chamar o serviço externo | `https://api.replicate.com/v1` |
| `AI_INTERVALO_CONSULTA_S` | intervalo entre consultas ao estado da predição | 1 s |
| `SIMULACAO_MAX_POR_HORA` | teto de simulações por conta a cada hora. Cada geração custa dinheiro no provedor: sem teto, uma conta — ou um token roubado — esvazia o crédito | 3 |
| `IMAGEM_MAX_BYTES`, `IMAGEM_MIN_LADO`, `IMAGEM_MAX_LADO`, `VALIDAR_ROSTO` | limites da foto | 8 MB, 480 px, 4096 px, `true` |
| `MODO_DEMO` | habilita os atalhos de demonstração do aplicativo | `false` |
| `AMBIENTE` | `desenvolvimento`, `teste` ou `producao` | `desenvolvimento` |
| `URL_PUBLICA` | endereço público da API, base das URLs de imagem. **Obrigatória em produção, com https**. Vazia: o endereço da própria requisição | — |
| `LOG_FORMATO` / `LOG_NIVEL` | `texto` ou `json` (uma linha por evento); nível | `texto` / `INFO` |
| `BANCO_POOL` / `BANCO_POOL_EXCEDENTE` / `BANCO_POOL_ESPERA_S` | conexões por processo e espera por uma livre | 5 / 10 / 10 s |
| `SIMULACAO_EXPIRA_MIN` | depois disso, uma simulação ainda "processando" é dada como interrompida | 5 min |
| `MIGRAR_AO_SUBIR` / `SEED_AO_SUBIR` | só na imagem Docker (`entrypoint.sh`): migrar e popular ao subir | `true` / `false` |

O arquivo `.env` **não** vai para o repositório (está no `.gitignore`). Nenhuma chave,
token ou senha fica no código.

Com `AMBIENTE=producao`: `/docs`, `/redoc` e `/openapi.json` respondem 404; as respostas
ganham o cabeçalho HSTS; `/api/v1/saude` não descreve a infraestrutura; `python -m app.seed`
se recusa a criar as contas de demonstração (a senha delas está publicada aqui); e a API
**se recusa a subir** com `MODO_DEMO=true`, com o `DATABASE_URL` padrão de desenvolvimento,
sem `URL_PUBLICA` com `https://` ou com `CORS_ORIGENS=*`. Ao subir, ela registra avisos para
escolhas permitidas mas arriscadas (provedor `fake`, origens sem https, storage local). Os demais
cabeçalhos de segurança (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`X-Permitted-Cross-Domain-Policies`) são enviados em qualquer ambiente.

### Para usar o provedor de IA de verdade

A integração está implementada; falta apenas a credencial. Nenhuma alteração de código é
necessária.

**1. Obtenha o token.** Crie conta em `replicate.com`, abra
`replicate.com/account/api-tokens` e gere um token. Ele começa com `r8_`.

**2. Configure o servidor.** No `backend/.env` — que não vai para o repositório:

```bash
AI_PROVIDER=replicate
AI_API_KEY=r8_...                               # o seu token, sem aspas
AI_TIMEOUT_S=120                                # folga para filas do provedor
SIMULACAO_MAX_POR_HORA=3                        # teto de custo por conta
```

Os dois modelos (`AI_MODELO` e `AI_MODELO_TEXTO`) já vêm com o padrão. Deixar
`AI_MODELO_TEXTO` vazio desliga a descrição livre (só os exemplos da tela são aceitos).

**2b. Confira os modelos sem gastar crédito:**

```bash
.venv/bin/python -m app.diagnostico_ia
```

Ele lê o schema publicado de cada modelo (consulta gratuita), mostra os campos e as opções
aceitas e aponta qualquer campo que o sistema envie e o modelo não tenha. Nenhuma predição é
criada e a chave não é impressa.

**3. Reinicie a API.** A configuração é lida uma vez, na inicialização:

```bash
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**4. Confirme que o servidor está pronto**, antes de gastar uma simulação:

```bash
curl -s http://localhost:8000/api/v1/saude
```

A resposta deve trazer `"provedorIa": "replicate"`, `"credencialIa": true` e o modelo
configurado. `credencialIa` é booleano: a chave em si nunca sai do servidor, nem nesta
rota nem em mensagem de erro.

**5. Faça a primeira chamada real** pelo aplicativo: escolha um cliente com consentimento
registrado, fotografe e gere. Acompanhe o log do servidor — em caso de falha, o motivo
registrado diz de quem é o problema (`credencial_invalida`, `sem_credito`,
`limite_do_provedor`, `timeout`, `resposta_invalida`, `falha_na_geracao`).

> **A chave fica só no servidor.** O aplicativo nunca a recebe: ele chama a API do
> Espelho, e é a API que fala com a Replicate. Não existe caminho pelo qual a credencial
> chegue ao aparelho — há teste automatizado que confere isso inclusive nas respostas de
> erro do provedor.

Com `AI_PROVIDER=fake` (padrão) o sistema funciona inteiro, sem custo e sem credencial: o
provedor local recolore os pixels escuros da foto e escreve "simulação local, sem IA" na
imagem, para ninguém confundir o resultado com o do modelo real.

O passo a passo completo do teste real está em
[`RELATORIO_PERSONALIZACAO_IA.md`](../docs/historico/RELATORIO_PERSONALIZACAO_IA.md#h-configuração-necessária-para-o-seu-teste).

---

## Endpoints

Prefixo `/api/v1`. Documentação interativa em `/docs`; esquema OpenAPI em `/openapi.json`.
Todas as rotas exigem `Authorization: Bearer <token>`, exceto as marcadas como públicas.

| Método | Rota | Observação |
| --- | --- | --- |
| POST | `/auth/registrar` · `/auth/login` · `/auth/renovar` | públicas |
| GET · PATCH · DELETE | `/usuarios/me` | o DELETE exige a senha no corpo |
| POST | `/usuarios/me/senha` | `senhaAtual` + `novaSenha`; encerra as outras sessões e devolve tokens novos |
| DELETE | `/usuarios/me/sessoes` | sair de todos os aparelhos (inclusive este) |
| GET · POST | `/usuarios/me/ciencia` | ciência das responsabilidades |
| DELETE | `/usuarios/me/imagens` | apaga as imagens de todos os clientes |
| GET · POST | `/clientes` | lista traz o resumo de consentimento junto |
| GET · PATCH · DELETE | `/clientes/{id}` | |
| POST · DELETE | `/clientes/{id}/foto` | foto de perfil |
| GET | `/clientes/{id}/consentimento` | decisão atual + bloqueio, se houver |
| GET · POST | `/clientes/{id}/consentimentos` | histórico e nova decisão |
| GET | `/clientes/{id}/historico` · `/simulacoes` · `/agendamentos` | |
| DELETE | `/clientes/{id}/simulacoes` | apaga imagens e simulações do cliente |
| POST | `/simulacoes` | multipart (`foto`, `corte`, `cor`, `manterCorte`, `manterCor`, `genero`, `chaveEnvio`); responde **202**. A mesma `chaveEnvio` devolve a simulação já criada |
| POST | `/simulacoes/plano` | prévia de como o pedido será gerado (provedor, modo, modelo, instrução); sem foto, sem custo |
| GET | `/simulacoes` · `/simulacoes/{id}` | |
| POST | `/simulacoes/{id}/preferida` | |
| DELETE | `/simulacoes/{id}` | apaga a simulação e as imagens dela; o atendimento vinculado fica, sem o vínculo. Em processamento: 409 |
| GET · POST | `/atendimentos` · GET · PATCH · DELETE `/atendimentos/{id}` | PATCH corrige serviço, dia e hora (`realizadoEm`), duração e notas; DELETE só no avulso (o vindo da agenda responde 422 `atendimento_da_agenda`) |
| GET · POST | `/agendamentos` · GET · PATCH · DELETE `/agendamentos/{id}` | |
| PATCH | `/agendamentos/{id}/status` | transições validadas |
| GET | `/imagens/{id}?t=<assinatura>` | pública por assinatura, não por token |
| GET | `/termos/{tipo}` · `/termos/{tipo}/{versao}` | públicas |
| GET | `/catalogo` · `/saude` · `/saude/vivo` | públicas. `/saude` é a prontidão (503 sem banco ou com migrations pendentes); `/saude/vivo`, a vida (não toca no banco) |

### Formato dos erros

```json
{ "erro": { "codigo": "consentimento_invalido", "mensagem": "…", "detalhes": [ … ] } }
```

| Código HTTP | Quando |
| --- | --- |
| 401 | sem token, token inválido ou expirado; `sessao_encerrada` depois de trocar a senha ou sair de todos os aparelhos |
| 403 | consentimento ausente/inválido, ou senha errada na exclusão da conta |
| 404 | não existe **ou** não pertence ao usuário autenticado |
| 409 | conflito (e-mail já cadastrado) |
| 413 | corpo acima do limite |
| 422 | validação, foto recusada, transição de status inválida |
| 429 | tentativas demais de login (`tentativas_demais`), ou teto de simulações por hora atingido (`limite_de_simulacoes`) |
| 502 | provedor de IA indisponível (inclusive `limite_do_provedor`, quando o serviço externo recusa por excesso de pedidos) |
| 503 | storage indisponível (`armazenamento_indisponivel`), inclusive S3/MinIO fora do ar |

---

## Testes

A suíte inteira roda por um comando, da raiz do repositório:

```bash
./qa.sh              # back-end (567 testes com cobertura), migrations x modelos, tipos, lint e
                     # testes de unidade do aplicativo
./qa.sh --interface  # recria o seed e roda as 11 baterias de navegador
./qa.sh --tudo       # acrescenta a auditoria de dependências
```

As baterias de navegador precisam da API e do `expo start --web` no ar. Se o Chromium do
Playwright estiver instalado fora do padrão, defina `CHROMIUM_PATH` com o executável. O `--interface`
recria a carga de demonstração antes de rodar, porque o roteiro de ponta a ponta altera
esses dados — revoga consentimento e apaga imagens, que é o que ele verifica.

Ou diretamente:

```bash
cd backend
.venv/bin/python -m pytest                 # 567 testes
.venv/bin/python -m pytest --cov=app       # com cobertura (93%)
DATABASE_URL=<banco de teste> JWT_SECRET=<32+ caracteres> .venv/bin/alembic check   # modelos x migrations
```

Os testes usam um PostgreSQL de verdade, no banco `espelho_test`, criado pelas mesmas
migrations da aplicação — inclusive os gatilhos de imutabilidade, que são parte da regra
de negócio. Crie o banco antes da primeira execução:

```bash
createdb -O espelho espelho_test
```

Para usar outro servidor ou outro banco, defina `TEST_DATABASE_URL`. A suíte **apaga** o
banco que recebe (`downgrade base` e `TRUNCATE`), por isso ignora o `DATABASE_URL` do
terminal e se recusa a rodar num banco cujo nome não termine em `_test`.

Entre os testes estão os sete casos críticos exigidos pela especificação do projeto
(`tests/test_casos_criticos.py`): sem consentimento, revogado, versão antiga, isolamento
entre contas, menor sem responsável, revogação como novo registro e exclusão de imagens
sem perder o histórico.

A integração com o provedor de IA é exercitada sem chamar o serviço externo:
`tests/mock_provedor_ia.py` levanta um servidor HTTP que imita o protocolo da Replicate, e
`tests/test_simulacao_com_mock_ia.py` aponta o cliente real para ele: sucesso, erro 4xx,
crédito esgotado, erro 5xx, tempo esgotado, resposta lenta, resposta malformada, resposta
vazia, predição recusada, conteúdo que não é imagem e, desde a revisão de produção, falhas
transitórias na consulta do estado e no download do resultado (repetidas até 3 vezes; a
criação da predição nunca é repetida, porque cobraria duas vezes).

O resultado completo da verificação de qualidade e segurança está em `docs/historico/RELATORIO_QA.md`.

---

## Organização do código

```
app/
├── main.py            aplicação, CORS, middlewares, tratamento de erros
├── core/              configuração, segurança, dependências, erros, proteções
├── db/                engine, sessão e base declarativa
├── models/            9 tabelas em SQLAlchemy 2.x
├── schemas/           entrada e saída em Pydantic (JSON em camelCase)
├── repositories/      consultas — todas filtram pelo usuário autenticado
├── services/          regras de negócio
│   ├── ai/            base.py (contrato), replicate.py (real), fake.py (local)
│   └── storage/       base.py (contrato), local.py (disco), s3.py (S3/MinIO)
├── api/v1/            routers por recurso
└── seed.py            dados de demonstração
migrations/            Alembic — o banco nasce daqui, nunca de create_all()
tests/                 unitários, integração e os casos críticos
```

Caminho de uma requisição: `router → service → repository → model`. O router não consulta
o banco direto nem devolve objeto do SQLAlchemy; o service não sabe o que é HTTP.

---

## Limitações conhecidas

- **Recuperação de senha** não implementada: exigiria um provedor de e-mail.
- **Notificação de lembrete** é persistida, mas não disparada.
- **Sessões** são revogadas por conta, não por aparelho: trocar a senha encerra as dos
  outros aparelhos, e "sair de todos os aparelhos" encerra todas (versão da sessão no
  token). Não há como encerrar só um aparelho específico.
- **Limite de tentativas de login** é por processo, em memória. Com mais de um processo ou
  réplica, cada um conta em separado; o papel caberia a um serviço compartilhado ou ao
  proxy de borda. O **teto de simulações por hora** é contado no banco e vale entre
  processos.
- **Listas sem paginação**: as rotas de lista devolvem a coleção inteira. Com carteiras
  pequenas não há impacto; com carteiras grandes, vira um limite real.
- **URL de imagem é credencial portadora**: a entrega vale por assinatura, não por sessão
  (o `<Image>` do React Native não envia cabeçalhos). Quem possui uma URL assinada válida
  lê a imagem até ela expirar, em 10 minutos.
- **Simulação interrompida**: se o servidor reiniciar durante uma geração, a simulação é
  marcada como falha ("interrompida") passados 5 minutos, na próxima vez que a conta
  consultar ou excluir simulações, ou na inicialização seguinte.
- **RF08 — recomendação automática de estilo** continua fora do escopo, como no TCC.
