# Relatório final da implementação

Entrega do back-end, do banco de dados e da integração com o aplicativo Espelho.
Documentos de apoio: [`DIAGNOSTICO-E-ARQUITETURA.md`](DIAGNOSTICO-E-ARQUITETURA.md)
(auditoria e arquitetura, feitas antes de escrever código),
[`DOCUMENTACAO-BACKEND.md`](../DOCUMENTACAO-BACKEND.md) (documentação técnica e acadêmica),
[`backend/README.md`](../../backend/README.md) (manual de operação) e
[`DOCUMENTACAO.md`](../DOCUMENTACAO.md) (interface).

---

## 1. Resumo

O protótipo rodava inteiramente no aparelho: dados fictícios, `AsyncStorage`, autenticação
simulada e uma "simulação" que devolvia a própria foto do cliente com uma camada de cor por
cima. Agora existe um sistema real de ponta a ponta:

**Aplicativo Expo → API FastAPI → PostgreSQL 16 / storage de objetos / provedor de IA.**

O que foi construído:

- API REST em FastAPI com 26 rotas em `/api/v1`, documentação OpenAPI automática;
- banco PostgreSQL com 9 tabelas, criado por migrations Alembic, com enums nativos,
  índices parciais, *check constraints* e três gatilhos de imutabilidade;
- autenticação real (bcrypt + JWT) e autorização por usuário imposta em toda consulta;
- consentimento de imagem com histórico imutável, termos versionados em tabela e bloqueio
  da simulação no servidor;
- storage de objetos atrás de uma interface, com URLs assinadas de curta duração;
- validação da fotografia no servidor — inclusive detecção de rosto — antes de qualquer
  chamada paga;
- integração com provedor de IA desacoplada, com implementação real (Replicate) e um
  provedor local para desenvolvimento, testes e demonstração;
- aplicativo integrado, sem nenhum mock e sem nenhum `TODO:BACKEND` restante;
- 310 testes automatizados (94% de cobertura) e três baterias de verificação em navegador
  real — uma que percorre o fluxo inteiro contra a API, outra de responsividade,
  acessibilidade e estados de tela;
- verificação dirigida de qualidade e segurança documentada em `RELATORIO_QA.md`, com os
  achados, as correções aplicadas e os riscos residuais.

---

## 2. Arquitetura

Monólito modular: um processo FastAPI, um banco, módulos separados por responsabilidade.
Para um sistema com um profissional por instalação e dezenas de clientes por carteira,
qualquer distribuição adicional custaria operação sem resolver problema existente.

```
Aplicativo (Expo/RN)
  │  HTTPS · Bearer JWT · JSON camelCase · multipart no envio da foto
  ▼
API FastAPI  —  routers → services → repositories → models
  ├─► PostgreSQL 16        (SQLAlchemy 2.x síncrono)
  ├─► Storage de objetos   (disco em dev; S3/MinIO/Supabase em produção)
  └─► Provedor de IA       (Replicate · FLUX.1 Kontext)
```

As imagens não trafegam pelo mesmo caminho dos dados: o aplicativo recebe URLs assinadas e
busca cada arquivo direto do endpoint de imagens, que confere a assinatura.

A camada de repositórios é onde o isolamento entre contas é garantido: não existe ali
nenhuma consulta que busque por identificador sem filtrar pelo dono.

---

## 3. Banco de dados

Nove tabelas: `usuarios`, `clientes`, `consentimentos`, `termos`, `ciencias`, `imagens`,
`simulacoes`, `atendimentos`, `agendamentos`.

```
usuarios 1──N clientes 1──N consentimentos ──N:1── termos
   │             │  1──N simulacoes ──N:1── consentimentos   (decisão que autorizou)
   │             │  1──N atendimentos ──0:1── simulacoes     (ON DELETE SET NULL)
   │             │  1──N agendamentos
   │             └──0:1── imagens (perfil)
   ├──N ciencias ──N:1── termos
   └──N imagens
```

Decisões de modelagem que valem registro:

- **`simulacoes.consentimento_id` é obrigatório**: cada imagem gerada aponta para a decisão
  que a autorizou. A prova de base legal está no esquema, não na interpretação de um log.
- **`pendente` não é persistido**: ausência de registro é ausência de decisão.
- **Imutabilidade por gatilho**: `UPDATE` em `consentimentos` e `ciencias` sempre falha;
  `DELETE` só passa em cascata da exclusão do cliente ou da conta — isto é, apenas quando
  se exerce o direito de eliminação. Em `termos`, o texto publicado não muda; só a marcação
  de vigência pode ser alterada.
