# Relatório final de implementação

Revisão, evolução e finalização do aplicativo do TCC (Sistemas de Informação, Faculdade
Antônio Meneghetti). Data da execução: 23 e 24 de outubro de 2026.

Nenhum commit foi feito, como pedido. Todo o trabalho está na área de trabalho do Git,
sobre o commit `38c01c6`, que foi preservado. O último item deste relatório explica como
revisar e registrar as mudanças.

---

## 13.1 Resumo executivo

O aplicativo passou a se chamar **Salão em Dia**. A agenda deixou de ser só um calendário
e virou o centro do trabalho do dia: cada horário pode ser confirmado, editado, cancelado
(sem apagar o registro) ou concluído, e a conclusão grava o atendimento no histórico do
cliente na mesma operação, ligado ao agendamento de origem e, se houver, à simulação usada.
Datas e horários no passado são recusados no aplicativo e no servidor. O login com Google
foi implementado de ponta a ponta, com verificação do token no servidor e sem vínculo
automático de contas por e-mail; falta apenas o dono do projeto criar as credenciais no
Google Cloud. A interface ganhou base escura com folhas claras de conteúdo, uma tela de
abertura que explica o aplicativo, e todos os textos visíveis foram revisados.

Números da verificação final (todos executados, nenhum declarado sem rodar):

| Verificação | Resultado |
|---|---|
| Testes do servidor (pytest, PostgreSQL real) | **375 aprovados**, 0 falhas, cobertura 94% |
| Verificação de tipos do aplicativo (`tsc --noEmit --noUnusedLocals`) | 0 erros |
| Build web de produção (`expo export --platform web`) | concluído |
| Baterias de navegador (6 roteiros) | 108 verificações aprovadas, 0 falhas |
| Contraste WCAG AA em 23 telas, celular e tablet (46 capturas) | 0 textos abaixo do mínimo |
| Rolagem horizontal indevida (390px e 820px) | 0 telas |
| Travessões e meias-riscas na interface e nas mensagens do servidor | 0 ocorrências (exceção documentada: textos dos termos já publicados) |
| Migrations: ida, volta e ida de novo, a partir do zero | executado a cada rodada de testes |
| Auditoria de dependências Python (`pip-audit`) | nenhuma vulnerabilidade conhecida |

## 13.2 Diagnóstico inicial

Problemas encontrados antes de qualquer mudança:

1. **Data no passado**: nada impedia criar ou mover um agendamento para ontem, nem no
   aplicativo nem na API.
2. **Concluir não gerava atendimento**: marcar "concluído" só trocava o status. O histórico
   dependia de alguém lembrar de registrar o atendimento à parte, sem ligação com o
   agendamento, e nada impedia registrá-lo duas vezes.
3. **Transições**: um agendamento pendente não podia ser concluído (só depois de
   confirmado), o que não corresponde à rotina de quem atende sem confirmar antes.
4. **Conflito de horários**: dois agendamentos podiam ocupar o mesmo horário.
5. **Edição limitada**: não havia tela de edição; a API não permitia trocar o cliente.
6. **Fuso**: horários sem fuso eram aceitos, e o servidor não sabia em que dia, no
   horário do Brasil, um atendimento tinha acontecido.
7. **Cancelados**: continuavam marcando o calendário e entrando nas contagens; o
   cancelamento não registrava quando nem por quê.
8. **Menu da agenda**: oferecia "Nova simulação" e "Registrar atendimento" (sem ligação com
   o agendamento) e não oferecia editar nem cancelar.
9. **Exclusão**: era possível apagar um agendamento já concluído pela API.
10. **Datas sem hora exibidas um dia antes**: `new Date("2026-10-19")` é meia-noite em
    Greenwich, que no Brasil ainda é dia 18. O histórico mostrava a data errada e a edição
    de cliente gravava a data de nascimento com um dia a menos.
11. **Atendimento avulso registrado no dia seguinte** quando feito depois das 21h, pelo
    mesmo motivo (data tirada em UTC).
12. **Botões sem função**: "Recuperar senha" (só avisava que não existia), três itens
    "em breve" no Perfil, o interruptor de lembrete (o envio nunca foi implementado) e os
    atalhos de demonstração visíveis mesmo fora do modo de demonstração.
13. **Dados fictícios na interface**: nome e e-mail inventados apareciam no Perfil e no
    Início enquanto a conta carregava.
14. **Texto incorreto**: a confirmação de saída dizia que os dados "continuam salvos neste
    aparelho"; eles ficam na conta, no servidor.
15. **Dados de demonstração em UTC**: os horários do seed apareciam 3 horas antes no Brasil.

## 13.3 Funcionalidades implementadas

**Agenda**
- Menu de cada horário conforme a situação: pendente (confirmar, atendimento concluído,
  editar, abrir perfil, cancelar); confirmado (as mesmas, sem confirmar); concluído e
  cancelado (só abrir o perfil). "Nova simulação" e "Registrar atendimento" saíram do menu.
- **Editar agendamento**: cliente, data, horário, serviço, duração e observações, com os
  dados atuais carregados, validação, proteção contra sair sem salvar e atualização
  imediata da agenda. A situação não se edita no formulário: tem ações próprias.
