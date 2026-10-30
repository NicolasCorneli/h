# Espelho — Back-end, banco de dados e integração

Documentação técnica e acadêmica da segunda etapa do projeto: a transformação do
protótipo de interface em um sistema funcional de ponta a ponta.

O texto está escrito para ser aproveitado na redação do TCC — especialmente nas seções de
metodologia, implementação e resultados. Os capítulos 1 a 7 descrevem o que foi
construído; o 8 registra as decisões arquiteturais no formato problema → alternativas →
escolha → justificativa → impactos; o 9 traz a matriz de rastreabilidade com os
requisitos; o 10 lista o que mudou em relação ao protótipo e o 11, as limitações.

Documentos relacionados:

- [`DIAGNOSTICO-E-ARQUITETURA.md`](historico/DIAGNOSTICO-E-ARQUITETURA.md) — auditoria do protótipo e arquitetura proposta antes da implementação;
- [`backend/README.md`](../backend/README.md) — manual de operação (executar, configurar, testar);
- [`DOCUMENTACAO.md`](DOCUMENTACAO.md) — documentação da interface.

---

## 1. Resumo

O protótipo funcionava inteiramente no aparelho: dados fictícios em memória, persistência
em `AsyncStorage`, autenticação simulada e uma "simulação" que devolvia a própria foto do
cliente com uma camada de cor por cima. Esta etapa substituiu cada uma dessas peças por
uma implementação real:

| Antes | Agora |
| --- | --- |
| `authService` aceitava qualquer e-mail válido | cadastro e login com senha em bcrypt e sessão por JWT |
| dados fictícios em `src/data/seed.ts` | PostgreSQL 16 com nove tabelas e migrations versionadas |
| consentimento validado só na interface | validado no servidor, com histórico imutável garantido por gatilho |
| textos do termo no pacote do aplicativo | tabela `termos`, com versões e indicação de vigência |
| `setTimeout` de 2,6 s devolvendo a foto de entrada | upload, validação, chamada ao provedor de IA e persistência do resultado |
| imagens como caminhos locais do aparelho | storage de objetos, com URL assinada de curta duração |
| nenhuma separação entre contas | isolamento por usuário em toda consulta, verificado por testes |

O sistema completo é: **aplicativo Expo → API FastAPI → PostgreSQL / storage de objetos /
provedor de IA**.

---

## 2. Arquitetura

### 2.1 Visão geral

```
┌──────────────────────────────┐
│  Aplicativo (Expo / RN)      │  Context + useReducer
│  src/services/api/*          │  cliente HTTP, token em armazenamento seguro
└───────────────┬──────────────┘
                │ HTTPS · Authorization: Bearer <JWT>
┌───────────────▼──────────────┐
│  API (FastAPI)               │  routers → services → repositories → models
│  /api/v1                     │  autorização por usuário em toda consulta
└───┬───────────┬──────────────┘
    │           │
    │           ├────────────► Storage de objetos (disco em dev; S3/MinIO/Supabase)
    │           │              imagens por usuário/cliente/simulação · URL assinada
    │           └────────────► Provedor de IA (Replicate · FLUX.1 Kontext)
    │                          acionado só após consentimento e foto válidos
┌───▼──────────────────────────┐
│  PostgreSQL 16               │  9 tabelas · enums nativos · gatilhos de imutabilidade
└──────────────────────────────┘
```

A arquitetura é um **monólito modular**: um processo, uma base de dados, módulos separados
por responsabilidade. Para um sistema com um usuário por instalação e algumas dezenas de
clientes por profissional, qualquer distribuição adicional acrescentaria custo
operacional sem resolver problema existente.

### 2.2 Comunicação entre os componentes

| De | Para | Como |
| --- | --- | --- |
| Aplicativo | API | HTTP/JSON em camelCase; `multipart/form-data` no envio da foto |
| Aplicativo | Imagens | `GET /api/v1/imagens/{id}?t=<assinatura>`, sem cabeçalho de autorização |
| API | PostgreSQL | SQLAlchemy 2.x, síncrono, com pool e `pool_pre_ping` |
| API | Storage | interface `ArmazenamentoObjetos`; driver escolhido por configuração |
| API | Provedor de IA | HTTPS com `httpx`; a foto vai como *data URI* no corpo |

### 2.3 Organização em camadas

```
api/v1/        rotas: traduzem HTTP ↔ domínio. Não consultam o banco diretamente.
services/      regras de negócio: consentimento, simulação, imagens, agenda, auth.
repositories/  consultas SQLAlchemy — todas recebem o usuário autenticado e filtram por ele.
models/        tabelas.
schemas/       contratos de entrada e saída (Pydantic). Nenhum objeto do ORM sai do router.
core/          configuração, segurança, dependências, erros e proteções de borda.
```

A separação não é formalidade: ela é o que permite afirmar, com uma leitura só, que
nenhuma rota acessa dado de cliente sem passar pela verificação de propriedade — as
consultas estão todas em `repositories/consultas.py`, e não há nenhuma que busque por
identificador sem dono.

### 2.4 Tecnologias e justificativas

