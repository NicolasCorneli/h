# Relatório de QA e melhorias — Salão em Dia

Auditoria completa, correção e validação do aplicativo recebido em
`salao-em-dia-completo_3.zip`. Execução em 25/10/2026, num contêiner Linux com
PostgreSQL 16.15, Python 3.13, Node 22 e Chromium (Playwright). Todos os números deste
relatório vêm de execuções feitas nesse ambiente; o que não pôde ser executado está marcado
como tal.

Nenhum commit foi feito, como pedido. O ZIP trazia um repositório Git com alterações ainda
não commitadas; o histórico dele foi importado e o trabalho está na área de trabalho, sobre
o commit `38c01c6` (a seção 11 explica como revisar).

---

## 1. Resumo executivo

**Estado inicial.** Um aplicativo maduro: API FastAPI com 417 testes passando (cobertura
94%), aplicativo Expo sem erros de tipo e oito baterias de navegador que passavam sem
falhas. A qualidade de partida era alta, e a auditoria precisou ir além do que as baterias
existentes cobriam.

**Problemas mais importantes encontrados** (todos reproduzidos antes de corrigir):

1. **Cadastrar ou editar cliente com data de nascimento falhava sempre.** O aplicativo
   enviava um instante (`1990-03-12T15:00:00.000Z`) num campo de data, o servidor recusava,
   e a mensagem "Confira os dados enviados" aparecia embaixo do campo *Nome*. Sem data de
   nascimento, a regra de responsável legal para menores (LGPD, art. 14) nunca se aplicava
   a um cliente cadastrado pelo aplicativo. Nenhuma bateria preenchia esse campo.
2. **Contas de demonstração com senha publicada podiam nascer em produção**: o seed não
   tinha proteção, o `docker-compose.yml` o roda por padrão, e o modo demonstração podia
   ficar ligado com `AMBIENTE=producao`.
3. **Corridas na agenda**: dois envios simultâneos gravavam o mesmo horário; confirmar
   podia desfazer um cancelamento feito no mesmo instante; a segunda conclusão simultânea
   virava erro 500.
4. **Foto de pessoa órfã no storage** quando as imagens (ou o cliente, ou a conta) eram
   apagadas durante a geração de uma simulação.
5. **Sessão**: uma falha de rede na renovação desconectava o profissional; sem sessão, os
   endereços internos (`/agenda`) abriam a tela vazia; com a sessão recusada no meio do uso,
   o aplicativo seguia "conectado" mostrando erros.
6. **Primeiro uso**: na tela inicial de uma conta nova, o aviso cobria o botão
   "Cadastrar primeiro cliente".
7. **Histórico sem correção**: um atendimento registrado com dados errados não podia ser
   corrigido nem excluído pelo aplicativo; a API aceitava atendimento com data futura e
   deixava dia e hora incoerentes.

**O que foi feito.** 23 problemas corrigidos (seção 3), uma funcionalidade completada
(correção e exclusão de atendimento), 21 testes novos no servidor, 2 testes de unidade e
uma bateria de navegador nova (27 verificações) no aplicativo, documentação atualizada.

**Estado atual** (depois também da segunda rodada, seção 13). 439 testes do servidor
passando (cobertura 95%), 0 erros de tipo, 88 casos de unidade do aplicativo passando, 9
baterias de navegador com 263 verificações e 0 falhas, build web de produção e pacote
Android concluídos.

**Riscos que permanecem** (seção 10): login com Google real e provedor de IA real não
validados (dependem de credenciais), build Docker não verificado (rede do ambiente), tokens
sem revogação no servidor, freio de login por IP que precisa de configuração atrás de proxy,
avisos do `npm audit` nas ferramentas do Expo.

---

## 2. Arquitetura encontrada

| Camada | Tecnologia | Observação |
| --- | --- | --- |
| Aplicativo | React Native 0.86, Expo SDK 57, expo-router, TypeScript estrito | Web (react-native-web) e celular; estado em Context + `useReducer` |
| API | FastAPI 0.142, Pydantic 2, SQLAlchemy 2.1 | Camadas: rotas `api/v1` → `services` → `repositories/consultas` → `models` |
| Banco | PostgreSQL 16, Alembic (7 migrations) | Gatilhos de imutabilidade em termos e consentimentos; índices únicos parciais |
| Imagens | driver local (disco) ou S3/MinIO/Supabase | Binário fora do banco; URLs assinadas (HMAC) de 10 minutos |
| Simulação | `fake` (local, sem custo) ou Replicate | Tarefa em segundo plano; o app consulta o estado |
| Autenticação | JWT HS256 (acesso 30 min, renovação 30 dias), bcrypt; Google (ID token) opcional | |
| Infra | Dockerfile e docker-compose (API + PostgreSQL); `qa.sh` | O aplicativo fica fora do Docker |

**Entidades:** usuários, identidades externas (Google), clientes, termos (versionados),
consentimentos (só inserção), ciências, imagens, simulações, atendimentos, agendamentos.

**Funcionalidades reais, não simuladas:** todas as do aplicativo falam com a API. O único
serviço simulado por padrão é o provedor de IA (`AI_PROVIDER=fake`), declarado como tal
na própria imagem gerada.

**Problemas arquiteturais encontrados:** ausência de travas em operações de
leitura-e-escrita concorrentes (agenda, exclusão de imagens), consultas N+1 nas listagens,
nenhum ponto central que avisasse a interface do fim da sessão, e nenhuma guarda de rotas.

**Decisões adotadas:** registradas em [`docs/DECISOES_TECNICAS.md`](../DECISOES_TECNICAS.md),
com destaque para a ordem única das travas no banco (quem apaga trava o cliente antes do
storage; quem grava resultado trava o cliente em modo compartilhado), datas do calendário
sempre como `aaaa-mm-dd`, e renovação de sessão com três resultados.

---

## 3. Problemas identificados

Severidade: P0 crítico, P1 alto, P2 médio, P3 baixo. "Teste" indica o que comprova a
correção (e que falha no código original, quando executado contra ele).

