# Espelho — Diagnóstico do front-end e arquitetura do back-end

Documento da **Etapa 1 (Auditoria)** e da **Etapa 2 (Arquitetura)**. Nenhum código de
back-end foi escrito antes dele. O objetivo é registrar, de forma verificável, o que o
aplicativo faz hoje, quais inconsistências existem entre front-end, documentação e TCC, e
qual arquitetura será implementada — com as decisões já tomadas e justificadas, para que a
implementação seja apenas execução.

Data: 02/10/2026.

---

## 1. Como a auditoria foi feita

Foram lidos integralmente:

| Fonte | O que foi extraído |
| --- | --- |
| `DOCUMENTACAO.md` (792 linhas, 12 seções) | Divergências já registradas, §8.4 modelo de dados proposto, §8.5 endpoints propostos, §7 tabela de `TODO:BACKEND` |
| `espelho/CLAUDE.md` → `AGENTS.md` | Regra do projeto: Expo SDK 57 mudou; versões vêm do SDK, não da memória |
| `espelho/package.json` | Expo 57.0.22, RN 0.86.3, React 19.2.3, expo-router 57, TypeScript 6.0.3 |
| `espelho/app/` (26 telas) | Fluxos reais, navegação, estados de tela |
| `espelho/src/data/{tipos,seed,catalogo,termos}.ts` | Contrato de domínio, cenários de demonstração, catálogo, termos versionados |
| `espelho/src/services/{authService,consentService,simulacaoService}.ts` | Mocks a substituir e regras de negócio que hoje só existem no cliente |
| `espelho/src/data/{store.tsx,rascunho.tsx}` | 14 ações, 8 seletores, persistência em `AsyncStorage`, rascunho em memória |
| `espelho/src/components/` (14 componentes) | Design system; `ImagemSimulada` é o ponto onde a "simulação" é fabricada hoje |
| Pré-projeto do TCC (seções 4.2, 5.5, 5.6, 5.8, 5.12; RF01–RF08; RNF01–RNF06) | Requisitos e justificativas acadêmicas |

Buscas executadas: `TODO:BACKEND` (13 ocorrências em 10 arquivos), `AsyncStorage`
(3 arquivos), `USUARIO_DEMO` (3 arquivos), chamadas `acoes.*` por tela, e os consumidores
de `gerarSimulacao` / `validarFoto` / `authService`.

---

## 2. Inventário: o que o aplicativo é hoje

### 2.1 Entidades (de `src/data/tipos.ts`)

| Tipo | Campos | Dono | Observação |
| --- | --- | --- | --- |
| `Usuario` | id, nome, email, atuacao, criadoEm | — | **não tem senha**: não existe autenticação de verdade |
| `Cliente` | id, usuarioId, nome, telefone, fotoUri, observacoes, dataNascimento, criadoEm | usuário | `fotoUri` é um caminho local do aparelho |
| `RegistroConsentimento` | id, clienteId, usuarioId, decisao, versaoTermo, registradoEm, formaObtencao, confirmadoPor, responsavel, observacao | cliente | histórico imutável por convenção (nada impede alteração) |
| `CienciaProfissional` | aceita, versao, registradaEm | usuário | hoje é um campo do estado, não uma entidade |
| `Simulacao` | id, clienteId, usuarioId, imgEntradaUri, imgSaidaUri, parametros{estilo,cor,observacoes}, modeloIa, tempoMs, preferida, criadoEm | cliente | `imgSaidaUri` **é a própria foto de entrada** |
| `HistoricoServico` | id, clienteId, simulacaoId, descricao, dataServico, observacoes | cliente | **sem `usuarioId`** |
| `Agendamento` | id, clienteId, usuarioId, dataHora, servico, status, observacoes, lembrete, duracaoMin | usuário | `lembrete` não tem efeito nenhum |
| `Termo` (`data/termos.ts`) | versao, vigenteDesde, titulo, resumo, secoes[] | — | duas versões do termo do cliente (1.0 vigente, 0.9 histórica) + aviso do profissional |

### 2.2 Regras de negócio que hoje existem **somente no front-end**

Todas em `src/services/consentService.ts` e `simulacaoService.ts`:

1. status do cliente = decisão do registro mais recente; ausência de registro = `pendente`;
2. `precisaRevalidar`: aceite válido mas em versão de termo anterior à vigente;
3. `faixaEtaria`: criança < 12, adolescente < 18, adulto, desconhecida (sem data de nascimento);
4. `exigeResponsavel`: criança ou adolescente;
5. `avaliarCaptura`: a câmera só abre com cliente escolhido **e** decisão `aceito` **na versão vigente**;
6. validação da foto: menor lado ≥ 480 px e proporção ≤ 1,35;
7. `marcarPreferida`: apenas uma simulação preferida por cliente;
8. exclusão de imagens do cliente apaga simulações e desvincula o histórico, **sem apagar o atendimento**.