- **Índices únicos parciais** garantem uma simulação preferida por cliente, uma versão
  vigente por tipo de termo e uma foto de perfil por cliente.
- **`atendimentos.simulacao_id ON DELETE SET NULL`**: excluir imagens não apaga o histórico
  de atendimentos — a regra é do banco, não do código.

O banco nasce de duas migrations (estrutura e publicação dos termos) e pode ser recriado do
zero. `create_all()` não é usado em lugar nenhum.

---

## 4. API

Prefixo `/api/v1`; documentação interativa em `/docs`.

| Método | Rota | Para quê |
| --- | --- | --- |
| POST | `/auth/registrar`, `/auth/login`, `/auth/renovar` | RF01 (públicas) |
| GET · PATCH · DELETE | `/usuarios/me` | perfil; o DELETE exige a senha |
| GET · POST | `/usuarios/me/ciencia` | ciência das responsabilidades |
| DELETE | `/usuarios/me/imagens` | apaga as imagens de todos os clientes |
| GET · POST | `/clientes` | RF02 — a lista já traz o resumo de consentimento |
| GET · PATCH · DELETE | `/clientes/{id}` | RF02 |
| POST · DELETE | `/clientes/{id}/foto` | foto de perfil |
| GET | `/clientes/{id}/consentimento` | decisão atual e bloqueio, se houver |
| GET · POST | `/clientes/{id}/consentimentos` | histórico e nova decisão |
| GET | `/clientes/{id}/historico`, `/simulacoes`, `/agendamentos` | consultas do perfil |
| DELETE | `/clientes/{id}/simulacoes` | RNF05 |
| POST | `/simulacoes` | RF04 — multipart, responde 202 |
| GET | `/simulacoes`, `/simulacoes/{id}` | RF05 |
| POST | `/simulacoes/{id}/preferida` | RF07 |
| GET · POST | `/atendimentos`; GET · PATCH `/atendimentos/{id}` | RF03 |
| GET · POST | `/agendamentos`; GET · PATCH · DELETE `/agendamentos/{id}` | RF06 |
| PATCH | `/agendamentos/{id}/status` | transições validadas |
| GET | `/imagens/{id}?t=…` | entrega por assinatura |
| GET | `/termos/{tipo}`, `/termos/{tipo}/{versao}`, `/catalogo`, `/saude` | públicas |

Erros saem sempre no mesmo formato, com código estável:

```json
{ "erro": { "codigo": "consentimento_invalido", "mensagem": "…", "detalhes": [...] } }
```

401 sem token · 403 consentimento inválido · 404 inexistente **ou** de outro usuário ·
409 conflito · 413 corpo grande demais · 422 validação e foto recusada · 429 tentativas
demais · 502 provedor de IA · 503 storage.

---

## 5. Autenticação

- **Senha**: bcrypt com custo 12. Mínimo de 8 caracteres; acima de 72 bytes a senha é
  recusada em vez de truncada em silêncio.
- **Sessão**: dois JWT HS256 — acesso (30 min) e renovação (30 dias), distinguidos por uma
  *claim* `tipo`, de modo que um não serve no lugar do outro. `JWT_SECRET` é obrigatório,
  com no mínimo 32 caracteres; sem ele a aplicação não sobe.
- **No aparelho**: o token fica no armazenamento seguro do sistema (Keychain/Keystore) via
  `expo-secure-store`; na web, onde isso não existe, cai para `AsyncStorage` — diferença
  registrada como limitação. Nenhum dado pessoal de cliente é guardado no aparelho.
- **Renovação transparente**: ao receber 401, o cliente HTTP troca o token de renovação por
  um novo acesso e repete a requisição uma vez.
- **Sem vazamento por mensagem ou por tempo**: e-mail inexistente e senha errada devolvem a
  mesma resposta, e a verificação roda mesmo sem usuário, contra um hash descartável.

Autorização: toda consulta parte do identificador do token. Trocar o id na URL devolve
**404**, não 403 — 403 confirmaria que o registro existe.

---

## 6. Consentimento

O consentimento pertence ao cliente; o profissional apenas registra a decisão. Cada decisão
é um registro novo — revogar não altera o aceite anterior.

Antes de qualquer imagem chegar ao provedor de IA, o servidor verifica: o cliente existe,
pertence ao usuário autenticado, tem decisão registrada, a decisão é `aceito` e a versão
aceita é a vigente. Qualquer falha interrompe com **403** e um motivo legível (`pendente`,
`recusado`, `revogado`, `revalidar`). O aplicativo também verifica, mas isso é conveniência
de interface: o controle de acesso é o do servidor, e vale mesmo para quem chama a API
diretamente.