| Escolha | Versão | Por quê |
| --- | --- | --- |
| Python | 3.11 | tipagem moderna; base ampla de bibliotecas de imagem |
| FastAPI | 0.142 | OpenAPI automática, validação por Pydantic e injeção de dependências — a autorização vira uma dependência reutilizável |
| Pydantic | 2.13 | contratos explícitos; o JSON sai em camelCase por gerador de alias |
| SQLAlchemy | 2.1, síncrono | o único I/O lento (a IA) roda fora da requisição; o modo síncrono simplifica testes e migrations |
| Alembic | 1.20 | banco construído por migrations versionadas, nunca por `create_all()` |
| PostgreSQL | 16 | enums nativos, `jsonb`, índices parciais e gatilhos — recursos usados de fato |
| PyJWT + bcrypt | — | JWT HS256 e hash com custo 12, sem dependências intermediárias |
| Pillow + OpenCV | — | decodificação real e detecção de rosto, localmente |
| httpx | 0.28 | chamadas ao provedor com tempo limite explícito |
| pytest | 9.1 | 310 testes, 94% de cobertura |

---

## 3. Banco de dados

### 3.1 Modelo conceitual

Um **profissional** mantém uma carteira de **clientes**. Cada cliente registra, ao longo
do tempo, **decisões de consentimento** sobre o uso da própria imagem; cada decisão
aponta para a **versão do termo** que lhe foi apresentada. Autorizado o uso, o
profissional gera **simulações** a partir de **imagens**, registra os **atendimentos**
executados e organiza os **agendamentos**. O profissional também registra a própria
**ciência** das responsabilidades.

### 3.2 Modelo lógico

```
usuarios 1──N clientes 1──N consentimentos ──N:1── termos
   │             │  1──N simulacoes ──N:1── consentimentos   (decisão que autorizou)
   │             │  1──N atendimentos ──0:1── simulacoes     (ON DELETE SET NULL)
   │             │  1──N agendamentos
   │             └──0:1── imagens (tipo = perfil)
   ├──N ciencias ──N:1── termos
   └──N imagens  (entrada e saída das simulações)
```

### 3.3 Tabelas

Chave primária `uuid` em todas, gerada na aplicação. Datas e instantes em `timestamptz`;
datas sem hora em `date`.

**`usuarios`** — `nome`, `email` (único, guardado em minúsculas), `senha_hash`, `atuacao`,
`ativo`, `criado_em`, `atualizado_em`.

**`termos`** — `tipo` (`cliente` | `profissional`), `versao`, `vigente_desde`, `vigente`,
`titulo`, `resumo`, `secoes` (`jsonb`). `UNIQUE (tipo, versao)` e índice único parcial
`(tipo) WHERE vigente`: existe exatamente uma versão vigente por tipo.

**`clientes`** — `usuario_id` (cascata), `nome`, `telefone`, `data_nascimento` (opcional),
`observacoes`, `criado_em`, `atualizado_em`. Índice `(usuario_id, nome)`.

**`consentimentos`** — `cliente_id`, `usuario_id`, `decisao` (`aceito` | `recusado` |
`revogado`), `termo_id`, `versao_termo`, `registrado_em`, `forma_obtencao`,
`confirmado_por`, `responsavel_nome`, `responsavel_parentesco`, `faixa_etaria`,
`observacao`. Índice `(cliente_id, registrado_em)`. **`pendente` não é persistido**:
ausência de registro é ausência de decisão.

**`ciencias`** — `usuario_id`, `termo_id`, `versao`, `registrada_em`.

**`imagens`** — `usuario_id`, `cliente_id`, `tipo` (`entrada` | `saida` | `perfil`),
`chave_objeto` (única), `mime`, `bytes`, `largura`, `altura`, `criado_em`. Só metadados: o
arquivo vive no storage. Índice único parcial `(cliente_id) WHERE tipo = 'perfil'`.

**`simulacoes`** — `cliente_id`, `usuario_id`, **`consentimento_id`**, `img_entrada_id`,
`img_saida_id`, `estilo`, `cor` (a descrição pedida, até 300 caracteres, ou "Corte
atual"/"Cor atual"), `genero` (gênero do corte, o valor do campo `gender` do modelo:
`none` | `male` | `female`, padrão `none`), `observacoes`, `status` (`processando` | `concluida` | `falhou`),
`provedor`, `modelo_ia`, `instrucao_ia` (o que foi pedido ao modelo), `tempo_ms`,
`erro_codigo`, `erro_detalhe`, `preferida`, `chave_envio`, `criado_em`, `concluida_em`.
Índices `(cliente_id, criado_em)`, único parcial `(cliente_id) WHERE preferida` e único
parcial `(usuario_id, chave_envio)`.

**`atendimentos`** — `cliente_id`, `usuario_id`, `simulacao_id` (`ON DELETE SET NULL`),
`descricao`, `data_servico`, `observacoes`, `criado_em`.

**`agendamentos`** — `cliente_id`, `usuario_id`, `data_hora`, `servico`, `duracao_min`,
`status`, `observacoes`, `lembrete`, `criado_em`, `atualizado_em`.

### 3.4 Restrições de integridade

Além das chaves estrangeiras, o banco carrega regras que não dependem do código da
aplicação:

| Restrição | O que garante |
| --- | --- |
| `uq_simulacoes_preferida_por_cliente` (índice único parcial) | no máximo uma simulação preferida por cliente |
| `uq_termos_vigente_por_tipo` (índice único parcial) | exatamente uma versão vigente por tipo de termo |
| `uq_imagens_perfil_por_cliente` (índice único parcial) | no máximo uma foto de perfil por cliente |
| `ck_simulacoes_saida_coerente_com_status` | só é `concluida` quem tem imagem de saída |
| `ck_simulacoes_preferida_concluida` | simulação que falhou não pode ser a preferida |
| `ck_consentimentos_responsavel_completo` | nome e parentesco do responsável vêm juntos ou não vêm |
| `ck_agendamentos_duracao_plausivel` | duração entre 15 e 480 minutos |
| `atendimentos.simulacao_id ON DELETE SET NULL` | excluir imagens não apaga o histórico de atendimentos |

### 3.5 Imutabilidade garantida pelo banco

Três gatilhos em PL/pgSQL, criados na migration inicial:

- **`consentimentos_imutaveis`** — `UPDATE` sempre falha. `DELETE` só é aceito quando o
  cliente **ou** a conta já não existem, isto é, apenas em cascata do direito de
  eliminação. Uma exclusão isolada de um registro de decisão é recusada.
- **`ciencias_imutaveis`** — mesma lógica, com a conta como pai.
- **`termos_imutaveis`** — uma versão publicada não muda: alterações em `tipo`, `versao`,
  `titulo`, `resumo`, `vigente_desde` ou `secoes` são recusadas. Só a marcação `vigente`
  pode mudar, que é o que permite publicar uma versão nova.

É a diferença entre afirmar que o histórico é imutável e **demonstrar** que é: nem um
`UPDATE` manual no banco reescreve uma decisão registrada. Há testes que atacam as tabelas
por SQL direto para comprovar isso (`tests/test_imutabilidade.py`).

### 3.6 Migrations

Duas, aplicáveis do zero:

1. `3de36fc61782` — estrutura: tabelas, enums, índices, constraints e os três gatilhos;
2. `b1a7c0dfe201` — publicação dos termos iniciais (cliente 1.0 e 0.9, profissional 1.0),
   migrados do antigo `src/data/termos.ts`.

Os termos são **dados de sistema**, não de demonstração: sem um termo vigente o aplicativo
não pode registrar consentimento algum. A migration de volta (`downgrade`) recusa-se a
remover versões já apresentadas a alguém, com mensagem explícita, em vez de falhar com
erro de integridade.

---

## 4. Autenticação e autorização

### 4.1 Autenticação

- **Cadastro** (`POST /auth/registrar`): e-mail único, senha de no mínimo 8 caracteres,
  guardada como hash **bcrypt com custo 12**. A senha em texto não é registrada em lugar
  nenhum — nem em log.
- **Login** (`POST /auth/login`): verificação do hash e emissão de dois tokens JWT HS256 —
  **acesso** (30 minutos) e **renovação** (30 dias), distinguidos por uma *claim* `tipo`,
  de modo que um não serve no lugar do outro.
- **Renovação** (`POST /auth/renovar`): o aplicativo troca o token de renovação por um de
  acesso novo quando recebe 401, de forma transparente para as telas.
- E-mail inexistente e senha errada produzem **a mesma resposta**, e a verificação roda
  mesmo sem usuário (contra um hash descartável), para que o tempo de resposta não revele
  se o e-mail está cadastrado.

`JWT_SECRET` é obrigatório e precisa ter ao menos 32 caracteres: sem ele a aplicação não
sobe. Não há valor padrão.

### 4.2 Autorização

Toda consulta parte do identificador contido no token. A dependência `cliente_do_usuario`
é o ponto único por onde passa qualquer acesso a dados de cliente:

```python
cliente = sessao.scalar(
    select(Cliente).where(Cliente.id == cliente_id, Cliente.usuario_id == usuario.id)
)
if cliente is None:
    raise NaoEncontrado("Cliente não encontrado.")
```

Trocar o identificador na URL resulta em **404**, e não em 403: responder "não é seu"
confirmaria que aquele registro existe. Há teste cobrindo nove rotas diferentes do mesmo
cliente a partir de outra conta (`tests/test_clientes.py`), além do caso crítico nº 4.

---

## 5. Consentimento e LGPD

### 5.1 O modelo adotado

O consentimento pertence ao **cliente**, titular da imagem (art. 5º, XII), e é registrado
pelo profissional, que responde pela informação prestada. Cada decisão gera um registro
novo; revogar **não** altera o aceite anterior.

```
(sem registro) ──aceita──► aceito ──revoga──► revogado ──aceita de novo──► aceito
       │                      │
       └──recusa──► recusado ─┘  (recusar não impede aceitar depois)
```

### 5.2 A regra crítica

Antes de qualquer imagem chegar ao provedor de IA, o servidor verifica, nesta ordem:

1. o cliente existe;
2. o cliente pertence ao usuário autenticado;
3. existe decisão registrada;
4. a decisão atual é `aceito`;
5. a versão aceita é a vigente.

Qualquer falha interrompe o fluxo com **403** e um motivo legível (`pendente`,
`recusado`, `revogado`, `revalidar`). A verificação está em
`services/consentimento.liberar_captura`, chamada por `services/simulacao.criar` antes da
validação da foto e antes de qualquer upload.

