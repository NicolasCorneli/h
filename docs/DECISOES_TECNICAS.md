# Decisões técnicas

Decisões que o código precisa manter. Cada uma corrige um defeito encontrado na auditoria
de QA (ver `historico/RELATORIO_QA_E_MELHORIAS.md`) e tem teste que falha se ela for desfeita.

## 1. Ordem das travas no banco

Leitura seguida de escrita, em PostgreSQL com `READ COMMITTED`, precisa de trava quando duas
requisições podem decidir sobre o mesmo dado. As travas usadas, e a ordem em que são pegas:

| Operação | Trava | Por quê |
| --- | --- | --- |
| Criar ou remarcar agendamento | linha do **usuário** (`FOR UPDATE`) antes de conferir conflito | sem ela, dois envios simultâneos gravavam o mesmo horário |
| Confirmar, cancelar, editar, concluir, excluir agendamento | linha do **agendamento** (`FOR UPDATE` + `populate_existing`), relida | sem ela, uma decisão tomada sobre o status antigo desfazia a outra (confirmar por cima de um cancelamento) e a segunda conclusão virava erro 500 |
| Criar simulação | linha do **usuário** (cota por hora) | dois envios não passam juntos do teto |
| Marcar simulação preferida | linha do **cliente** | duas marcações simultâneas batiam no índice único |
| Apagar imagens, cliente ou conta | linha do(s) **cliente(s)** (`FOR UPDATE`) **antes** de limpar o storage | a gravação do resultado de uma simulação em andamento espera, ou é descartada |
| Gravar o resultado da simulação | linha do **cliente** (`FOR SHARE`) antes de gravar o arquivo | ver acima |

`populate_existing` é obrigatório quando o objeto já foi lido na mesma sessão antes da
trava: sem ele o SQLAlchemy devolve o objeto em memória, com o valor antigo.

Regra para código novo: quem apaga arquivos do storage trava o cliente antes; quem grava
arquivo de cliente trava o cliente (compartilhado) antes de gravar. Agendamento de um
usuário: trava do agendamento antes da trava do usuário, nunca o contrário.

## 2. Datas

- Instantes (horário de agendamento, `realizadoEm`) sempre com fuso; o servidor recusa
  horário sem fuso.
- Dias do calendário (nascimento, `dataServico`) trafegam como `aaaa-mm-dd`, sem hora. O
  aplicativo usa `isoDeDataCurta`/`diaLocalIso`; mandar um instante num campo de data é
  recusado (era o defeito que impedia cadastrar cliente com nascimento).
- "Hoje" para recusar atendimento no futuro é o maior entre o dia no fuso do salão
  (`FUSO_HORARIO`) e o dia em UTC: o aparelho manda o dia do calendário dele, e todo o
  Brasil está atrás de UTC.
- Corrigir só o dia de um atendimento que tinha hora de outro dia apaga a hora: o registro
  não pode afirmar duas datas.

## 3. Atendimentos: corrigir sempre, excluir só o avulso

O atendimento que veio da agenda é o registro de um agendamento concluído; excluí-lo
deixaria o compromisso "concluído" sem o serviço. Ele pode ser corrigido (`PATCH`). O
avulso registrado por engano pode ser excluído (`DELETE`).

## 4. Sessão no aplicativo

- A renovação tem três resultados: renovada, recusada (4xx do servidor) e sem conexão.
  Só a recusa encerra a sessão. Antes, um Wi-Fi instável desconectava o profissional.
- Todo fim de sessão avisa a interface (`aoEncerrarSessao`), e o layout raiz tem uma guarda
  de rotas: sem sessão, só `onboarding`, `login`, `cadastro` e a porta de entrada abrem.

## 5. Produção

- `AMBIENTE=producao` com `MODO_DEMO=true` impede a API de subir.
- O seed se recusa em produção (as contas de demonstração têm senha publicada).
- Envios de imagem são lidos até um byte além do limite: o limite de corpo da borda olha o
  `Content-Length`, que um envio em partes não traz.

## 6. Envio de arquivos no aparelho

Desde o Expo SDK 57 o `fetch` do aparelho é o `expo/fetch`, que não aceita o formato
antigo do React Native (`{ uri, name, type }`) no `FormData`. Fotos locais vão como `File`
do `expo-file-system` (`src/services/api/arquivoLocal.ts`); na web, como `Blob`
(`arquivoLocal.web.ts` nunca é usado com foto sem `Blob`). Não volte ao objeto `{ uri }`.

## 7. Caminho do storage local

`STORAGE_DIR` relativo é resolvido a partir da pasta `backend`, não da pasta de onde a
API foi iniciada. Ao mover ou extrair o projeto em outro lugar, leve junto
`backend/dados/` se o banco de dados for o mesmo: as linhas de `imagens` apontam para
arquivos dessa pasta.

## 8. Sessões revogáveis no servidor