Outras regras implementadas:

- **Menor de 18 anos** exige nome e parentesco do responsável legal; sem isso o registro é
  recusado (art. 14, §1º). A faixa etária apurada fica gravada na decisão.
- **A versão do termo não é enviada pelo aplicativo** — quem define é o servidor. Isso
  corrige uma fragilidade real: um app desatualizado registraria aceite sobre texto antigo.
- **Termos versionados em tabela**, com uma única versão vigente por tipo. A consulta mostra
  o texto exato que aquele cliente aceitou; se o servidor não tiver mais aquela versão, a
  tela avisa em vez de exibir outro texto.
- **Revogação** cria registro novo e oferece a exclusão das imagens (art. 18, VI), sem tocar
  no histórico de atendimentos.

---

## 7. Imagens

**Recebimento.** `POST /simulacoes` recebe a foto em `multipart`. Antes de guardar, o
servidor valida, em ordem: tamanho (≤ 8 MB; acima de 12 MB o corpo é recusado antes de ser
lido), tipo real obtido da decodificação (não da extensão nem do `Content-Type`), formato
aceito, dimensões (≥ 480 px no menor lado, ≤ 4096 no maior), proporção de retrato,
luminância média e **detecção de rosto** por cascata de Haar. Falhando qualquer item, a
resposta é 422 com a lista de problemas — e nenhuma chamada paga acontece.

A imagem aprovada é recodificada em JPEG, o que **descarta os metadados EXIF**, inclusive
coordenadas de GPS.

**Armazenamento.** O PostgreSQL guarda só metadados; o arquivo vai para o storage, atrás da
interface `ArmazenamentoObjetos`, em chaves derivadas de identificadores do sistema —
nunca do nome enviado pelo cliente:

```
usuarios/{usuario}/clientes/{cliente}/simulacoes/{simulacao}/entrada-<hex>.jpg
```

**Entrega.** Nenhuma URL pública permanente. Cada imagem abre por
`GET /api/v1/imagens/{id}?t=<assinatura>`, um HMAC-SHA256 de imagem + dono + expiração,
válido por 10 minutos. É a única rota sem `Authorization`, porque o `<Image>` do React
Native não envia cabeçalhos — a assinatura é a autorização. Com driver S3, o endpoint
redireciona para uma URL pré-assinada.

**Exclusão.** Por cliente, por conta inteira ou junto com o cliente; sempre removendo os
objetos do storage e as linhas do banco, e sempre preservando o histórico de atendimentos.

---

## 8. Inteligência artificial

**Provedor escolhido: Replicate, modelo `flux-kontext-apps/change-haircut` (FLUX.1 Kontext
pro).** O protótipo citava SDXL img2img; a avaliação mostrou que img2img genérico
reconstrói o rosto, e uma simulação que troca a face não serve para mostrar ao cliente. O
modelo escolhido é especializado em cabelo, edita por instrução preservando a identidade e
recebe exatamente os parâmetros que o aplicativo já coletava (`haircut`, `hair_color`).
Custo por execução, sem infraestrutura.

**Desacoplamento.** `services/ai/base.py` define o contrato; `replicate.py` implementa o
provedor real; `fake.py` é um provedor local, sem custo e sem credencial, que recolore os
pixels escuros e escreve "simulação local — sem IA" na imagem, para o resultado não ser
confundido com o do modelo real. A escolha é feita por `AI_PROVIDER`; nenhum outro módulo
importa `replicate`.

**Fluxo.** `POST /simulacoes` valida tudo, sobe a entrada, cria a simulação em
`processando` e responde **202**; uma tarefa em segundo plano chama o provedor, guarda o
resultado e marca `concluida` — ou `falhou`, com código de erro. O aplicativo acompanha por
`GET /simulacoes/{id}`. Nenhuma simulação nasce concluída, e nenhuma fica concluída sem
imagem (há *check constraint* para isso).

**A chave vive só no servidor.** O aplicativo nunca a vê, não a recebe em resposta alguma e
não tem como acionar o provedor diretamente. O corpo de erro do provedor — que pode conter
o *prompt* e dados da imagem — fica apenas no log.

**Transparência.** A foto vai como *data URI* no corpo da requisição, e não por URL
pública: enviar por link exigiria expor a imagem, ainda que por pouco tempo.

