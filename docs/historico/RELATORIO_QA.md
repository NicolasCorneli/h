# Relatório de Qualidade e Segurança — Espelho

**Sistema:** Espelho — aplicativo de simulação capilar com inteligência artificial e gestão de clientes
**Autor do sistema:** Nícolas Marin Corneli — Sistemas de Informação, Faculdade Antônio Meneghetti
**Período da verificação:** outubro de 2026
**Versão verificada:** base recebida em `espelho-completo.zip`, com os commits de QA aplicados sobre ela

---

## 1. Objetivo e escopo

### 1.1 Objetivo

Verificar, por evidência de execução, se o Espelho faz o que a sua documentação afirma que
faz: se os requisitos funcionais se comportam como especificado, se os controles de
segurança resistem a tentativas deliberadas de burlá-los, e se as exigências da Lei Geral
de Proteção de Dados que o sistema diz atender são efetivamente impostas pelo código.

A verificação foi conduzida sob uma premissa explícita: **nada é considerado correto por
estar planejado ou documentado.** Toda afirmação foi confrontada com o código-fonte e com
a execução real. Divergências entre documentação e comportamento foram tratadas como
achados, e não como erros de redação.

Essa postura não é retórica, e três episódios desta verificação mostram por quê:

- o sistema **não subia** em ambiente limpo. Seguindo o procedimento documentado
  (`pip install -r requirements.txt`), a aplicação falhava no import por falta de uma
  dependência não declarada. No ambiente de desenvolvimento anterior o pacote existia por
  acidente, o que escondia a falta (achado A-16);
- os testes que comprovavam a ausência de dados pessoais nos registros de log estavam
  passando **sem verificar nada**, porque um efeito colateral das migrations silenciava os
  loggers da aplicação durante a suíte. Um teste verde não prova nada se o seu instrumento
  de observação está desligado (achado A-03);
- um teste que eu havia escrito afirmava uma garantia que o sistema não oferece — e, nesse
  caso, **o teste estava errado e o código estava certo**. A conclusão correta foi
  reescrever o teste e registrar a característica real como risco residual, não "corrigir"
  um comportamento deliberado (seção 5.4, A-18).

### 1.2 Escopo coberto

| Camada | O que foi verificado |
| --- | --- |
| Aplicativo (front-end) | 28 telas, fluxos de ponta a ponta, estados de carregamento/vazio/erro/sucesso, validação de formulários, responsividade (390 / 768 / 1280 px), acessibilidade básica, console do navegador |
| API (back-end) | 42 endpoints em 27 caminhos: entradas válidas, inválidas, ausentes e nos limites; códigos HTTP; formato e consistência das mensagens de erro; ausência de vazamento de detalhes internos |
| Integração | correspondência campo a campo entre os tipos TypeScript do aplicativo e os schemas publicados no OpenAPI; valores das enumerações; camelCase; forma das listas |
| Banco de dados | restrições, chaves estrangeiras, campos obrigatórios, índices parciais, gatilhos de imutabilidade, migrations do zero, ausência de registros órfãos e de arquivos esquecidos após exclusões |
| Segurança | OWASP Top 10, com ênfase em A01 (controle de acesso), A02 (falhas criptográficas), A03 (injeção), A04 (projeto inseguro), A05 (configuração), A06 (componentes vulneráveis), A07 (autenticação) e A09 (registro) |
| LGPD | consentimento prévio, revogação com efeito real, exclusão efetiva, transparência sobre o envio ao provedor externo, ausência de dados sensíveis nos logs |
| Dependências | auditoria com `pip-audit` (Python) e `npm audit` (Node) |

### 1.3 Fora do escopo

**A chamada real à API externa de simulação capilar não foi executada.** O provedor
previsto é o modelo `flux-kontext-apps/change-haircut`, hospedado na Replicate, e não há
credencial contratada; além disso, o domínio do provedor está bloqueado pela política de
rede do ambiente de desenvolvimento.

Para que a ausência do serviço real não deixasse o fluxo mais crítico do sistema sem
verificação, foi construído um **servidor que imita o protocolo da Replicate**
(`backend/tests/mock_provedor_ia.py`). O cliente HTTP real da aplicação — a mesma classe
`ProvedorReplicate` que roda em produção, sem substituição nem monkeypatch do seu
comportamento — conversa com esse servidor por HTTP de verdade, em todos os cenários
pedidos: sucesso, erro 4xx, erro 5xx, tempo esgotado, resposta lenta, resposta malformada,
resposta vazia e imagem inválida; mais crédito esgotado e predição recusada pelo modelo.
**Nenhum serviço externo real foi chamado em momento algum desta verificação.**

O que não pode ser verificado sem a credencial real está listado, item por item, na
seção 8.3.

Permanecem fora do escopo, por decisão anterior do próprio TCC: **RF08** (recomendação
automática de estilo), recuperação de senha por e-mail, disparo efetivo de notificações de
lembrete e execução em aparelho iOS.

---

## 2. Metodologia

### 2.1 Tipos de teste aplicados

| Tipo | Como foi aplicado |
| --- | --- |
| **Teste unitário (caixa-branca)** | regras de consentimento isoladas, sem banco e sem HTTP: 24 casos sobre a função que decide se a captura é permitida |
| **Teste de integração** | 310 testes contra um PostgreSQL 16 real, criado pelas mesmas migrations da aplicação — inclusive os gatilhos de imutabilidade, que são parte da regra de negócio e não seriam exercitados por um banco em memória |
| **Teste de contrato** | comparação automatizada entre `espelho/src/data/tipos.ts` e os schemas do OpenAPI, campo a campo, em 15 pares de tipos, mais os valores das 5 enumerações usadas em `switch` no aplicativo |
| **Teste de ponta a ponta** | três baterias em navegador real (Chromium, via Playwright) contra a API em execução |
| **Teste negativo e de borda** | entradas ausentes, de tipo errado, no limite e um caractere além, strings de 100 mil caracteres, valores negativos, UUIDs malformados, corpos gigantes, JSON inválido |
| **Teste de segurança (caixa-cinza)** | tentativas deliberadas de acesso cruzado entre contas, injeção, falsificação e expiração de assinatura, reuso de token revogado, abuso de custo |
| **Simulação de falha** | servidor de mentira configurável por cenário para o provedor de IA; API derrubada no meio da sessão do aplicativo |
| **Inspeção de repositório** | varredura do histórico do Git em busca de segredos versionados |
| **Teste do próprio instrumento** | asserções-canário: antes de afirmar que algo *não* aparece no log, o teste afirma que recebeu log; antes de verificar exclusão, afirma que havia dado a excluir |

### 2.2 Referências normativas

**OWASP Top 10 (2021)** orientou a seção de segurança:

| Categoria | Verificação realizada | Resultado |
| --- | --- | --- |
| A01 — Quebra de controle de acesso | varredura de IDOR em todas as rotas que recebem identificador, por URL e por corpo | nenhuma falha |
| A02 — Falhas criptográficas | hash de senha (bcrypt, custo 12), assinatura HMAC das URLs de imagem com expiração, ausência de segredo embutido | nenhuma falha |
| A03 — Injeção | SQL via parâmetros de busca e filtros; XSS armazenado e refletido; travessia de caminho em nomes de arquivo | nenhuma falha |
| A04 — Projeto inseguro | ausência de teto de chamadas ao provedor pago; tratamento do caminho de erro no envio de imagem | **2 achados (1 Alta, 1 Média)** — corrigidos |
| A05 — Configuração insegura | CORS, cabeçalhos de segurança, documentação exposta, divulgação de versão do servidor | **3 achados** — corrigidos |
| A06 — Componentes vulneráveis | `pip-audit` e `npm audit` | **3 achados** (2 corrigidos, incluindo a Alta do Pillow; 1 risco residual justificado) |
| A07 — Falhas de autenticação | expiração e invalidação de tokens, limite de tentativas de login, impossibilidade de enumerar contas | nenhuma falha |
| A09 — Falhas de registro | dados pessoais em logs; mecanismo de log desligado por efeito colateral | **1 achado (Média)** — corrigido |

**ISO/IEC 25010** organizou os resultados além da segurança:

| Característica | Subcaracterística avaliada | Como foi avaliada |
| --- | --- | --- |
| **Adequação funcional** | completude, correção e pertinência | cada requisito funcional (RF01–RF07) tem testes nomeados; os sete casos críticos da especificação estão reunidos em arquivo próprio |
| **Confiabilidade** | maturidade, tolerância a falhas, recuperabilidade | comportamento quando o provedor de IA falha, demora ou devolve lixo; quando a API está fora do ar; quando a aplicação é instalada do zero |
| **Segurança** | confidencialidade, integridade, não repúdio, responsabilização | seção 5 e a tabela OWASP acima; a imutabilidade dos registros de consentimento, imposta por gatilhos no banco, sustenta o não repúdio |
| **Usabilidade** | operabilidade, proteção contra erro do usuário, acessibilidade | estados de tela, mensagens de validação, alvos de toque ≥ 44 px, rótulos acessíveis, navegação por teclado, alternativas textuais, contraste da paleta |
| **Manutenibilidade** | testabilidade, modularidade | suíte executável por um comando; 93% de cobertura; o endereço do provedor externo foi tornado configurável justamente para permitir teste sem rede |

### 2.3 Ferramentas

| Ferramenta | Versão | Uso |
| --- | --- | --- |
| pytest | 9.1.1 | execução da suíte |
| pytest-cov | 7.1.0 | medição de cobertura |
| httpx | 0.28.1 | cliente HTTP dos testes e da aplicação |
| uvicorn | 0.54.0 | servidor da API e do servidor de mentira do provedor |
| Playwright | 1.56.1 | automação do navegador |
| Chromium | 141.0.7390.37 | navegador das baterias de interface |
| pip-audit | — | auditoria de dependências Python |
| npm audit | npm 10 | auditoria de dependências Node |
| `git log -p` | 2.x | varredura do histórico em busca de segredos |

### 2.4 Classificação de severidade adotada