| ID | Problema | Sev. | Área | Causa raiz | Impacto | Solução |
| --- | --- | --- | --- | --- | --- | --- |
| QA-01 | Cliente com data de nascimento nunca era salvo; erro mostrado sob "Nome" | P1 | App | `isoDeDataCurta` devolvia `toISOString()`; o servidor exige data sem hora | Cadastro/edição falhava; regra de menor de idade nunca aplicada a clientes do app | Devolve `aaaa-mm-dd`; erro vai ao campo que o servidor apontou; validação de data futura e implausível no formulário. Teste: `testes/datas.mjs`, `e2e/auditoria.mjs` (3, 4, 5) |
| QA-02 | Seed e modo demonstração permitidos em produção | P1 | API/Infra | Sem verificação de ambiente; compose roda o seed por padrão | Contas com senha publicada e atalhos de demonstração em produção | API não sobe com `AMBIENTE=producao` + `MODO_DEMO=true`; seed recusa em produção; entrypoint pula o seed. Teste: `test_producao_nao_sobe_com_modo_demonstracao`, `test_seed_se_recusa_em_producao` |
| QA-03 | Criações simultâneas gravavam o mesmo horário | P2 | API | Conferência de conflito e inserção sem trava | Agenda com dois clientes no mesmo horário | Trava da linha do usuário antes de conferir. Teste: `test_criacoes_simultaneas_nao_ocupam_o_mesmo_horario` |
| QA-04 | Mudança de status decidida sobre status antigo (confirmar desfazia cancelamento; 2ª conclusão = 500) | P2 | API | `with_for_update` devolvia o objeto já em memória (sem `populate_existing`); confirmar/cancelar/editar sem trava | Estado inconsistente da agenda; erro 500 em toque duplo | `_reler_com_trava` em toda mudança. Testes: `test_conclusao_simultanea_devolve_o_mesmo_atendimento`, `test_confirmar_nao_desfaz_um_cancelamento_simultaneo` |
| QA-05 | Foto gerada ficava órfã no storage se as imagens/cliente/conta fossem apagados durante a geração (e a tarefa terminava com exceção) | P2 | API/LGPD | Exclusão limpava o storage antes de travar; gravação do resultado não conferia se a simulação ainda existia nem limpava o arquivo em erro | Imagem de pessoa sem registro depois do pedido de eliminação | Ordem de travas (cliente) entre exclusão e gravação; descarte do resultado; limpeza do arquivo em falha. Teste: `test_apagar_imagens_durante_a_geracao_nao_deixa_arquivo_orfao` |
| QA-06 | Falha de rede na renovação da sessão desconectava o profissional | P2 | App | `renovarSessao` devolvia `false` para rede e para recusa, e o chamador encerrava a sessão | Logout indevido com rede instável | Três resultados (renovada, recusada, sem conexão); só recusa 4xx encerra; tempo limite na renovação. Teste: `e2e/auditoria.mjs` (6) |
| QA-07 | Sem guarda de rotas; sessão recusada no meio do uso deixava o app "conectado" | P2 | App | Redirecionamento só existia na porta de entrada; o fim de sessão não avisava a interface | Telas vazias e erros "token inválido" em vez do login | `GuardaDeSessao` no layout raiz; `aoEncerrarSessao` avisa o store. Teste: `e2e/auditoria.mjs` (1, 7) |
| QA-08 | Aviso cobria o botão "Cadastrar primeiro cliente" na conta nova | P2 | App/UX | `flex: 0` vira `flex: 0 0 0%` no react-native-web; a caixa encolhia e o conteúdo transbordava | Primeira ação de quem acabou de criar a conta escondida | `flexGrow: 0, flexShrink: 0, flexBasis: 'auto'`. Teste: `e2e/auditoria.mjs` (2). A captura da equipe anterior (`e2e/telas/04-painel-vazio.png`) já mostrava o defeito |
| QA-09 | API aceitava atendimento com data futura; corrigir só o dia deixava a hora de outro dia | P2 | API/Dados | Validação de futuro só no caminho com hora | Histórico com datas impossíveis ou contraditórias | Recusa de dia futuro (limite: maior entre hoje no salão e hoje em UTC); corrigir o dia apaga a hora incoerente. Testes: 3 em `test_auditoria_regressao.py` |
| QA-10 | Edição de cliente aceitava nascimento em 2099 ou 1800 | P2 | API/Dados | Validador só no schema de criação | Faixa etária errada e regra de responsável legal sem sentido | Mesmo validador na edição. Teste: `test_edicao_do_cliente_valida_o_nascimento` |
| QA-11 | Atendimento não podia ser corrigido nem excluído pelo aplicativo | P2 | App/API | Funcionalidade incompleta: a API tinha `PATCH` parcial e o app nenhuma tela | Registro errado ficava para sempre no histórico | Tela "Corrigir atendimento" (serviço, dia e hora, duração, notas, simulação); `PATCH` aceita `realizadoEm` e `duracaoMin`; `DELETE` só para avulso. Testes: 2 no servidor, `e2e/auditoria.mjs` (8) |
| QA-12 | Revogar consentimento de quem aceitou menor e já fez 18 anos era recusado | P2 | App/LGPD | O app reenviava o responsável do aceite antigo | Cliente não conseguia retirar o consentimento | Responsável só vai junto se o cliente ainda é menor. Teste: `test_quem_aceitou_menor_e_fez_18_revoga_sem_responsavel` (contrato) e `e2e/fluxo-completo.mjs` (revogação) |
| QA-13 | Busca de clientes sensível a acento ("julia" não achava "Júlia") | P3 | App/UX | Comparação de texto sem normalização | Cliente "sumido" na busca do celular | `normalizarBusca` nas três buscas. Testes: `testes/busca.mjs`, `e2e/auditoria.mjs` (9) |
| QA-14 | Busca no servidor tratava `%` e `_` como curinga | P3 | API | `ILIKE` sem escape | Buscar "_" devolvia a carteira toda | Escape dos curingas. Teste: `test_busca_trata_curingas_como_texto` |
| QA-15 | Consultas N+1: foto por cliente na lista; uma consulta por cliente e duas por simulação na lista de simulações | P3 | API/Desempenho | Carregamento preguiçoso em laço | Tempo cresce com a carteira | Consultas em lote e `selectinload`. Teste: `test_lista_de_clientes_e_simulacoes_sem_consulta_por_linha`; medição na seção 6 |
| QA-16 | Envio de imagem lido inteiro para a memória antes de medir | P3 | API/Segurança | Limite de corpo só olha `Content-Length` (envio em partes passa) | Conta autenticada podia ocupar memória do servidor | `ler_envio` lê até 1 byte além do limite. Teste: `test_envio_em_partes_nao_e_lido_alem_do_limite` |
| QA-17 | Erros HTTP genéricos em inglês na tela ("Method Not Allowed") | P3 | API/UX | Tratador repassava o texto padrão do Starlette | Mensagem incompreensível | Mensagens em português. Teste: `test_erros_http_genericos_saem_em_portugues` |
| QA-18 | Duas marcações simultâneas de "preferida" no mesmo cliente → erro 500 | P3 | API | Troca sem trava contra índice único | Erro 500 raro | Trava do cliente. (Sem teste dedicado: mesmo padrão de QA-04) |
| QA-19 | Forma de atuação vazia aceita | P3 | API | Sem tamanho mínimo | Perfil com campo vazio | `min_length=2`. Teste: `test_atuacao_vazia_e_recusada` |
| QA-20 | Atendimentos do mesmo dia em ordem arbitrária na API | P3 | API | Ordenação só pelo dia | Ordem instável | Desempate por hora real e gravação. Teste: `test_historico_do_mesmo_dia_vem_do_mais_recente` |
| QA-21 | "Tentar de novo" alinhado à esquerda na tela "Sem conexão" | P3 | App/Visual | Botão estreito se alinha à esquerda por padrão | Tela desalinhada | `alignSelf: 'center'` (conferido na captura `e2e/telas-auditoria/04-renovacao-sem-rede.png`) |
| QA-22 | README da raiz era o texto de handoff da ferramenta de design | P3 | Docs | Nunca substituído | Instruções erradas para quem chega | README real do projeto |
| QA-23 | `entrypoint.sh` dizia "seed já aplicado" para qualquer falha do seed | P3 | Infra | Mensagem genérica | Diagnóstico enganoso | Seed pulado explicitamente em produção |