---

## 9. Aplicativo: o que mudou e por quê

**Arquivos novos**

| Arquivo | Por quê |
| --- | --- |
| `src/services/api/cliente.ts` | cliente HTTP único: URL base descoberta sozinha, token, renovação em 401, tempo limite e tradução de falhas em `ErroApi` com código estável |
| `src/services/api/sessao.ts` | tokens no armazenamento seguro, fora do React, porque o cliente HTTP precisa deles em qualquer chamada |
| `src/services/api/index.ts` | um módulo por recurso; as telas nunca chamam `fetch` |
| `src/components/DocumentoTermo.tsx` | o termo passou a vir da rede: carregando, falha e versão desconhecida precisavam de um lugar só |
| `src/components/Atualizar.tsx` | puxar para atualizar — antes não havia o que recarregar |
| `app/cadastro.tsx` | criação de conta real (antes "Criar conta" só limpava os dados locais) |
| `app/excluir-conta.tsx` | a exclusão passou a exigir a senha; virou tela própria |

**Arquivos removidos**: `src/data/seed.ts` (o seed vive no banco) e
`src/services/authService.ts` (substituído pela API).

**Reescritos**: `src/data/store.tsx` (ações assíncronas contra a API, mantendo
`Context + useReducer` e a assinatura dos seletores, para as telas mudarem pouco),
`src/data/tipos.ts` (contrato da API), `src/data/termos.ts` (cache + hook `useTermo`),
`src/data/rascunho.tsx`, `src/services/consentService.ts` (só rótulos e idade; as regras
foram para o servidor), `src/services/simulacaoService.ts` (só a pré-checagem local),
`src/components/ImagemSimulada.tsx` (exibe a imagem gerada; a tonalização que fabricava o
"depois" saiu), `app/simulacao/processando.tsx` (envio + acompanhamento),
`app/simulacao/resultado.tsx` (a simulação já chega salva), `app/login.tsx` e
`app/index.tsx` (espera e falha da carga inicial).

**Ajustados**: as demais telas, para tratar carregamento, erro e ações assíncronas.

Nenhum `TODO:BACKEND` restou no código.

---

## 10. Segurança

| Mecanismo | Implementação |
| --- | --- |
| Hash de senha | bcrypt, custo 12; senha nunca registrada em log |
| Tokens | JWT HS256, segredo obrigatório de 32+ caracteres, tipos distintos para acesso e renovação |
| Autorização | filtro por usuário em toda consulta; 404 para recurso de outra conta |
| Validação de entrada | Pydantic em todos os corpos, limites de tamanho por campo |
| Upload | tipo real por decodificação, limite de 8 MB, dimensões, barreira contra bomba de descompressão |
| Caminhos | chave do objeto gerada pelo servidor, validada por expressão regular e confirmada dentro da raiz |
| SQL | ORM com parâmetros vinculados; nenhuma consulta montada por concatenação |
| CORS | lista explícita de origens, sem curinga, sem credenciais |
| Corpo da requisição | acima de 12 MB é recusado antes da leitura |
| Força bruta | no máximo 10 tentativas falhas de login por origem a cada 5 minutos |
| Erros | mensagem genérica ao cliente; detalhe e *stack trace* só no log |
| Segredos | só em variáveis de ambiente; `.env` fora do versionamento; `.env.example` sem valores |
| Diagnóstico | `/saude` não descreve a infraestrutura quando `AMBIENTE=producao` |

Varredura do repositório: nenhuma chave, token ou senha versionada. As duas ocorrências
encontradas são o segredo de teste em `tests/conftest.py` e a senha das contas de
demonstração em `app/seed.py`, ambas intencionais e documentadas.

---

## 11. Testes

**310 testes, 94% de cobertura**, contra um PostgreSQL real criado pelas mesmas migrations
da aplicação — inclusive os gatilhos, que são parte da regra de negócio. A suíte inteira,
com as baterias de navegador e a auditoria de dependências, roda por um comando: `./qa.sh`.