O aplicativo também verifica — mas isso é conveniência de interface, para não abrir a
câmera à toa. O controle de acesso é o do servidor, e ele vale mesmo que alguém chame a
API diretamente.

### 5.3 Vínculo entre a imagem e a autorização

`simulacoes.consentimento_id` é obrigatório: **cada imagem gerada aponta para a decisão
que a autorizou**. É uma adição ao modelo descrito no pré-projeto, e dá ao sistema uma
propriedade útil para o TCC — a prova de base legal não depende de interpretação de log,
está na própria chave estrangeira.

### 5.4 Menores de idade

`data_nascimento` é opcional. Quando informada, o servidor calcula a idade e, abaixo de
18 anos, **exige** nome e parentesco do responsável legal; sem isso, recusa o registro com
`responsavel_obrigatorio` (art. 14, §1º). A faixa etária apurada no momento da decisão
fica gravada no registro. O critério é mais rígido do que a letra da lei, que trata
especificamente de crianças: a extensão a adolescentes é uma precaução já adotada no
protótipo e mantida aqui.

Sem data de nascimento não há como inferir idade, e a exigência não se aplica — limitação
registrada na seção 11.

### 5.5 Versionamento dos termos

A versão do termo **não** é enviada pelo aplicativo: quem define é o servidor, a partir da
versão vigente. Essa inversão corrige uma fragilidade real do protótipo, onde um aplicativo
desatualizado registraria um aceite sobre um texto que não é mais o apresentado.

Publicada uma versão nova, os aceites anteriores continuam válidos como registro histórico,
mas deixam de liberar a captura: o resumo passa a indicar `revalidar`, e o termo novo
precisa ser apresentado. A tela de consulta mostra **o texto exato da versão que aquele
cliente aceitou**, buscado por número de versão; se o servidor não tiver mais aquele texto,
a tela avisa — e não exibe outro no lugar.

### 5.6 Exclusão (art. 18, VI)

| Operação | Efeito |
| --- | --- |
| `DELETE /clientes/{id}/simulacoes` | apaga objetos do storage, simulações e metadados de imagem; `atendimentos.simulacao_id` vira `NULL` pela chave estrangeira; **consentimentos preservados** |
| `DELETE /simulacoes/{id}` | uma simulação só: apaga ela e as duas imagens dela (entrada e saída), no banco e no storage; `atendimentos.simulacao_id` vira `NULL`; foto de perfil e consentimentos preservados. Em processamento responde 409 `simulacao_em_processamento` |
| `DELETE /usuarios/me/imagens` | o mesmo, para todos os clientes da conta |
| `DELETE /clientes/{id}` | exclusão física em cascata + remoção do prefixo no storage |
| `DELETE /usuarios/me` | exclusão física de tudo, exigindo a senha novamente |

A estratégia de exclusão da conta é **física**, não anonimização nem *soft delete*: o
profissional é o controlador dos dados e, ao encerrar a conta, não resta finalidade que
justifique manter dado pessoal de terceiros. O impacto está assumido e documentado: o
sistema não guarda comprovante das decisões depois da exclusão.

### 5.7 Transparência sobre o terceiro

O termo do cliente continua afirmando, em seção destacada, que a foto é enviada a uma
empresa terceira e que **não há controle** sobre quanto tempo ela a mantém nem sobre o uso
para treinamento. A implementação não enfraquece essa informação em nenhum ponto; ao
contrário, ela passou a ser verdade literal, já que agora a imagem realmente sai do
aparelho.

### 5.8 Minimização

A imagem aprovada é recodificada em JPEG antes de ser guardada ou enviada, o que **remove
os metadados EXIF** — inclusive data, modelo do aparelho e coordenadas de GPS que a câmera
possa ter embutido. Só os pixels necessários seguem adiante. Há teste para isso
(`test_metadados_exif_sao_descartados`).

---

## 6. Imagens

### 6.1 Armazenamento

O PostgreSQL guarda apenas metadados; o binário vai para um storage de objetos, atrás da
interface `ArmazenamentoObjetos` (`salvar`, `obter`, `excluir`, `excluir_prefixo`,
`url_temporaria`). Dois drivers:

- **`local`** — disco, padrão em desenvolvimento: dispensa contêiner extra e funciona sem rede;
- **`s3`** — compatível com AWS S3, MinIO e Supabase Storage.

A chave do objeto é derivada de identificadores do sistema, nunca do nome enviado pelo
cliente:

```
usuarios/{usuario}/clientes/{cliente}/simulacoes/{simulacao}/entrada-<hex>.jpg
```

O formato por prefixo é o que torna a exclusão em massa barata: apagar um cliente é
remover um prefixo.

### 6.2 Entrega por URL assinada

Nenhuma imagem tem endereço público permanente. Cada uma é servida por
`GET /api/v1/imagens/{id}?t=<assinatura>`, onde a assinatura é um HMAC-SHA256 do trio
*imagem + dono + expiração*, válida por 10 minutos.