Achados avaliados e mantidos de propósito:

- **Espaços nas pontas da senha são removidos** (cadastro e login, de forma consistente).
  Mudar agora trancaria fora quem cadastrou senha com espaço. Registrado como pendência
  P3 (seção 10).
- **A busca no servidor (`?busca=`) continua sensível a acento**: o aplicativo filtra
  localmente; resolver no banco exige a extensão `unaccent`.

---

## 4. Alterações realizadas

### Frontend e design (melhorias visuais)
- `src/components/EstadoVazio.tsx`: estado vazio compacto com altura pelo conteúdo (QA-08).
- `app/index.tsx`: botão "Tentar de novo" centralizado (QA-21).
- `src/components/ItemHistorico.tsx`: ação "Corrigir" em cada atendimento, com alvo de
  toque de 44 px (QA-11).

### UX e acessibilidade (mudanças funcionais)
- `app/cliente/editar.tsx`: erro do servidor no campo certo; nascimento futuro ou anterior
  a 1900 apontado antes de enviar (QA-01).
- `app/atendimento/editar/[id].tsx` (nova): corrigir atendimento; excluir o avulso com
  confirmação destrutiva; aviso explicando por que o da agenda não se exclui (QA-11).
- `src/components/FormularioAtendimento.tsx`: modo de correção (só protege a saída se algo
  mudou) e espaço para ação extra.
- `app/(tabs)/clientes.tsx`, `app/simulacao/cliente.tsx`, `src/utils/busca.ts` (novo):
  busca sem acento (QA-13).
- `app/cliente/[id].tsx`: revogação de quem já é adulto (QA-12).

### Sessão no aplicativo (mudanças funcionais)
- `src/services/api/cliente.ts`: renovação com três resultados e tempo limite (QA-06).
- `src/services/api/sessao.ts`: `aoEncerrarSessao` (QA-07).
- `src/data/store.tsx`: assina o fim de sessão; ações `corrigirAtendimento` e
  `excluirAtendimento`.
- `app/_layout.tsx`: `GuardaDeSessao` (QA-07).
- `src/utils/datas.ts`: `isoDeDataCurta` devolve dia do calendário (QA-01).

### Backend e regras de negócio
- `app/services/agendamentos.py`: `_travar_agenda`, `_reler_com_trava`, `hoje_no_salao`,
  `validar_dia_nao_futuro` (QA-03, QA-04, QA-09).
- `app/services/atendimentos.py`, `app/schemas/atendimento.py`, `app/api/v1/atendimentos.py`:
  validação de datas, correção de `realizadoEm`/`duracaoMin`, `DELETE` do avulso (QA-09, QA-11).
- `app/schemas/cliente.py`: validação de nascimento na edição (QA-10).
- `app/schemas/auth.py`: atuação com tamanho mínimo (QA-19).
- `app/main.py`: mensagens HTTP em português (QA-17).

### Banco de dados
- Nenhuma migration nova foi necessária: as correções são de consulta, trava e validação.
  Ver seção 7.

### Segurança
- `app/core/config.py`, `app/seed.py`, `entrypoint.sh`, `docker-compose.yml`: produção sem
  demonstração (QA-02, QA-23).
- `app/services/validacao_foto.py` e as três rotas de envio: leitura limitada (QA-16).
- `app/services/imagens.py`, `clientes.py`, `auth.py`, `simulacao.py`: ordem de travas
  e limpeza de arquivo órfão (QA-05).

### Desempenho
- `app/repositories/consultas.py`: `fotos_dos_clientes`, `foto_do_cliente`,
  `simulacoes_do_usuario`, `selectinload` das imagens; desempate na ordem do histórico
  (QA-15, QA-20).
- `app/services/clientes.py`, `app/api/v1/simulacoes.py`: usam as consultas em lote.

### Testes automatizados
- `backend/tests/test_auditoria_regressao.py` (novo): 19 funções, 20 casos.
- `backend/tests/test_idor_completo.py`: a nova rota `DELETE /atendimentos/{id}` entrou na
  varredura entre contas (a guarda do próprio teste acusou a rota nova, como deveria).
- `backend/tests/test_seguranca_aplicacao.py`: os testes de produção passam
  `MODO_DEMO=false`, coerente com a nova regra.
- `espelho/testes/datas.mjs`, `busca.mjs` (novos) e `resolver-ts.mjs`/`carregar-ts.mjs`
  (gancho que permite ao Node importar módulos TypeScript sem extensão).
- `espelho/e2e/auditoria.mjs` (novo): 27 verificações em navegador.

### Infraestrutura e documentação
- `qa.sh`: novos testes de unidade e a bateria `auditoria.mjs`.
- `README.md` (reescrito), `backend/README.md`, `espelho/e2e/README.md`,
  `docs/DECISOES_TECNICAS.md` (novo), `docs/evidencias-qa/` (capturas antes e depois),
  `.gitignore` (todas as pastas `e2e/telas-*` fora do versionamento, como o histórico do
  projeto já pretendia).

---

## 5. Bateria de testes executada