| Arquivo | Cobre |
| --- | --- |
| `test_regras_consentimento.py` | idade, faixa etária, exigência de responsável, revalidação, liberação da captura |
| `test_validacao_foto.py` | formato, dimensões, proporção, luminância, rosto, EXIF descartado, arquivo que não é imagem |
| `test_seguranca.py` | bcrypt, JWT (tipo, expiração, segredo trocado), assinatura de imagem |
| `test_auth.py` | cadastro, conflito de e-mail, login, renovação, ciência, exclusão de conta |
| `test_clientes.py` | CRUD, busca, foto de perfil e **nove rotas negadas para outra conta** |
| `test_consentimento.py` | aceite, recusa, revogação, menor com e sem responsável, versão antiga, termos por versão |
| `test_simulacoes.py` | fluxo completo, bloqueios, foto ruim, catálogo inválido, falha do provedor, preferida única |
| `test_agenda_e_atendimentos.py` | vínculo opcional com simulação, transições de status, isolamento |
| `test_imutabilidade.py` | ataque por SQL direto: `UPDATE`/`DELETE` em consentimentos, texto do termo, preferida duplicada |
| `test_provedor_ia.py` | provedor local e integração Replicate com HTTP simulado (sucesso, 401, 402, 500, falha, timeout) |
| `test_entradas_maliciosas.py` | injeção no campo de busca, travessia de caminho, executável disfarçado de imagem, vazamento em erro |
| `test_protecoes.py` | limite de corpo e freio de força bruta |
| `test_seed.py` | a carga de demonstração produz os sete cenários |
| **`test_casos_criticos.py`** | os sete casos exigidos pela especificação |
| `test_limites_e_contratos.py` | entradas ausentes, de tipo errado, no limite e um byte além; forma das respostas |
| `test_idor_completo.py` | varredura de IDOR em todas as rotas que recebem identificador, por URL e por corpo |
| `test_seguranca_aplicacao.py` | cabeçalhos, exposição da documentação, CORS, abuso de custo, bomba de descompressão |
| `test_integridade_dados.py` | órfãos no banco e arquivos esquecidos no disco depois de cada exclusão |
| `test_lgpd.py` | pontos de LGPD verificados pelo comportamento, inclusive ausência de dado pessoal nos logs |
| `test_contrato_com_aplicativo.py` | correspondência campo a campo entre os tipos TypeScript e os schemas do OpenAPI |
| `test_simulacao_com_mock_ia.py` | o cliente real contra um servidor que imita a Replicate, em dez cenários |

Os sete casos críticos, na ordem pedida: cliente sem consentimento não gera simulação;
consentimento revogado não gera; consentimento antigo exige revalidação; usuário A não
acessa dados de B; menor sem responsável não registra consentimento; revogação cria
registro novo; exclusão de imagens não apaga o histórico de atendimentos.

**Verificação em navegador**, em duas baterias. `espelho/e2e/fluxo-completo.mjs`: o fluxo
completo contra a API real, do cadastro à revogação com exclusão das imagens, passando por
captura, validação, geração, URL assinada, atendimento e agendamento.
`espelho/e2e/qa-interface.mjs`: responsividade em 390, 768 e 1280 px, alvos de toque,
rótulos acessíveis, alternativas textuais, navegação por teclado, validação de formulário,
estado vazio, comportamento com a API fora do ar e limpeza do console. Última execução: 26 passos,
nenhuma falha, nenhum erro de console.

---

## 12. Alterações em relação ao projeto original

**Modelo de dados** (ante a seção 5.6 do pré-projeto): `termos`, `ciencias` e `imagens` são
entidades novas; `simulacoes` ganhou `consentimento_id`, `status` e campos de erro;
`atendimentos` ganhou `usuario_id` (o tipo do aplicativo não tinha dono); `consentimentos`
ganhou `faixa_etaria`.

**Provedor de IA**: FLUX.1 Kontext no lugar de SDXL img2img, por preservar a identidade.

**Fragilidades do protótipo corrigidas**: credenciais de demonstração pré-preenchidas na
tela de login (removidas); "Criar conta" que apagava dados locais; versão do termo definida
pelo aplicativo; unicidade da simulação preferida garantida só em memória; transições de
status da agenda sem validação; estado inteiro — inclusive consentimentos — persistido em
claro no aparelho; e o texto da tela de privacidade, que não mencionava que apagar imagens
também apaga a foto de perfil do cliente.

**Atalhos de demonstração**: continuam existindo para a apresentação, mas deixaram de
fingir. "Foto ruim" e "falha da IA" viajam como marca até o servidor, que responde como
responderia de verdade — e só quando `MODO_DEMO=true`.

---

## 13. Decisões técnicas importantes

1. **Imutabilidade no banco, não só no código** — gatilhos em vez de disciplina de serviço.
   A afirmação do TCC passa a ser verificável; o custo foi tratar a exclusão em cascata.