Esta é a única rota sem `Authorization`, por um motivo técnico: o componente `<Image>` do
React Native não envia cabeçalhos de forma confiável. A autorização, portanto, está na
assinatura — que só este servidor consegue produzir, e apenas para aquele par
imagem/dono. Com o driver S3, o endpoint redireciona para uma URL pré-assinada
equivalente. O cabeçalho de resposta é `Cache-Control: private`, para que nenhum
intermediário guarde cópia.

### 6.3 Validação antes de qualquer custo

Em ordem, do mais barato ao mais caro:

1. tamanho do arquivo (≤ 8 MB; acima de 12 MB o corpo é recusado antes de ser lido);
2. tipo real, obtido da **decodificação** — não da extensão nem do `Content-Type`;
3. formato aceito (JPEG, PNG ou WebP);
4. dimensões (menor lado ≥ 480 px, maior lado ≤ 4096 px);
5. proporção (retrato: largura/altura ≤ 1,35);
6. luminância média entre 40 e 230;
7. **detecção de rosto** por cascata de Haar (OpenCV), executada localmente.

Falhando qualquer item, a resposta é **422** com a lista de problemas no mesmo formato que
a tela de recusa do aplicativo já exibia — e **nenhuma chamada paga é feita**. O limite de
50 milhões de pixels na decodificação protege contra arquivos pequenos que explodem em
memória.

---

## 7. Inteligência artificial

### 7.1 Escolha do provedor

O protótipo citava "Replicate / SDXL img2img". A avaliação refez a pergunta:

| Provedor / modelo | image-to-image | Preserva identidade | Latência | Custo | Observação |
| --- | --- | --- | --- | --- | --- |
| **Replicate · `flux-kontext-apps/change-haircut`** (FLUX.1 Kontext pro) | sim, **especializado em cabelo** | alta — edita por instrução | ~5–15 s | ~US$ 0,04/execução | parâmetros `haircut` e `hair_color` correspondem ao que o app já coleta |
| Replicate · SDXL img2img | sim, genérico | **baixa** — reconstrói o rosto | ~5–10 s | ~US$ 0,01 | inadequado: trocar a face inutiliza a simulação |
| fal.ai · FLUX Kontext | sim | alta | ~4–10 s | semelhante | alternativa direta |
| Google Gemini (imagem) | sim | alta | ~5–10 s | baixo | política de retenção menos transparente para foto de rosto |
| Black Forest Labs (API direta) | sim | alta | ~5–10 s | menor | menos exemplos e ferramental |
| Modelo local | sim | média | muito alta sem GPU | infraestrutura | inviável para demonstração |

**Escolhido: Replicate com `flux-kontext-apps/change-haircut`.** É o único candidato
especializado na tarefa, e preservar o rosto é requisito implícito do produto — uma
simulação que troca a face não serve para mostrar ao cliente.

### 7.2 Desacoplamento

```
services/ai/
├── base.py        EntradaSimulacao, SaidaSimulacao, ProvedorIA (contrato), FalhaDoProvedor
├── replicate.py   implementação real
├── fake.py        provedor local, sem custo e sem credencial
└── __init__.py    fábrica, escolhida por AI_PROVIDER
```

Nenhum outro módulo importa `replicate`. Trocar de provedor é escrever outra
implementação do contrato e mudar uma variável de ambiente.

O provedor local recolore os pixels escuros da foto na direção da cor escolhida e escreve
"simulação local — sem IA" na imagem. Ele existe para desenvolver, testar e demonstrar sem
credencial — e o aviso impresso evita que o resultado seja confundido com o do modelo real.

### 7.3 Fluxo da imagem

```
POST /api/v1/simulacoes  (multipart: clienteId, corte, manterCorte, cor, manterCor,
                          genero, chaveEnvio, observacoes, foto)
 1 autenticação ......................... 401 se ausente ou inválida
 2 cliente pertence ao usuário ........... 404 se não
 3 consentimento aceito e vigente ........ 403 com o motivo
 4 pedido descrito e válido .............. 422 (vazio, marcação, acima de 300 caracteres,
                                           gênero fora de none/male/female)
 5 validação da foto ..................... 422 com a lista de problemas
 6 upload da entrada no storage
 7 cria simulacoes(status=processando, consentimento_id=<decisão que autorizou>)
 → 202 { id, status: "processando" }

 (tarefa em segundo plano)
 8 chamada ao provedor — a foto vai como data URI, nunca por URL pública
 9 upload do resultado no storage
10 status=concluida, modelo_ia, tempo_ms, concluida_em
   em caso de falha: status=falhou, erro_codigo — nunca "concluída sem imagem"

GET /api/v1/simulacoes/{id} → o aplicativo consulta até mudar de estado
```

A credencial do provedor existe apenas no servidor. O aplicativo nunca a vê, não a recebe
em resposta alguma e não tem como acioná-la diretamente.

### 7.4 Tratamento de falhas

| Situação | Resposta |
| --- | --- |
| credencial recusada / sem crédito | `credencial_invalida` / `sem_credito`; simulação marcada como falhou |
| provedor não responde no tempo | `timeout` |
| predição falhou no provedor | `falha_na_geracao` |
| resposta inesperada, vazia ou fora do contrato | `resposta_invalida` |
| conteúdo devolvido não é imagem | `resposta_invalida` — atribuído ao provedor, não ao armazenamento |
| provedor recusa por excesso de pedidos (429) | `limite_do_provedor` — teto do serviço externo, distinto do nosso; o `Retry-After` vai para o log |
| servidor reiniciado durante a geração | simulações presas há mais de 5 minutos viram `falhou` na inicialização |