Ambiente: API em `localhost:8000` (código final), `expo start --web` em `localhost:8081`,
Chromium headless com fuso `America/Sao_Paulo`, banco de testes `espelho_test` isolado do
banco de desenvolvimento.

### 5.1 Verificações exploratórias (manuais, por script) que originaram os achados

| ID | Categoria | Cenário | Resultado esperado | Resultado obtido | Status | Evidência |
| -- | --- | --- | --- | --- | --- | --- |
| M-01 | API | `POST /atendimentos` com `dataServico` 2099 | 422 | Antes: 201. Depois: 422 | PASSOU | `sonda.py`, item 1 |
| M-02 | API | `PATCH /clientes` com nascimento 2099 e 1800 | 422 | Antes: 200 e 200. Depois: 422 e 422 | PASSOU | `sonda.py`, item 2 |
| M-03 | Concorrência | Duas sessões criam o mesmo horário antes de qualquer commit | 1 criado, 1 recusado | Antes: 2 criados. Depois: 1 criado, 1 recusado | PASSOU | `corrida.py` |
| M-04 | Concorrência | Sessão tardia conclui agendamento já concluído | Mesmo atendimento | Antes: `IntegrityError` (500). Depois: mesmo atendimento | PASSOU | `corrida.py` |
| M-05 | API | Buscar `_` e `%` | 0 clientes | Antes: 2 e 2. Depois: 0 e 0 | PASSOU | `sonda.py`, item 5 |
| M-06 | Dados | Corrigir o dia de atendimento com hora | Hora apagada | Antes: hora de outro dia mantida. Depois: `null` | PASSOU | `sonda.py`, item 6 |
| M-07 | API | `PATCH /usuarios/me` com atuação vazia | 422 | Antes: 200. Depois: 422 | PASSOU | `sonda.py`, item 7 |
| M-08 | API | Cliente com `dataNascimento` no formato que o app enviava | Salvar | 422 "Datetimes provided to dates should have zero time" | PASSOU (após correção do app, que passou a enviar `aaaa-mm-dd`) | curl na API; `e2e/auditoria.mjs` (3) |
| M-09 | Visual | Início de conta nova, 390 px | Botão visível | Antes: coberto pelo aviso. Depois: inteiro | PASSOU | `docs/evidencias-qa/antes-inicio-conta-nova.png`, `depois-inicio-conta-nova.png` |
| M-10 | Visual | `/agenda` sem sessão | Ir para a abertura | Antes: agenda vazia aberta. Depois: abertura | PASSOU | `docs/evidencias-qa/antes-agenda-sem-sessao.png` |
| M-11 | Visual | Revisão das 46 capturas de `visual-contraste` e das telas novas | Sem cortes, sobreposições ou desalinhamentos | Encontrado e corrigido QA-21; demais telas sem problema | PASSOU | `e2e/telas-visual/`, `e2e/telas-auditoria/` |
| M-12 | Senha | Cadastro com espaços nas pontas e login sem eles | Decisão de produto | Entra (espaços são removidos nos dois lados) | PASSOU (comportamento mantido; ver seção 10) | `sonda.py`, item 8 |

### 5.2 Testes automatizados do servidor (pytest, PostgreSQL real)

| ID | Categoria | Cenário | Resultado esperado | Resultado obtido | Status | Evidência |
| -- | --- | --- | --- | --- | --- | --- |
| A-01 | Regressão | Suíte original (417 testes) | Todos passam | 417 passam | PASSOU | linha de base e execução final |
| A-02 | Concorrência | `test_conclusao_simultanea_devolve_o_mesmo_atendimento` | Idempotente | idem | PASSOU | falha no código original |
| A-03 | Concorrência | `test_confirmar_nao_desfaz_um_cancelamento_simultaneo` | 422 `transicao_invalida` | idem | PASSOU | falha no original |
| A-04 | Concorrência | `test_criacoes_simultaneas_nao_ocupam_o_mesmo_horario` | 2ª espera e recebe `horario_ocupado` | idem | PASSOU | falha no original |
| A-05 | Dados | `test_atendimento_avulso_no_futuro_e_recusado` | 422 | idem | PASSOU | falha no original |
| A-06 | Dados | `test_corrigir_a_data_do_atendimento_para_o_futuro_e_recusado` | 422 | idem | PASSOU | falha no original |
| A-07 | Dados | `test_corrigir_o_dia_descarta_o_horario_de_outro_dia` | `realizadoEm` nulo | idem | PASSOU | falha no original |
| A-08 | Validação | `test_edicao_do_cliente_valida_o_nascimento` (2 casos) | 422 | idem | PASSOU | falha no original |
| A-09 | API | `test_historico_do_mesmo_dia_vem_do_mais_recente` | Ordem por hora | idem | PASSOU | falha no original |
| A-10 | Segurança | `test_busca_trata_curingas_como_texto` | Curinga literal | idem | PASSOU | falha no original |
| A-11 | Validação | `test_atuacao_vazia_e_recusada` | 422 | idem | PASSOU | falha no original |
| A-12 | Segurança | `test_producao_nao_sobe_com_modo_demonstracao` | Erro de configuração | idem | PASSOU | falha no original |
| A-13 | Segurança | `test_seed_se_recusa_em_producao` | Código 2, nenhuma conta | idem | PASSOU | falha no original |
| A-14 | LGPD | `test_apagar_imagens_durante_a_geracao_nao_deixa_arquivo_orfao` | 0 arquivos, 0 linhas | idem | PASSOU | no original: erro 500 na tarefa |
| A-15 | Desempenho | `test_lista_de_clientes_e_simulacoes_sem_consulta_por_linha` | Consultas constantes | idem | PASSOU | falha no original |
| A-16 | Funcional | `test_corrigir_dia_hora_e_duracao_do_atendimento` | Dia no fuso do salão; `null` apaga duração; futuro 422 | idem | PASSOU | funcionalidade nova |
| A-17 | Funcional | `test_exclui_atendimento_avulso_mas_nao_o_da_agenda` | 204 / 422 | idem | PASSOU | funcionalidade nova |
| A-18 | UX/API | `test_erros_http_genericos_saem_em_portugues` | Mensagens em português | idem | PASSOU | |
| A-19 | Segurança | `test_envio_em_partes_nao_e_lido_alem_do_limite` | Lê 1.001 de 50.000 bytes | idem | PASSOU | |
| A-20 | LGPD | `test_quem_aceitou_menor_e_fez_18_revoga_sem_responsavel` | 201 revogado | idem | PASSOU | contrato do app |
| A-21 | IDOR | Varredura entre contas com `DELETE /atendimentos/{id}` (23 rotas) | 404 para a outra conta | idem | PASSOU | |