Todo token (acesso e renovação) leva `sv`, a versão da sessão da conta
(`usuarios.versao_sessao`). Trocar a senha (`POST /usuarios/me/senha`) ou sair de todos os
aparelhos (`DELETE /usuarios/me/sessoes`) incrementa a versão **no banco**
(`versao_sessao + 1`, não a partir do valor em memória), e os tokens anteriores passam a ser
recusados (`401 sessao_encerrada` no acesso, `refresh_invalido` na renovação). Token sem `sv`
(emitido antes desta mudança) vale como versão 0: a atualização não desconectou ninguém.

## 9. Migrations: uma por vez, e compatíveis com o código anterior

- `migrations/env.py` pega um advisory lock do PostgreSQL antes de migrar. Sem ele, duas
  instâncias subindo juntas falhavam com `UniqueViolation` (reproduzido em 2 de 3 processos).
- Em produção as migrations rodam no serviço `migrar` do compose, uma vez por implantação;
  a API sobe com `MIGRAR_AO_SUBIR=false`.
- Toda migration precisa funcionar com o código da versão anterior (coluna nova com valor
  padrão, índice), para que o rollback do código não exija rollback do esquema. As de
  `e1b4c7d29a50` e `f3a8d6e2b571` foram conferidas rodando a API anterior sobre o banco migrado.

## 10. Endereço público e proxy

- `URL_PUBLICA` é a base das URLs de imagem quando definida (obrigatória em produção). O
  endereço da requisição só vale no desenvolvimento: atrás de proxy ele seria o interno.
- O uvicorn roda com `--proxy-headers` (confia nos `X-Forwarded-*` de `FORWARDED_ALLOW_IPS`; no compose da raiz, `*`, porque só o Caddy alcança a API),
  `--no-access-log` (o log de acesso é o da aplicação, sem a query: a query das imagens é a
  assinatura que abre a foto) e `--no-server-header`.

## 11. Testes nunca tocam um banco que não seja de teste

`tests/conftest.py` usa `TEST_DATABASE_URL` e ignora o `DATABASE_URL` herdado do terminal,
e recusa banco cujo nome não termine em `_test`. A suíte faz `downgrade base`: com o
`DATABASE_URL` de um banco real exportado no terminal, ela o apagava.

## 12. Provedor de IA: o que pode ser repetido

Só leituras idempotentes, depois de a predição existir (consulta do estado, download do
resultado), são repetidas diante de erro de rede, 5xx ou 429 (até 3 vezes). A criação da
predição nunca é repetida: um erro na resposta não garante que ela não foi criada e cobrada.

## 13. Simulação presa expira também na leitura

Uma simulação "processando" há mais de `SIMULACAO_EXPIRA_MIN` é marcada como falha
("interrompida") ao listar, consultar ou excluir simulações da conta, além de na
inicialização. Só na inicialização não bastava: interrompida por um reinício, ela tinha
menos de 5 minutos naquele momento e ficava presa até o reinício seguinte, sem poder ser
excluída (409). Um resultado que chegue depois da expiração ainda é gravado.

## 14. Endereço da API no aplicativo de produção

`EXPO_PUBLIC_API_URL` quando definida; no build de produção para a web, sem ela, a origem
do próprio site (API no mesmo domínio); no build do celular, sem ela, toda chamada falha
com `servidor_nao_configurado`. A descoberta pelo Metro (porta 8000 do computador) vale só
no desenvolvimento: antes, ela valia também no build de produção e gerava
`http://<domínio>:8000` na web e `http://espelho:8000` no celular.

## 15. Build web sempre com o cache limpo

`npm run build:web` é `expo export --platform web --clear`. As `EXPO_PUBLIC_*` são embutidas
quando o Metro transforma cada módulo, e o resultado fica no cache: sem `--clear`, um build
gerado depois de outro com URL diferente saiu com a URL anterior (reproduzido). A CI e o
`DEPLOY.md` usam o script; não troque por `npx expo export` sem `--clear`.

## 16. Uma subida só: site e API no mesmo domínio, atrás do Caddy

O `docker-compose.yml` da raiz sobe a aplicação inteira. O serviço `web` (Caddy) entrega o
site, encaminha `/api/` para a API e obtém o certificado HTTPS sozinho para `DOMINIO`.
Consequências que o código e a configuração precisam manter:

- o site é gerado sem `EXPO_PUBLIC_API_URL` e chama a API na própria origem (seção 14);
  `URL_PUBLICA` e `CORS_ORIGENS` derivam de `DOMINIO`;
- a API e o banco não publicam porta: só a rede interna os alcança. Por isso a API confia
  nos `X-Forwarded-*` de qualquer origem interna (`FORWARDED_ALLOW_IPS=*`), e o Caddy
  descarta os que vêm do cliente (conferido: forjar `X-Forwarded-For` não escapa do freio de
  login);
- o Caddy remove o cabeçalho `Server` e limita o corpo de `/api/` a 12 MB, com 180 s de
  tempo limite, para os envios de foto.