O comentário no topo de `consentService.ts` já reconhece o problema:
“validação só no aplicativo é conveniência de interface, não controle de acesso”.

### 2.3 Mocks e pontos de integração

| Local | Hoje | Vira |
| --- | --- | --- |
| `authService.entrar` | e-mail com regex + senha ≥ 6 caracteres → `USUARIO_DEMO` | `POST /auth/login` com bcrypt + JWT |
| `authService.recuperarSenha` | `await espera(300)` e nada | fora de escopo (sem servidor de e-mail) — documentado |
| `simulacaoService.validarFoto` | largura/altura no cliente | repetida no servidor, com decodificação real |
| `simulacaoService.gerarSimulacao` | `setTimeout` de 2600 ms que devolve a foto de entrada | `POST /simulacoes` + provedor de IA |
| `ImagemSimulada` | aplica uma camada de cor sobre a foto para *parecer* simulação | exibe a imagem gerada por URL assinada |
| `data/seed.ts` | 7 clientes fictícios no aparelho | seed no PostgreSQL |
| `data/termos.ts` | textos no bundle | tabela `termos`, com os textos atuais migrados |
| `store.tsx` | `useReducer` + `AsyncStorage` (`espelho.estado.v1`) | mesmo `useReducer`, alimentado por HTTP |
| `login.tsx` | credenciais pré-preenchidas; “Criar conta” apaga os dados locais | login real + tela de cadastro |
| `app/(tabs)/perfil.tsx`, `privacidade.tsx`, `agendamento/novo.tsx` | avisos de que o recurso depende do servidor | ações reais |

---

## 3. Achados da auditoria

Severidade: **[A]** impede uma implementação correta de back-end · **[B]** inconsistência
real a corrigir · **[C]** ponto a documentar ou pequeno ajuste.

| # | Achado | Sev. | Decisão |
| --- | --- | --- | --- |
| A1 | `Usuario` não tem senha nem credencial; `USUARIO_DEMO.id` é escrito como dono em **todas** as ações do store (`salvarCliente`, `salvarSimulacao`, `salvarAgendamento`, `registrarConsentimento`) | A | dono passa a vir do `sub` do JWT; o front-end nunca envia `usuarioId` |
| A2 | `login.tsx` nasce com `nicolas@studio.com` / `espelho2026` no estado | A | remover; nenhuma credencial padrão no código |
| A3 | Não existe cadastro: “Criar conta” apenas zera o `AsyncStorage` | A | tela `cadastro.tsx` + `POST /auth/registrar` |
| A4 | `HistoricoServico` não tem `usuarioId` | B | adicionar `usuario_id` no banco (preenchido pelo servidor) e validar propriedade por `cliente_id`; o tipo do front-end ganha o campo apenas como leitura |
| A5 | Nada garante no banco que o histórico de consentimentos é imutável | A | `UPDATE` bloqueado por *trigger*; `DELETE` só é aceito em cascata da exclusão do cliente (art. 18) |
| A6 | `precisaRevalidar` compara com a constante `TERMO_CLIENTE` do bundle: um aplicativo desatualizado consideraria válido um aceite vencido | A | versão vigente passa a ser atributo da tabela `termos`; a decisão é do servidor |
| A7 | `gerarSimulacao` devolve a imagem de entrada e `ImagemSimulada` pinta a cor por cima | A | substituído pelo provedor real; `OpcaoCor.tonalizacao` deixa de existir |
| A8 | `validarFoto` roda só no cliente e aceita qualquer coisa que tenha dimensão | A | validação no servidor **antes** da chamada paga: MIME real, tamanho, dimensões, proporção, luminância e detecção de rosto |
| A9 | `forcarRecusa` / `forcarFalha` são chaves de demonstração embutidas no fluxo de produção | B | passam a depender de `MODO_DEMO` no servidor e de `EXPO_PUBLIC_MODO_DEMO` no app; sem elas, as rotas não aceitam o parâmetro |
| A10 | Unicidade de `preferida` por cliente é garantida só pelo reducer | B | índice único parcial `WHERE preferida` |
| A11 | `ParametrosSimulacao.cor` guarda o rótulo em português (“Castanho acobreado”) | B | o servidor passa a ser o dono do mapeamento rótulo → parâmetro do provedor, e valida `estilo`/`cor` contra o catálogo (422 se desconhecido) |
| A12 | `excluirImagens` global também apaga `cliente.fotoUri`, mas o texto da tela diz que só as imagens de simulação são apagadas | C | texto corrigido: a foto de perfil do cliente também é apagada |
| A13 | O estado inteiro — inclusive consentimentos e `fotoUri` — é persistido em claro no `AsyncStorage` | B | após a integração, o aparelho guarda apenas o token (em `expo-secure-store`) e um cache volátil; o dado sensível fica no servidor |
| A14 | Transições de status do agendamento não são validadas (de `cancelado` para `confirmado` é possível) | B | máquina de estados no servidor |
| A15 | `lembrete` não agenda nada | C | persistido e documentado como não implementado (sem `expo-notifications` no escopo) |
| A16 | Datas são `toISOString()` (UTC) comparadas como string; `dataServico` é data, `dataHora` é instante, e os dois são `string` | C | `timestamptz` para instantes e `date` para datas; a API devolve ISO 8601 com fuso |
| A17 | `tempoMs` é medido no aparelho | C | medido no servidor — é a evidência do RNF02 (resposta < 30 s em 80% das chamadas) |
| A18 | Sem data de nascimento, `exigeResponsavel` é `false`: um menor cadastrado sem data passa | C | mantido (não há como inferir idade), mas o servidor passa a exigir responsável sempre que a data indicar menor de 18, e registra `faixa_etaria` no consentimento |
| A19 | `DOCUMENTACAO.md` §8.4 propõe seis entidades; a implementação precisa de nove | C | documentar a diferença (§4.4 abaixo): `termos`, `ciencias` e `imagens` são novas |
| A20 | RF08 (recomendação automática) continua `won't have` | — | **não será implementado**; registrado na matriz de rastreabilidade |