Os testes A-02 a A-15 foram rodados contra uma cópia do código original do ZIP: os 15
casos falharam (14 por asserção, A-14 por erro 500 na tarefa de geração). Os A-16 a A-20
cobrem código novo ou contratos novos e não foram rodados contra o original.

### 5.3 Testes de unidade do aplicativo

| ID | Categoria | Cenário | Resultado esperado | Resultado obtido | Status | Evidência |
| -- | --- | --- | --- | --- | --- | --- |
| U-01 | Unidade | `testes/duracao.mjs` (existente) | 34 casos | 34, 0 falhas | PASSOU | |
| U-02 | Unidade | `testes/inicio-agendamento.mjs` (existente) | 9 casos | 9, 0 falhas | PASSOU | |
| U-03 | Unidade | `testes/painel.mjs` (existente) | 11 casos | 11, 0 falhas | PASSOU | |
| U-04 | Unidade | `testes/datas.mjs` (novo), fusos de Brasília e Tóquio | 12 + 12 casos | 24, 0 falhas | PASSOU | falha com a função original |
| U-05 | Unidade | `testes/busca.mjs` (novo) | 9 casos | 9, 0 falhas | PASSOU | |
| U-06 | Tipos | `tsc --noEmit --noUnusedLocals` | 0 erros | 0 erros | PASSOU | |
| U-07 | Textos | `scripts/verificar_travessoes.py` | 0 ocorrências | 0 | PASSOU | |

### 5.4 Baterias de navegador (Chromium, E2E, responsividade, acessibilidade)

Linha de base (código do ZIP): as 8 baterias existentes passaram sem falhas. Final (código
corrigido), com a carga de demonstração recriada antes de cada uma:

| ID | Categoria | Cenário | Resultado esperado | Resultado obtido | Status | Evidência |
| -- | --- | --- | --- | --- | --- | --- |
| E-01 | E2E | `fluxo-completo.mjs` (cadastro até revogação) | 0 falhas | 26 ok, 0 falhas, 0 erros de console | PASSOU | rodado também após QA-12 |
| E-02 | Responsividade/acessibilidade | `qa-interface.mjs` (390/768/1280 px, teclado, alvos) | 0 falhas | 22 ok, 0 falhas | PASSOU | |
| E-03 | E2E | `mudancas-interface.mjs` | 0 falhas | 21 ok, 0 falhas | PASSOU | |
| E-04 | E2E | `agenda.mjs` | 0 falhas | 27 ok, 0 falhas | PASSOU | |
| E-05 | E2E | `atendimentos.mjs` | 0 falhas | 49 ok, 0 falhas | PASSOU | |
| E-06 | E2E | `painel-e-comparacao.mjs` | 0 falhas | 18 ok, 0 falhas | PASSOU | expectativa do painel atualizada na seção 13 |
| E-07 | E2E | `fotos-e-camera.mjs` (câmera falsa) | 0 falhas | 25 ok, 0 falhas | PASSOU | |
| E-08 | Acessibilidade/visual | `visual-contraste.mjs` (23 telas × 2 larguras) | 0 contraste baixo, 0 rolagem horizontal | 46 telas ok | PASSOU | |
| E-09 | Regressão | `auditoria.mjs` (novo) | 0 falhas | 29 ok, 0 falhas | PASSOU | no app original: 4 ok, 14 falhas (versão de 18 verificações); 27 na primeira rodada, 29 com a seção 13 |
| E-10 | E2E | `google.mjs` (Entrar com Google sem conta real) | 12 verificações | não executada | BLOQUEADO | exige `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`/`GOOGLE_CLIENT_IDS` |

### 5.5 Build, infraestrutura, segurança e desempenho

| ID | Categoria | Cenário | Resultado esperado | Resultado obtido | Status | Evidência |
| -- | --- | --- | --- | --- | --- | --- |
| I-01 | Build | `npx expo export --platform web` | Concluir | Concluído; bundle principal 1,6 MB | PASSOU | |
| I-02 | Banco | Migrations da base ao topo e de volta (a cada execução da suíte) | Sem erro | Sem erro | PASSOU | `conftest.py` |
| I-03 | Saúde | `GET /api/v1/saude` | `ok: true`, banco atualizado | idem | PASSOU | |
| I-04 | Docker | `docker build` da API | Imagem criada | Contêiner sem acesso ao repositório Debian; com rede do host, Docker Hub respondeu 429 | BLOQUEADO | seção 10 |
| I-05 | Docker | `docker compose up` | API pronta | não executado (depende de I-04; portas 5432/8000 em uso no ambiente) | BLOQUEADO | |
| S-01 | Dependências | `pip-audit -r requirements.txt` | 0 vulnerabilidades | 0 | PASSOU | |
| S-02 | Dependências | `npm audit --omit=dev` | 0 | 12 avisos (6 altos) em ferramentas do Expo, os mesmos da etapa anterior | FALHOU | seção 8 |
| P-01 | Desempenho | Consultas e tempo de `/clientes` e `/simulacoes` com 30 clientes | Constante | ver seção 6 | PASSOU | `medir_consultas.py` |
| X-01 | Integração | Provedor de IA real (Replicate) | Gerar imagem | não executado (sem credencial; custo) | BLOQUEADO | coberto por servidor de mentira na suíte existente |
| X-02 | Dispositivo | Android/iOS físico | Fluxos principais | não executado (sem aparelho) | BLOQUEADO | |

Comandos usados:

```bash
cd backend && .venv/bin/python -m pytest --cov=app        # 439 passed, cobertura 95%
cd espelho && npx tsc --noEmit --noUnusedLocals             # 0 erros
node --experimental-strip-types --no-warnings testes/duracao.mjs   # e os demais testes/*.mjs
CHROMIUM_PATH=... node e2e/<bateria>.mjs                    # cada bateria, após app.seed --reset
npx expo export --platform web                              # build de produção
backend/.venv/bin/pip-audit -r backend/requirements.txt ; npm audit --omit=dev
./qa.sh                                                     # tudo acima, exceto navegador
```

---

## 6. Comparação antes e depois