O corpo de erro do provedor nunca é repassado ao aplicativo: ele pode conter o *prompt* e
dados da imagem, e fica apenas no log do servidor. A tela "serviço indisponível" explica
que a falha é do provedor externo e que clientes, histórico e agenda seguem funcionando.

Cada motivo existe para apontar o responsável certo. Registrar uma resposta fora do
contrato como `timeout` mandaria a investigação para a rede, que está intacta; registrar
conteúdo que não é imagem como falha de armazenamento culparia um componente que nem foi
tocado. Os dois casos já aconteceram e foram corrigidos na verificação de QA.

### 7.5 Verificar se a integração está pronta

`GET /api/v1/saude` informa, fora de produção, qual provedor está configurado, se a
credencial chegou ao servidor (`credencialIa`, booleano — nunca a chave) e qual modelo
será usado. É o que permite confirmar a configuração antes de gastar uma simulação. O
passo a passo está no `backend/README.md`.

### 7.6 Contenção de custo

Cada simulação é uma chamada paga. Três barreiras ficam antes dela, em ordem: a
verificação de consentimento, a validação da fotografia e o teto de chamadas por conta
(`SIMULACAO_MAX_POR_HORA`, padrão 20 por hora). As duas primeiras evitam gastar com uma
chamada que não deveria acontecer; a terceira evita que uma conta autenticada — ou um
token roubado — esvazie o crédito contratado em um laço de requisições. Atingido o teto, a
resposta é 429 com o código `limite_de_simulacoes`, antes de qualquer processamento.

---

## 8. Decisões arquiteturais

Formato: problema → alternativas → escolha → justificativa → impactos.

**8.1 Imutabilidade no banco, não só no código**
Como sustentar que o histórico de consentimentos é confiável? Alternativas: disciplina na
camada de serviço; log de auditoria paralelo; gatilhos no banco. Escolha: gatilhos.
Justificativa: a afirmação passa a ser verificável — nem um `UPDATE` manual altera uma
decisão. Impacto: `DELETE` só funciona em cascata, o que exigiu cuidado na exclusão de
conta e nas rotinas de teste (que usam `TRUNCATE`).

**8.2 `simulacoes.consentimento_id` obrigatório**
Como provar que cada imagem gerada tinha base legal? Alternativas: confiar na validação do
serviço; inferir pelo histórico comparando datas. Escolha: coluna obrigatória apontando
para a decisão. Justificativa: a prova fica no esquema, não na interpretação. Impacto:
acréscimo ao modelo descrito no pré-projeto (Tabela 4), a ser registrado no TCC.

**8.3 Simulação assíncrona com consulta de estado**
A inferência leva de 5 a 20 segundos. Alternativas: resposta síncrona (risco de tempo
limite em rede móvel); fila com Celery/Redis (infraestrutura adicional vedada pelo
escopo). Escolha: `BackgroundTasks` + `GET /simulacoes/{id}`. Justificativa: resolve o
problema com o que já existe e mantém a tela de progresso que o aplicativo já tinha.
Impacto: simulações interrompidas por reinício precisam ser expiradas na partida.

**8.4 404 em vez de 403 para recurso de outra conta**
Alternativa: 403, semanticamente mais preciso. Escolha: 404. Justificativa: 403 confirma a
existência do identificador. Impacto: os testes de isolamento verificam 404.

**8.5 Exclusão física da conta**
Alternativas: *soft delete* (mantém dado pessoal vivo, contra o art. 18); anonimização
(preserva metadados de imagens de terceiros sem finalidade). Escolha: exclusão física.
Impacto: não resta comprovante das decisões; em produção, o caminho seria exportar um
recibo assinado antes de apagar.

**8.6 Senha reconfirmada para excluir a conta**
Alternativa: bastar o token. Escolha: pedir a senha. Justificativa: é a operação
irreversível mais sensível, e um aparelho desbloqueado nas mãos de outra pessoa não deve
ser suficiente. Impacto: uma tela nova no aplicativo.

**8.7 JSON em camelCase**
Alternativa: snake_case idiomático, com tradução no aplicativo. Escolha: camelCase, por
gerador de alias do Pydantic. Justificativa: o contrato da API passa a coincidir com os
tipos que o aplicativo já tinha, eliminando uma camada inteira de mapeamento — e os erros
que vêm com ela. Impacto: nenhum no servidor, onde os campos seguem snake_case.

**8.8 Catálogo de estilos e cores no aplicativo**
Alternativa: tabela no banco. Escolha: permanece no código, no aplicativo e no servidor,
com um teste que confere que as listas não divergem. Justificativa: o catálogo é fixo; não
há administração em tempo de execução que justifique persisti-lo. Desde a reformulação da
etapa "Estilo e cor", corte e cor são descritos livremente, e o catálogo virou uma lista de
exemplos (em alta e clássicos) que a tela cita em texto; o servidor reconhece um exemplo
escrito exatamente e usa a descrição pronta e a opção equivalente do modelo. Impacto: `GET
/catalogo` publica as listas para conferência. Detalhes em `RELATORIO_PERSONALIZACAO_IA.md`.