Nenhum segredo foi encontrado no repositório (não há `.env`, chaves ou tokens).

---

## 4. Arquitetura

### 4.1 Visão geral

```
┌──────────────────────────┐
│  App Expo / React Native │  Context + useReducer (mantido)
│  src/services/api/*      │  cliente HTTP tipado, token em SecureStore
└────────────┬─────────────┘
             │ HTTPS, Bearer JWT
┌────────────▼─────────────┐
│  FastAPI  /api/v1        │  routers → services → repositories → models
│  core/{config,security}  │  autorização por usuário em TODA consulta
└──┬──────────┬────────────┘
   │          │
   │          ├────────────► Storage de objetos (local em dev, S3/MinIO/Supabase)
   │          │              imagens por usuário/cliente/simulação, URL assinada
   │          └────────────► Provedor de IA (Replicate · FLUX.1 Kontext)
   │                         chamado só depois de consentimento + foto válidos
┌──▼───────────────────────┐
│  PostgreSQL 16           │  9 tabelas, enums nativos, trigger de imutabilidade
└──────────────────────────┘
```

Monólito modular, como pede a seção 40 da especificação: sem filas, sem Redis, sem
microsserviços.

### 4.2 Stack e justificativa

| Escolha | Versão | Por quê |
| --- | --- | --- |
| Python | 3.11 | versão do ambiente; `match`, tipos nativos |
| FastAPI | 0.11x | OpenAPI automática (seção 35), validação por Pydantic, injeção de dependências — a autorização vira dependência reutilizável |
| Pydantic | 2.x | schemas de entrada/saída; nenhum objeto SQLAlchemy sai do router |
| SQLAlchemy | 2.x **síncrono** | o único I/O lento é a IA, que roda fora do request; o modo síncrono simplifica testes e Alembic. `async` seria complexidade sem ganho mensurável aqui |
| psycopg | 3 (binary) | driver atual, suporte a `timestamptz` e tipos nativos |
| Alembic | 1.x | migrations versionadas; `create_all()` **não** é usado |
| PyJWT + bcrypt | — | JWT HS256 e hash de senha com custo 12; sem `passlib` (sem manutenção ativa) |
| Pillow + OpenCV (headless) | — | decodificação real da imagem e detecção de rosto por Haar cascade, offline |
| httpx | — | chamadas ao provedor de IA, com timeout explícito |
| boto3 | — | driver S3/MinIO/Supabase (opcional; o padrão em dev é o disco) |
| pytest | — | unitários e integração |
| Docker Compose | — | `api` + `db`; o app Expo fica **fora** do Docker (precisa da rede do aparelho físico) — decisão exigida pela seção 4 da especificação |

### 4.3 Estrutura de pastas

```
backend/
├── app/
│   ├── main.py                  # app, CORS, handlers globais, startup
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings), .env
│   │   ├── security.py          # hash, JWT, assinatura de URL de imagem
│   │   ├── dependencies.py      # usuario_atual, cliente_do_usuario, sessao
│   │   └── erros.py             # ErroDeNegocio → resposta JSON padronizada
│   ├── db/{session.py,base.py}
│   ├── models/                  # usuario, cliente, consentimento, termo, ciencia,
│   │                            # imagem, simulacao, atendimento, agendamento
│   ├── schemas/                 # mesmos nomes, entrada e saída
│   ├── repositories/            # consultas; todas recebem usuario_id
│   ├── services/
│   │   ├── auth.py  consentimento.py  clientes.py  atendimentos.py
│   │   ├── agendamentos.py  termos.py  imagens.py  catalogo.py
│   │   ├── simulacao.py         # orquestra validação → storage → IA → persistência
│   │   ├── storage/{base.py,local.py,s3.py}
│   │   ├── ai/{base.py,replicate.py,fake.py,fabrica.py}
│   │   └── validacao_foto.py
│   ├── api/v1/{auth,usuarios,clientes,consentimentos,termos,simulacoes,
│   │            atendimentos,agendamentos,imagens,catalogo}.py
│   └── seed.py
├── migrations/                  # Alembic
├── tests/
├── alembic.ini  Dockerfile  docker-compose.yml  requirements.txt
├── .env.example  README.md
```

