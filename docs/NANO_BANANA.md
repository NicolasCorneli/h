# Nano Banana 2.1 na simulação capilar

Pesquisa e guia de uso do modelo `google/nano-banana-2.1`, oferecido pela Replicate, como
caminho alternativo da simulação (`AI_ESTRATEGIA=instrucao`). Todas as fontes foram
consultadas em **2026-11-05**. O que não pôde ser confirmado em fonte pública está marcado
como **desconhecido**, sem suposição.

Sumário: [1. Schema](#1-schema-do-modelo) · [2. Envio da imagem](#2-envio-da-imagem) ·
[3. Preço e tempo](#3-preço-e-tempo) · [4. Caminho dos dados](#4-caminho-dos-dados) ·
[5. Políticas de uso](#5-políticas-de-uso-e-menores-de-18-anos) ·
[6. O que muda nos textos](#6-o-que-muda-nos-textos) ·
[7. Ativar e voltar](#7-ativar-e-voltar) ·
[8. Testar a qualidade](#8-testar-a-qualidade-scriptscomparar_simulacoespy)

---

## 1. Schema do modelo

Fonte: `GET https://api.replicate.com/v1/models/google/nano-banana-2.1` (API da Replicate,
leitura sem custo), versão `1cd4e9c2466ff4dfc1e30070d4a1eb4334ac19d7b9e2eed6af485765e5ac4bf5`,
criada em 2026-11-05T01:29:42Z. Conferido também por `python -m app.diagnostico_ia`.

| Campo | Tipo | Obrigatório | Opções / padrão | O que o sistema envia |
|---|---|---|---|---|
| `prompt` | string | **sim** | — | a instrução detalhada (`instrucoes.prompt_detalhado`) |
| `image_input` | lista de URI | não | padrão `[]`; "supports up to 14 images" | `[foto]` (uma) |
| `aspect_ratio` | opções | não | `match_input_image` (padrão), `1:1`, `1:4`, `1:8`, `2:3`, `3:2`, `3:4`, `4:1`, `4:3`, `4:5`, `5:4`, `8:1`, `9:16`, `16:9`, `21:9` | `match_input_image` |
| `resolution` | opções | não | `1K` (padrão), `2K`, `4K` | `AI_RESOLUCAO` (padrão `1K`) |
| `google_search` | booleano | não | `false` | `false` |
| `image_search` | booleano | não | `false` | `false` |
| `output_format` | opções | não | `jpg` (padrão), `png` | `jpg` |

Saída: uma URI (string).

- **Filtro de segurança:** o schema **não tem** campo de ajuste (diferente do
  `flux-kontext-pro`, que tem `safety_tolerance`). O filtro, se houver, é o do Google e não é
  configurável por aqui.
- **"Thinking":** o schema **não tem** campo para isso.
- **Buscas:** `google_search` ("Use Google Web Search grounding…") e `image_search` ("Use
  Google Image Search grounding to find web images… When enabled, web search is also used
  automatically") existem e são desligadas por padrão. O sistema as envia **explicitamente**
  como `false`, para não depender do padrão: a foto do cliente não pode virar consulta de
  busca na web. O diagnóstico acusa problema se um dia o campo existir e o sistema não o
  desligar.
- A versão foi publicada no próprio dia da consulta: o schema pode mudar. Por isso o
  servidor relê o schema publicado (a cada `AI_CACHE_ESQUEMA_MIN`) e confere cada envio
  contra ele antes de gastar.

Página do modelo: <https://replicate.com/google/nano-banana-2.1>. O README (mesmo
endereço, aba README, e `GET /v1/models/google/nano-banana-2.1/readme`) descreve o modelo
como "Google's fast image generation and editing model" e "the quicker and cheaper
counterpart to Nano Banana Pro"; não diz nada sobre dados, segurança ou pessoas.

## 2. Envio da imagem

Como o provedor já envia a foto ao Kontext (`services/ai/replicate.py`), e continua igual:

1. a foto é a já validada e regravada em JPEG pela validação (`validacao_foto.py`), que
   descarta o EXIF; antes de sair, `_reduzir` limita o lado maior a `AI_LADO_MAXIMO_ENVIO`
   (1536 px) e regrava de novo se ainda houver EXIF;
2. até `AI_LIMITE_DATA_URI_KB` (1024 KB) ela vai como **data URI** no corpo da predição;
   acima disso, pela API de arquivos (`POST /v1/files`), e o arquivo é apagado ao fim
   (`DELETE /v1/files/{id}`), com sucesso ou falha. Nenhum dos caminhos cria URL pública.

O que a Replicate documenta:

- "Files should be passed as HTTP URLs or data URLs." e "Use a data URL when: you have a
  small file <= 256kb … you don't need to use the file again (Replicate will not store
  it)" — <https://replicate.com/docs/reference/http> (predictions.create).
- "This is only recommended if the file is less than 1MB" (data URI) —
  <https://replicate.com/docs/topics/predictions/input-files>. As duas páginas divergem no
  limite (256 KB × 1 MB); o sistema segue o de 1 MB, como já fazia com o Kontext.
- Nenhuma das páginas diz explicitamente que campos do tipo **lista** de arquivos
  (`image_input`) aceitam data URI. **Confirmado no uso em 2026-11-05:** três simulações
  reais pelo aplicativo, com a foto em data URI dentro de `image_input`, concluíram sem
  erro. Se um dia a Replicate passar a recusar (`entrada_recusada`), a saída é
  `AI_LIMITE_DATA_URI_KB=0`, que manda toda foto pela API de arquivos.

Na Nano Banana a foto vai em `image_input` (lista com um item), não em `input_image`. Essa
diferença fica no perfil do modelo (`planos.perfil_de`).

## 3. Preço e tempo

Preço: configuração de cobrança publicada na página de cada modelo (o bloco
`billingConfig` do HTML de <https://replicate.com/google/nano-banana-2.1>,
<https://replicate.com/black-forest-labs/flux-kontext-pro> e
<https://replicate.com/flux-kontext-apps/change-haircut>). A cobrança é por imagem gerada
(`image_output_count`).

| Modelo | Preço por imagem | Tempo nos exemplos publicados |
|---|---|---|
| `google/nano-banana-2.1`, 1K | **US$ 0,0336** ("around 29 images for $1") | 9,7 s |
| `google/nano-banana-2.1`, 2K | US$ 0,0504 ("around 19 images for $1") | 18,1 s e 19,0 s |
| `google/nano-banana-2.1`, 4K | US$ 0,1134 ("around 88 images for $10") | sem exemplo |
| `black-forest-labs/flux-kontext-pro` | US$ 0,04 ("25 images for $1") | 4,4 s |
| `flux-kontext-apps/change-haircut` | US$ 0,04 ("25 images for $1") | 6,2 s |

- Os tempos são o `predict_time` dos exemplos do próprio modelo
  (`GET /v1/models/{modelo}` e `/examples`). Os do Nano Banana são de **geração a partir
  de texto, sem foto de entrada**.
- **Medido no uso (2026-11-05, 1K, com foto):** 14,0 s, 16,7 s e 16,7 s por simulação,
  do envio ao resultado gravado (`simulacoes.tempo_ms`). No caminho atual, as últimas
  medidas foram de 6,0 a 8,8 s.
- O mesmo bloco de cobrança traz também `"price": "$0.0001 per second"` (hardware "CPU") e
  um `p50price`. A página não diz se esse valor se soma ao preço por imagem; com os tempos
  acima, seria menos de US$ 0,002 por geração. **Desconhecido** se é cobrado.
- Em 1K, o Nano Banana sai mais barato que o caminho atual (US$ 0,0336 × US$ 0,04 por
  simulação) e mais lento (cerca de 10 s × 4 a 6 s).

Tempo limite: `AI_TIMEOUT_S` passou de 60 para **120 s** no padrão do código (o
`docker-compose.yml` já usava 120). Cobre a fila do provedor e um 2K com folga de mais de
seis vezes. `SIMULACAO_EXPIRA_MIN` continua em 5 min, acima dos 120 s, e a configuração
agora recusa subir se a expiração não passar do tempo limite.

## 4. Caminho dos dados

### O que se sabe do caminho

- O modelo pertence ao dono `google` na Replicate, é "oficial" (`is_official: true`) e
  aponta como código-fonte `https://github.com/replicate/cog-google-proxy` (metadados de
  `GET /v1/models/google/nano-banana-2.1`). O nome indica um proxy da Replicate para a API
  do Google. A página do repositório responde **404** (não é pública na data da consulta).
- A página da Replicate liga o modelo ao guia da Gemini API
  (<https://ai.google.dev/gemini-api/docs/image-generation>), onde o modelo aparece como
  `gemini-nano-banana-2.1` ("An update to Nano Banana 2").
- **Desconhecido:** se a Replicate chama a Gemini API ou a Vertex AI, com qual conta, e se
  essa conta é "paga" nos termos do Google. Isso decide se o Google pode usar a foto para
  treinar (abaixo). O contrato entre as duas empresas não é público.

### Replicate

| Afirmação | Fonte |
|---|---|
| "For predictions created through the API, all input parameters, output values, output files, and logs are automatically removed after an hour, by default." | <https://replicate.com/docs/topics/predictions/data-retention> |
| Data URL: "Replicate will not store it" | <https://replicate.com/docs/reference/http> |
| Não há rota da API para apagar uma predição antes disso (só `predictions.cancel`). Apagar manualmente é só pelo site, para predições feitas nele. | <https://replicate.com/docs/reference/http>, página de retenção acima |
| O cliente concede à Replicate licença sobre os dados "to the extent necessary to provide the Output, train and generate Customer Derivative Models, provide the Services under these Terms, and create and compile Resultant Data" (5.2). "Customer Derivative Model" é um modelo ajustado *pelo cliente*; "Resultant Data" é agregado e anonimizado e, pela definição, não inclui os dados do cliente. | <https://replicate.com/terms> (Terms of Service, "Last Update: April 1, 2026") |
| Modelos de terceiros: "Replicate does not control and has no liability for any Marketplace Models … or how the Marketplace Models use your Content" (2.5); "THE SERVICES UTILIZE THIRD-PARTY OFFERINGS THAT REPLICATE HAS NO CONTROL OVER" (8.3). | <https://replicate.com/terms> |
| Quem envia declara ter "all rights, consents, and permissions necessary" (3.1) e direitos "of publicity, privacy or confidentiality" (7.2). | <https://replicate.com/terms> |
| A Política de Privacidade não trata de entradas e saídas de modelos (fala de dados de conta); diz que a Replicate atua como "processor" e que cópias residuais podem ficar em backup "for a limited period". | <https://replicate.com/privacy> ("Last Updated: April 1, 2026") |

Resumo: a Replicate não declara usar as fotos para treinar modelos próprios e declara
apagar entradas e saídas da API em cerca de uma hora. Sobre o que o modelo de terceiro faz,
ela remete aos termos dele.

### Google

| Afirmação | Fonte |
|---|---|
| Serviços **gratuitos**: "Google uses the content you submit to the Services and any generated responses to provide, improve, and develop" os produtos; "human reviewers may read, annotate, and process your API input and output"; "Do not submit sensitive, confidential, or personal information to the Unpaid Services." | Gemini API Additional Terms, <https://ai.google.dev/gemini-api/terms> (redireciona para <https://aistudio.google.com/docs/terms>), "Effective March 23, 2026" |
| Serviços **pagos**: "Google doesn't use your prompts (including associated system instructions, cached content, and files such as images …) to improve our products"; registra prompts e respostas "for a limited period of time, solely for detecting and preventing violations of the" Prohibited Use Policy; os dados "may be stored transiently or cached in any country in which Google or its agents maintain facilities". | mesma página |
| Pago só "when accessing the API through a Cloud Project associated with an active billing account". | mesma página |
| Registros de uso: retidos "for a default maximum period of 55 days". | <https://ai.google.dev/gemini-api/docs/logs-policy> (→ <https://aistudio.google.com/docs/logs-policy>) |
| Monitoramento de abuso: sistemas automáticos examinam o uso da API; prompts e saídas retidos por 55 dias para aplicação da política. | <https://ai.google.dev/gemini-api/docs/usage-policies> (→ <https://aistudio.google.com/docs/usage-policies>) |
| Se o caminho for a Vertex AI: "Google won't use your data to train or fine-tune any AI/ML models without your prior permission or instruction"; "Google may log prompts to detect potential abuse". | <https://cloud.google.com/vertex-ai/generative-ai/docs/data-governance> |
| Marca d'água: "All generated images include a SynthID watermark". | <https://ai.google.dev/gemini-api/docs/image-generation> (→ <https://aistudio.google.com/docs/image-generation>) |

**Desconhecido:** qual desses regimes se aplica às fotos que chegam pela Replicate (pago
ou gratuito; Gemini API ou Vertex AI). Por decisão do responsável pelo projeto, os textos
tratam como **possível** o pior caso documentado: o Google usar as imagens para melhorar e
treinar os modelos, com revisão humana. É verdadeiro em qualquer dos cenários.

## 5. Políticas de uso e menores de 18 anos

| Afirmação | Fonte |
|---|---|
| Proíbe conteúdo que "Relates to child sexual abuse or exploitation" (1.1), "Facilitates non-consensual intimate imagery" (1.3), uso de "personal data or biometrics without legally-required consent" (1.6) e "Impersonating an individual … without explicit disclosure, in order to deceive" (4.2). Nada sobre edição consentida, não sexual, da aparência de uma pessoa real. | Generative AI Prohibited Use Policy, <https://policies.google.com/terms/generative-ai/use-policy> ("Last Modified: December 17, 2024") |
| Para usar a API é preciso ter 18 anos, e não se pode usá-la num app "directed towards or is likely to be accessed by individuals under the age of 18". | Gemini API Additional Terms (acima) |
| Os filtros de imagem do Gemini têm uma categoria "Child": "Detects child content that isn't allowed due to the API request settings or allowlisting". As páginas não dizem o que dispara o filtro numa edição comum. | <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/gemini-image-responsible-ai> |
| Na geração com busca: "Grounding with Google Search do[es] not support using real-world images of people from web search" (não se aplica: as buscas vão desligadas). | página de geração de imagens (acima) |
| Replicate proíbe "exploitation or harm to children" e "impersonating another individual without consent". | <https://replicate.com/terms> (2.7) |

**Conclusão e decisão.** Nenhuma política encontrada proíbe ou restringe editar o cabelo
de uma pessoa real, inclusive menor de 18 anos, com consentimento do responsável e sem
conteúdo sexual. Por isso o servidor **não bloqueia** a simulação de clientes menores
quando o Nano Banana está ativo. O app já exige o consentimento do responsável legal (LGPD,
art. 14). Os usuários do app são profissionais adultos: o app não é dirigido a menores, que
é o que os termos do Google restringem.

Risco que fica: o filtro "Child" do Google pode recusar algumas fotos de crianças e
adolescentes. Isso chega à tela como "O filtro de segurança recusou o pedido"
(`conteudo_bloqueado`). O teste da seção 8 deve incluir só adultos (a regra do script),
então esse comportamento só aparece em uso real.

## 6. O que muda nos textos

| Onde | Antes (termo 1.1 e app) | Agora (termo 1.2 e app) |
|---|---|---|
| Para onde vai a foto | "um serviço de inteligência artificial de outra empresa" | a Replicate, que envia ao Google, dono do modelo |
| O que vai | "a sua foto e as duas escolhas do atendimento — o corte e a cor" (o gênero do corte já ia desde a migration `d2f6a8c31e94`) | a foto (sem EXIF) e o corte, o gênero do corte e a cor |
| O que a empresa pode fazer | "os termos de uso dessa empresa permitem … treinar" | a Replicate declara apagar em cerca de 1 hora; o Google guarda por um tempo para fiscalizar abuso e, conforme o contrato (não público), pode usar para melhorar e treinar, com revisão humana |
| Onde é processada | não dizia | pode ser processada fora do Brasil |
| Marca na imagem | não dizia | marca invisível do Google (SynthID) indicando IA |

Arquivos: `backend/migrations/versions/a9e4c2b7d158_termo_1_2_replicate_e_google.py`
(termos do cliente e do profissional), `espelho/src/data/servicoExterno.ts`,
`espelho/app/privacidade.tsx`, `espelho/app/responsabilidades.tsx`.

## 7. Ativar e voltar

Ativar (no `.env` do servidor, junto com o deploy desta versão, que publica o termo 1.2):

```
AI_PROVIDER=replicate
AI_ESTRATEGIA=instrucao
AI_MODELO_TEXTO=google/nano-banana-2.1
AI_RESOLUCAO=1K
```

Voltar ao caminho original:

```
AI_ESTRATEGIA=especializado
AI_MODELO_TEXTO=black-forest-labs/flux-kontext-pro
```

Voltar o modelo é só isso. O termo, não: o 1.2 diz que a foto vai ao Google, e o servidor
avisa no log (`TERMO E MODELO NÃO BATEM`) se o caminho em uso não usar o Google. Antes de
voltar de vez, publique uma versão do termo que descreva o Kontext. Passo a passo em
`DEPLOY.md`, seção 12.

## 8. Testar a qualidade (`scripts/comparar_simulacoes.py`)

O script gera simulações com o **mesmo código da produção**: a foto passa por
`validar_e_normalizar` (a que for recusada fica de fora), o pedido por `interpretar`, e a
geração pelo `ProvedorReplicate`, com a mesma montagem de parâmetros e a mesma instrução.

1. Na pasta `backend`, confira que o `.env` tem a `AI_API_KEY` (a mesma de produção serve).
2. Ponha numa pasta **fora do repositório** as fotos de teste: só de adultos que
   autorizaram o uso, de frente, com boa luz (as mesmas regras da câmera do app).
3. Ensaio, sem nenhuma chamada:

   ```powershell
   cd backend
   .venv\Scripts\python scripts\comparar_simulacoes.py --fotos C:\caminho\das\fotos --pedidos scripts\pedidos_exemplo.json --estrategias nano,atual
   ```

   Ele lista as fotos aprovadas, quantas chamadas fará, o custo estimado e a instrução de
   cada pedido. Com 3 fotos, os 6 pedidos do exemplo e os dois caminhos são 36 chamadas,
   cerca de US$ 1,33.
4. Para valer, repita com `--confirmar-custo`. Opções: `--resolucao 2K` (só no Nano),
   `--saida PASTA`, `--maximo N` (teto de chamadas, padrão 60).
5. Abra `backend/resultados/comparacao-AAAAMMDD-HHMM/comparacao.html` no navegador. Para
   cada foto e pedido aparecem o original e as simulações, com notas de 1 a 5 para
   naturalidade, fidelidade da cor e preservação do rosto, e um campo de observação. As
   notas ficam salvas no navegador; "Exportar notas (CSV)" baixa um arquivo com elas.
6. `resultado.csv`, na mesma pasta, traz por geração: foto, pedido, caminho, modelo, tempo,
   sucesso ou código de erro, e a instrução enviada.

A pasta `backend/resultados/` está no `.gitignore`: as fotos são de pessoas reais e não
vão para o repositório.

Arquivo de pedidos (`scripts/pedidos_exemplo.json`): lista de objetos com `id`,
`descricao` (opcional), `corte`, `cor`, `manter_corte`, `manter_cor` e `genero` (`female`,
`male` ou `none`). Valem as mesmas regras da tela: corte vazio exige `manter_corte`, cor
vazia exige `manter_cor`, e os dois "manter" juntos são recusados.