- **Confirmar**: só para pendentes; repetir é inofensivo.
- **Cancelar**: diálogo de confirmação com motivo opcional (até 300 caracteres). O registro
  continua na agenda, riscado, com o motivo; o horário fica livre.
- **Atendimento concluído**: tela própria com o horário marcado, quando o atendimento de
  fato aconteceu (pode diferir do marcado; não pode estar no futuro), serviço realizado,
  observações e simulação usada (opcional). Concluir duas vezes não duplica nada.
- Horários que se sobrepõem são recusados com mensagem clara; cancelados e concluídos não
  ocupam horário.
- Calendário e contagens ignoram cancelados; o próximo atendimento do Início ignora
  concluídos e cancelados.

**Datas passadas**: recusadas na criação e na edição, no aplicativo (dia anterior ao de hoje
e horário de hoje que já passou) e no servidor (chamada direta à API). A comparação é por
instante, com fuso, e tolera 5 minutos de diferença de relógio. Na edição, a regra só vale
se a data mudar: anotar algo num compromisso de hoje cedo continua possível.

**Histórico do cliente**: cada atendimento mostra a data (e a hora, quando registrada) em
que aconteceu, o horário que estava marcado quando veio da agenda, as observações e a
simulação usada, que abre a imagem. Registros antigos sem essas informações aparecem sem
elas, sem valor inventado.

**Entrar com Google**: no login, no cadastro, no Perfil (conectar e desconectar) e na
exclusão de conta sem senha. Detalhes em 13.7.

**Perfil**: "Meus dados" (nome e forma de atuação) substitui os itens "em breve".

**Tela de abertura**: nome, para quem é, as cinco atividades (clientes, agenda,
atendimentos, histórico, simulações) e três passos para começar.

## 13.4 Alterações no frontend