### 4.4 Banco de dados

Nove tabelas. As seis do `DOCUMENTACAO.md` §8.4 mais `termos`, `ciencias` e `imagens`
(achado A19). Nomes em `snake_case` português para manter a rastreabilidade com a Tabela 4
do TCC.

```
usuarios 1──N clientes 1──N consentimentos ──N:1── termos
   │             │  1──N simulacoes ──N:1── consentimentos   (qual decisão autorizou)
   │             │  1──N atendimentos ──0:1── simulacoes     (ON DELETE SET NULL)
   │             │  1──N agendamentos
   │             └──0:1── imagens                            (foto de perfil)
   ├──N ciencias ──N:1── termos
   └──N imagens  (entrada e saída das simulações)
```

**`usuarios`** — id (uuid, pk), nome, email (`citext` único), senha_hash, atuacao, ativo
(bool), criado_em, atualizado_em.

**`termos`** — id, tipo (`enum tipo_termo`: cliente | profissional), versao (text),
vigente_desde (date), titulo, resumo, secoes (`jsonb`, mesma forma de `Termo.secoes`),
vigente (bool), criado_em. `UNIQUE (tipo, versao)` e índice único parcial
`UNIQUE (tipo) WHERE vigente` — há exatamente uma versão vigente por tipo. *Trigger*
rejeita alteração de `tipo`, `versao`, `titulo`, `resumo` e `secoes`: só o campo `vigente`
pode mudar, o que atende “uma versão publicada não deve ser alterada silenciosamente”.

**`clientes`** — id, usuario_id (fk, `ON DELETE CASCADE`), nome, telefone,
data_nascimento (date, nulo), observacoes, foto_imagem_id (fk `imagens`, `ON DELETE SET
NULL`), criado_em, atualizado_em. Índice `(usuario_id, nome)`.

**`consentimentos`** — id, cliente_id (fk cascade), usuario_id (fk restrict — quem
registrou), decisao (`enum decisao_consentimento`: aceito | recusado | revogado),
termo_id (fk), versao_termo (text, cópia desnormalizada para leitura histórica),
registrado_em (timestamptz), forma_obtencao (`enum`: tela_dispositivo | lido_em_voz_alta |
termo_impresso), confirmado_por, responsavel_nome, responsavel_parentesco, faixa_etaria
(`enum`), observacao. Índice `(cliente_id, registrado_em DESC)`.
`pendente` **não é persistido** — é a ausência de registro, como pede a seção 7 da
especificação. *Trigger* `consentimentos_imutaveis`: `UPDATE` sempre falha; `DELETE` falha
a menos que o cliente já não exista (isto é, só em cascata da exclusão do cliente ou da
conta, que é o direito de eliminação do art. 18).

**`ciencias`** — id, usuario_id (fk cascade), termo_id (fk), versao, registrada_em.
Append-only pela mesma lógica; o estado `cienciaProfissional` do front-end passa a ser o
registro mais recente.

**`imagens`** — id, usuario_id (fk cascade), cliente_id (fk cascade, nulo), tipo (`enum`:
entrada | saida | perfil), chave_objeto (text, único), mime, bytes, largura, altura,
criado_em. **Só metadados**: o binário vive no storage de objetos (seção 19).

**`simulacoes`** — id, cliente_id (fk cascade), usuario_id (fk cascade),
consentimento_id (fk restrict, **not null**), img_entrada_id (fk), img_saida_id (fk,
nulo), estilo, cor, observacoes, provedor, modelo_ia, tempo_ms, status (`enum
status_simulacao`: processando | concluida | falhou), erro_codigo, erro_detalhe,
preferida (bool), criado_em, concluida_em. Índices `(cliente_id, criado_em DESC)` e
`UNIQUE (cliente_id) WHERE preferida`.
`consentimento_id` é uma adição ao modelo do TCC: **cada imagem gerada aponta para a
decisão de consentimento que a autorizou**. É a prova, no próprio banco, de que nenhuma
simulação existiu sem base legal.

**`atendimentos`** (`historico_servicos` no front-end) — id, cliente_id (fk cascade),
usuario_id (fk cascade), simulacao_id (fk `ON DELETE SET NULL`), descricao,
data_servico (date), observacoes, criado_em. O `SET NULL` é o que faz “excluir imagens não
apaga o atendimento” ser garantido pelo banco, e não por código.