| Severidade | Critério |
| --- | --- |
| **Crítica** | falha de segurança explorável, ou perda/vazamento de dados |
| **Alta** | funcionalidade essencial quebrada, ou risco de segurança relevante |
| **Média** | atrapalha o uso, mas existe caminho alternativo |
| **Baixa** | melhoria visual, textual ou de qualidade interna |

### 2.5 Regra de trabalho para correções

Correções simples e de baixo risco foram aplicadas durante a verificação, cada uma em
commit próprio e descritivo, com reexecução dos testes relacionados em seguida. Nenhuma
correção alterou arquitetura, modelo de dados ou fluxo de telas. O único achado que
exigia decisão — a atualização de uma dependência deliberadamente fixada, A-20 — foi
descrito, submetido à confirmação do autor e aplicado somente depois dela, com a suíte
inteira reexecutada em seguida.

Todos os dados utilizados são **fictícios**, gerados pela carga de demonstração
(`python -m app.seed`). Nenhum dado pessoal real foi usado, e os testes rodam contra um
banco separado (`espelho_test`), nunca contra a base de desenvolvimento.

---

## 3. Ambiente de teste

### 3.1 Plataforma

| Item | Versão |
| --- | --- |
| Sistema operacional | Linux 6.18 (contêiner de desenvolvimento) |
| Python | 3.11.17 |
| PostgreSQL | 16.15 |
| Node.js | 22.22.0 |
| Navegador | Chromium 141.0.7390.37 |

### 3.2 Dependências principais do back-end

| Pacote | Versão |
| --- | --- |
| FastAPI | 0.142.2 |
| Pydantic | 2.13.5 |
| SQLAlchemy | 2.1.2 (modo síncrono) |
| Alembic | 1.20.0 |
| psycopg | 3.3.6 |
| PyJWT | 2.15.1 |
| bcrypt | 5.0.0 (custo 12) |
| Pillow | 13.0.0 — elevada nesta verificação (A-20) |
| opencv-python-headless | 4.14.0.94 |
| httpx | 0.28.1 |
| numpy | 2.4.6 |
| uvicorn | 0.54.0 |
| boto3 | 1.43.108 |
| pytest | 9.1.1 |

### 3.3 Dependências principais do aplicativo

| Pacote | Versão |
| --- | --- |
| Expo SDK | ~57.0.22 |
| React Native | 0.86.3 |
| React | 19.2.3 |
| TypeScript | ~6.0.3, modo estrito |
| @playwright/test | 1.56.1 (dependência de desenvolvimento) |

### 3.4 Configuração

- **Banco de testes:** `espelho_test`, construído do zero pelas migrations do Alembic a
  cada execução da suíte — não por `create_all()`. O `conftest.py` executa
  `downgrade base` seguido de `upgrade head`, o que exercita a reversibilidade das
  migrations em toda rodada. Os gatilhos de imutabilidade e os índices parciais fazem
  parte das migrations e, portanto, estão presentes nos testes.
- **Provedor de IA:** `AI_PROVIDER=fake` na operação normal (gera o resultado localmente,
  sem custo e sem credencial); `AI_PROVIDER=replicate` com `AI_BASE_URL` apontada para o
  servidor de mentira nos testes de integração do provedor.
- **Armazenamento:** driver `local` (disco), em diretório apagado entre os testes.
- **Ambiente declarado:** `AMBIENTE=teste` na suíte; os comportamentos específicos de
  produção (HSTS, documentação fechada) são verificados forçando `AMBIENTE=producao` em
  testes dedicados, que remontam a aplicação.

### 3.5 Dados fictícios utilizados

A carga de demonstração cria o cenário de que os testes precisam, com nomes, telefones e
observações inventados. Execução registrada:

> `Seed concluído: 2 usuários · 9 clientes · 7 consentimentos · 5 simulações · 10 imagens · 4 atendimentos · 7 agendamentos`

| Entidade | Cenários deliberadamente incluídos |
| --- | --- |
| Profissionais | duas contas distintas, para comprovar isolamento |
| Clientes | com consentimento ativo; sem consentimento; recusado; revogado; aceite em versão anterior do termo; menor de idade com e sem responsável legal |
| Termos | termo vigente e versão anterior, para exercitar o versionamento |
| Imagens | retrato válido; sem rosto; escura; fora de proporção; arquivo que não é imagem apesar da extensão; PNG de 68 bytes declarando 900 milhões de pixels |
| Simulações | concluída, falhada e uma marcada como preferida |

As fotos são geradas por código (Pillow), com um rosto sintético detectável pela cascata
de Haar. **Nenhuma fotografia de pessoa real foi utilizada.**

---

## 4. Casos de teste

A coluna **Status** registra `Aprovado` quando o resultado obtido coincidiu com o
esperado, e `Aprovado após correção` quando o caso revelou um defeito corrigido durante
esta verificação e cuja correção foi confirmada por reexecução.

### 4.1 Instalação e inicialização

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-01 | Instalação em ambiente limpo | criar ambiente virtual novo, `pip install -r requirements.txt`, importar a aplicação | a aplicação importa e a suíte coleta | `ImportError: email-validator is not installed` — a aplicação não subia, e a suíte não coletava um único teste — **A-16** | Aprovado após correção |
| CT-02 | Migrations do zero | banco vazio, `alembic upgrade head` | 9 tabelas, 18 chaves estrangeiras, índices parciais e gatilhos criados | conforme | Aprovado |
| CT-03 | Reversibilidade das migrations | `downgrade base` seguido de `upgrade head` | executa sem erro | conforme — e é executado a cada rodada da suíte | Aprovado |
| CT-04 | Carga de demonstração | `python -m app.seed` em banco limpo | produz todos os cenários que o roteiro exige | conforme | Aprovado |
| CT-05 | Segredo obrigatório | subir sem `JWT_SECRET`, e com segredo curto | recusa a iniciar, com mensagem explícita | conforme | Aprovado |
| CT-06 | Diagnóstico | `GET /api/v1/saude` | informa banco, storage e provedor fora de produção; em produção não descreve a infraestrutura | conforme | Aprovado |

### 4.2 Autenticação e conta (RF01)

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-07 | Cadastro de profissional | `POST /auth/registrar` com dados válidos | 201, tokens emitidos | conforme | Aprovado |
| CT-08 | Cadastro com entrada inválida | 6 variações: e-mail malformado, senha curta, nome vazio, campos ausentes | 422 em todas | conforme nas 6 | Aprovado |
| CT-09 | Cadastro com e-mail repetido | repetir CT-07 com o mesmo e-mail | 409, sem revelar detalhe interno | conforme | Aprovado |
| CT-10 | Armazenamento da senha | consultar a coluna no banco | hash bcrypt, custo 12; senha em claro ausente | conforme | Aprovado |
| CT-11 | Login correto | `POST /auth/login` | 200, access e refresh token | conforme | Aprovado |
| CT-12 | Impossibilidade de enumerar contas | login com e-mail inexistente e com senha errada | mesmo status **e mesma mensagem** | conforme — mensagens idênticas | Aprovado |
| CT-13 | Token malformado | 5 variações de cabeçalho `Authorization` | 401 em todas | conforme nas 5 | Aprovado |
| CT-14 | Token assinado com outro segredo | forjar JWT | 401 | conforme | Aprovado |
| CT-15 | Expiração do access token | apresentar token vencido | 401 | conforme | Aprovado |
| CT-16 | Renovação de sessão | `POST /auth/renovar` | 200, novo access token | conforme | Aprovado |
| CT-17 | Limite de tentativas de login | tentativas falhas consecutivas | 429 a partir da excedente | conforme | Aprovado |
| CT-18 | Invalidação por exclusão de conta | excluir a conta e reapresentar o token | 401 — o token deixa de valer | conforme | Aprovado |
| CT-19 | Exclusão de conta exige senha | `DELETE /usuarios/me` sem senha e com senha errada | recusado; a conta permanece | conforme | Aprovado |

### 4.3 Clientes (RF02)

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-20 | Criar cliente | `POST /clientes` | 201, vinculado à conta autenticada | conforme | Aprovado |
| CT-21 | Nome obrigatório | 8 variações: ausente, vazio, só espaços, nulo, número, lista, objeto | 422 em todas | conforme nas 8 | Aprovado |
| CT-22 | Nome no limite | limite exato do schema, e um caractere além | 201 e 422, respectivamente | conforme | Aprovado |
| CT-23 | String gigante | nome e telefone com 100 mil caracteres | 422, sem derrubar o servidor | conforme | Aprovado |
| CT-24 | Listar clientes | `GET /clientes` com duas contas povoadas | apenas os da conta autenticada | conforme | Aprovado |
| CT-25 | Busca por nome e telefone | `GET /clientes?busca=` | somente os correspondentes, da própria conta | conforme | Aprovado |
| CT-26 | Atualizar cliente | `PATCH` com campos parciais | 200, apenas os campos enviados alterados | conforme | Aprovado |
| CT-27 | Atribuição em massa | `POST` e `PATCH` tentando definir `id`, `usuarioId`, `criadoEm` | campos ignorados; vínculo e identificador preservados | conforme nos dois verbos | Aprovado |
| CT-28 | Excluir cliente | `DELETE /clientes/{id}` | 204 | conforme | Aprovado |
| CT-29 | Identificador inexistente | UUID aleatório | 404 | conforme | Aprovado |
| CT-30 | Identificador malformado | 5 variações, incluindo `' OR 1=1 --` e `../../etc/passwd` | 404 ou 422, sem stack trace | conforme nas 5 | Aprovado |