| Indicador | Antes (ZIP) | Depois | Como foi medido |
| --- | --- | --- | --- |
| Testes do servidor | 417 passam | 439 passam | pytest |
| Cobertura do servidor | 94% | 95% | pytest-cov |
| Regressões novas do servidor contra o código original | — | 15 de 15 falham no original | cópia do ZIP |
| Bateria `auditoria.mjs` contra o app original | 4 ok, 14 falhas | 29 ok, 0 falhas | mesma bateria, app original na porta 8082 |
| Baterias de navegador existentes | 8 sem falhas | 8 sem falhas | regressão |
| Consultas SQL por `GET /clientes` (30 clientes com foto) | 34 | 5 | contador de `before_cursor_execute` |
| Consultas SQL por `GET /simulacoes` (30 simulações) | 32 | 2 | idem |
| Tempo médio de `GET /clientes` (30 clientes, 10 requisições) | 23,3 ms | 9,1 ms | TestClient, mesma máquina |
| Tempo médio de `GET /simulacoes` | 18,2 ms | 6,5 ms | idem |
| Cliente com data de nascimento pelo app | sempre falhava | salva | E2E |

Os tempos são de um único ambiente local, com banco na mesma máquina; servem para comparar
as duas versões, não como previsão de produção. O ganho que generaliza é o número de
consultas, que antes crescia com a carteira e agora é constante.

---

## 7. Banco de dados e integridade

- **Esquema:** nenhuma alteração; nenhuma migration criada ou modificada. As 7 migrations
  existentes continuam reversíveis e são exercitadas (base → topo) a cada execução da
  suíte.
- **Travas:** agenda (linha do usuário na criação/remarcação; linha do agendamento,
  relida, em toda mudança de status), cliente (exclusão de imagens, de cliente e de conta,
  e gravação do resultado da simulação), cliente (preferida). Ordem documentada em
  `docs/DECISOES_TECNICAS.md`.
- **Consultas:** em lote para fotos e simulações; `selectinload` das imagens; desempate
  determinístico no histórico; escape de curingas na busca.
- **Integridade de dados:** atendimento sem data futura; dia e hora coerentes; nascimento
  plausível também na edição; atendimento da agenda não pode ser excluído (o agendamento
  concluído continuaria sem o serviço).
- **Estratégia de teste:** banco `espelho_test` próprio, recriado pelas migrations;
  tabelas truncadas entre testes; os testes de concorrência usam duas sessões e transações
  reais; o banco de desenvolvimento (`espelho`) só foi alterado pelo seed de demonstração.
- **Persistência validada:** cada correção do app foi conferida na API depois da ação na
  tela (cliente salvo com a data digitada, correção e exclusão de atendimento).
- **Riscos:** a garantia contra horários sobrepostos é da aplicação (trava + consulta), não
  uma restrição do banco; uma escrita direta no banco pode sobrepor. Uma restrição de
  exclusão (`EXCLUDE USING gist`) exigiria a extensão `btree_gist` e tratar duração
  opcional; não foi adotada.

---

## 8. Segurança

**Verificado nesta auditoria:** controle de acesso entre contas (varredura de 23 rotas com
identificador, mais as de foto e imagem), proteção de produção (demonstração e seed),
leitura de envios, curingas de busca, mensagens de erro (sem detalhe interno; agora em
português), segredos no código (nenhum; `.env` fora do Git), dependências (pip-audit sem
vulnerabilidades), cabeçalhos de segurança e CORS (testes existentes passando), validação
de imagem e bomba de descompressão (testes existentes), fim de sessão no aplicativo.

**Corrigido:** QA-02, QA-05, QA-07, QA-14, QA-16 (seção 3).

**Riscos residuais:**

- Tokens JWT não são revogáveis no servidor: "Sair" apaga os tokens do aparelho, mas um
  token de renovação copiado continua válido por até 30 dias. Não há troca de senha nem
  recuperação por e-mail.
- O freio de tentativas de login é em memória e por `request.client.host`. Atrás de proxy
  reverso, todos os usuários compartilham o IP do proxy; é preciso rodar o uvicorn com
  `--proxy-headers --forwarded-allow-ips=<proxy>`, ou mover o freio para o proxy.
- `npm audit`: 12 avisos em `@expo/cli`, `node-forge`, `zod`, `xcode`, `uuid` e outros.
  São ferramentas de desenvolvimento e build do Expo; a correção sugerida rebaixa o Expo
  (quebra). Revisar a cada atualização do SDK.
- Exclusão de conta criada pelo Google confere o token sem `nonce`: um ID token capturado
  serviria por até 1 hora para confirmar a exclusão (o atacante ainda precisaria de um
  token de acesso válido da mesma conta).
- `POST /simulacoes/enquadramento` roda detecção de rosto a cada quadro, sem limite de
  frequência por conta (exige sessão e consentimento).

**Fora do escopo verificado:** login real com Google, provedor de IA real, S3 real,
configuração de HTTPS/proxy de produção, aplicativo nativo instalado.

---

## 9. Resultado final dos testes

Contagem por caso de teste executado, sem repetir o mesmo teste: cada função ou
parametrização do pytest conta uma vez; cada caso dos testes de unidade conta uma vez (o
teste de datas conta duas vezes porque roda em dois fusos, que são cenários distintos);
cada verificação `[ok]`/`[FALHA]` das baterias de navegador conta uma vez, e na bateria de
contraste cada tela em cada largura conta uma vez. Verificações estáticas e de build são
contadas à parte.

| Grupo | Planejados | Executados | Aprovados | Falharam | Bloqueados | Não executados |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Servidor (pytest) | 439 | 439 | 439 | 0 | 0 | 0 |
| Unidade do aplicativo | 88 | 88 | 88 | 0 | 0 | 0 |
| Navegador (9 baterias) | 263 | 263 | 263 | 0 | 0 | 0 |
| Navegador: `google.mjs` | 12 | 0 | 0 | 0 | 12 | 0 |
| **Automatizados, total** | **802** | **790** | **790** | **0** | **12** | **0** |
| Estáticos e build (tipos, travessões, build web, pip-audit, npm audit) | 5 | 5 | 4 | 1 (npm audit) | 0 | 0 |
| Infra e integrações externas (I-04, I-05, X-01, X-02) | 4 | 0 | 0 | 0 | 4 | 0 |
| Verificações exploratórias (5.1) | 12 | 12 | 12 | 0 | 0 | 0 |

`./qa.sh` (servidor com cobertura, tipos, testes de unidade e travessões) foi rodado de
ponta a ponta ao final.

---

## 10. Problemas pendentes

