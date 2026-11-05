# Relatório: Nano Banana 2.1 na simulação capilar

Branch `feat/nano-banana`, a partir da `main` em `b023bc8`. Sem commit, sem push, sem deploy
e sem migration contra a produção. Nenhuma chamada paga à Replicate foi feita: as únicas
consultas reais foram leituras de schema (`GET /v1/models/...`), que não geram cobrança.

## 1. Resumo

**O que muda.** A simulação ganhou um segundo caminho, escolhido por variável de ambiente:

- `AI_ESTRATEGIA=especializado` (padrão, o de hoje): exemplos da tela no
  `change-haircut`, descrição livre no `flux-kontext-pro`. Nada mudou nele: os testes
  antigos passam sem alteração de comportamento.
- `AI_ESTRATEGIA=instrucao` com `AI_MODELO_TEXTO=google/nano-banana-2.1`: todo pedido,
  inclusive os exemplos do catálogo, vai ao Nano Banana como uma instrução detalhada.

**Por quê assim.** A troca precisava ser só por variável e reversível. Em vez de criar um
terceiro modelo na configuração, o caminho `instrucao` reaproveita o `AI_MODELO_TEXTO`, que
já era "o modelo de edição por instrução". O que muda entre Kontext e Nano Banana (nome do
campo da foto, foto em lista, `resolution`, buscas desligadas, instrução curta ou longa)
ficou num **perfil por modelo** (`planos.perfil_de`). Se um dia o Nano Banana for posto
como modelo de texto no caminho especializado, ele também recebe o formato certo.

**Instrução.** O Nano Banana segue bem instruções longas, então ganhou uma instrução
própria (`instrucoes.prompt_detalhado`): diz o contexto (prévia de salão), o corte e a cor
(os exemplos do catálogo com uma descrição completa nova, `detalhe`; o texto livre como foi
escrito, com os termos técnicos em inglês), o gênero do corte, as frases de "manter",
como o cabelo deve parecer e a lista explícita do que não pode mudar (rosto, identidade,
expressão, pele, maquiagem, roupa, fundo, luz, enquadramento, e "não retocar o rosto"). A
instrução curta do Kontext não mudou.

**Privacidade.** Com o Nano Banana a foto passa pela Replicate e pelo Google. Publiquei o
**termo 1.2** (cliente e profissional) e reescrevi os textos do app. O contrato entre a
Replicate e o Google não é público. Por decisão sua, os textos tratam como possível o pior
caso documentado: o Google usar as imagens para melhorar e treinar os modelos dele, com
revisão humana. O 1.2 também corrige o que o 1.1 dizia sobre o que é enviado: desde a
migration do gênero vão três escolhas (corte, gênero do corte e cor), não duas.

**Menores de 18 anos.** Nenhuma política do Google ou da Replicate encontrada proíbe editar
o cabelo de um menor com consentimento do responsável e sem conteúdo sexual. **Não
bloqueei** esses clientes. O risco que fica: o filtro "Child" do Google pode recusar
algumas fotos; isso aparece na tela como bloqueio do filtro de segurança (detalhes em
`docs/NANO_BANANA.md`, seção 5).

**Outras decisões**

- `AI_TIMEOUT_S` passou de 60 para 120 s no padrão do código (o compose de produção já
  usava 120). `SIMULACAO_EXPIRA_MIN` ficou em 5 min, e a configuração agora se recusa a
  subir se a expiração não passar do tempo limite.
- A foto já saía sem EXIF (a validação regrava o JPEG). Agora o provedor confere de novo no
  ponto em que a foto sai do sistema e regrava se encontrar EXIF.
- As falhas do Nano Banana caem nos códigos que a tela `simulacao/indisponivel` já explica:
  recusa do Google → `conteudo_bloqueado` (passei a reconhecer também "blocked" e
  "prohibited" no motivo); erro do Google repassado → `falha_na_geracao`; resposta sem
  imagem → `resposta_invalida`; parâmetro recusado → `entrada_recusada`; tempo esgotado →
  `timeout`; schema sem `image_input` → `modelo_incompativel`, antes de gastar.
- Ao subir, a API compara o termo vigente com o modelo em uso e registra
  `TERMO E MODELO NÃO BATEM` no log se um citar o Google e o outro não.