**`agendamentos`** — id, cliente_id (fk cascade), usuario_id (fk cascade), data_hora
(timestamptz), servico, duracao_min (int, `CHECK BETWEEN 15 AND 480`), status (`enum
status_agendamento`: pendente | confirmado | cancelado | concluido), observacoes,
lembrete (bool), criado_em, atualizado_em. Índice `(usuario_id, data_hora)`.

Transições permitidas: `pendente → confirmado | cancelado`, `confirmado → concluido |
cancelado`; `cancelado` e `concluido` são finais (achado A14).

### 4.5 Autenticação e autorização

- `POST /auth/registrar` → cria usuário (e-mail único, senha ≥ 8 caracteres) e devolve os tokens;
- `POST /auth/login` → verifica bcrypt e devolve **access token (30 min)** e **refresh token (30 dias)**, ambos JWT HS256 com claim `tipo`;
- `POST /auth/renovar` → troca o refresh por um novo access;
- `JWT_SECRET` é obrigatório: a aplicação não sobe sem ele.

Autorização: **toda** consulta parte do `usuario_id` do token. Não existe repositório que
busque por id sem filtrar o dono. O acesso a um cliente passa pela dependência
`cliente_do_usuario`, que devolve 404 (e não 403) quando o cliente existe mas é de outro
profissional — não vazar a existência do registro é o comportamento correto. Assim,
“usuário B altera o id na URL” resulta em 404, e há teste para isso.

Recuperação de senha fica **fora do escopo**: exigiria provedor de e-mail. A tela já
informa isso ao usuário.

### 4.6 Imagens e storage

- interface `ArmazenamentoObjetos`: `salvar`, `obter`, `url_assinada`, `excluir`, `excluir_prefixo`;
- `local.py` (padrão em desenvolvimento): grava em `STORAGE_DIR`, com nome derivado de UUID — nunca do nome enviado pelo cliente (protege contra *path traversal*);
- `s3.py`: compatível com MinIO, AWS S3 e Supabase Storage, via `STORAGE_*` no `.env`;
- chave do objeto: `usuarios/{usuario}/clientes/{cliente}/simulacoes/{simulacao}/{entrada|saida}.jpg`;
- **nenhuma URL pública permanente**: `GET /api/v1/imagens/{id}?t=<assinatura>` aceita um token HMAC com validade de 10 minutos, ligado ao id da imagem e ao usuário. O driver S3 usa URL pré-assinada equivalente. O `<Image>` do React Native consome a URL sem precisar de cabeçalho;
- limites documentados: ≤ 8 MB, `image/jpeg|png|webp`, menor lado ≥ 480 px, maior lado ≤ 4096 px.

### 4.7 Validação da foto no servidor (antes da IA)

Em ordem, com código de erro próprio para cada caso: tamanho do arquivo → MIME real
(decodificação, não extensão) → dimensões → proporção ≤ 1,35 → luminância média entre 40 e
230 → **detecção de rosto** (Haar cascade do OpenCV, um rosto frontal no quadro).
Se qualquer item falhar, a resposta é 422 com a lista de problemas no mesmo formato que a
tela `simulacao/recusada.tsx` já exibe — e **nenhuma chamada paga é feita**.

### 4.8 Provedor de IA

Comparação objetiva (seção 17 da especificação):

| Provedor / modelo | image-to-image | Preserva identidade | Latência típica | Custo | Integração | Observações |
| --- | --- | --- | --- | --- | --- | --- |
| **Replicate · `flux-kontext-apps/change-haircut`** (FLUX.1 Kontext pro) | sim, **especializado em cabelo**: recebe `input_image`, `haircut`, `hair_color`, `gender` | alta (edição por instrução, não regeneração) | ~5–15 s | ~US$ 0,04/execução, pago por uso | REST simples: cria predição e consulta até concluir | documentação boa; saídas em CDN temporária |
| Replicate · SDXL img2img (o que o mock citava) | sim, genérico | **baixa**: reconstrói o rosto, quebra a semelhança | ~5–10 s | ~US$ 0,01 | igual | tecnicamente inadequado para o caso de uso |
| fal.ai · FLUX Kontext | sim | alta | ~4–10 s | semelhante | REST + SDK | alternativa direta; exige outra conta |
| Google Gemini (imagem) | sim, edição por instrução | alta | ~5–10 s | baixo | REST | bom resultado, porém política de retenção/treino menos transparente para foto de rosto |
| Black Forest Labs (API direta) | sim | alta | ~5–10 s | menor por chamada | REST | menos exemplos e tooling |
| Modelo local (Stable Diffusion próprio) | sim | média | muito alta sem GPU | custo de infra | complexo | inviável para demonstração de TCC |