**8.9 Storage local como padrão de desenvolvimento**
Alternativas: exigir MinIO (mais um contêiner); gravar binário no PostgreSQL (vedado).
Escolha: mesma interface, dois drivers, disco por padrão. Impacto: `docker compose up` não
precisa de MinIO; produção muda uma variável.

**8.10 Manter `Context + useReducer` no aplicativo**
Alternativa: biblioteca de cache remoto (React Query e afins). Escolha: manter.
Justificativa: o volume de dados é pequeno, o fluxo é por tela e não há sincronização
concorrente; a troca acrescentaria dependência sem resolver problema existente. Impacto:
atualizações manuais em pontos específicos (puxar para atualizar, releitura do cliente
após registrar decisão).

---

## 9. Matriz de rastreabilidade

| Requisito | Implementação | Endpoint | Banco | Aplicativo | Teste |
| --- | --- | --- | --- | --- | --- |
| **RF01** Autenticação | `services/auth.py`, `core/security.py` (bcrypt 12, JWT HS256) | `POST /auth/registrar`, `/auth/login`, `/auth/renovar` | `usuarios` | `app/login.tsx`, `app/cadastro.tsx`, `src/services/api/sessao.ts` | `test_auth.py` (11), `test_seguranca.py` (11) |
| **RF02** Cadastro de clientes | `services/clientes.py` | `GET/POST /clientes`, `GET/PATCH/DELETE /clientes/{id}` | `clientes` | `app/(tabs)/clientes.tsx`, `app/cliente/editar.tsx`, `app/cliente/[id].tsx` | `test_clientes.py` (10) |
| **RF03** Histórico de atendimentos | `services/atendimentos.py` | `GET/POST /atendimentos`, `PATCH /atendimentos/{id}` | `atendimentos` | `app/atendimento/novo.tsx` | `test_agenda_e_atendimentos.py` |
| **RF04** Simulação capilar | `services/simulacao.py`, `services/ai/*`, `services/validacao_foto.py` | `POST /simulacoes` | `simulacoes`, `imagens` | `app/simulacao/{captura,parametros,processando}.tsx` | `test_simulacoes.py` (11), `test_provedor_ia.py` (12), `test_validacao_foto.py` (12) |
| **RF05** Persistência da simulação | mesma, com storage e metadados | `GET /simulacoes/{id}`, `GET /clientes/{id}/simulacoes` | `simulacoes`, `imagens` | `app/simulacao/resultado.tsx`, `app/cliente/[id].tsx` | `test_simulacoes.py` |
| **RF06** Agenda | `services/agendamentos.py`, com máquina de estados | `GET/POST /agendamentos`, `PATCH /agendamentos/{id}/status` | `agendamentos` | `app/(tabs)/agenda.tsx`, `app/agendamento/novo.tsx` | `test_agenda_e_atendimentos.py` |
| **RF07** Comparação de simulações | `services/simulacao.marcar_preferida` | `POST /simulacoes/{id}/preferida` | índice único parcial `preferida` | `app/cliente/[id].tsx` (preferida), `app/simulacao/comparar.tsx` | `test_simulacoes.py`, `test_imutabilidade.py` |
| **RF08** Recomendação automática | **fora do escopo**, como no TCC | — | — | — | — |
| **RNF05** Privacidade / LGPD | `services/consentimento.py`, gatilhos, URLs assinadas, exclusões | `/clientes/{id}/consentimento(s)`, `DELETE /clientes/{id}/simulacoes`, `DELETE /usuarios/me` | `consentimentos`, `termos`, `ciencias` | `app/consentimento/[clienteId].tsx`, `app/termo/[clienteId].tsx`, `app/privacidade.tsx`, `app/excluir-conta.tsx` | `test_consentimento.py` (14), `test_casos_criticos.py` (9), `test_imutabilidade.py` (8) |

Requisitos não funcionais com evidência direta no código:

| Requisito | Onde se verifica |
| --- | --- |
| RNF02 — resposta da API em até 30 s em 80% das chamadas | `simulacoes.tempo_ms`, medido no servidor a cada geração |
| RNF03 — proteção dos dados | bcrypt, JWT, URLs assinadas, CORS restrito, limites de upload |
| RNF05 — consentimento e eliminação | seção 5 deste documento |

### 9.1 Casos críticos exigidos

`tests/test_casos_criticos.py`, na ordem da especificação:

1. cliente sem consentimento → não gera simulação (403, nada é criado);
2. consentimento revogado → não gera simulação;
3. consentimento antigo → exige revalidação, e volta a liberar após o novo aceite;
4. usuário A não acessa dados do usuário B (seis rotas + a URL de imagem);
5. menor sem responsável → não registra consentimento, e a câmera segue bloqueada;
6. revogação cria um registro novo, preservando o anterior;
7. exclusão de imagens não apaga o histórico de atendimentos, e o arquivo some do storage.

---

## 10. O que mudou em relação ao protótipo

### 10.1 Mudanças no modelo de dados