- `simulacoes.modelo_ia` registra `google/nano-banana-2.1`, e `instrucao_ia`, a instrução
  enviada. O diagnóstico (`python -m app.diagnostico_ia`) e o `/api/v1/saude` (fora de
  produção) mostram o caminho em vigor.

**Defeito antigo encontrado nos testes.** `test_casos_criticos::test_3_...` devolvia a
vigência do termo ao "1.0" fixo, e desde o 1.1 deixava os testes seguintes com o termo
errado em vigor. Três testes só passavam por causa disso (`test_clientes`,
`test_imutabilidade` e os dois de volta de migration em `test_personalizacao_api`). Corrigi
os quatro para ler a versão vigente do banco.

## 2. Arquivos

**Criados**

| Arquivo | O que é |
|---|---|
| `docs/NANO_BANANA.md` | pesquisa (schema, envio, preço, tempo, dados, políticas, textos), com fontes e datas, e o guia do teste de qualidade |
| `backend/migrations/versions/a9e4c2b7d158_termo_1_2_replicate_e_google.py` | termo 1.2 do cliente e do profissional |
| `backend/scripts/comparar_simulacoes.py` | ferramenta de comparação de qualidade |
| `backend/scripts/pedidos_exemplo.json` | 6 pedidos de exemplo |
| `backend/tests/test_nano_banana.py` | 38 testes do caminho novo |
| `backend/tests/test_termo_1_2.py` | 7 testes do termo 1.2 e do aviso de termo × modelo |
| `backend/tests/test_comparar_simulacoes.py` | 4 testes do script |
| `RELATORIO_NANO_BANANA.md` | este relatório |

**Alterados**

| Arquivo | O que mudou |
|---|---|
| `backend/app/core/config.py` | `AI_ESTRATEGIA`, `AI_RESOLUCAO`, `AI_TIMEOUT_S` 120, validações |
| `backend/app/services/ai/planos.py` | caminho `instrucao`, `Perfil`, `Modo.instrucao`, foto em lista |
| `backend/app/services/ai/instrucoes.py` | `prompt_detalhado` |
| `backend/app/services/ai/replicate.py` | configuração explícita (para o script), schema só do modelo usado, EXIF, sinais de bloqueio |
| `backend/app/services/ai/pedido.py`, `backend/app/services/catalogo.py` | descrição completa (`detalhe`) de cada exemplo |
| `backend/app/main.py` | log de início, `/saude`, aviso de termo × modelo |
| `backend/app/diagnostico_ia.py` | confere o caminho em vigor e as buscas desligadas |
| `backend/tests/mock_provedor_ia.py` | schema do Nano Banana (cópia do publicado) e cenários do Google |
| `backend/tests/test_casos_criticos.py`, `test_clientes.py`, `test_imutabilidade.py`, `test_personalizacao_api.py` | defeito da vigência do termo (acima) |
| `backend/tests/conftest.py` | fixa a configuração de IA dos testes, que vazava do `.env` local |
| `backend/.gitignore` | `resultados/` (fotos de pessoas reais do teste) |
| `espelho/src/data/servicoExterno.ts` | `USO_DE_DADOS` e `RESUMO_ENVIO` com a Replicate e o Google |
| `espelho/app/privacidade.tsx`, `espelho/app/responsabilidades.tsx` | títulos e texto da ciência |
| `espelho/e2e/fluxo-completo.mjs`, `espelho/e2e/README.md` | o teste aceita o termo que nomeia as empresas |
| `docker-compose.yml`, `backend/docker-compose.yml`, `.env.example`, `backend/.env.example` | variáveis novas |
| `DEPLOY.md` (seção 12 nova), `README.md`, `backend/README.md`, `docs/DOCUMENTACAO.md`, `docs/DOCUMENTACAO-BACKEND.md` | documentação |

`docs/historico/` e `RELATORIO_REVISAO_E_DEPLOY.md` (registro de uma revisão passada) não
foram reescritos.

## 3. Fontes

Todas consultadas em **2026-11-05**. As citações estão em `docs/NANO_BANANA.md`.