### 4.4 Consentimento e termos (RNF05, LGPD)

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-31 | Captura bloqueada sem consentimento | enviar foto de cliente sem consentimento | recusado com código de bloqueio e motivo legível | conforme | Aprovado |
| CT-32 | Registro do aceite | `POST /clientes/{id}/consentimentos` com a versão vigente | 201; decisão vinculada à versão exata do termo | conforme | Aprovado |
| CT-33 | Consentimento com entrada inválida | 4 variações: decisão inventada, forma inventada, confirmação vazia, campo ausente | 422 em todas | conforme nas 4 | Aprovado |
| CT-34 | Simulação exige consentimento | solicitar simulação para cliente sem consentimento | 403; **o provedor não é chamado** | conforme — lista de chamadas do mock permanece vazia | Aprovado |
| CT-35 | Revogação | revogar e tentar capturar de novo | captura bloqueada; histórico anterior preservado | conforme | Aprovado |
| CT-36 | Imutabilidade do consentimento | `UPDATE` e `DELETE` por SQL direto | recusado pelo gatilho do banco | conforme | Aprovado |
| CT-37 | Imutabilidade do termo | alterar versão já publicada, por SQL direto | recusado pelo gatilho | conforme | Aprovado |
| CT-38 | Um único termo vigente por tipo | marcar segunda versão como vigente | recusado pelo índice único parcial | conforme | Aprovado |
| CT-39 | Menor com responsável | cliente menor com responsável informado | consentimento aceito | conforme | Aprovado |
| CT-40 | Menor sem responsável | cliente menor sem responsável | captura bloqueada com motivo específico (art. 14 §1º) | conforme | Aprovado |
| CT-41 | Versionamento | registrar aceite, publicar nova versão, consultar o aceite | continua apontando para a versão apresentada | conforme | Aprovado |
| CT-42 | Ciência do profissional | operar sem ter registrado a ciência | bloqueio com orientação; registro imutável após o aceite | conforme | Aprovado |
| CT-43 | Ciência exigida na interface | tela de responsabilidades, botão de avançar | só habilita depois de marcada a caixa de ciência | conforme | Aprovado |

### 4.5 Envio e validação de foto

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-44 | Foto válida | retrato dentro dos limites, com rosto detectável | 201; binário fora do banco | conforme | Aprovado |
| CT-45 | Tipo real do arquivo | executável renomeado para `.jpg`; conteúdo que não é imagem com `Content-Type` de imagem | 422 — a validação decodifica o conteúdo, não confia na extensão nem no cabeçalho | conforme | Aprovado |
| CT-46 | Tamanho máximo | arquivo no limite e além | aceito e recusado | conforme | Aprovado |
| CT-47 | Corpo acima do limite | requisição muito acima do permitido | 413, antes de consumir a requisição | conforme | Aprovado |
| CT-48 | Bomba de descompressão | PNG de 68 bytes declarando 30.000 × 30.000 px (900 milhões de pixels) | recusado **como foto inválida** (422), antes da decodificação | a barreira de pixels impedia a decodificação, mas a recusa saía como erro interno (500) — **A-15** | Aprovado após correção |
| CT-49 | Dimensões e proporção | abaixo do mínimo, acima do máximo, fora da proporção | 422 com motivo específico | conforme | Aprovado |
| CT-50 | Luminância | imagem muito escura e muito clara | 422 com orientação | conforme | Aprovado |
| CT-51 | Ausência de rosto | imagem sem rosto detectável | 422 com motivo específico | conforme | Aprovado |
| CT-52 | Metadados EXIF | enviar JPEG com fabricante e data | metadados descartados na normalização | conforme — minimização verificada na saída | Aprovado |
| CT-53 | Nome de arquivo hostil | `../../etc/passwd` e caracteres de controle | nome descartado; arquivo gravado com nome gerado pelo servidor | conforme | Aprovado |
| CT-54 | Uma única foto de perfil | inserir segunda imagem de tipo `perfil`, por SQL direto | recusado pelo índice único parcial | conforme | Aprovado |

### 4.6 Fluxo de simulação com o servidor de mentira (RF04, RF05, RF07)

Todos os casos exercitam o cliente HTTP real da aplicação contra o servidor descrito em
1.3. Nenhuma chamada externa real foi feita.

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-55 | Resposta de sucesso | cenário `sucesso` | simulação `concluida`, imagem gerada persistida | conforme | Aprovado |
| CT-56 | Resultado chega à tela | obter a URL assinada da imagem de saída | 200, `image/jpeg`, conteúdo é JPEG de verdade | conforme | Aprovado |
| CT-57 | Erro 4xx do provedor | cenário `erro_4xx` (401) | falha com motivo de credencial; credencial não aparece na resposta | conforme | Aprovado |
| CT-58 | Crédito esgotado | cenário `sem_credito` (402) | motivo próprio, distinguível de erro de requisição | conforme | Aprovado |
| CT-59 | Erro 5xx do provedor | cenário `erro_5xx` | falha registrada; mensagem ao usuário sem detalhe interno | conforme | Aprovado |
| CT-60 | Tempo esgotado | cenário `timeout`, com `AI_TIMEOUT_S` curto | requisição abandonada no tempo configurado; simulação falha por tempo esgotado | conforme | Aprovado |
| CT-61 | Resposta lenta | cenário `lento` (demora abaixo do limite) | conclui com sucesso, e o tempo medido reflete a demora | conforme | Aprovado |
| CT-62 | Resposta malformada | cenário `malformada` (JSON fora do contrato) | falha registrada como resposta inválida | registrava `timeout` — o provedor respondeu em milissegundos, e o motivo mandava a investigação para a rede — **A-17** | Aprovado após correção |
| CT-63 | Resposta vazia | cenário `vazia` (corpo sem conteúdo) | falha registrada como resposta inválida | registrava `erro_interno`, atribuindo ao sistema um problema do terceiro — **A-17** | Aprovado após correção |
| CT-64 | Predição recusada | cenário `predicao_falhou` | falha com a razão informada pelo provedor | conforme | Aprovado |
| CT-65 | Conteúdo não é imagem | cenário `imagem_invalida` (provedor devolve HTML com tipo de imagem) | falha atribuindo o problema ao provedor | registrava `falha_no_armazenamento`, culpando componente que nem foi tocado — **A-07** | Aprovado após correção |
| CT-66 | Foto inválida não chega ao provedor | solicitar simulação com foto recusada | 422; lista de chamadas do mock vazia | conforme | Aprovado |
| CT-67 | Credencial no lugar certo | inspecionar as chamadas recebidas e as respostas devolvidas | cabeçalho de autorização chega ao provedor; credencial não aparece em resposta alguma | conforme | Aprovado |
| CT-68 | Minimização no envio | inspecionar o corpo recebido pelo mock | apenas imagem e parâmetros do penteado | conforme — nenhum nome, telefone ou data de nascimento | Aprovado |
| CT-69 | Teto de chamadas por conta | emitir simulações em sequência além do teto | 429 com código próprio | **não havia teto algum** — A-01 | Aprovado após correção |
| CT-70 | Teto não vaza entre contas | esgotar o teto da conta A e gerar pela conta B | B não é afetada | conforme | Aprovado |
| CT-71 | Teto age antes do processamento | com teto zerado, enviar foto inválida | 429 (e não 422), provando que a barreira antecede a decodificação | conforme | Aprovado |
| CT-72 | Comparação e preferida | marcar duas simulações como preferidas | apenas uma por cliente (índice único parcial) | conforme | Aprovado |
| CT-73 | Simulação interrompida | simulação presa em `processando` além do prazo | reconciliada como falhada na inicialização | conforme | Aprovado |

### 4.7 Agenda e atendimentos (RF03, RF06)

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-74 | Registrar atendimento | `POST /atendimentos`, com e sem simulação vinculada | 201; histórico atualizado | conforme | Aprovado |
| CT-75 | Atendimento com cliente inválido | 3 variações: ausente, malformado, nulo | 404 ou 422 | conforme nas 3 | Aprovado |
| CT-76 | Histórico sobrevive à exclusão da simulação | excluir a simulação vinculada | atendimento preservado, vínculo anulado (`ON DELETE SET NULL`) | conforme | Aprovado |
| CT-77 | Criar agendamento | data e hora futuras | 201, status `pendente` | conforme | Aprovado |
| CT-78 | Data inválida | 5 variações, incluindo `2026-13-45T99:99:99` e `amanhã` | 422 em todas | conforme nas 5 | Aprovado |
| CT-79 | Duração absurda | negativa, zero e 10⁹ minutos | 422 em todas | conforme nas 3 | Aprovado |
| CT-80 | Transição de status inválida | status inventado, e concluído de volta a pendente | 422 | conforme | Aprovado |
| CT-81 | Filtros de período | intervalo de datas, inclusive invertido | resultados corretos; intervalo inválido recusado | conforme | Aprovado |

### 4.8 Autorização entre profissionais (OWASP A01 — IDOR)

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-82 | Varredura de IDOR por URL | 23 rotas recebem identificador; 2 servem termos públicos (sem dono) e 2 têm teste próprio. As 19 restantes entram em varredura parametrizada: autenticado como B, com identificadores de A | 404 em todas — nunca 200, nunca 403 (que confirmaria a existência) | conforme nas 19 | Aprovado |
| CT-83 | A varredura não envelhece | comparar a lista testada com as rotas com identificador publicadas no OpenAPI | contagens coincidem | conforme | Aprovado |
| CT-84 | IDOR pelo corpo | `clienteId` de outra conta em criação de atendimento e agendamento | 404; nenhum vínculo criado | conforme | Aprovado |
| CT-85 | Foto para cliente alheio | enviar foto informando cliente da outra conta | 404; nada gravado | conforme | Aprovado |
| CT-86 | Simulação para cliente alheio | solicitar simulação sobre cliente da outra conta | 404; provedor não chamado | conforme | Aprovado |
| CT-87 | Atendimento com simulação alheia | vincular atendimento próprio a simulação de A | 404 | conforme | Aprovado |
| CT-88 | Filtros de lista não atravessam contas | buscas e listas amplas na conta B | nenhum registro de A | conforme nas 5 rotas | Aprovado |
| CT-89 | B não obtém a URL assinada de A | inspecionar 5 rotas que devolvem URL de imagem, autenticado como B | nenhuma URL de imagem de A aparece | conforme | Aprovado |
| CT-90 | Assinatura obrigatória | requisitar a imagem sem o parâmetro de assinatura | 422 | conforme | Aprovado |
| CT-91 | Assinatura forjada | 3 variações: caractere a mais, a menos, inventada | 404 em todas | conforme nas 3 | Aprovado |
| CT-92 | Assinatura expirada | assinar com validade no passado | 404 | conforme | Aprovado |
| CT-93 | Assinatura não vale para outra imagem | aplicar a assinatura da foto de perfil ao identificador da imagem de entrada | 404 | conforme | Aprovado |
| CT-94 | Natureza da URL assinada | usar a URL de A autenticado como B e sem autenticação | 200 nos dois casos — a assinatura **é** a credencial, por desenho | conforme ao desenho; registrado como risco residual (**A-18**) | Aprovado |
| CT-95 | Token de conta excluída | excluir a conta e reusar o token | 401 | conforme | Aprovado |