2. **`simulacoes.consentimento_id` obrigatório** — a prova de base legal fica no esquema.
3. **Simulação assíncrona com consulta de estado** — `BackgroundTasks` + `GET /simulacoes/{id}`
   em vez de resposta síncrona (risco de tempo limite) ou fila (infraestrutura vedada).
4. **404 em vez de 403** para recurso de outra conta — não confirmar a existência do id.
5. **Exclusão física da conta** — *soft delete* manteria dado pessoal vivo; anonimização
   preservaria metadados sem finalidade. O impacto (não resta comprovante) está assumido.
6. **Senha reconfirmada para excluir a conta** — operação irreversível não deve depender só
   de um aparelho desbloqueado.
7. **JSON em camelCase** — faz o contrato da API coincidir com os tipos que o aplicativo já
   tinha, eliminando uma camada inteira de tradução e os erros que vêm com ela.
8. **Catálogo no aplicativo, validação no servidor** — o catálogo é fixo e tem
   representação visual; o servidor valida e é dono da tradução para o provedor.
9. **Storage local como padrão de desenvolvimento** — mesma interface, dois drivers; sobe
   sem MinIO e troca para S3 com uma variável.
10. **`Context + useReducer` mantido no aplicativo** — o volume é pequeno e o fluxo é por
    tela; trocar por cache remoto seria dependência sem problema a resolver.
11. **SQLAlchemy síncrono** — o único I/O lento roda fora da requisição; `async` traria
    complexidade sem ganho mensurável.
12. **Provedor local como padrão** — o sistema inteiro funciona sem credencial e sem custo,
    com aviso impresso na imagem para ninguém confundir com o modelo real.

---

## 14. Fora do escopo

| Item | Situação |
| --- | --- |
| **RF08 — recomendação automática de estilo** | permanece `won't have`, como no TCC. Não foi implementado |
| Recuperação de senha | exigiria provedor de e-mail; a tela informa isso |
| Disparo das notificações de lembrete | o campo é persistido; a notificação não é agendada |
| Revogação de token de renovação | não há lista de invalidados; excluir a conta invalida tudo |
| Limite de tentativas distribuído | o freio atual é por processo, em memória |
| Modo escuro, testes com usuários, publicação nas lojas | continuam na lista de próximos passos |

**O que não pôde ser executado neste ambiente, e por quê**

- **A chamada real à Replicate**: não há credencial aqui e o domínio está bloqueado pelo
  proxy de rede. A integração está implementada e coberta por testes com HTTP simulado
  (sucesso, saída em lista, 401, 402, 500, predição falhada, resposta inesperada e tempo
  esgotado). Para rodar de verdade: `AI_PROVIDER=replicate` e `AI_API_KEY=<token>`.
- **`docker compose up`**: não há daemon do Docker neste ambiente. O `Dockerfile` e o
  `docker-compose.yml` foram escritos e conferidos, mas a validação usou o PostgreSQL 16
  local — com as mesmas migrations e o mesmo seed.
- **Aparelhos Android e iOS**: a verificação automatizada usou a versão web do aplicativo.

Nada além disso foi declarado como funcionando sem ter sido executado.

---

## 15. Como executar

```bash
# 1. Back-end
cd backend
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # cole em JWT_SECRET

# com Docker (sobe banco + API, migra e popula)
docker compose up --build

# ou sem Docker
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head          # cria o banco do zero, com os termos publicados
python -m app.seed            # dados de demonstração
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Testes
python -m pytest              # 310 testes
python -m pytest --cov=app    # com cobertura

# 3. Aplicativo
cd ../espelho
npm install
npx expo start                # celular: Expo Go, mesma rede · navegador: tecla w

# 4. Verificação de ponta a ponta (com os dois no ar)
node e2e/fluxo-completo.mjs
```

Contas de demonstração criadas pelo seed (dados fictícios):

| Conta | E-mail | Senha |
| --- | --- | --- |
| Principal — 7 clientes, 5 simulações, agenda e histórico | `carolina@salaoexemplo.com.br` | `espelho-demo-2026` |
| Segunda conta — prova o isolamento | `diego@salaoexemplo.com.br` | `espelho-demo-2026` |

O aplicativo encontra a API sozinho pelo endereço do Metro bundler, na porta 8000. Para
apontar para outro servidor: `EXPO_PUBLIC_API_URL=https://… npx expo start`.

Para usar o provedor de IA real, basta `AI_PROVIDER=replicate` e `AI_API_KEY=<token>` no
`.env` do back-end, e reiniciar. Com o padrão (`fake`), tudo funciona sem custo e sem
credencial.