| Fonte | Para quê |
|---|---|
| `GET https://api.replicate.com/v1/models/google/nano-banana-2.1` (e `/readme`, `/examples`) | schema, versão, tempos dos exemplos, dono e código-fonte |
| <https://replicate.com/google/nano-banana-2.1>, <https://replicate.com/black-forest-labs/flux-kontext-pro>, <https://replicate.com/flux-kontext-apps/change-haircut> | preço por imagem (`billingConfig` da página) |
| <https://replicate.com/terms> ("Last Update: April 1, 2026") | licença sobre os dados, modelos de terceiros, usos proibidos |
| <https://replicate.com/privacy> ("Last Updated: April 1, 2026") | papel de processador, backups |
| <https://replicate.com/docs/topics/predictions/data-retention> | remoção em 1 hora |
| <https://replicate.com/docs/topics/predictions/input-files>, <https://replicate.com/docs/reference/http> | envio de arquivos, data URI, rotas de exclusão |
| <https://github.com/replicate/cog-google-proxy> | **404** na data da consulta |
| <https://ai.google.dev/gemini-api/terms> ("Effective March 23, 2026") | uso do conteúdo em serviço pago e gratuito, idade, países |
| <https://ai.google.dev/gemini-api/docs/logs-policy>, <https://ai.google.dev/gemini-api/docs/usage-policies> | retenção de registros (55 dias), monitoramento de abuso |
| <https://cloud.google.com/vertex-ai/generative-ai/docs/data-governance> | regime da Vertex AI, caso seja ela |
| <https://ai.google.dev/gemini-api/docs/image-generation> | SynthID, pessoas na busca |
| <https://policies.google.com/terms/generative-ai/use-policy> ("Last Modified: December 17, 2024") | usos proibidos |
| <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/gemini-image-responsible-ai> | filtro "Child" |

## 4. Variáveis de ambiente

**Ativar o Nano Banana** (no `.env` do servidor):

```
AI_PROVIDER=replicate
AI_ESTRATEGIA=instrucao
AI_MODELO_TEXTO=google/nano-banana-2.1
AI_RESOLUCAO=1K
```

**Voltar ao caminho atual:**

```
AI_ESTRATEGIA=especializado
AI_MODELO_TEXTO=black-forest-labs/flux-kontext-pro
```

`AI_MODELO`, `AI_TIMEOUT_S` (120) e `SIMULACAO_EXPIRA_MIN` (5) podem ficar como estão. A
volta do **modelo** é só isso; a do **termo**, não (seção 7).

## 5. O que muda para quem usa

- **Clientes que aceitaram o termo 1.1 (ou anterior):** passam a aparecer como "Aceito em
  versão anterior". A próxima simulação é bloqueada até o profissional apresentar o 1.2 e
  o cliente decidir de novo. É o efeito desejado: o destino da foto mudou e o cliente
  precisa saber antes da próxima foto. Recusas e cancelamentos continuam como estão.
- **Profissionais:** a ciência das responsabilidades também foi para a 1.2; cada conta
  precisa reconhecê-la de novo.
- **Quando isso acontece:** no deploy desta versão, porque o serviço `migrar` aplica a
  migration do termo a cada subida. Por isso o deploy e a troca das variáveis precisam ser
  feitos juntos (`DEPLOY.md`, seção 12).
- **Textos do app:** no site, mudam com o deploy (`docker compose up -d --build`). No
  Android, só com um APK novo (`npx eas-cli@25.2.0 build --platform android --profile apk`).
  Até lá, quem usa o APK antigo vê os textos antigos de privacidade. O termo, que vem do
  servidor, já aparece na versão 1.2 em qualquer aparelho.

## 6. Como rodar o teste de qualidade

1. Na pasta `backend`, confira que o `.env` tem a `AI_API_KEY` que você já usa.
2. Separe, numa pasta **fora do repositório**, de 2 a 4 fotos de adultos que autorizaram o
   uso, de frente e com boa luz.
3. Ensaio, sem nenhuma chamada (PowerShell):

   ```powershell
   cd D:\downloads\salaoemdia\salao-em-dia\backend
   .venv\Scripts\python scripts\comparar_simulacoes.py --fotos C:\caminho\das\fotos --pedidos scripts\pedidos_exemplo.json --estrategias nano,atual
   ```

   Ele lista as fotos aceitas pela validação, quantas chamadas fará, o custo estimado e a
   instrução de cada pedido. Com 3 fotos são 36 chamadas, cerca de US$ 1,33.