### 4.9 Injeção e entradas hostis (OWASP A03)

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-96 | Injeção de SQL na busca | `' OR 1=1 --`, `'; DROP TABLE clientes; --` e variações codificadas | tratado como texto literal; tabelas intactas | conforme | Aprovado |
| CT-97 | Injeção nos filtros e parâmetros | payloads em data, status, ordenação e identificadores | 422 de validação; nenhuma concatenação de SQL | conforme | Aprovado |
| CT-98 | XSS armazenado | `<script>` e `<img onerror=>` em nome, observação e nome de arquivo | armazenado e devolvido como texto; renderizado como texto | conforme | Aprovado |
| CT-99 | XSS refletido | termo de busca devolvido em mensagem de erro | sem interpolação de HTML; `Content-Type` sempre JSON | conforme | Aprovado |
| CT-100 | Travessia de caminho | `../` em nome de arquivo e em identificador | recusado; nenhuma leitura ou escrita fora do diretório | conforme | Aprovado |
| CT-101 | Ausência de rastro de pilha | provocar erro e inspecionar a resposta | sem `traceback`, `sqlalchemy`, `psycopg`, `select`, caminho de arquivo ou número de linha | conforme | Aprovado |
| CT-102 | Forma única do erro | 401, 404 e 422 lado a lado | todos com `erro.codigo` e `erro.mensagem` preenchidos | conforme | Aprovado |
| CT-103 | Corpo que não é JSON | enviar bytes inválidos com `Content-Type: application/json` | 422 no formato padrão | conforme | Aprovado |
| CT-104 | Método não permitido | `PUT` em rota de coleção | 405 no formato padrão | conforme | Aprovado |