| Descrição | Sev. | Por que não foi resolvido | Impacto | Próxima ação |
| --- | --- | --- | --- | --- |
| Login com Google real e bateria `google.mjs` | P2 | Depende de credenciais OAuth do dono do projeto | Funcionalidade implementada e testada com tokens forjados, não com conta real | Seguir `docs/GUIA_LOGIN_GOOGLE.md`, preencher as variáveis e rodar `e2e/google.mjs` |
| Build Docker e `docker compose up` | P2 | O contêiner de build não alcançava `deb.debian.org`; com rede do host, o Docker Hub respondeu 429 | Imagem não verificada neste ambiente. A imagem base atual (Debian trixie) renomeou `libglib2.0-0` para `libglib2.0-0t64`; o apt resolve o nome antigo para o novo (conferido no Ubuntu 24.04 do ambiente, que fez a mesma transição), mas sem o build isso é evidência indireta | Rodar `docker compose up --build` com rede e conferir `GET /api/v1/saude` |
| Revogação de tokens no servidor; troca e recuperação de senha | P2 | Mudança de modelo (lista de revogação ou versão de token por usuário) além do escopo seguro | Token roubado vale até expirar | Guardar `versao_token` no usuário e conferi-la no JWT; criar troca de senha |
| Freio de login atrás de proxy | P2 | Depende da topologia de produção | Freio compartilhado entre todos os usuários | `--proxy-headers` com `--forwarded-allow-ips`, ou limite no proxy |
| Avisos do `npm audit` (12) | P3 | Correção exige rebaixar o Expo | Ferramentas de build, não o pacote do app | Reavaliar na próxima versão do SDK |
| Provedor de IA real | P3 | Credencial e custo | Integração testada contra servidor de mentira | Configurar `AI_PROVIDER=replicate` e `AI_API_KEY` e gerar uma simulação |
| Aparelho físico Android/iOS | P2 | Sem aparelho no ambiente | Verificação visual só no navegador (390, 768, 820 e 1280 px). A correção do envio de fotos no celular (QA-24) foi verificada no conversor do Expo e no pacote Android gerado, não num aparelho | Enviar foto de cliente, foto do profissional e uma simulação pelo Expo Go (seção 13) |
| Espaços nas pontas da senha são removidos | P3 | Mudar trancaria fora quem cadastrou assim | Senha efetiva difere da digitada nas pontas | Se mudar, aceitar as duas formas no login por um período |
| Revogar de quem tinha aceite como adulto e teve a data corrigida para menor | P3 | O servidor exige o responsável e a tela de revogação não o pede | Recusa com mensagem clara; a revogação passa pela tela do termo | Pedir o responsável na revogação quando o cliente for menor |
| Busca no servidor sensível a acento | P3 | Exige a extensão `unaccent` | Nenhum hoje (o app filtra localmente) | Criar a extensão por migration, se a busca no servidor passar a ser usada |
| Listas de agenda e histórico sem paginação | P3 | Volume atual pequeno | Carga inicial cresce com os anos | Paginar por período |
| Lint (ESLint) não configurado | P3 | `expo lint` precisa baixar pacotes e alterar a configuração do projeto | Sem regras de estilo automáticas; a verificação de tipos com `--noUnusedLocals` cobre parte | Configurar o ESLint do Expo |
| Travessões nos termos já publicados | P3 | Versões imutáveis; trocar exige nova autorização de todos os clientes | Só pontuação | Aproveitar a próxima mudança de conteúdo dos termos |

---

## 11. Como executar o projeto

**Pré-requisitos:** Python 3.11+, Node 22+, PostgreSQL 16 (ou Docker), Chromium para as
baterias de navegador.

```bash
# Banco (uma vez)
createuser -P espelho          # senha: espelho (ou ajuste DATABASE_URL)
createdb -O espelho espelho
createdb -O espelho espelho_test

# API
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # JWT_SECRET com 32+ caracteres; AMBIENTE e MODO_DEMO
alembic upgrade head            # migrations
python -m app.seed              # dados de demonstração (recusado com AMBIENTE=producao)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Aplicativo
cd ../espelho
npm ci
npx expo start --web            # navegador; `npx expo start` para o celular

# Verificação
cd ..
./qa.sh                         # servidor, tipos, testes de unidade, travessões
./qa.sh --interface             # + 9 baterias de navegador (API e Expo no ar)
./qa.sh --tudo                  # + auditoria de dependências
```

Variáveis novas ou com regra nova: nenhuma variável nova. `MODO_DEMO=true` passou a ser
proibido com `AMBIENTE=producao` (a API não sobe). Defina `CHROMIUM_PATH` se o Chromium do
Playwright estiver fora do padrão.

**Para revisar e registrar o trabalho** (nada foi commitado):

```bash
git status
git diff                         # mudanças desta auditoria e da etapa anterior
git add -A && git commit
```

A área de trabalho contém, além desta auditoria, as alterações que já vinham sem commit
no ZIP (etapa descrita em `RELATORIO_FINAL_IMPLEMENTACAO.md`). Para separar as duas, a
lista de arquivos desta auditoria está na seção 4.

---

## 12. Avaliação final

**O que melhorou:** integridade da agenda sob concorrência, eliminação real de imagens
(LGPD) mesmo durante a geração, cadastro de cliente com data de nascimento (e, com ele, a
regra de menores), sessão resistente a rede instável e coerente quando acaba, primeira
experiência de uma conta nova, histórico corrigível, busca natural em português, proteção
contra configuração de produção perigosa, desempenho das listagens.

**Pontos fortes atuais:** regras de negócio no servidor (o app não é a última barreira),
consentimento imutável e versionado, isolamento entre contas testado rota a rota, testes
que exercitam banco real, migrations e navegador real, documentação extensa.

**Riscos que merecem atenção:** os da seção 10, em especial revogação de tokens, freio de
login atrás de proxy e a validação do build Docker e das integrações reais.

**Conclusão técnica:**

- **Funcional no ambiente testado:** sim. Todos os testes executados passam; as falhas
  encontradas foram corrigidas e cobertas por teste.
- **Apto para testes com usuários:** sim, em ambiente de demonstração ou piloto, com o
  provedor local ou com a credencial do provedor real configurada.
- **Apto para produção:** ainda não. Faltam validar o build Docker, o login com Google e o
  provedor de IA reais, tratar a revogação de tokens e configurar o freio de login para o
  proxy de produção. Nenhum desses itens é um defeito conhecido do código testado; são
  verificações e decisões que dependem do ambiente de produção.

O que não foi possível verificar está listado nas seções 5.5, 8 e 10, com o motivo.

---

## 13. Segunda rodada: correções relatadas no uso real