4. Se estiver de acordo, repita o mesmo comando com `--confirmar-custo` no fim.
5. Abra no navegador o `comparacao.html` da pasta que ele indicar
   (`backend\resultados\comparacao-AAAAMMDD-HHMM\`) e dê as notas de 1 a 5 de cada imagem.
   "Exportar notas (CSV)" baixa as notas; o `resultado.csv` da mesma pasta tem tempos,
   falhas e a instrução de cada geração.
6. Opcional: `--resolucao 2K` para comparar a resolução maior (US$ 0,0504 por imagem).

Se gostar do resultado: faça o commit e o deploy desta branch com as variáveis da seção 4
(passo a passo em `DEPLOY.md`, seção 12) e gere um APK novo.

## 7. Pendências e riscos

- **Contrato entre Replicate e Google: desconhecido.** Não se sabe se a Replicate usa a
  Gemini API paga, a gratuita ou a Vertex AI. Os textos tratam o uso para treino como
  possível. Se a Replicate confirmar por escrito que usa um serviço pago (ou a Vertex),
  dá para publicar um termo mais preciso.
- **Foto em lista como data URI: confirmado no uso.** A documentação não diz, mas as três
  simulações reais de 2026-11-05 concluíram com a foto em data URI. Se um dia a Replicate
  passar a recusar (`entrada_recusada`), use `AI_LIMITE_DATA_URI_KB=0` (a foto passa a ir
  pela API de arquivos, que o sistema já apaga depois).
- **Tempo real com foto, em 1K: 14 a 17 s** por simulação (três medidas), contra 6 a 9 s
  no caminho anterior. Fica bem abaixo do tempo limite de 120 s.

**Decisão (2026-11-05):** depois dos testes, o Nano Banana foi escolhido para produção
pela qualidade superior das simulações.
- **Voltar ao Kontext depois de publicar o 1.2** exige um termo novo (1.3) que descreva o
  Kontext, numa migration no mesmo padrão. Não use `alembic downgrade`: ele se recusa a
  remover um termo já aceito. O aviso `TERMO E MODELO NÃO BATEM` no log acusa o
  desencontro.
- **Deploy sem ativar o Nano Banana** publica o termo 1.2 com o Kontext ainda em uso (o
  log acusa). Só faça o deploy desta branch quando for ativar.
- **Filtro "Child" do Google** pode recusar fotos de crianças e adolescentes, com
  consentimento ou não. Aparece como bloqueio do filtro de segurança.
- **A versão do modelo muda sem aviso** (a atual foi publicada no próprio dia da
  pesquisa). O servidor relê o schema e confere cada envio; rode
  `python -m app.diagnostico_ia` depois de qualquer surpresa.
- **Textos de erro do Google:** a Replicate não documenta o que repassa quando o Google
  recusa. Os sinais "blocked" e "prohibited" foram acrescentados por precaução; um texto
  não reconhecido cai em `falha_na_geracao`, que também tem mensagem na tela.
- **Teste que já falhava antes, nesta máquina** (não é regressão):
  `test_producao_e_operacao::test_testes_se_recusam_a_rodar_fora_de_um_banco_de_teste`
  (o Windows recusa o subprocesso, WinError 10106). A outra falha antiga
  (`test_saude_informa_se_a_credencial_do_provedor_existe`, causada pela `AI_API_KEY` do
  `backend/.env` local) foi corrigida: o `tests/conftest.py` passou a fixar a credencial e
  a escolha dos modelos, que antes vazavam do `.env` de quem roda a suíte (com o Nano
  Banana ligado no `.env` local, 16 testes do caminho especializado falhavam por isso).

**Verificação feita:** `pytest` com 615 testes passando e a falha acima; no app,
`npx tsc --noEmit` sem erros e `eslint` sem erros (os 18 avisos já existiam);
`e2e/fluxo-completo.mjs` sem falhas, com o termo 1.2 lido na tela (banco **local** migrado;
a produção não foi tocada); `python -m app.diagnostico_ia` contra o schema publicado nos
dois caminhos, sem custo.