**Escolha: Replicate com `flux-kontext-apps/change-haircut`.** É o único candidato
*especializado na tarefa do TCC*, e seus parâmetros de entrada correspondem exatamente a
`ParametrosSimulacao` (estilo → `haircut`, cor → `hair_color`). Preservar o rosto é
requisito implícito do produto: uma simulação que troca a face não serve para mostrar ao
cliente. O custo por uso dispensa infraestrutura e o modelo de "criar predição + consultar"
encaixa no fluxo assíncrono da seção 4.9.

Desacoplamento (seção 17): `services/ai/base.py` define `ProvedorIA.gerar(entrada) ->
SaidaSimulacao`; `replicate.py` implementa a chamada real; `fake.py` gera o resultado
localmente com Pillow, para desenvolvimento, testes e demonstração sem credencial;
`fabrica.py` escolhe por `AI_PROVIDER`. Nenhum outro módulo importa `replicate`.

A chave **nunca** vai para o aplicativo: `AI_API_KEY` só existe no `.env` do servidor.

### 4.9 Fluxo da simulação — assíncrono com consulta

Decisão (seção 29): **assíncrono simples, sem fila**.

```
POST /api/v1/simulacoes  (multipart: cliente_id, estilo, cor, observacoes, foto)
  1 autenticação                       401
  2 cliente pertence ao usuário        404
  3 consentimento aceito e na versão vigente   403  ← regra crítica da seção 8
  4 validação da foto                  422  (antes de qualquer custo)
  5 upload da entrada no storage
  6 cria simulacoes(status=processando, consentimento_id=<decisão que autorizou>)
  → 202 { id, status: "processando" }
  (BackgroundTask) chama o provedor → upload da saída → status=concluida | falhou

GET /api/v1/simulacoes/{id}   → processando | concluida (com URL assinada) | falhou
```

O aplicativo já tem a tela `simulacao/processando.tsx` com barra de progresso: ela passa a
consultar o estado a cada 1,5 s. Nada de Celery ou Redis. Limitação assumida e
documentada: se o servidor reiniciar durante uma geração, a simulação fica `processando`;
uma rotina de inicialização marca como `falhou` tudo que estiver `processando` há mais de
5 minutos.

Consistência (seção 30): a linha só vira `concluida` depois do upload da saída; falha do
provedor grava `falhou` + `erro_codigo` e **não** cria simulação concluída; falha no banco
após o upload remove o objeto órfão no `except`.

### 4.10 Exclusão de dados

| Operação | Efeito |
| --- | --- |
| `DELETE /clientes/{id}/simulacoes` | apaga os objetos do storage, as linhas de `simulacoes` e de `imagens`; `atendimentos.simulacao_id` → `NULL`; **consentimentos preservados** |
| `DELETE /clientes/{id}` | exclusão física em cascata (consentimentos, simulações, atendimentos, agendamentos) + remoção do prefixo do storage |
| `DELETE /usuarios/me` | exclusão física de tudo que pertence ao profissional, incluindo credencial, + remoção do prefixo; exige a senha atual no corpo da requisição |

Estratégia escolhida para a conta: **exclusão física**. Alternativas consideradas:
*soft delete* mantém dado pessoal vivo, o que contraria o art. 18, VI; anonimização
preservaria metadados de imagens de terceiros sem utilidade, já que o profissional é o
controlador e, ao sair, não há mais finalidade. Impacto registrado: o sistema não guarda
comprovante das decisões depois da exclusão — em produção, o caminho correto seria
exportar um recibo assinado antes de apagar. Isso será documentado como limitação.

### 4.11 API

Prefixo `/api/v1`. Reconciliada com o `DOCUMENTACAO.md` §8.5 (todos os endpoints
propostos lá existem aqui).

| Método | Rota | Observação |
| --- | --- | --- |
| POST | `/auth/registrar` | RF01 |
| POST | `/auth/login` | RF01 |
| POST | `/auth/renovar` | refresh |
| GET/PATCH | `/usuarios/me` | perfil |
| DELETE | `/usuarios/me` | exige senha |
| GET/POST | `/usuarios/me/ciencia` | ciência das responsabilidades |
| GET/POST | `/clientes` | RF02 |
| GET/PATCH/DELETE | `/clientes/{id}` | RF02 |
| POST/DELETE | `/clientes/{id}/foto` | foto de perfil |
| GET | `/clientes/{id}/consentimento` | decisão atual + necessidade de revalidação |
| GET/POST | `/clientes/{id}/consentimentos` | histórico e nova decisão (inclui revogação) |
| GET | `/clientes/{id}/historico` · `/simulacoes` · `/agendamentos` | consultas da tela de perfil |
| DELETE | `/clientes/{id}/simulacoes` | RNF05 |
| GET | `/termos/{tipo}` e `/termos/{tipo}/{versao}` | vigente e versão específica |
| POST | `/simulacoes` | RF04 — 202 |
| GET | `/simulacoes/{id}` | RF05 — estado |
| GET | `/simulacoes` | lista por cliente (RF07) |
| POST | `/simulacoes/{id}/preferida` | RF07 |
| GET/POST | `/atendimentos` · GET/PATCH `/atendimentos/{id}` | RF03 |
| GET/POST | `/agendamentos` · GET/PATCH/DELETE `/agendamentos/{id}` | RF06 |
| PATCH | `/agendamentos/{id}/status` | transições validadas |
| GET | `/imagens/{id}` | URL assinada, 10 min |
| GET | `/catalogo` | estilos, cores e serviços válidos |
| GET | `/saude` | diagnóstico (banco, storage, provedor) |