Depois da entrega, o uso do aplicativo no celular (Expo Go) apontou dois problemas. Os dois
foram reproduzidos, corrigidos e cobertos por teste; um terceiro, que apareceu no mesmo log,
também foi tratado.

### 13.1 Problemas

| ID | Problema | Sev. | Causa raiz | Solução |
| --- | --- | --- | --- | --- |
| QA-24 | No celular, enviar foto de cliente ou do profissional falhava antes de chegar ao servidor: `Unsupported FormDataPart implementation`. O mesmo valia para simulações e para a conferência da câmera | P1 | Desde o Expo SDK 57 o `fetch` do aparelho é o `expo/fetch`, que não aceita o formato antigo do React Native (`{ uri, name, type }`) no `FormData`. Na web funcionava porque lá a foto já ia como `Blob`, e por isso nenhuma bateria de navegador pegou | A foto local vai como `File` do `expo-file-system` (`src/services/api/arquivoLocal.ts`), a forma documentada pelo Expo; na web segue como `Blob` (`arquivoLocal.web.ts`). `expo-file-system` passou a ser dependência declarada do app, na mesma versão (57.0.7) que o Expo já instalava |
| QA-25 | O painel mostrava 3 "agendados" com 4 horários confirmados na agenda | P2 | `clientesAgendados` contava clientes distintos (um `Set` de `clienteId`): a mesma cliente com dois horários contava um. O rótulo "agendados" se lê como horários | `horariosAgendados` conta um por agendamento (pendente ou confirmado, de hoje em diante), como a agenda. Rótulo acessível: "N horários marcados, de hoje em diante" |
| QA-26 | Log `objeto ausente no storage` e imagem com 404 (quadro vazio na tela) | P2 | O `.env` usa `STORAGE_DIR=./dados/imagens`, resolvido a partir da pasta de onde a API é iniciada. Com o projeto extraído numa pasta nova e o mesmo banco, as linhas de `imagens` apontavam para arquivos que ficaram em `backend/dados` da pasta antiga | Caminho relativo agora é sempre a partir da pasta `backend`. O aplicativo mostra "Imagem indisponível" quando uma imagem não carrega, em vez de um quadro vazio |

**Ação sua para as imagens antigas:** copie a pasta `backend\dados` da pasta antiga do
projeto para `backend\dados` da pasta nova. As imagens geradas depois dessa correção
ficam sempre em `backend\dados`, de onde quer que a API seja iniciada.

### 13.2 Arquivos alterados

- App: `src/services/api/arquivoLocal.ts` e `arquivoLocal.web.ts` (novos),
  `src/services/api/index.ts` (`anexarImagem`), `src/utils/painel.ts`,
  `app/(tabs)/index.tsx`, `src/components/ImagemSimulada.tsx`, `package.json` e
  `package-lock.json` (`expo-file-system ~57.0.7`).
- Servidor: `app/core/config.py` (`STORAGE_DIR` relativo à pasta `backend`),
  `.env.example` (comentário).
- Testes: `testes/painel.mjs` (caso relatado: quatro confirmados, dois da mesma cliente),
  `e2e/painel-e-comparacao.mjs` (valor esperado por horário), `e2e/auditoria.mjs`
  (cenários 10 e 11), `tests/test_auditoria_regressao.py`
  (`test_storage_relativo_e_resolvido_a_partir_da_pasta_backend`).
- Documentação: `docs/DECISOES_TECNICAS.md` (seções 6 e 7), `backend/README.md`,
  `espelho/e2e/README.md`.

### 13.3 Testes executados

| ID | Categoria | Cenário | Resultado esperado | Resultado obtido | Status | Evidência |
| -- | --- | --- | --- | --- | --- | --- |
| R2-01 | Envio (aparelho) | Conversor de `FormData` do `expo/fetch` com o formato antigo `{ uri }` | Recusar (reproduzir o erro relatado) | `Unsupported FormDataPart implementation` | PASSOU | código do Expo 57 rodado em Node |
| R2-02 | Envio (aparelho) | O mesmo conversor com um objeto na interface do `File` do `expo-file-system` (`name`, `type`, `bytes()`) | Aceitar, com nome do arquivo e bytes da imagem no corpo | Aceito; `filename="foto.jpg"` e assinatura JPEG no corpo | PASSOU | idem |
| R2-03 | Build | `npx expo export --platform android` | Pacote gerado com o `arquivoLocal` nativo | Pacote Hermes de 3,5 MB; contém o `ExpoFileSystem` e não contém o texto da versão web | PASSOU | |
| R2-04 | Envio (web) | `e2e/fotos-e-camera.mjs` e `e2e/fluxo-completo.mjs` com o novo `anexarImagem` | 0 falhas | 25 e 26 ok, 0 falhas | PASSOU | regressão |
| R2-05 | Unidade | `testes/painel.mjs`: quatro confirmados, dois da mesma cliente | 4 | 4 (12 verificações, 0 falhas) | PASSOU | com a função antiga, 3 |
| R2-06 | E2E | `e2e/auditoria.mjs` (10): três horários, dois da mesma cliente | Painel mostra 3 | 3 | PASSOU | `e2e/telas-auditoria/10-painel-horarios.png` |
| R2-07 | E2E | `e2e/painel-e-comparacao.mjs` com a contagem por horário | 0 falhas | 18 ok, 0 falhas | PASSOU | |
| R2-08 | Servidor | `STORAGE_DIR=./dados/imagens` com a API iniciada de outra pasta | Resolve para `backend/dados/imagens` | idem | PASSOU | teste novo |
| R2-09 | E2E | `e2e/auditoria.mjs` (11): imagem responde 404 | "Imagem indisponível" na miniatura | idem | PASSOU | `e2e/telas-auditoria/11-imagem-indisponivel.png` |
| R2-10 | Regressão | Suíte do servidor, tipos, testes de unidade, 9 baterias de navegador | 0 falhas | 439 / 0 erros / 88 / 263, todos aprovados | PASSOU | totais da seção 9 já atualizados |
| R2-11 | Aparelho | Enviar foto e simulação pelo Expo Go num celular | Sem erro | não executado neste ambiente | BLOQUEADO | sem aparelho; ver seção 10 |

**O que confirmar no seu celular:** depois de `npm ci` (que instala o `expo-file-system`)
e `npx expo start -c`, envie uma foto de cliente, uma foto em "Meus dados" e uma simulação.
Se usar build de desenvolvimento em vez do Expo Go, gere o build de novo: o módulo nativo do
`expo-file-system` precisa estar nele.