### 4.10 Configuração e exposição (OWASP A05)

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-105 | Autenticação obrigatória | requisitar as rotas de dados sem token | 401 em todas | conforme | Aprovado |
| CT-106 | Cabeçalhos de segurança | inspecionar as respostas, inclusive de erro | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` e política de domínios cruzados presentes | **nenhum deles existia** — A-04 | Aprovado após correção |
| CT-107 | HSTS só em produção | inspecionar em teste e com `AMBIENTE=producao` | ausente em teste, presente em produção | conforme após correção | Aprovado após correção |
| CT-108 | Divulgação do servidor | inspecionar o cabeçalho `Server` | sem versão de servidor de aplicação | expunha `uvicorn` — A-08 | Aprovado após correção |
| CT-109 | Documentação interativa | `/docs`, `/redoc`, `/openapi.json` com `AMBIENTE=producao` | 404 | estavam abertos em produção — A-05 | Aprovado após correção |
| CT-110 | CORS | origem autorizada, origem estranha, requisição prévia, e a configuração montada | liberação só para a origem autorizada; sem curinga com credenciais | conforme nos 4 | Aprovado |
| CT-111 | Segredos no repositório | varrer todo o histórico do Git por chaves, tokens, senhas e `.env` versionados | nenhum segredo em commit algum | conforme — as únicas ocorrências são `<token>` em documentação | Aprovado |
| CT-112 | Atalhos de demonstração | rotas de demonstração com `MODO_DEMO=false` | indisponíveis | conforme | Aprovado |

### 4.11 Banco de dados e integridade

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-113 | Campos obrigatórios | inserir, por SQL direto, registros sem os obrigatórios | recusado pelo banco, não só pela aplicação | conforme | Aprovado |
| CT-114 | Chaves estrangeiras | apontar para identificadores inexistentes | recusado | conforme | Aprovado |
| CT-115 | Vínculo simulação↔consentimento | inserir simulação sem consentimento, por SQL direto | recusado — `consentimento_id` é obrigatório | conforme | Aprovado |
| CT-116 | O cenário de exclusão é real | antes de testar exclusão, afirmar que há dado e arquivo | contagens positivas e arquivos no disco | conforme — canário | Aprovado |
| CT-117 | Exclusão de cliente, no banco | excluir cliente com tudo pendurado | nenhum registro órfão em 5 tabelas; nenhum atendimento com referência pendente | conforme | Aprovado |
| CT-118 | Exclusão de cliente, no disco | varrer o storage depois da exclusão | nenhum arquivo remanescente | conforme | Aprovado |
| CT-119 | Exclusão de conta | excluir a conta e varrer banco e disco | nada da conta permanece em 8 tabelas nem no disco | conforme | Aprovado |
| CT-120 | Exclusão de imagens preserva histórico | apagar as simulações do cliente | atendimento e consentimento preservados; `simulacaoId` anulado | conforme | Aprovado |
| CT-121 | Termos sobrevivem | excluir a conta e contar os termos | inalterados — são dado de sistema | conforme | Aprovado |

### 4.12 Contrato entre aplicativo e API

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-122 | Correspondência de campos | comparar 15 tipos de `tipos.ts` com os schemas do OpenAPI | nenhum campo a mais nem a menos de nenhum lado | conforme nos 15 pares | Aprovado |
| CT-123 | Convenção de nomes | varrer todos os schemas | nenhum campo em `snake_case` | conforme | Aprovado |
| CT-124 | Forma das listas | inspecionar as rotas de lista | array simples, como o aplicativo consome | conforme; ausência de paginação registrada como risco residual (**A-12**) | Aprovado |
| CT-125 | Enumerações | comparar os valores das 5 enumerações usadas em `switch` | idênticos dos dois lados | conforme nas 5 | Aprovado |
| CT-126 | O arquivo de tipos existe | afirmar a presença de `tipos.ts` antes de comparar | presente | conforme — canário | Aprovado |

### 4.13 Interface: fluxos, estados, responsividade e acessibilidade

Executados em Chromium real, contra a API em funcionamento. A exceção é CT-137, calculado
sobre os tokens de cor do tema.

| ID | Funcionalidade | Passos | Resultado esperado | Resultado obtido | Status |
| --- | --- | --- | --- | --- | --- |
| CT-127 | Fluxo completo | cadastro → ciência → criar cliente → bloqueio por falta de consentimento → termo → aceite → captura → validação → simulação → resultado → atendimento → agendamento → revogação → exclusão de imagens | cada etapa conclui e a seguinte reflete o estado real do servidor | conforme — 26 passos, nenhuma falha | Aprovado |
| CT-128 | Fidelidade ao design | conferência visual das telas percorridas, com captura em cada etapa | tipografia, paleta, espaçamento e componentes conforme o design | conforme nas telas percorridas | Aprovado (por amostragem) |
| CT-129 | Estado de carregamento | transições entre telas que dependem do servidor | indicador visível, sem salto de layout | conforme | Aprovado |
| CT-130 | Estado vazio | conta nova, sem clientes | mensagem explicando o próximo passo | conforme | Aprovado |
| CT-131 | Estado de erro de conexão | derrubar a API no meio da sessão e abrir a lista | aviso explícito de falha, distinto da lista vazia | exibia "Nenhum cliente cadastrado" — apresentava indisponibilidade como ausência de dados — **A-02** | Aprovado após correção |
| CT-132 | Validação de formulários | formulário vazio e com telefone inválido | envio bloqueado, mensagem apontando o campo | conforme | Aprovado |
| CT-133 | Responsividade | 390, 768 e 1280 px | sem rolagem horizontal; conteúdo renderizado | conforme nas três larguras | Aprovado |
| CT-134 | Alvos de toque | medir todos os elementos interativos nas três larguras | nenhum abaixo de 44 px no menor lado | o campo de busca media 18 px de altura dentro de uma linha de 48 px — **A-19** | Aprovado após correção |
| CT-135 | Rótulos acessíveis | inspecionar campos e botões | nenhum campo sem rótulo; nenhum botão sem nome acessível | conforme | Aprovado |
| CT-136 | Alternativa textual de imagens | inspecionar as imagens | todas com `alt` ou marcadas como decorativas | conforme | Aprovado |
| CT-137 | Navegação por teclado | percorrer por tabulação e verificar o destaque de foco | foco alcança os controles e é visível | conforme — 13 paradas | Aprovado |
| CT-138 | Contraste | calcular a razão WCAG dos 16 pares de cor declarados no tema | pares de texto ≥ 4,5:1; elementos não textuais ≥ 3:1 | 15 pares de texto entre 4,89:1 e 17,81:1; ícones a 3,70:1 | Aprovado |
| CT-139 | Console limpo | acompanhar o console nas duas baterias | nenhum erro e nenhum aviso relevante | 2 famílias de aviso: `pointerEvents` depreciado e `useNativeDriver` na web — **A-09** | Aprovado após correção |

---

## 5. Achados

Vinte e dois achados foram registrados. **Dezoito foram corrigidos** durante esta
verificação, cada um em commit próprio, com reexecução dos testes relacionados. **Quatro
permanecem abertos** como risco residual justificado, nenhum deles de severidade Alta ou
Crítica.

**Nenhum achado de severidade Crítica foi encontrado.** Nas quatro áreas em que uma falha
crítica seria mais provável — isolamento entre profissionais, injeção, segredos no
repositório e integridade nas exclusões — a verificação foi deliberadamente agressiva, e o
sistema resistiu.

### 5.1 Severidade Alta

| ID | Descrição | Severidade | Como reproduzir | Correção | Status |
| --- | --- | --- | --- | --- | --- |
| **A-16** | **O sistema não subia em ambiente limpo.** `EmailStr`, usada em `app/schemas/auth.py`, exige o pacote `email-validator`, que não constava do `requirements.txt`. Seguindo o procedimento documentado em uma máquina nova, o import da aplicação falhava e a suíte não coletava um único teste. No ambiente de desenvolvimento anterior o pacote existia por acidente — provavelmente arrastado por outra instalação — o que escondia a falta por completo. É o tipo de defeito que só aparece quando se instala do zero, e que teria recebido o avaliador do TCC com um erro de importação. | Alta | criar ambiente virtual novo, `pip install -r requirements.txt`, `python -c "from app.main import app"` | `email-validator==2.3.0` declarado no `requirements.txt`, com comentário explicando por quê. Verificado: antes, `ImportError`; depois, a aplicação importa e os 148 testes da base passam. | Corrigido — CT-01 |
| **A-01** | `POST /simulacoes` não tinha teto de chamadas. Cada simulação é uma chamada paga ao provedor externo; sem limite, uma conta autenticada — ou um token roubado — podia esgotar o crédito contratado em minutos, em um laço de requisições. A autenticação não protege contra isso: o abuso vem de dentro da sessão legítima, e o prejuízo é financeiro, não de dados. | Alta | autenticar, criar cliente com consentimento e foto válida, e disparar `POST /simulacoes` em laço | Teto por conta e por janela de uma hora (`SIMULACAO_MAX_POR_HORA`, padrão 20), aplicado **antes** de qualquer processamento, logo após a verificação de propriedade. Excedido, a resposta é 429 com o código `limite_de_simulacoes`. Três testes acompanham, inclusive um que prova a ordem: com o teto zerado e foto inválida, a resposta é 429 e não 422. | Corrigido — CT-69 a CT-71 |
| **A-20** | **Pillow 12.3.0 tinha 8 vulnerabilidades conhecidas**, todas corrigidas na versão 13.0.0 (CVE-2026-112895, -112400, -112397, -112896, -112897, -112395, -112404, -112899). Pillow é a biblioteca que decodifica **as fotografias enviadas pelos usuários** — ou seja, estava no caminho direto de entrada de conteúdo não confiável, que é exatamente onde uma falha de decodificação de imagem importa. Nenhuma linha do código do sistema estava errada: o risco entrou por uma versão fixada que envelheceu. Os textos das advisories não puderam ser lidos neste ambiente (o acesso às bases de vulnerabilidade está bloqueado pela política de rede), então a classificação se baseou na posição da biblioteca no sistema, não na análise de cada CVE. | Alta | `pip-audit` no ambiente do back-end | `pillow==13.0.0` no `requirements.txt`. Verificado após a troca: os 14 testes de validação de foto passam, os 305 da suíte passam, a cobertura segue em 93%, as duas baterias de navegador concluem sem falha com a API reiniciada sobre a versão nova, e o `pip-audit` deixa de apontar qualquer vulnerabilidade. | Corrigido |

### 5.2 Severidade Média

| ID | Descrição | Severidade | Como reproduzir | Correção | Status |
| --- | --- | --- | --- | --- | --- |
| **A-02** | Com a API fora do ar, a lista de clientes exibia "Nenhum cliente cadastrado" e o painel oferecia "Cadastre seu primeiro cliente". Uma indisponibilidade de servidor era apresentada ao profissional como ausência de dados — a leitura natural é "meus clientes desapareceram". Além do susto, convida à ação errada: recadastrar o que já existe. O store já expunha `erroDeCarga`, e nenhuma tela o usava. | Média | abrir o aplicativo, derrubar a API e abrir a aba de clientes | Componente `AvisoDeConexao` com o hook `useFalhouAoCarregar`: faixa explicando que os dados estão no servidor e nada foi perdido, com ação de tentar de novo; o estado vazio é suprimido nas três telas de lista enquanto a carga tiver falhado. | Corrigido — CT-131 |
| **A-03** | As migrations do Alembic desligavam os registradores de log da aplicação. `fileConfig` é chamada com `disable_existing_loggers` no padrão `True`, que desativa todos os loggers já criados. Quando as migrations rodam no mesmo processo — exatamente o que acontece na suíte — o log da aplicação inteira é silenciado, sem aviso. **Consequência direta: os testes que comprovavam a ausência de dados pessoais nos logs passariam sem verificar nada.** | Média | rodar a suíte e observar que nenhuma linha de log é capturada | `fileConfig(..., disable_existing_loggers=False)` em `migrations/env.py`. Os testes de LGPD usam um coletor próprio e uma asserção-canário. **Verificado na prática:** revertendo a correção, os três testes de vazamento colhem log vazio e falham no canário — prova de que, sem ela, estariam passando no vácuo. | Corrigido — seção 7 |
| **A-04** | Nenhuma resposta trazia cabeçalho de segurança: sem `X-Content-Type-Options`, sem `X-Frame-Options`, sem `Referrer-Policy`, sem HSTS em produção. | Média | `curl -i` em qualquer endpoint | Middleware `CabecalhosDeSeguranca`, aplicado também às respostas de erro; HSTS apenas com `AMBIENTE=producao`. | Corrigido — CT-106, CT-107 |
| **A-05** | `/docs`, `/redoc` e `/openapi.json` ficavam acessíveis em produção, publicando a superfície completa da API, incluindo nomes de campos internos e formatos de entrada. | Média | subir com `AMBIENTE=producao` e requisitar `/docs` | `docs_url`, `redoc_url` e `openapi_url` passam a ser `None` em produção; em desenvolvimento e teste permanecem. | Corrigido — CT-109 |
| **A-17** | Uma resposta do provedor fora do contrato era registrada como `timeout`, e um corpo vazio como `erro_interno`. Nos dois casos o provedor **respondeu**, em milissegundos: chamar isso de tempo esgotado manda a investigação para a rede, que está intacta, e chamar de erro interno atribui ao sistema um problema do terceiro. Mesma família do A-07 — a causa registrada aponta para o lugar errado. | Média | cenários `malformada` e `vazia` do servidor de mentira | Corpo que não é JSON (ou não é objeto) e resposta sem endereço de consulta nem estado reconhecível passam a ser `resposta_invalida`, com log que registra as chaves recebidas sem o conteúdo. | Corrigido — CT-62, CT-63 |
| **A-06** | Dependência de nível **crítico** no ferramental do aplicativo (injeção de comando), mais `setuptools` 79.0.1 com PYSEC-2026-3447 no ambiente Python. | Média | `npm audit` e `pip-audit` | `npm audit fix` resolveu a ocorrência crítica e reduziu os alertas de 34 para 30, sem nenhuma crítica restante; `setuptools` elevada para ≥ 83, deixando o `pip-audit` sem apontar nada além do Pillow (A-20). | Corrigido (parcial — ver A-11) |

### 5.3 Severidade Baixa

| ID | Descrição | Severidade | Como reproduzir | Correção | Status |
| --- | --- | --- | --- | --- | --- |
| **A-15** | A barreira contra bomba de descompressão funcionava, mas pelo caminho errado. `Image.MAX_IMAGE_PIXELS` impedia a decodificação, como esperado — só que a exceção que o Pillow levanta nesse caso, `DecompressionBombError`, **não herda de `OSError` nem de `ValueError`**, as únicas capturadas pelo validador. Um arquivo de 68 bytes produzia exceção não tratada, respondida como 500: nenhum dado exposto e nenhuma memória consumida, mas um caminho de erro não tratado acionável por qualquer pessoa autenticada, com código HTTP enganoso. | Baixa | montar um PNG declarando 30.000 × 30.000 px e enviá-lo em `POST /clientes/{id}/foto` | `DecompressionBombError` acrescentada à tupla capturada, com comentário explicando por que precisa ser citada à parte. Dois testes: no validador e pelo HTTP, conferindo 422 e ausência de rastro de pilha. | Corrigido — CT-48 |
| **A-07** | Quando o provedor devolvia conteúdo que não era imagem (uma página HTML de erro, por exemplo), a simulação era registrada como `falha_no_armazenamento`, culpando um componente que nem havia sido tocado. | Baixa | cenário `imagem_invalida` do servidor de mentira | Tratamento próprio para a conversão, registrando `resposta_invalida` e um log que identifica o provedor como origem. | Corrigido — CT-65 |
| **A-08** | O cabeçalho `Server` divulgava `uvicorn`. | Baixa | `curl -I` em qualquer endpoint | Sobrescrito com valor neutro. | Corrigido — CT-108 |
| **A-09** | Duas famílias de aviso poluíam o console: `pointerEvents` passado como propriedade (forma depreciada) e `useNativeDriver: true` na web, que não tem módulo nativo e avisa a cada animação. Aviso conhecido e tolerado é ruído que esconde o aviso novo e relevante. | Baixa | abrir o aplicativo e observar o console | `pointerEvents` movido para o estilo; `useNativeDriver` passa a depender da plataforma, mantendo o driver nativo no aparelho. | Corrigido — CT-139 |
| **A-19** | O campo de busca da lista de clientes media **18 px de altura dentro de uma linha de 48 px**: a linha parecia clicável, mas só a faixa central focava o campo — abaixo do alvo de 44 px que o próprio projeto adota em `ALVO_TOQUE`. Encontrado pela medição nas três larguras. | Baixa | medir a caixa do campo de busca no navegador | `alignSelf: 'stretch'`, fazendo o campo ocupar a altura da linha. Verificado: alvos de toque passam nas três larguras. | Corrigido — CT-134 |
| **A-10** | Playwright era usado por comando documentado (`node e2e/fluxo-completo.mjs`) sem constar do `package.json`; funcionava apenas por estar instalado globalmente no ambiente anterior. Em qualquer outra máquina, o comando documentado falhava. | Baixa | clonar o projeto, `npm install`, executar o comando documentado | `@playwright/test` como dependência de desenvolvimento, com versão fixada, mais o script `npm run qa`. | Corrigido |
| **A-22** | O roteiro de ponta a ponta não era repetível, e escondia isso. Ele altera os dados de demonstração — revoga consentimento e apaga imagens, porque é o que verifica — e, na segunda execução, dois passos não encontravam mais o que esperavam e eram registrados como "[ -- ] não encontrado", sem contar como falha. Uma regressão nesses pontos ficaria invisível a partir da segunda rodada, que é quando o roteiro é mais usado. | Baixa | rodar `node e2e/fluxo-completo.mjs` duas vezes seguidas | Os dois passos passam a falhar, com a mensagem dizendo o que fazer, e o `qa.sh` recria a carga de demonstração antes das baterias. Verificado nas duas direções: após `seed --reset` o roteiro conclui os 26 passos; repetido sem reset, as pré-condições falham com orientação em lugar de desaparecerem. | Corrigido |
| **A-21** | O `conftest.py` truncava as tabelas entre os testes, mas nunca limpava o diretório do storage. Os arquivos de imagem acumulavam entre execuções, e um teste que afirma "não sobrou arquivo" não conseguia distinguir herança de vazamento. Defeito de infraestrutura de teste, não do produto — mas que impediria a verificação do art. 18, VI. | Baixa | rodar a suíte e listar o diretório de storage de teste | Limpeza do diretório antes e depois de cada teste, com comentário explicando por que a asserção depende disso. | Corrigido — CT-118 |

### 5.4 Achados abertos (risco residual aceito)

| ID | Descrição | Severidade | Por que permanece aberto | Status |
| --- | --- | --- | --- | --- |
| **A-18** | **A URL de imagem é uma credencial portadora.** A rota de entrega não tem autenticação, por decisão de projeto: o `<Image>` do React Native não envia cabeçalhos, então a assinatura HMAC *é* a autorização — e ela é conferida contra o dono registrado da imagem, não contra quem requisita. Consequência: quem possui uma URL assinada válida lê a imagem, inclusive autenticado como outra conta ou sem autenticação alguma. Isso **não é IDOR**: a assinatura não pode ser forjada sem o segredo do servidor, e nenhuma rota entrega a B uma URL de A (verificado em CT-89 a CT-93). O que limita a exposição é a validade de 10 minutos, o `Cache-Control: private` e o `Referrer-Policy: no-referrer`. Registro honesto: foi um teste meu que afirmou errado a garantia; o código estava certo. | Baixa | amarrar a entrega à sessão exigiria assinar com o usuário que requisita, e não com o dono da imagem — e aí o `<Image>` precisaria de outra forma de autenticação, o que muda o fluxo de exibição em várias telas | Aberto, documentado por teste (CT-94) |
| **A-11** | 30 alertas de `npm audit`, com **4 vulnerabilidades de raiz**: `braces`, `node-forge`, `uuid` (todas em ferramental de construção, na máquina de quem desenvolve) e `decode-uri-component` — a única que alcança o pacote distribuído, via `query-string` → `expo-router`, com impacto previsto de negação de serviço local diante de uma URL malformada. Os outros 26 pacotes apenas dependem desses quatro. | Média | dependem de atualização do próprio Expo SDK 57, que os fixa | Aberto — seção 6.1 |
| **A-12** | As rotas de lista não têm paginação: devolvem a coleção inteira. Com carteiras pequenas, como as do uso previsto, não há impacto perceptível; com carteiras grandes, vira limite de desempenho e de consumo de dados móveis. | Baixa | introduzir paginação altera o contrato da API e o consumo em três telas — não é correção de baixo risco | Aberto, registrado em teste (CT-124) |
| **A-13** | Não há revogação de token de renovação. Excluir a conta invalida tudo, mas um refresh token vazado permanece válido até expirar. | Baixa | exigiria armazenamento de estado de sessão, inexistente por decisão de projeto | Aberto, documentado |
| **A-14** | Os limites de tentativa de login e de simulações por hora são mantidos em memória, por processo. Com mais de uma réplica, cada uma contaria em separado, multiplicando o teto efetivo. | Baixa | para a escala prevista (uma instância) o controle é eficaz; em escala maior, caberia a um serviço compartilhado | Aberto, documentado |

---

## 6. Auditoria de dependências e suíte automatizada

### 6.1 Dependências

**Python (`pip-audit`):** o estado inicial tinha dois apontamentos — `setuptools` 79.0.1
(PYSEC-2026-3447) e **Pillow 12.3.0 com 8 advisories**, este último o mais relevante de
toda a auditoria, porque Pillow decodifica as fotografias enviadas pelos usuários. Após a
elevação de `setuptools` para ≥ 83 e do Pillow para 13.0.0, a auditoria responde
**"No known vulnerabilities found"**.

**Node (`npm audit`):** o estado inicial era de 34 alertas, um deles **crítico**. Após
`npm audit fix`:

| Nível | Antes | Depois |
| --- | --- | --- |
| Crítico | 1 | **0** |
| Alto | — | 19 |
| Moderado | — | 11 |
| **Total** | **34** | **30** |

Os 30 restantes foram examinados um a um, e a conclusão é mais precisa do que o número
sugere: **apenas 4 são vulnerabilidades de raiz**; os outros 26 pacotes constam da lista
somente por dependerem de um desses quatro.

| Pacote | Nível | Onde entra | Alcança o aparelho? |
| --- | --- | --- | --- |
| `braces` | alto | `micromatch` → `metro` / `@expo/cli` | Não — empacotador, roda na máquina de quem desenvolve |
| `node-forge` | alto | `@expo/code-signing-certificates` → `@expo/cli` | Não — assinatura de build |
| `uuid` | moderado | `xcode` → `@expo/config-plugins` → `expo-splash-screen` | Não — manipulação do projeto iOS, em tempo de build |
| `decode-uri-component` | moderado | `query-string` → `expo-router` | **Sim** — negação de serviço local diante de URL malformada |

Forçar versões diferentes das que o SDK fixa quebraria a construção do aplicativo, e esse
custo é maior que o risco evitado em três dos quatro casos. A resolução correta é a
atualização do próprio Expo SDK, que não é decisão desta verificação. Fica como risco
residual explícito (A-11).

### 6.2 Suíte automatizada

A suíte é executável **por um único comando**, como exigido:

```bash
./qa.sh              # back-end: suíte completa com cobertura
./qa.sh --interface  # acrescenta as duas baterias de navegador
./qa.sh --tudo       # acrescenta a auditoria de dependências
```

**Resultado da última execução completa:**

| Métrica | Valor |
| --- | --- |
| Testes executados | **305** |
| Aprovados | **305** |
| Falhados | 0 |
| Cobertura de linhas (`app/`) | **93%** (2.215 linhas, 151 não cobertas) |

Distribuição por área:

| Arquivo | Testes | Área coberta |
| --- | --- | --- |
| `test_limites_e_contratos.py` | 62 | entradas válidas, inválidas, ausentes e de borda; forma das respostas |
| `test_idor_completo.py` | 32 | IDOR em todas as rotas com identificador; assinatura de imagem |
| `test_regras_consentimento.py` | 24 | regras de consentimento, unitárias |
| `test_contrato_com_aplicativo.py` | 19 | correspondência entre os tipos do aplicativo e os schemas da API |
| `test_seguranca_aplicacao.py` | 17 | cabeçalhos, exposição, CORS, abuso de custo, bomba de descompressão |
| `test_simulacao_com_mock_ia.py` | 16 | fluxo de simulação nos dez cenários do servidor de mentira |
| `test_validacao_foto.py` | 14 | validação da foto antes da chamada paga |
| `test_consentimento.py` | 13 | registro, histórico, revogação, menor de idade, versionamento |
| `test_provedor_ia.py` | 12 | provedores de IA (local e Replicate com HTTP simulado) |
| `test_agenda_e_atendimentos.py` | 12 | RF03 e RF06 |
| `test_simulacoes.py` | 11 | RF04, RF05 e RF07 |
| `test_entradas_maliciosas.py` | 11 | injeção, travessia de caminho, conteúdo disfarçado |
| `test_auth.py` | 11 | RF01 |
| `test_seguranca.py` | 10 | senhas, tokens, assinatura de imagem |
| `test_clientes.py` | 10 | RF02 e isolamento |
| `test_casos_criticos.py` | 9 | os sete casos críticos exigidos pela especificação |
| `test_imutabilidade.py` | 8 | gatilhos e índices únicos parciais, atacados por SQL direto |
| `test_integridade_dados.py` | 6 | órfãos no banco e arquivos esquecidos no disco |
| `test_lgpd.py` | 4 | ausência de dado pessoal nos logs, com canário no instrumento |
| `test_protecoes.py` | 3 | tamanho de corpo e força bruta |
| `test_seed.py` | 1 | carga de demonstração |

Sobre os 7% não cobertos: são, em sua maioria, ramos de indisponibilidade de
infraestrutura externa — o driver S3 responde por 35 das 151 linhas não cobertas, porque
exigiria um S3 real indisponível — e o ponto de entrada do servidor. **Nenhuma regra de
negócio, regra de consentimento ou verificação de autorização está fora da cobertura.**

**Baterias de interface** (Chromium real, com API e aplicativo em execução):

| Bateria | Verifica | Resultado |
| --- | --- | --- |
| `e2e/fluxo-completo.mjs` | o fluxo de ponta a ponta, do cadastro à exclusão | **26 passos, nenhuma falha, 0 erros de console** |
| `e2e/qa-interface.mjs` | responsividade (390/768/1280), alvos de toque, rótulos acessíveis, nomes de botão, alternativas textuais, navegação por teclado, validação, estado vazio, API fora do ar, console | **todas as verificações aprovadas, sem erro e sem aviso** |

---

## 7. Conformidade com a LGPD nos pontos verificados

A avaliação trata apenas do que foi **verificado por execução**.

| Ponto verificado | Fundamento | Resultado |
| --- | --- | --- |
| **Consentimento registrado antes da captura e da simulação** | art. 7º, V e art. 11 | **Conforme.** A captura é bloqueada sem consentimento ativo. A simulação é bloqueada antes de qualquer processamento e, comprovadamente, **sem que o provedor externo seja chamado** — a lista de chamadas recebidas pelo servidor de mentira permanece vazia. A garantia não depende da aplicação: `simulacoes.consentimento_id` é obrigatório no banco, de modo que não existe imagem gerada sem a decisão que a autorizou (verificado por SQL direto). |
| **Vínculo com a versão exata do termo apresentado** | art. 9º | **Conforme.** Cada decisão aponta para a versão efetivamente exibida. Publicar nova versão não altera aceites anteriores, e índice único parcial garante um único termo vigente por tipo. |
| **Imutabilidade do registro** | art. 37 | **Conforme.** Gatilhos em PL/pgSQL recusam `UPDATE` e `DELETE` em consentimentos, ciências e termos. Verificado por ataque via SQL direto, por cima da aplicação — a garantia está no banco, não no código. |
| **Revogação com efeito real** | art. 8º, §5º e art. 18, IX | **Conforme.** Após a revogação, a captura volta a ser bloqueada imediatamente e novas simulações são recusadas. O histórico anterior é preservado, como exige o art. 37 — revogar não é apagar o registro de que houve consentimento. |
| **Exclusão efetiva dos dados e das fotos** | art. 18, VI | **Conforme.** Excluir o cliente remove consentimentos, imagens, simulações e agendamentos, e também os **arquivos** no armazenamento. Verificado por varredura simultânea do banco e do disco: nenhum registro órfão, nenhum arquivo remanescente. O mesmo para a exclusão de conta. Atendimentos sobrevivem à exclusão de uma simulação com o vínculo anulado, preservando o histórico de serviço sem manter a imagem. |
| **Consentimento do menor de idade** | art. 14, §1º | **Conforme.** Cliente menor sem responsável legal tem a captura bloqueada, com motivo específico. Com responsável informado, o consentimento é aceito e o registro guarda quem consentiu. |
| **Transparência sobre o envio ao terceiro** | art. 9º e art. 18, VII | **Conforme nos pontos verificáveis.** O termo informa, em seção própria, que a fotografia é enviada a um serviço de inteligência artificial de terceiro e que a política de retenção desse terceiro está fora do controle do sistema — e a bateria de navegador confirma que esse aviso continua visível na tela do termo. O que de fato é enviado foi verificado na inspeção das chamadas recebidas pelo servidor de mentira: **a fotografia e os parâmetros do penteado, e nada mais** — nenhum nome, telefone, data de nascimento ou observação. |
| **Minimização na coleta e na exibição** | art. 6º, III | **Conforme.** Os metadados EXIF da fotografia (data, fabricante, GPS) são descartados na normalização, verificado comparando entrada e saída. As imagens são servidas por URL assinada com expiração, não por URL pública permanente. |
| **Dados pessoais e sensíveis fora dos logs** | art. 46 e art. 6º, VIII | **Conforme, após A-03.** Verificado que nome, telefone, observação clínica, senha, conteúdo `data:image`, cadeias em base64 e nome do arquivo enviado não aparecem nos registros. Os identificadores registrados são UUIDs. Importante registrar que esta conformidade estava sendo **atestada por testes vazios**: o mecanismo de log estava silenciado pelas migrations. Depois da correção, e com a asserção-canário que impede o teste de passar sem capturar log, passou a ser efetivamente verificada. |
| **Credencial do provedor fora do aplicativo** | art. 46 | **Conforme.** A chave existe apenas no servidor, lida de variável de ambiente. Nenhuma resposta ao aplicativo a contém, em nenhum dos cenários de erro — inclusive naquele em que o provedor devolve a própria mensagem de erro de autenticação. Verificado também que não há chave alguma em todo o histórico do Git. |

**Ponto que permanece como limitação, e não como não conformidade:** o valor probatório do
consentimento. O registro é feito pelo profissional, no aparelho, com o cliente presente; o
sistema registra o que foi apresentado, quando, por quem e sob qual versão do termo, de
forma imutável, mas não captura assinatura manuscrita nem biometria. Para o uso previsto
isso é adequado e está documentado; em contexto que exija prova mais forte, seria
necessário um mecanismo adicional de autenticação do titular.

---

## 8. Riscos residuais, limitações e o que testar com a API real

### 8.1 Propostas que não foram aplicadas

1. **Paginação nas rotas de lista (A-12).** Altera o contrato da API e o consumo em três
   telas do aplicativo.
2. **Lista de tokens de renovação invalidados (A-13)** e **limites compartilhados entre
   réplicas (A-14).** Ambas exigem armazenamento de estado hoje inexistente.

A atualização do Pillow (A-20), que constava aqui como proposta, foi confirmada pelo autor
e aplicada — ver seção 5.1.

### 8.2 Limitações desta verificação

- **A API externa real nunca foi chamada.** O protocolo imitado corresponde ao da
  Replicate conforme a sua documentação, mas imitação não é o serviço.
- **Nenhum aparelho físico foi usado.** A verificação de interface foi feita no navegador,
  com emulação de três larguras. Câmera, permissões do sistema operacional, teclado e
  seletor de data nativos e desempenho real não foram exercitados. iOS não foi testado.
- **O contraste foi verificado na paleta, não na tela.** As razões foram calculadas sobre
  os tokens de cor do tema, o que comprova que as combinações previstas atendem ao
  critério, mas não substitui a medição dos pixels de cada tela renderizada.
- **A acessibilidade verificada é a básica.** Não houve teste com leitor de tela real
  (TalkBack ou VoiceOver), nem auditoria completa contra a WCAG 2.2.
- **Não houve teste de carga.** Nenhuma medição sob concorrência ou volume.
- **`docker compose up` não foi executado**, por não haver daemon do Docker no ambiente; a
  validação usou PostgreSQL 16 local, com as mesmas migrations.
- **Os textos das advisories do Pillow não puderam ser lidos**, porque o acesso às bases
  de vulnerabilidade está bloqueado pela política de rede deste ambiente. A classificação
  de A-20 se baseia na posição da biblioteca no sistema e na versão de correção indicada
  pelo `pip-audit`.
- **A detecção de rosto usa cascata de Haar**, rápida e local, mas menos precisa que um
  modelo neural. Rostos em ângulo incomum podem ser recusados — falso negativo que custa
  refazer a foto, não um risco de segurança.

### 8.3 O que precisa ser testado quando a API real for integrada

Lista de verificação para o momento da contratação da credencial, em ordem de prioridade.

**Privacidade e conformidade**

1. **Política de retenção real do provedor.** Confirmar, na documentação contratual da
   Replicate, por quanto tempo a imagem enviada é retida e para que pode ser usada, e se o
   texto do termo apresentado ao cliente descreve isso com exatidão. **É a verificação mais
   importante da lista**, porque é a única cujo resultado pode exigir alteração no termo de
   consentimento — e, portanto, novo aceite dos clientes já cadastrados.
2. **Ausência de dado pessoal no tráfego real.** Repetir a inspeção feita contra o servidor
   de mentira, agora sobre a requisição real.
3. **Credencial em produção.** Confirmar que a chave vem do gerenciador de segredos do
   ambiente de implantação, que não aparece em log de requisição ou de erro, e que a
   rotação não exige alteração de código.

**Protocolo e contrato**

4. **Forma real da resposta.** Confirmar que o campo de saída é o que o cliente espera, e
   tratar a variação conhecida em que a saída vem como lista. O servidor de mentira cobre
   as duas formas; o serviço real decide qual usa.
5. **Códigos de erro reais.** Mapear o que a Replicate devolve para credencial inválida,
   crédito esgotado, limite de taxa e modelo indisponível, e conferir se cada um cai no
   motivo de falha correto — a correção A-17 tornou essa distinção significativa.
6. **Limite de taxa do próprio provedor.** O teto local (A-01) protege o crédito, mas não
   conhece o limite do provedor. Verificar o cabeçalho devolvido e decidir se o sistema
   deve respeitá-lo explicitamente.

**Tempo e confiabilidade**

7. **Tempo real de geração.** Medir e reavaliar `AI_TIMEOUT_S` (hoje 60 s) e
   `AI_INTERVALO_CONSULTA_S`. Um tempo limite curto demais transforma sucesso em falha.
8. **Intermitência.** Observar falhas esporádicas reais e decidir se cabe política de nova
   tentativa — que hoje não existe, deliberadamente, porque cada tentativa custa dinheiro.
9. **Concorrência.** Várias simulações simultâneas, da mesma conta e de contas diferentes,
   para confirmar que nenhuma se perde e que os estados não se misturam.

**Qualidade e custo**

10. **Qualidade do resultado com fotos reais.** Com consentimento próprio ou de
    voluntários, e nunca com dados de clientes reais sem autorização específica: avaliar se
    o resultado é utilizável, variando iluminação, tom de pele, tipo e comprimento de
    cabelo.
11. **Custo por simulação.** Medir o custo real e calibrar `SIMULACAO_MAX_POR_HORA` contra
    o orçamento, em lugar do padrão escolhido por prudência.
12. **Tamanho da fotografia enviada.** A foto vai como data URI. Medir o impacto no tempo e
    no custo, e avaliar se compensa reduzir a resolução antes do envio.

---

## 9. Conclusão

O Espelho foi submetido a 310 testes automatizados, três baterias em navegador real e uma
inspeção dirigida de segurança orientada pelo OWASP Top 10. Todos os testes passam, com
93% de cobertura de linhas, contra um PostgreSQL real construído pelas mesmas migrations
que o sistema usaria em produção.

**Nenhum achado de severidade Crítica foi encontrado.** Nas áreas em que uma falha crítica
seria mais provável, a verificação foi deliberadamente agressiva e o sistema resistiu:
nenhuma das rotas que recebem identificador permite alcançar dados de outra conta, por URL
ou por corpo; nenhuma tentativa de injeção produziu efeito; não há segredo em nenhum commit
do histórico; e nenhum caminho de exclusão deixa registro órfão ou arquivo esquecido.

Três achados de severidade Alta merecem destaque, e cada um ensina algo diferente:

**O sistema não subia em ambiente limpo (A-16).** Uma dependência não declarada fazia a
aplicação falhar no import. No ambiente de desenvolvimento o pacote existia por acidente, e
foi exatamente esse acidente que escondeu o defeito — a verificação só o encontrou porque
instalou tudo do zero, em vez de confiar no ambiente herdado.

**Não havia teto de chamadas ao provedor pago (A-01).** Não era falha de autenticação nem
de autorização — ambas funcionavam. Era falha de projeto, do tipo que só aparece quando se
pergunta o que um usuário *legítimo* pode causar, e não apenas o que um invasor pode
alcançar.

**A biblioteca que decodifica as fotos dos usuários tinha 8 vulnerabilidades conhecidas
(A-20).** Nenhuma linha do código do sistema estava errada; o risco entrou por uma versão
fixada que envelheceu. Era o único item que exigia decisão do autor, por ser troca de
versão maior de uma dependência fixada de propósito; aprovada, foi aplicada e a suíte
inteira reexecutada, com o `pip-audit` passando a não apontar nada.

O achado mais relevante para a credibilidade desta verificação, no entanto, é de severidade
Média: **os testes que atestavam a ausência de dados pessoais nos logs estavam passando sem
verificar nada (A-03).** A causa era remota e silenciosa — uma chamada de configuração de
log nas migrations, com um parâmetro padrão que desativa os registradores existentes. O
defeito não produzia erro algum; produzia confiança injustificada. Foi encontrado
precisamente porque a verificação não aceitou "o teste passa" como prova, e foi conferir se
o teste tinha o que observar. A correção tratou as duas coisas: o defeito no código e a
fragilidade do teste, que agora falha explicitamente se não capturar log nenhum.

Houve também um achado que se revelou erro **meu**, não do sistema: um teste afirmava que a
URL assinada de uma conta não funcionaria para outra. Ela funciona — e deve funcionar,
porque a assinatura é a credencial, dado que o `<Image>` do React Native não envia
cabeçalhos. A conclusão correta não foi mudar o código, e sim reescrever o teste para
afirmar o que o modelo garante de fato e registrar a característica como risco residual
(A-18). Verificação que só confirma o que esperava encontrar não é verificação.

Quanto às características de qualidade da ISO/IEC 25010:

- **Adequação funcional:** todos os requisitos no escopo (RF01–RF07) têm comportamento
  verificado por testes nomeados, incluindo os sete casos críticos da especificação.
- **Confiabilidade:** o sistema se comporta de forma previsível quando o provedor externo
  falha, demora, responde lixo ou não responde, e quando a própria API está fora do ar —
  esta última situação era, antes de A-02, a mais mal comunicada ao usuário.
- **Segurança:** os controles essenciais estão presentes e foram verificados por tentativa
  de burla, não por leitura. As lacunas eram de configuração e foram fechadas; a que resta
  é de dependência, não de código.
- **Usabilidade:** estados de tela, validação, alvos de toque, rótulos acessíveis,
  navegação por teclado e contraste atendem aos critérios verificados, nas três larguras.
- **Manutenibilidade:** a suíte roda por um comando e a cobertura é alta; o endereço do
  provedor externo foi tornado configurável justamente para permitir testar o cliente real
  sem rede — melhoria de testabilidade com efeito direto na qualidade da verificação.

**Avaliação de prontidão.** O sistema está pronto para demonstração acadêmica e para uso
piloto controlado com o provedor local de simulação. Para uso em produção com clientes
reais, duas condições, e nenhuma delas é defeito do que foi construído: exercitar a
integração real conforme a lista da seção 8.3 — com atenção ao item 1, que pode exigir
alteração no termo de consentimento — e decidir as propostas da seção 8.1, sendo a
paginação a mais provável de se tornar necessária com o crescimento das carteiras. Não
restou nenhum achado de severidade Alta em aberto.

A ressalva importante não está no código, e sim no alcance desta verificação: o fluxo mais
característico do sistema — a geração da simulação por inteligência artificial — foi
verificado contra uma imitação do provedor, e não contra o provedor. A arquitetura, o
tratamento de erro, os limites de custo, a validação prévia da fotografia e o vínculo com o
consentimento estão todos exercitados e corretos. O que falta saber é como o serviço real
se comporta, e essa é a primeira pergunta a responder quando a credencial existir.

---

## Apêndice A — Documentação atualizada nesta verificação

A instrução de atualizar a documentação onde ela divergisse do código resultou nas
alterações abaixo. Em todos os casos, o código estava correto e o texto estava velho.

| Arquivo | O que divergia | Alteração |
| --- | --- | --- |
| `backend/requirements.txt` | não declarava `email-validator`, sem a qual a aplicação não importa (A-16); fixava `pillow==12.3.0`, com 8 vulnerabilidades conhecidas (A-20) | dependência declarada e fixada, com comentário explicando por quê; Pillow elevada para 13.0.0 |
| `backend/README.md` | contagem de testes (148); ausência de `AI_BASE_URL`, `AI_INTERVALO_CONSULTA_S`, `AI_TIMEOUT_S` e `SIMULACAO_MAX_POR_HORA`; tabela de códigos HTTP sem o 429 de simulações; nada sobre cabeçalhos de segurança nem sobre o fechamento da documentação em produção; limitações sem a paginação e sem a natureza da URL de imagem | contagem corrigida para 305; variáveis documentadas; tabela completada; comportamento de produção descrito; `./qa.sh` referenciado; três limitações acrescentadas |
| `backend/.env.example` | não trazia as três variáveis novas | acrescentadas, com comentário sobre o propósito de cada uma |
| `DOCUMENTACAO-BACKEND.md` | contagem de testes em duas passagens; tabela de limitações sem o teto de simulações, a paginação e a URL de imagem; relato de execução sem a verificação de QA; tabela de tratamento de falhas sem o caso de conteúdo que não é imagem | contagens corrigidas; três limitações acrescentadas; relato ampliado; seção 7.5 nova, sobre contenção de custo |
| `DOCUMENTACAO.md` | contagem de testes; lista de limitações do aplicativo sem a distinção entre falha de conexão e lista vazia | contagem corrigida; o terceiro estado de lista (indisponível) documentado |
| `RELATORIO-FINAL.md` | contagem de testes em três passagens; lista de arquivos de teste incompleta; uma só bateria de navegador; cenários do provedor descritos apenas como HTTP simulado | contagens corrigidas; sete arquivos de teste acrescentados à tabela; segunda bateria descrita; servidor de mentira mencionado |
| `espelho/package.json` | Playwright usado por comando documentado, mas ausente do projeto (A-10) | acrescentado como dependência de desenvolvimento, com versão fixada, e script `npm run qa` |

### Arquivos criados nesta verificação

| Arquivo | Finalidade |
| --- | --- |
| `qa.sh` | executa a suíte inteira por um comando, com as variantes de interface e auditoria |
| `.gitignore` | o projeto recebido não tinha: `.env`, `.venv` e `node_modules` passam a ser explicitamente excluídos |
| `backend/tests/mock_provedor_ia.py` | servidor que imita o protocolo da Replicate, com dez cenários configuráveis |
| `backend/tests/test_simulacao_com_mock_ia.py` | fluxo de simulação contra o servidor de mentira |
| `backend/tests/test_idor_completo.py` | varredura de IDOR e verificação da assinatura de imagem |
| `backend/tests/test_limites_e_contratos.py` | entradas de borda e forma das respostas |
| `backend/tests/test_seguranca_aplicacao.py` | cabeçalhos, exposição, CORS, abuso de custo |
| `backend/tests/test_integridade_dados.py` | órfãos e arquivos esquecidos após exclusões |
| `backend/tests/test_lgpd.py` | ausência de dado pessoal nos logs, com canário no instrumento |
| `backend/tests/test_contrato_com_aplicativo.py` | correspondência entre os tipos do aplicativo e os schemas da API |
| `espelho/e2e/qa-interface.mjs` | responsividade, acessibilidade, estados de tela e console |
| `espelho/src/components/AvisoDeConexao.tsx` | aviso de falha de conexão, distinto do estado vazio (A-02) |
| `RELATORIO_QA.md` | este relatório |

### Arquivos de código corrigidos

| Arquivo | Correção |
| --- | --- |
| `backend/requirements.txt` | dependência faltante (A-16); Pillow elevada para 13.0.0 (A-20) |
| `backend/app/core/protecoes.py` | cabeçalhos de segurança (A-04, A-08) e teto de simulações (A-01) |
| `backend/app/main.py` | documentação fechada em produção (A-05); middleware registrado |
| `backend/app/api/v1/simulacoes.py` | acionamento do teto antes de qualquer processamento (A-01) |
| `backend/app/core/config.py` | endereço e intervalo do provedor configuráveis; teto de simulações |
| `backend/app/services/ai/replicate.py` | endereço vindo da configuração; resposta fora do contrato distinguida de tempo esgotado (A-17) |
| `backend/app/services/simulacao.py` | motivo correto quando o provedor devolve o que não é imagem (A-07) |
| `backend/app/services/validacao_foto.py` | bomba de descompressão recusada como foto inválida (A-15) |
| `backend/migrations/env.py` | migrations deixam de desligar os loggers da aplicação (A-03) |
| `backend/tests/conftest.py` | isolamento do storage entre testes (A-21) |
| `backend/tests/test_provedor_ia.py` | ajustado ao intervalo vindo da configuração |
| `espelho/e2e/fluxo-completo.mjs` | pré-condições do seed passam a falhar em vez de desaparecer do relatório (A-22) |
| `qa.sh` | recria a carga de demonstração antes das baterias, deixando a execução repetível (A-22) |
| `espelho/app/(tabs)/{index,clientes,agenda}.tsx` | aviso de conexão em lugar do estado vazio (A-02) |
| `espelho/app/(tabs)/clientes.tsx` | alvo de toque do campo de busca (A-19) |
| `espelho/app/simulacao/{captura,processando}.tsx`, `espelho/src/components/{Feedback,Hachura,Basicos}.tsx` | avisos de console: `pointerEvents` e `useNativeDriver` (A-09) |