| Mudança | Motivo | Necessária ou recomendada |
| --- | --- | --- |
| `termos` virou tabela | a versão vigente precisa ser decidida pelo servidor | necessária |
| `ciencias` virou tabela | era um campo do estado local; precisa de histórico por versão | necessária |
| `imagens` virou tabela | separar metadados do binário | necessária |
| `simulacoes.consentimento_id` | provar a base legal de cada imagem | recomendada, de alto valor para o TCC |
| `atendimentos.usuario_id` | o tipo do aplicativo não tinha dono | necessária |
| `simulacoes.status` / `erro_codigo` | o fluxo passou a ser assíncrono | necessária |
| `faixa_etaria` no consentimento | registrar a apuração no momento da decisão | recomendada |
| `preferida` com índice único parcial | a regra existia só no reducer | necessária |

### 10.2 Correções de fragilidades do protótipo

- credenciais de demonstração pré-preenchidas na tela de login — **removidas**;
- "Criar conta" apagava os dados locais; agora cria conta de verdade;
- versão do termo definida pelo aplicativo — agora é do servidor;
- `preferida` garantida só em memória — agora pelo banco;
- transições de status da agenda não validadas — agora há máquina de estados;
- estado inteiro (inclusive consentimentos) persistido em claro no aparelho — agora só o
  token fica no aparelho, em armazenamento seguro;
- a tela de privacidade dizia que apagar imagens não afetava mais nada, mas também apagava
  a foto de perfil do cliente — texto corrigido.

### 10.3 Arquivos do aplicativo alterados

Novos: `src/services/api/{cliente,sessao,index}.ts`, `src/components/{DocumentoTermo,Atualizar}.tsx`,
`app/cadastro.tsx`, `app/excluir-conta.tsx`.
Removidos: `src/data/seed.ts`, `src/services/authService.ts`.
Reescritos: `src/data/{store.tsx,tipos.ts,termos.ts,rascunho.tsx}`,
`src/services/{consentService,simulacaoService}.ts`, `src/components/ImagemSimulada.tsx`,
`app/simulacao/{processando,resultado}.tsx`, `app/login.tsx`, `app/index.tsx`.
Ajustados: as demais telas, para tratar carregamento, erro e as ações assíncronas.

---

## 11. Limitações

| Limitação | Situação |
| --- | --- |
| **RF08 — recomendação automática** | fora do escopo, como no TCC |
| Recuperação de senha | exigiria provedor de e-mail; a tela informa isso ao profissional |
| Notificação de lembrete | o campo é persistido; o disparo não é implementado |
| Revogação de token de renovação | não há lista de invalidados; excluir a conta invalida tudo |
| Limite de tentativas de login | em memória, por processo; com réplicas, caberia a um serviço compartilhado |
| Teto de simulações por hora | existe (`SIMULACAO_MAX_POR_HORA`, padrão 20 por conta), mas também em memória e por processo — mesma ressalva das réplicas |
| Listas sem paginação | as rotas de lista devolvem a coleção inteira; com carteiras grandes, vira um limite real |
| URL de imagem é credencial portadora | a entrega vale por assinatura, não por sessão; quem tem a URL lê a imagem até expirar, em 10 minutos |
| Idade sem data de nascimento | não há como inferir; a exigência de responsável não se aplica |
| Retenção no provedor de IA | fora do controle do sistema — é exatamente o que o termo informa ao cliente |
| Detecção de rosto | cascata de Haar: rápida e local, menos precisa que um modelo neural |

### 11.1 O que foi executado e o que não foi

Executado e verificado neste ambiente: migrations do zero, seed, 310 testes automatizados,
a API em funcionamento e o aplicativo (versão web) percorrendo o fluxo completo contra o
servidor real — cadastro, ciência, criação de cliente, bloqueio por ausência de
consentimento, registro do aceite, captura, validação da foto, geração da simulação,
exibição por URL assinada, registro de atendimento, agendamento, revogação e exclusão de
imagens com preservação do histórico.

Posteriormente, o sistema passou por uma verificação dirigida de qualidade e segurança,
cujo resultado completo está em `RELATORIO_QA.md`: varredura de IDOR em todas as rotas que
recebem identificador, entradas de borda em todos os endpoints, injeção e XSS, auditoria de
dependências, conferência campo a campo entre os tipos do aplicativo e os schemas da API,
verificação dos pontos de LGPD pelo comportamento, e duas baterias em navegador real.

**Não executado:** a chamada real à API da Replicate, por não haver credencial neste
ambiente e por o domínio estar bloqueado pelo proxy de rede. A integração está implementada
e coberta de duas formas, ambas sem tocar o serviço externo: por testes com HTTP simulado
(sucesso, saída em lista, 401, 402, 500, predição falhada, resposta inesperada e tempo
esgotado) e por um servidor que imita o protocolo da Replicate
(`backend/tests/mock_provedor_ia.py`), contra o qual o cliente real é exercitado em dez
cenários, inclusive resposta lenta, resposta vazia e conteúdo que não é imagem. A execução
com a chave real é um passo de um comando, descrito no `backend/README.md`; o que precisa
ser verificado nesse momento está na seção 8 do `RELATORIO_QA.md`. O `docker compose up` também
não pôde ser executado aqui, por não haver daemon do Docker no ambiente; a validação usou
o PostgreSQL 16 local, com as mesmas migrations.