Erros padronizados: `{ "erro": { "codigo": "...", "mensagem": "...", "detalhes": [...] } }`,
com 401 (sem token), 403 (consentimento inválido), 404 (não é seu / não existe),
409 (conflito, como e-mail repetido), 422 (validação), 502 (provedor de IA indisponível),
503 (storage). Mensagem legível para o usuário; detalhe técnico só no log.

### 4.12 Catálogo (seção 23)

Fica **no front-end** como catálogo de exibição — é fixo e faz parte da lógica da
interface. O servidor, porém, passa a ser dono do **mapeamento para os parâmetros do
provedor** (`estilo`/`cor` em português → `haircut`/`hair_color`) e valida as opções
recebidas; `GET /catalogo` publica a lista para o app conferir. Não se torna tabela:
não há administração em tempo de execução que justifique isso. O campo
`OpcaoCor.tonalizacao` será removido, porque existia só para fabricar a falsa simulação.

---

## 5. Mudanças previstas no front-end

Cirúrgicas, preservando a interface (seção 26) e mantendo `Context + useReducer`
(seção 27 — continua adequado: o volume de dados é pequeno e o fluxo é por tela).

| Arquivo | Mudança |
| --- | --- |
| **novo** `src/services/api/cliente.ts` | `fetch` tipado: base URL por `EXPO_PUBLIC_API_URL`, `Authorization`, renovação em 401, timeout, erros traduzidos |
| **novo** `src/services/api/{auth,clientes,consentimentos,termos,simulacoes,atendimentos,agendamentos,catalogo}.ts` | um módulo por recurso |
| **novo** `src/data/sessao.tsx` | token em `expo-secure-store` (nativo) com queda para `AsyncStorage` na web |
| **novo** `app/cadastro.tsx` | criação de conta real (achado A3) |
| `src/data/store.tsx` | ações passam a ser `async` e falham com erro tratado; carga inicial por HTTP; `AsyncStorage` deixa de guardar dado sensível (A13) |
| `src/services/authService.ts` | mock → HTTP |
| `src/services/simulacaoService.ts` | mock → upload + consulta de estado |
| `src/services/consentService.ts` | mantém as funções puras de interface; a autoridade passa a ser o servidor (A6) |
| `src/data/termos.ts` | textos migram para o banco; o módulo passa a tipar e cachear o que vem da API |
| `src/data/seed.ts` | removido (o seed passa a ser do banco) |
| `src/data/catalogo.ts` | sai `tonalizacao` (A7) |
| `src/components/ImagemSimulada.tsx` | exibe a imagem gerada, sem camada de cor |
| `app/login.tsx` | sem credenciais pré-preenchidas (A2); “Criar conta” leva ao cadastro |
| `app/simulacao/{captura,processando,resultado,comparar,indisponivel}.tsx` | upload, polling, URL assinada, erro de provedor |
| `app/consentimento/[clienteId].tsx`, `app/termo/[clienteId].tsx` | POST e leitura de versão pela API |
| `app/cliente/{[id],editar}.tsx`, `app/atendimento/novo.tsx`, `app/agendamento/novo.tsx` | CRUD por HTTP, estados de carregamento e erro |
| `app/privacidade.tsx` | exclusões reais; texto do A12 corrigido |
| `app/(tabs)/*.tsx` | estados de carregando/erro/offline nas listas |
| `app/responsabilidades.tsx` | ciência persistida no servidor |
| `package.json`, `app.json` | `expo-secure-store`; `extra.apiUrl` |

---

## 6. Decisões técnicas registradas

Formato Problema → Alternativas → Escolha → Justificativa → Impacto (seção 36).