- **Tema**: novo token `cores.base` (#17130F) para a base escura e `cores.baseBorda`; a cor
  de conteúdo (`cores.fundo`) continua clara. Cores próprias para "concluído" (azul
  petróleo), distintas do verde de "confirmado". A aparência de cada situação (cor, ícone e
  texto) fica em `src/theme/status.ts`, usada na agenda e no Início.
- **Estrutura de tela**: `Tela` põe os cabeçalhos sobre a faixa escura e o restante numa
  folha clara de cantos arredondados, em todas as telas, sem que cada uma repita a
  estrutura. Telas com topo próprio usam o componente `Faixa`. `Cabecalho` e `BotaoIcone`
  escolhem as cores pelo fundo em que estão (contexto `SuperficieContext`).
- Barra de abas escura com marca na aba ativa (a cor não é o único sinal).
- Componentes novos: `FormularioAgendamento` (criar e editar), `DialogoCancelamento`,
  `ItemHistorico`, `BotaoGoogle`, `Marca`.
- Telas novas: `agendamento/editar/[id]`, `agendamento/concluir/[id]`, `meus-dados`.
  Reescritas: `onboarding`, `login`, menu da agenda.
- Telas abertas direto pelo endereço (ou recarregadas) esperam os dados antes de montar o
  formulário, em vez de começar com valores errados.
- `paraData` passou a ler datas sem hora como dia do calendário local (corrige 13.2, itens
  10 e 11).
- Dependências novas, nas versões do SDK 57: `expo-auth-session`, `expo-crypto`,
  `expo-web-browser`, `expo-application` (exigida pelo provedor Google) e
  `react-native-svg` (logotipo do Google).

## 13.5 Alterações no backend

- `POST /agendamentos/{id}/confirmar`, `POST /agendamentos/{id}/cancelar` (motivo opcional)
  e `POST /agendamentos/{id}/concluir` (devolve agendamento e atendimento juntos).
- `PATCH /agendamentos/{id}` aceita trocar o cliente (com conferência de posse), valida data
  passada e conflito de horário (ignorando o próprio agendamento), e recusa editar
  agendamento cancelado ou concluído.
- A rota genérica `PATCH /agendamentos/{id}/status` passou a delegar para cancelar e
  concluir, para não ser uma porta lateral que conclui sem gerar atendimento.
- Conclusão **atômica**: trava a linha do agendamento (`SELECT ... FOR UPDATE`), confere a
  transição, cria o atendimento e muda o status num único `commit`. Se algo falha, nada
  muda. Uma segunda chamada devolve o atendimento já criado.
- O dia do atendimento é calculado no fuso do salão (`FUSO_HORARIO`, padrão
  `America/Sao_Paulo`): concluir às 22h30 de Brasília grava o dia certo, não o seguinte.
- Pendente pode ir direto para concluído; concluído e cancelado são finais. Agendamento
  concluído não pode ser excluído.
- Horários sem fuso são recusados (422).
- Login com Google: `GET /auth/provedores`, `POST /auth/google`, `POST` e
  `DELETE /usuarios/me/google`; `DELETE /usuarios/me` aceita confirmação pelo Google em
  contas sem senha. Serviço `app/services/google.py`.
- A rota `/auth/google` entrou no freio de tentativas que já protegia login e cadastro.
- Mensagens de erro revisadas (sem travessões e sem jargão).

## 13.6 Alterações no banco de dados

Duas migrations novas, ambas reversíveis, ambas sem alterar registros existentes:

**`d7b2e9c41a03` (agenda: conclusão e cancelamento)**
- `atendimentos.agendamento_id` (opcional, `ON DELETE SET NULL`) e índice único parcial:
  um agendamento gera no máximo um atendimento, garantido pelo banco.
- `atendimentos.realizado_em` (opcional): quando o atendimento aconteceu.
- `agendamentos.cancelado_em` e `agendamentos.motivo_cancelamento`.
- Registros antigos ficam com os campos vazios; nada é inventado.
- A volta remove as colunas novas (e, com elas, essas informações).

**`e5a9c3f17b20` (entrar com Google)**
- Tabela `identidades_externas` (provedor, `sub`, e-mail de referência), com duas
  restrições únicas: uma conta Google não entra em duas contas, e uma conta tem no máximo
  uma conta Google.
- `usuarios.senha_hash` passa a aceitar vazio (contas criadas pelo Google).
- A volta **se recusa** se houver conta sem senha, em vez de apagar contas ou inventar
  senhas (testado).

Validação: as duas foram aplicadas sobre o banco de desenvolvimento com os dados de
demonstração; a suíte de testes desfaz todas as migrations até o início e refaz a cada
execução; há teste específico de ida e volta da migration do Google.

## 13.7 Integração com Google

**Implementado e testado sem credencial real:**
- Verificação do ID token no servidor com a biblioteca oficial `google-auth`: assinatura
  (chaves públicas do Google), validade, emissor, público (só os IDs de cliente deste
  projeto), e-mail confirmado e `nonce`.
- A conta é encontrada pelo `sub` do Google, nunca pelo e-mail.
- **Sem vínculo automático por e-mail**: se já existe conta com senha e o mesmo e-mail, o
  login pelo Google é recusado com orientação. A pessoa entra com a senha e conecta o
  Google no Perfil. Motivo: o cadastro por senha não confirma o e-mail.
- Conta criada pelo Google não tem senha: o login por senha nunca entra nela, desconectar o
  Google é recusado e a exclusão é confirmada entrando de novo no Google.
- O token nunca vai para o log (testado).
- Os testes geram um par de chaves RSA e um certificado no próprio teste e entregam o
  certificado à biblioteca no lugar do endereço do Google; o resto é a verificação real.
  Por mutação, confirmou-se que desligar a conferência de público ou ligar contas pelo
  e-mail faz testes falharem.
- No navegador, o roteiro `e2e/google.mjs` confirma o pedido enviado ao Google (ID de
  cliente, `id_token`, `nonce`, escopos, endereço de retorno) e que um token forjado volta
  recusado pelo servidor, com mensagem na tela e sem abrir sessão.
- O botão só aparece quando o aplicativo e o servidor estão configurados.

**Depende de ação externa do dono do projeto** (passo a passo em
`docs/GUIA_LOGIN_GOOGLE.md`):
- criar o projeto e os IDs de cliente OAuth no Google Cloud;
- preencher `GOOGLE_CLIENT_IDS` (servidor) e `EXPO_PUBLIC_GOOGLE_*_CLIENT_ID` (aplicativo).

**Não validado**: login com uma conta Google real; login no Android e no iOS (exige build de
desenvolvimento; não funciona no Expo Go, onde o botão não aparece).

## 13.8 Testes executados

Todos executados neste ambiente (Linux, PostgreSQL 16, Chromium), com os resultados abaixo.

**Servidor**: 375 testes, todos aprovados, cobertura 94%. Novos nesta etapa:
`test_agenda_fluxo.py` (32) e `test_google.py` (29); ajustados: transições de status,
varredura de acesso entre contas (22 rotas com identificador, incluindo as 3 novas),
contrato com o aplicativo e dados de demonstração.

Cenários pedidos, com o teste que os cobre:

| Cenário | Onde |
|---|---|
| Criar no futuro / recusar ontem / recusar ano passado / recusar hora de hoje que passou | `test_agenda_fluxo` (API) e `e2e/agenda.mjs` (tela) |
| Dia 22 recusado e dia 24 aceito com "hoje" = 23/10/2026 | `test_dia_22_recusado_quando_hoje_e_23` |
| Fuso: mesmo instante em UTC e em Brasília; perto da meia-noite | `test_fuso_nao_confunde_utc_com_horario_local`, `test_data_do_atendimento_e_a_do_salao_e_nao_a_de_greenwich` |
| Editar: dados carregados, salvar, recusar passado, nota em compromisso passado | `test_agenda_fluxo` e `e2e/agenda.mjs` |
| Sair sem salvar pede confirmação | `e2e/agenda.mjs` |
| Conflito, horários vizinhos, cancelado libera horário, sem conflito consigo mesmo | `test_agenda_fluxo` |
| Confirmar (e repetir), não confirmar finalizado | `test_agenda_fluxo` e `e2e/agenda.mjs` |
| Cancelar preserva o registro, guarda data e motivo | `test_agenda_fluxo` e `e2e/agenda.mjs` |
| Concluir cria atendimento ligado; não duplica; índice único no banco; transação desfeita em erro | `test_agenda_fluxo` |
| Simulação ligada; simulação de outro cliente recusada | `test_agenda_fluxo` |
| Histórico separado entre clientes de mesmo nome; registros antigos sem dados inventados | `test_agenda_fluxo` |
| Histórico mostra horário marcado e abre a simulação | `e2e/agenda.mjs` |
| Google: primeiro acesso, segundo acesso, `sub` estável, token adulterado/vencido/de outro app/outro emissor, e-mail não confirmado, `nonce`, falha de rede, sem log do token, sem vínculo por e-mail, conectar, desconectar, exclusão sem senha, freio de tentativas | `test_google.py` |
| Acesso a recurso de outra conta (IDOR) | `test_idor_completo.py` |

**Mutação** (o teste precisa falhar quando a regra é removida): desligar a validação de data
passada (6 falhas), retirar a idempotência da conclusão (barrada pelo índice único),
retirar a conferência de público do token Google (1 falha), ligar contas pelo e-mail
(1 falha). Todas as regras foram restauradas e a suíte voltou a passar.

**Aplicativo**: `tsc --noEmit --noUnusedLocals` sem erros; `expo export --platform web`
concluído.

**Navegador** (Chromium, fuso de Brasília):

| Roteiro | Verificações |
|---|---|
| `fluxo-completo.mjs` (cadastro até agendamento) | 26 aprovadas |
| `qa-interface.mjs` (responsividade, teclado, estados) | 22 aprovadas |
| `mudancas-interface.mjs` (mudanças da etapa anterior) | 21 aprovadas |
| `agenda.mjs` (novo) | 27 aprovadas |
| `google.mjs` (novo, sem conta real) | 12 aprovadas |
| `visual-contraste.mjs` (novo: 23 telas × 2 tamanhos) | 0 problemas de contraste, 0 rolagens horizontais |

**Lint**: o projeto não tem configuração de ESLint. O comando `expo lint` tenta criá-la
baixando pacotes, o que o ambiente bloqueou. No lugar, a verificação de tipos rodou com
`--noUnusedLocals`, e quatro importações sem uso que já existiam foram removidas.

**Segurança das dependências**: `pip-audit` sem vulnerabilidades. `npm audit` aponta 12
avisos (6 altos) nas ferramentas do Expo (`@expo/cli`, `node-forge`, `zod` e outras); os
mesmos 12 existem no `package-lock.json` anterior a esta etapa, não vieram das dependências
novas, e a correção sugerida exige atualização forçada com quebra de versão.

**Varredura de segredos**: nenhuma chave, token ou credencial nos arquivos alterados ou
novos; `.env` continua fora do Git.

## 13.9 Arquivos alterados

Servidor (novos): `app/models/identidade_externa.py`, `app/services/google.py`,
`migrations/versions/d7b2e9c41a03_agenda_conclusao_e_cancelamento.py`,
`migrations/versions/e5a9c3f17b20_entrar_com_google.py`, `tests/test_agenda_fluxo.py`,
`tests/test_google.py`.

Servidor (alterados): `app/api/v1/agendamentos.py`, `auth.py`, `usuarios.py`;
`app/core/config.py`, `erros.py`, `protecoes.py`; `app/main.py`; `app/models/__init__.py`,
`agendamento.py`, `atendimento.py`, `enums.py`, `usuario.py`;
`app/repositories/consultas.py`; `app/schemas/agendamento.py`, `atendimento.py`, `auth.py`;
`app/seed.py`; `app/services/agendamentos.py`, `auth.py`, `ai/fake.py`,
`regras_consentimento.py`, `simulacao.py`, `validacao_foto.py`; `requirements.txt`;
`docker-compose.yml`; `.env.example`; `tests/conftest.py`,
`test_agenda_e_atendimentos.py`, `test_idor_completo.py`, `test_seed.py`.

Aplicativo (novos): `app/agendamento/editar/[id].tsx`, `app/agendamento/concluir/[id].tsx`,
`app/meus-dados.tsx`; `src/components/BotaoGoogle.tsx`, `DialogoCancelamento.tsx`,
`FormularioAgendamento.tsx`, `ItemHistorico.tsx`, `Marca.tsx`; `src/services/google.ts`,
`modoDemo.ts`; `src/theme/status.ts`, `superficie.ts`; `.env.example`;
`e2e/agenda.mjs`, `google.mjs`, `visual-contraste.mjs` (e as pastas de capturas
`e2e/telas-agenda`, `telas-google`, `telas-visual`).

Aplicativo (alterados): `app.json`, `package.json`, `package-lock.json`;
`app/_layout.tsx`, `app/index.tsx`, `onboarding.tsx`, `login.tsx`, `cadastro.tsx`,
`excluir-conta.tsx`, `privacidade.tsx`, `responsabilidades.tsx`;
`app/(tabs)/_layout.tsx`, `index.tsx`, `agenda.tsx`, `clientes.tsx`, `perfil.tsx`;
`app/agendamento/novo.tsx`; `app/atendimento/novo.tsx`, `sucesso.tsx`;
`app/cliente/[id].tsx`, `editar.tsx`; `app/simulacao/captura.tsx`, `cliente.tsx`,
`indisponivel.tsx`, `parametros.tsx`, `processando.tsx`, `recusada.tsx`;
`src/components/AvisoDeConexao.tsx`, `Basicos.tsx`, `Cabecalho.tsx`, `CampoData.tsx`,
`DocumentoTermo.tsx`; `src/data/servicoExterno.ts`, `store.tsx`, `tipos.ts`;
`src/services/api/cliente.ts`, `index.ts`; `src/services/consentService.ts`;
`src/theme/textos.ts`, `tokens.ts`; `src/utils/datas.ts`;
`e2e/fluxo-completo.mjs`, `mudancas-interface.mjs`, `qa-interface.mjs`.

Raiz: `qa.sh` (novas etapas), `scripts/verificar_travessoes.py` (novo),
`docs/GUIA_LOGIN_GOOGLE.md` (novo), este relatório.

## 13.10 Configurações necessárias

| Variável | Onde | Obrigatória | Para quê |
|---|---|---|---|
| `GOOGLE_CLIENT_IDS` | `backend/.env` | Não | IDs de cliente OAuth aceitos, separados por vírgula. Vazio desliga o Google |
| `FUSO_HORARIO` | `backend/.env` | Não (padrão `America/Sao_Paulo`) | Dia do atendimento no horário do salão |
| `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` | `espelho/.env` | Não | Botão do Google no navegador |
| `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID` / `_IOS_` | `espelho/.env` | Não | Botão do Google em build próprio |

Depois de atualizar o código:

```
cd backend
pip install -r requirements.txt     # google-auth, requests, tzdata
alembic upgrade head                # aplica as duas migrations novas
cd ../espelho
npm ci                              # dependências novas do aplicativo
npx expo start --web --clear
```

**Importante:** sem o `alembic upgrade head`, o código novo roda sobre o banco antigo e o
login responde com erro 500 (a tabela `identidades_externas` ainda não existe). Desde a
correção feita depois da entrega, a API avisa no terminal ao iniciar ("BANCO
DESATUALIZADO", com o comando que resolve) e `GET /api/v1/saude` traz
`"bancoAtualizado": false`.

Os arquivos `.env.example` (servidor e, agora, aplicativo) trazem as variáveis sem valores.
Nenhum segredo é necessário para o Google: o servidor não usa "client secret".

## 13.11 Pendências e limitações

1. **Travessões nos textos dos termos já publicados** (termo do cliente v1.1 e aviso do
   profissional): esses textos são versões imutáveis, guardadas pelas migrations e
   protegidas por gatilho no banco, porque provam o que o cliente leu. Trocar a pontuação
   exige publicar uma versão nova, e a regra do sistema pede **nova autorização de todos os
   clientes** antes da próxima foto (e nova ciência do profissional). Não publiquei por ser
   uma decisão sua, com efeito sobre todos os clientes. Para fazer: criar uma migration
   que insira a versão 1.2 dos dois termos com o mesmo conteúdo sem travessões e a marque
   como vigente (como a `c3f1a2d45e60` fez com a 1.1). Proposta: aproveitar a próxima
   mudança de conteúdo dos termos.
2. **Login com Google real** depende das credenciais (13.7). No celular, exige build de
   desenvolvimento.
3. O provedor Google do `expo-auth-session` está marcado como "deprecated" pelo Expo em
   favor do login nativo; segue funcionando no SDK 57 e é o caminho que funciona também no
   navegador. Para publicação nas lojas, a troca pelo login nativo é a evolução indicada.
4. **Lembrete**: o interruptor saiu da tela porque o envio de notificação nunca existiu. O
   campo continua no banco e o valor gravado é preservado.
5. **Recuperação de senha por e-mail** não existe; o botão que só avisava isso saiu.
6. **Desfazer a migration da agenda** remove as informações novas (horário real, motivo e
   data de cancelamento, ligação atendimento-agendamento). É reversível na estrutura, não
   no conteúdo criado depois dela.
7. **Lint** não configurado no projeto (13.8).
8. **Avisos do `npm audit`** nas ferramentas do Expo, anteriores a esta etapa (13.8).
9. O freio de tentativas de login (agora também no Google) é em memória, por processo,
   como já estava documentado.
10. Não testado em aparelho físico Android ou iOS nesta etapa; a verificação visual foi no
    navegador, em largura de celular (390px) e de tablet (820px).

## 13.12 Resultado por requisito

| Requisito | Situação |
|---|---|
| §2 Diagnóstico antes de alterar | Concluído e validado |
| §3 Nome novo, usado de forma consistente | Concluído e validado (identificadores internos mantidos de propósito: `slug`, pacote, chaves de armazenamento) |
| §3 Tela inicial pública | Concluído e validado |
| §4.1 Menu da agenda por situação, sem "Nova simulação" e "Registrar atendimento" | Concluído e validado |
| §4.2 Editar agendamento | Concluído e validado |
| §4.3 Confirmar agendamento | Concluído e validado |
| §4.4 Cancelar agendamento com motivo, sem apagar | Concluído e validado |
| §4.5 Atendimento concluído, atômico e sem duplicidade | Concluído e validado |
| §4.6 Histórico correto no perfil do cliente | Concluído e validado |
| §4.7 Simulações ligadas ao atendimento | Concluído e validado |
| §5 Bloqueio de datas passadas (aplicativo e servidor, fuso, meia-noite) | Concluído e validado |
| §6 Revisão de textos e remoção de travessões | Parcialmente implementado: interface e servidor sem travessões; textos dos termos publicados mantidos (13.11, item 1) |
| §7 Base escura, folhas claras, tokens, cores por situação, contraste | Concluído e validado |
| §8 Login com Google: código, verificação no servidor, vínculo seguro, documentação | Implementado, mas não totalmente validado (sem conta Google real) |
| §8 Login com Google funcionando para usuários | Bloqueado por dependência externa (credenciais no Google Cloud) |
| §9 Revisão de segurança | Concluído e validado (IDOR, token, log, freio, segredos, dependências Python) |
| §10 Migrations seguras e reversíveis | Concluído e validado |
| §11 Testes (unidade, integração, navegador, tipos, build, migrations, contraste, travessões) | Concluído e validado, exceto lint (não configurado no projeto) |
| §12 Revisão de experiência | Concluído e validado (correções descritas em 13.2 e 13.4) |
| §13 Relatório final | Concluído |

## 13.13 Continuidade

**Para revisar e registrar o trabalho** (nada foi commitado):

```
git status                      # lista o que mudou
git diff                        # revisa as alterações
./qa.sh                         # servidor, tipos e travessões
./qa.sh --interface             # com API e "npx expo start --web" no ar
git add -A
git commit -m "Agenda completa, login com Google, novo visual e nome Salão em Dia"
```

As pastas `espelho/e2e/telas-*` guardam as capturas geradas pelos roteiros; podem ir para o
repositório como evidência ou ficar de fora.

**Próximos passos sugeridos**, em ordem:
1. Criar as credenciais do Google seguindo `docs/GUIA_LOGIN_GOOGLE.md` e testar com a sua
   conta (no navegador, `npx expo start --web`).
2. Decidir sobre a versão 1.2 dos termos (13.11, item 1).
3. Configurar o ESLint do Expo (`npx expo lint` com acesso à internet) e incluí-lo no
   `qa.sh`.
4. Gerar um build de desenvolvimento Android para validar câmera e Google no aparelho.
5. Atualizar o texto do TCC com: o nome novo, o fluxo de conclusão que liga agenda,
   atendimento e simulação, a verificação do token Google no servidor e a decisão de não
   ligar contas pelo e-mail.

---

## Etapa seguinte: correções em agendamentos, agenda e atendimentos

Executada em 24/10/2026, sobre o trabalho acima, também sem commits.

### Problemas e causas encontradas

| Item | Causa real | Correção |
|---|---|---|
| 1. Duração obrigatória | `agendamentos.duracao_min` era `NOT NULL`, a API tinha padrão de 60 min e o formulário só oferecia botões | Coluna opcional (migration), sem padrão na API, campo digitado opcional |
| 2. "Sair sem salvar?" ao criar | A marca de "salvo" só era ligada depois que a função de salvar terminava, mas essa função já navegava para a agenda | `useProtecaoDeSaida`: a tela salva, libera a saída e só então navega; trava contra clique duplo |
| 3. Câmera acima da barra | `marginTop: -12` fixo no botão e itens alinhados pelo topo | Itens centralizados na mesma linha, sem deslocamento fixo |
| 4. Data do "+" | O "+" abria sempre "amanhã às 15h" | O dia selecionado vai para o formulário; dia passado vira hoje |
| 5. "Cancelar consentimento" | `alignSelf: 'flex-start'` | `alignSelf: 'center'`, mesmo tamanho e estilo |
| 6. Data da conclusão | A tela usava "agora" quando o horário marcado ainda não tinha passado | Começa sempre no horário marcado do agendamento |
| 7. "Outro" na conclusão | A tela montava os chips só com a lista fixa | Componente único `CampoServico`, com "Outro" e o texto original |
| 8. "Registrar atendimento" | Tela antiga com data fixa em "hoje" e campos próprios | Mesmo formulário da conclusão, com dia, hora, duração, "Outro" e simulação |
| Bug extra: chips | O estado "selecionado" não chegava ao HTML no navegador | `aria-selected` no `Chip` |

### Regras implementadas

- **Duração**: aceita "45", "45 min", "1h", "1 hora", "1h30", "1 hora e 30 minutos", "1:30",
  "1,5h". Fica entre 15 minutos e 8 horas (a mesma faixa de antes, agora num lugar só:
  `DURACAO_MINIMA`/`DURACAO_MAXIMA` no servidor e em `src/utils/duracao.ts`). Vazio grava
  `null`. Na edição, `duracaoMin` ausente mantém a duração; `null` apaga.
- **Conflito sem duração**: o compromisso ocupa o horário de início. Conflita com quem
  começa no mesmo horário ou com um compromisso em andamento naquele instante; nenhuma
  duração é presumida.
- **Data inicial do agendamento**: dia futuro selecionado, esse dia às 15h; hoje ou dia
  passado, hoje às 15h (ou a próxima meia hora, se 15h já passou); sem dia (perfil, fim de
  atendimento), amanhã às 15h como antes. Por dia do calendário local.
- **Depois de criar**: a agenda abre no dia do agendamento criado.
- **Conclusão**: começa com data, hora, serviço, duração e observações do agendamento.
  O que for alterado vai para o atendimento; o agendamento continua com o previsto.
- **Atendimento avulso**: `POST /atendimentos` aceita `realizadoEm` (o dia é calculado no
  fuso do salão), `duracaoMin` e recusa horário no futuro. O formato antigo (só
  `dataServico`) continua aceito, sem hora inventada. Nada de agendamento é criado ou
  concluído; o histórico mostra "Registrado sem agendamento".
- A regra "não pode estar no futuro" e o cálculo do dia são a mesma função
  (`dia_do_atendimento`) para a conclusão e para o registro avulso.

### Banco de dados

Migration `f8c4d2a6b913` (reversível): `agendamentos.duracao_min` passa a aceitar vazio
(registros existentes intactos) e `atendimentos.duracao_min` é criada, opcional, com a
mesma restrição de faixa. A volta se recusa se houver agendamento sem duração, em vez de
inventar uma. **É preciso rodar `alembic upgrade head`** ao atualizar (a API avisa no
terminal se esquecer).

### Arquivos principais

Servidor: `schemas/base.py`, `schemas/agendamento.py`, `schemas/atendimento.py`,
`models/agendamento.py`, `models/atendimento.py`, `services/agendamentos.py`,
`services/atendimentos.py`, `seed.py`, migration nova, `tests/test_duracao_e_atendimento_avulso.py`
(novo), `tests/test_seed.py`.

Aplicativo (novos): `src/components/CampoDuracao.tsx`, `CampoServico.tsx`,
`FormularioAtendimento.tsx`, `LinhaCliente.tsx`, `PartesFormulario.tsx`,
`ProtecaoDeSaida.ts`; `src/utils/duracao.ts`, `inicioAgendamento.ts`; `testes/duracao.mjs`,
`testes/inicio-agendamento.mjs`; `e2e/atendimentos.mjs`.
Aplicativo (alterados): `FormularioAgendamento.tsx`, `Campo.tsx`, `Basicos.tsx` (Chip),
`ItemHistorico.tsx`, `app/agendamento/novo.tsx`, `editar/[id].tsx`, `concluir/[id].tsx`,
`app/atendimento/novo.tsx`, `sucesso.tsx`, `app/(tabs)/agenda.tsx`, `app/(tabs)/_layout.tsx`,
`app/cliente/[id].tsx`, `src/data/tipos.ts`, `store.tsx`, `src/services/api/index.ts`,
`src/utils/datas.ts`; roteiros `e2e/agenda.mjs` e `e2e/fluxo-completo.mjs`; `qa.sh`.

### Verificações executadas

| Verificação | Resultado |
|---|---|
| pytest (PostgreSQL real) | **397 aprovados**, 0 falhas, cobertura 94% (22 testes novos) |
| Mutação: retirar a regra de conflito no horário de início | o teste correspondente falha (restaurado) |
| Interpretador de duração (`testes/duracao.mjs`) | 34 casos, 0 falhas |
| Data inicial do agendamento (`testes/inicio-agendamento.mjs`) | 9 casos, 0 falhas, nos fusos de Brasília, UTC e Tóquio |
| `tsc --noEmit --noUnusedLocals` | 0 erros |
| `expo export --platform web` | concluído |
| `alembic upgrade` / `downgrade` / `upgrade` e `alembic check` | sem diferença entre modelo e banco |
| `e2e/atendimentos.mjs` (novo, os 16 cenários pedidos, conferindo a API) | 49 aprovadas |
| `e2e/agenda.mjs`, `fluxo-completo.mjs`, `qa-interface.mjs`, `mudancas-interface.mjs`, `google.mjs` | 27, 26, 22, 21 e 12 aprovadas, 0 falhas |
| `e2e/visual-contraste.mjs` (23 telas, celular e tablet) | 0 problemas de contraste ou largura |
| Alinhamentos em 360×640, 390×844 e 820×1180 | câmera dentro da barra e no eixo das abas; botão centralizado |
| Travessões na interface | 0 ocorrências |

Regressão encontrada e corrigida no caminho: o formulário novo de registro começava sem
serviço escolhido, e o caminho "simulação → registrar atendimento" parava na validação. A
verificação antiga do roteiro era frouxa e não acusava. A sugestão visível de antes
(Coloração vindo de simulação, Corte nos demais casos) foi restaurada e o roteiro passou a
conferir a tela de confirmação.

### Pendências

- Não testado em aparelho físico; os alinhamentos foram medidos no navegador, em três
  tamanhos. O cálculo das áreas seguras (`useSafeAreaInsets`) não mudou.
- O serviço sugerido no agendamento novo continua sendo o primeiro da lista, como antes;
  a duração não tem mais sugestão nenhuma.

---

## Ajustes no painel inicial e na comparação de simulações

| Item | Causa | Correção |
|---|---|---|
| Data no próximo atendimento | O cartão só mostrava a hora | Linha com a data ("Hoje, sábado, 24 de outubro", "Terça, 27 de outubro"); ao lado da hora fica só a distância ("em 3 dias"), sem repetir o dia da semana |
| "na agenda" sempre em zero | Contava só os agendamentos de hoje | Passa a ser **"agendados"**: clientes distintos com horário pendente ou confirmado de hoje em diante (`clientesAgendados`) |
| "simulações hoje" | Contava também tentativas que falharam ou estavam em curso | Conta só as simulações prontas de hoje (`simulacoesDeHoje`) |
| "Voltar ao perfil" descentralizado | `Botao` estreito força `alignSelf: 'flex-start'` | Centralizado em todos os estados vazios; sem tela anterior (aberta pelo endereço), o botão leva ao perfil |
| "Marcar como preferida" vazando | Texto numa linha flexível sem permissão para encolher (no Android e no iOS, não quebra sozinho) | `flex: 1, flexShrink: 1` no texto |
| Opções extras na comparação | "Registrar atendimento com a preferida" e "Agendar para depois" | Removidas: a tela é só para comparar e escolher a preferida |
| Ordem das simulações | Só por data | Preferida primeiro, depois da mais recente para a mais antiga, no app (`ordenarSimulacoes`) e na API |

Verificações: 398 testes do servidor (1 novo, da ordem); `testes/painel.mjs` com 11
verificações, nos fusos de Brasília e UTC; tipos sem erro; `e2e/painel-e-comparacao.mjs`
(novo) com 18 verificações em 320, 360, 390 e 820px, conferindo a API; demais roteiros e
contraste sem falhas (`qa.sh --interface` completo).

Limite conhecido: o vazamento de "Marcar como preferida" não se reproduz no navegador (o
navegador quebra a linha sozinho); a correção trata o comportamento do Android e do iOS e
foi validada no navegador apenas como "nada vaza".

---

## Fotos, câmera e ajustes de listas

| Item | Causa | Correção |
|---|---|---|
| "DE A A Z" | A etiqueta converte tudo para maiúsculas | Texto já em caixa, sem a conversão: "DE A a Z" |
| Lista de clientes | Selo com a contagem de simulações; status curto ("autorizado") | Contagem removida; selos "uso de imagem autorizado/pendente/recusado/cancelado/a renovar" |
| Foto do cliente com "Sem conexão" | A foto ia sem redução; fotos de celular passam do limite de 12 MB por envio, e o servidor fecha a conexão ainda durante o envio (o Android mostra "sem conexão") | A foto é reduzida no aparelho (1024 px, JPEG) antes do envio (`reduzirParaEnvio`); confirmado por mutação: sem a redução, a foto de 18 MB volta 413 |
| Foto "não fica salva" | O `Avatar` só mostrava iniciais: a foto não aparecia em lugar nenhum | `Avatar` mostra a foto (perfil, lista, seletores, Início) |
| Sem como remover a foto do cliente | Faltava a ação | "Remover foto" no cadastro; se só a foto falhar, os dados ficam salvos e o aviso diz o que faltou |
| Editar cliente aberto pelo endereço | Formulário montado antes da carga, com campos vazios | Espera os dados antes de montar |
| Foto do profissional | Não existia | `POST`/`DELETE /usuarios/me/foto`, `fotoUri` na conta, índice único (migration `a3e7b5c90d14`), tela em Meus dados com adicionar, trocar e remover |
| "Liberar câmera" | `Botao` estreito alinhado à esquerda | Centralizado |
| "Luz de frente" | Aviso fixo | Removido |
| "Rosto dentro do guia" | Selo fixo, sempre "confirmado", sem detecção | Conferência ao vivo: miniatura silenciosa a cada ~1,2 s, o servidor detecta o rosto (OpenCV) na região do guia; sem rosto: "Enquadre o rosto no guia para um melhor resultado". A miniatura não é guardada, não gasta cota e exige autorização de imagem do cliente |
| "Agendado para" no histórico | Data marcada ao lado da realizada | Só a origem: "Marcado pela agenda" (e o serviço previsto, se diferente) |
| Foto original da simulação | A tela só mostrava o resultado | Abas "Simulação", "Foto original" e "Lado a lado" (antes e depois) |
| Teto de simulações | Contado em memória (zerava ao reiniciar) e gasto antes de validar foto e autorização | Contagem no banco, só do que vai ao provedor, com trava da conta contra envios simultâneos; padrão **3 por hora por conta** (`SIMULACAO_MAX_POR_HORA`) |

Verificações: 417 testes do servidor (novos: foto do profissional, enquadramento, cota);
tipos sem erro; `e2e/fotos-e-camera.mjs` (novo) com 25 verificações, incluindo a câmera
falsa do Chromium com um vídeo de rosto (confirmação real do servidor) e sem rosto; todas
as baterias anteriores e o contraste sem falhas (`qa.sh --interface`).

Ao atualizar: `alembic upgrade head` (migration nova) e conferir `SIMULACAO_MAX_POR_HORA`
no `.env` (o valor do `.env` prevalece sobre o padrão).

Limites conhecidos: a conferência do rosto depende de rede (cada consulta é uma miniatura
de poucos kB) e é uma orientação, não uma trava: a foto pode ser tirada sem ela, e a
validação completa continua no envio. A posição do guia é aproximada, porque a prévia da
câmera corta a imagem de forma diferente em cada aparelho. Não testado em aparelho físico.

## Etapa "Estilo e cor": personalização e integração com a Replicate

A etapa 3 da simulação foi reformulada (corte e cor descritos em dois passos guiados, com
exemplos em texto, "manter o atual" e revisão antes de gerar), e a integração com a
Replicate passou a conferir o schema publicado de cada modelo antes de gastar. A foto de
referência e o pedido por voz chegaram a ser implementados e foram retirados depois, por
custo e complexidade para o protótipo. Diagnóstico, decisões, testes, limitações
e o passo a passo do teste real estão em
[`RELATORIO_PERSONALIZACAO_IA.md`](RELATORIO_PERSONALIZACAO_IA.md).