1. **SQLAlchemy síncrono** · alternativas: `async`. Escolha: síncrono. O único I/O lento roda em background; testes e migrations ficam mais simples. Impacto: nenhum no contrato da API.
2. **Imutabilidade por trigger** · alternativas: só disciplina no serviço. Escolha: trigger no banco. É o argumento verificável do TCC: nem um `UPDATE` manual altera o histórico. Impacto: `DELETE` só em cascata.
3. **`simulacoes.consentimento_id` obrigatório** · alternativas: só validar no serviço. Escolha: coluna obrigatória. Liga cada imagem à decisão que a autorizou. Impacto: acréscimo ao modelo do TCC (documentar na Tabela 4).
4. **Simulação assíncrona com polling** · alternativas: síncrona (risco de timeout) ou Celery/Redis (proibido pela seção 29). Escolha: `BackgroundTasks` + `GET /simulacoes/{id}`. Impacto: tela de processamento passa a consultar; simulações presas são expiradas na inicialização.
5. **Replicate / FLUX.1 Kontext `change-haircut`** · alternativas na tabela §4.8. Escolha justificada pela preservação da identidade e pela correspondência de parâmetros. Impacto: `modelo_ia` deixa de ser “SDXL img2img”; a documentação e o TCC precisam ser atualizados.
6. **Provedor `fake` como padrão de desenvolvimento** · alternativa: exigir chave sempre. Escolha: `AI_PROVIDER=fake` roda tudo sem credencial e sem custo; `replicate` é a configuração real. Impacto: permite demonstração e teste offline — e deixa claro na documentação quando o resultado é sintético.
7. **Storage local em dev, S3 em produção** · alternativas: MinIO obrigatório (mais um container), binário no Postgres (vedado pela seção 19). Escolha: mesma interface, dois drivers. Impacto: `docker compose up` não precisa de MinIO.
8. **URL assinada por HMAC** · alternativas: URL pública (vedada) ou cabeçalho `Authorization` no `<Image>` (não suportado de forma confiável). Escolha: token curto na query, 10 min. Impacto: nenhuma imagem sensível fica acessível de forma permanente.
9. **404 em vez de 403 para recurso de outro usuário** · Escolha: 404. Não revela que o id existe. Impacto: teste de isolamento verifica 404.
10. **Exclusão física da conta** · ver §4.10.
11. **Catálogo permanece no app** · ver §4.12.
12. **Senha exigida para excluir a conta** · alternativa: só o JWT. Escolha: reconfirmar a senha, por ser a operação irreversível mais sensível. Impacto: pequena mudança na tela de privacidade.

---

## 7. O que continua fora do escopo

- **RF08 — recomendação automática de estilo**: permanece `won't have`, conforme o TCC (seção 38 da especificação). Será marcado como tal na matriz de rastreabilidade.
- **Recuperação de senha**: exige provedor de e-mail.
- **Notificações de lembrete**: o campo é persistido; o agendamento de notificação não é implementado.
- **Filas, Redis, Celery, Kubernetes**: explicitamente evitados (seção 40).

## 8. Limitações do ambiente desta sessão (transparência)

| Limitação | Consequência | Como fica contornada |
| --- | --- | --- |
| Sem daemon do Docker neste contêiner | `docker compose up` não pode ser executado aqui | `Dockerfile` e `docker-compose.yml` são entregues e conferidos; a validação roda contra o **PostgreSQL 16 instalado localmente** (já no ar), com as mesmas migrations |
| `api.replicate.com` bloqueado pelo proxy e sem credencial | a chamada paga real não pode ser executada aqui | integração implementada e testada com HTTP simulado; a execução de ponta a ponta usa o provedor `fake`. **Não declararei como testada uma chamada real que não ocorreu** — você faz isso na sua máquina com `AI_API_KEY` |
| `docs.expo.dev` bloqueado | sem consulta à documentação Expo online | versões vêm de `node_modules/expo/bundledNativeModules.json` e os contratos, dos `.d.ts` dos pacotes |

## 9. Plano de execução

| Etapa | Entrega | Verificação |
| --- | --- | --- |
| 3 | models, migrations Alembic, constraints, índices, triggers, seed com os 7 cenários | `alembic upgrade head` do zero no Postgres local; seed executado |
| 4 | configuração, auth, autorização, CRUD, consentimento, termos, imagens, agenda, histórico | OpenAPI gerada; chamadas reais via `httpx` |
| 5 | validação da foto, `services/ai/*`, `POST /simulacoes` assíncrono, preferida | simulação completa com provedor `fake`; teste do `replicate` com HTTP simulado |
| 6 | cliente HTTP, sessão, store assíncrono, telas | `tsc --noEmit` limpo; app web falando com a API real |
| 7 | pytest unitário e de integração + os 7 casos críticos da seção 33 | suíte verde, com saída no relatório |
| 8 | revisão de segurança e varredura de segredos | checklist da seção 31 item a item |
| 9 | `backend/README.md`, documentação acadêmica, matriz RF01–RF08/RNF05 | revisão cruzada com o TCC |
| 10 | execução do fluxo completo da seção 44 e dos fluxos de erro | roteiro Playwright contra a API real + relatório final de 15 seções |

A implementação começa agora pela Etapa 3.
