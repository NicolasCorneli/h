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
[8. Testar a qualidade](#8-testar-a-qualidade-scriptscomparar_simulacoespy) ·
[9. Preservação do cabelo natural](#9-preservação-do-cabelo-natural-2026-11-07)

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

## 9. Preservação do cabelo natural (2026-11-07)

### O problema

Numa rodada de testes, uma pessoa relatou: "Durante a simulação, a IA deixou meus cachos
mais abertos. Além disso, aumentou o comprimento do meu cabelo." A primeira instrução
(`prompt_detalhado_original`, guardada para comparação) pedia para mudar "só o cabelo" e
listava o que preservar fora dele (rosto, roupa, fundo), mas nada dizia sobre o próprio
cabelo: curvatura, tamanho do cacho, densidade, volume e comprimento ficavam a critério do
modelo.

### Pesquisa complementar

Fontes consultadas em 2026-11-07, além das das seções 1 a 5:

| Afirmação | Fonte |
|---|---|
| O schema na Replicate continua o mesmo (versão `1cd4e9c2…`): `prompt`, `image_input` (até 14), `aspect_ratio`, `resolution`, `google_search`, `image_search`, `output_format`. Nenhum campo de textura, máscara, semente ou "thinking". | `GET https://api.replicate.com/v1/models/google/nano-banana-2.1` |
| "The `seed`, `topK`, `logprobs`, `temperature`, and `topP` parameters aren't supported for Nano Banana 2.1. Setting any of these parameters returns an API error." O "thinking" existe no Google, mas a Replicate não o expõe. | <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/nano-banana-2-1> |
| Edição localizada ("semantic masking"): "Using the provided image, change only the [specific element] to [new element/description]. Keep everything else in the image exactly the same, preserving the original style, lighting, and composition." A máscara é feita só pela instrução. | <https://ai.google.dev/gemini-api/docs/image-generation> (redireciona para aistudio.google.com/docs/image-generation) |
| "Be specific: More details give you more control." / "Provide context and intent" / "Use step-by-step instructions: For complex scenes, split your request into steps." / "Describe what you want, not what you don't" | <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/gemini-image-generation-best-practices> |
| Várias imagens: os exemplos nomeiam cada uma pela posição e dizem o papel dela na frase ("Take the blue floral dress from the first image and let the woman from the second image wear it"). Para o 2.1: "Up to 4 images of characters to maintain character consistency". | aistudio.google.com/docs/image-generation |
| Limitações declaradas: "Character consistency is not always perfect between input images and generated output image"; "Partial instruction following and ink persistence in masked/doodle based editing"; "rare instances of persistent subject pose". Nada específico sobre cabelo, textura ou detalhes finos. | <https://deepmind.google/models/model-cards/nano-banana-2-1/> (publicado em 6 de outubro de 2026) |

**Conclusão.** Na Replicate não existe parâmetro que controle textura, curvatura ou
comprimento: a única alavanca é a instrução (e, no máximo, imagens de referência). O que a
documentação do Google recomenda e o projeto adotou: abrir com o padrão de máscara
semântica, ser específico, dar o contexto (prévia de salão) e dizer o papel de cada imagem.
A recomendação de preferir descrições positivas é seguida em parte: a instrução descreve o
que manter e depois lista os desvios conhecidos ("do not loosen, open up… curls"), porque o
desvio relatado é justamente um desses, e o próprio Google usa "Do not change" nos exemplos
de edição.

### O que mudou na instrução (`instrucoes.prompt_detalhado`)

A instrução passou a ter quatro prioridades, nesta ordem:

1. **a pessoa**: identidade, rosto, expressão, pele, posição da cabeça, roupa, fundo, luz,
   enquadramento; sem retoque no rosto;
2. **o cabelo natural**: a mesma curvatura, o mesmo tamanho e aperto de cada onda, cacho ou
   mola, a mesma densidade, volume, frizz e definição; "não abrir, esticar, relaxar ou
   alisar", "não deixar mais uniforme ou mais definido"; e o comprimento (abaixo);
3. **a mudança pedida**: o corte (com a descrição completa do catálogo) e a cor, cada um
   só quando foi pedido; o corte é "moldado com a textura da própria cliente"; a cor é
   aplicada "sem mudar a curvatura nem a textura";
4. **a naturalidade**: foto sem edição aparente, fios individuais, luz coerente, sem
   aparência de peruca.

Regras que dependem do pedido, para nenhuma frase contradizer outra:

| Situação | O que a instrução diz |
|---|---|
| Sem corte pedido | mantém o corte e o comprimento exatamente ("não pode ficar mais longo nem mais curto") |
| Com corte pedido | muda o comprimento só o que o corte exige; nunca deixa mais longo que na foto, a não ser que o corte peça explicitamente |
| Sempre | comprimento lido como o cabelo cai na foto, com o encolhimento natural, não esticado; volume não vira comprimento |
| Corte que pede outra textura (escova, permanente) | é a única exceção à preservação da curvatura |
| Curvatura informada | entra como apoio à leitura da foto ("a foto continua sendo a referência principal") |
| Curvatura não informada | a foto é a única referência |

Também foram trocadas, nas descrições completas do catálogo, palavras que indicavam
textura onde só se queria descrever o corte ("straight, blunt base" e "smooth, polished
lines" viraram "blunt, even perimeter" e "defined lines"): num cabelo 3C elas podiam ser
lidas como pedido de alisar.

A instrução curta do Kontext (`prompt_edicao`) não mudou, nem o caminho especializado.

### Curvatura informada (substituída em 2026-11-10, ver seção 10)

A etapa "Estilo e cor" ganhou a pergunta opcional **"Cabelo natural"**: liso, ondulado,
cacheado ou crespo e, se a pessoa souber, o tipo de 1A a 4C, com uma descrição de salão
("3C, cachos fechados, da largura de um lápis"). Começa em "Não sei informar".

Decisão de implementar, e seus limites:

- **por quê**: é a única informação sobre a textura que cabe no que o modelo aceita (texto);
  o tamanho do cacho, que o modelo tende a perder, é exatamente o que diferencia 3A de 3C;
- **como**: vira uma frase da instrução, não um parâmetro (o schema não tem nenhum); a foto
  continua sendo a referência principal, então uma escolha errada não se sobrepõe ao que a
  foto mostra;
- **o que não faz**: não infere nada sobre a pessoa, não fica no cadastro do cliente, e não
  muda o caminho especializado (Kontext), que não tem onde usá-la;
- **persistência**: coluna `simulacoes.curvatura` (opcional, conferida por restrição), pela
  migration `b5c8e1d3a742`. Necessária porque a geração roda em segundo plano e remonta o
  pedido a partir da simulação gravada, como o gênero do corte;
- **eficácia**: não medida ainda. Fica para o experimento abaixo (estratégia
  `nano-curvatura`).

### Estratégias avaliadas e o experimento

`scripts/comparar_simulacoes.py` ganhou estratégias que mudam uma coisa de cada vez:

| Estratégia | O que muda | Situação |
|---|---|---|
| `atual` | Kontext (caminho especializado) | implementada, referência |
| `nano-original` | instrução de 2026-11-05 | implementada, para comparar |
| `nano` | instrução por prioridades (a da produção) | **implementada e em uso** |
| `nano-curvatura` | a anterior com a curvatura informada | removida em 2026-11-10 com a pergunta (seção 10) |
| `nano-textura` | `nano` com um close da textura natural como segunda imagem | só no experimento; hipótese |
| `nano-referencia` | `nano` com a foto do corte desejado como segunda imagem | só no experimento; hipótese |
| `nano-etapas` | corte numa chamada, cor sobre o resultado em outra | só no experimento; hipótese, custa o dobro |

As referências (textura e corte) não chegaram ao aplicativo. A foto de referência do corte
saiu do escopo numa decisão anterior (migration `c6a2f9d41b87`: escopo e custo) e exigiria
tratar a imagem de uma terceira pessoa; a instrução já diz que a pessoa da referência "não
é a cliente". Só vale trazê-las de volta se o experimento mostrar ganho claro.

Critérios de avaliação na página gerada (`comparacao.html`), de 1 a 5: identidade,
curvatura, textura, comprimento, volume, corte, cor e naturalidade.

**Resultados experimentais: ainda não há.** As chamadas são pagas e precisam de fotos
autorizadas de pessoas com cabelo liso, ondulado, cacheado e crespo, que o projeto ainda
não tem. Nenhuma afirmação de melhora de qualidade é feita aqui: a instrução nova é uma
hipótese fundamentada, a confirmar.

Protocolo para reproduzir (na pasta `backend`):

1. Reúna de 4 a 8 fotos de adultos que autorizaram o uso, de frente e com boa luz, cobrindo
   liso, ondulado, cacheado e crespo, com comprimentos e volumes variados. Para
   `nano-textura`, junte um close do cabelo (`maria.textura.jpg`).
2. Ensaio, sem custo:

   ```
   .venv\Scripts\python scripts\comparar_simulacoes.py --fotos C:\fotos-cacheados --pedidos scripts\pedidos_cacheados.json --estrategias nano-original,nano,nano-textura
   ```

   Com 4 fotos e os 6 pedidos de `pedidos_cacheados.json`: 72 chamadas, cerca de US$ 2,42
   em 1K. O teto padrão é 60 chamadas: use `--maximo 80`, ou menos fotos.
3. Repita com `--confirmar-custo`, abra `comparacao.html`, dê as notas e exporte o CSV.
4. Numa segunda rodada, inclua `nano-textura`, `nano-etapas` e `atual` nos pedidos em que a
   primeira mostrar diferença.

Parâmetros fixos para a comparação ser justa: as mesmas fotos (já validadas e sem EXIF), os
mesmos pedidos, `--resolucao 1K`, o mesmo `AI_INSTRUCAO_IDIOMA` (`pt_com_termos`). O
resultado não é determinístico (o modelo não aceita semente): repetir a mesma combinação
duas vezes mostra a variação natural, e uma diferença só conta se aparecer nas duas.

Idioma: a instrução continua em inglês, com a descrição livre do profissional em português
ao lado dos termos técnicos em inglês (`AI_INSTRUCAO_IDIOMA=pt_com_termos`). O modelo é
multilíngue, mas o ganho de trocar de idioma não foi medido; a variável continua disponível
(`pt`) para um teste de comparação.

### Resolução, tempo e custo

A resolução continua em 1K (US$ 0,0336 por imagem). 2K custa 50% a mais, e a documentação
não indica ganho de fidelidade de textura, só de nitidez: não há evidência que justifique
subir. O tempo medido em 2026-11-05 (14 a 17 s em 1K, com foto) é a referência. A instrução
nova é mais longa, mas o texto de entrada não muda o preço por imagem, e o tempo real fica
registrado em `simulacoes.tempo_ms` e no CSV do experimento.

### Limitações que continuam

- nenhum parâmetro controla textura ou comprimento: tudo depende de o modelo seguir a
  instrução, e o próprio Google declara "partial instruction following";
- o resultado varia entre execuções (sem semente);
- (até 2026-11-10) a curvatura informada podia contradizer a foto; a pergunta foi
  substituída pelo tipo de cabelo desejado (seção 10);
- o filtro "Child" do Google pode recusar fotos de crianças (seção 5).

## 10. Tipo de cabelo desejado, gênero neutro e descrições livres (2026-11-10)

### O que mudou no pedido

| Antes | Agora |
|---|---|
| "Cabelo natural (opcional)": a curvatura que a pessoa **tem**, só um apoio para o modelo ler a foto | "Qual tipo de cabelo você deseja na simulação?": o tipo que a pessoa **quer**, aplicado na imagem |
| "Não sei informar" (ausência de informação) | "Manter meu tipo de cabelo atual" (já vem marcado): instrução **positiva** de preservar a textura da foto |
| Gênero "Não especificar" (sem frase na instrução) | "Neutro": corte sem gênero definido, com frase própria na instrução |
| Manter corte e cor ao mesmo tempo era recusado | Manter corte e cor e mudar só o tipo de cabelo é um pedido válido |
| Texto escrito antes de marcar "manter" era ignorado em silêncio | A tela mostra o texto e pede uma decisão: usar a descrição ou apagá-la |

Contrato e banco:

- o aplicativo manda `textura` (formulário do envio e JSON da prévia do plano): uma das 4
  categorias ou um dos 12 tipos de 1A a 4C, ou vazio (manter). O servidor valida
  (`pedido.validar_textura`, código `textura_invalida`) e grava em `simulacoes.textura`
  (migration `c7d3f9a1e64b`, só acrescenta);
- a coluna antiga `simulacoes.curvatura` fica com os valores já gravados e deixa de ser
  preenchida; o campo `curvatura` que um APK antigo ainda manda é ignorado. Sem `textura`,
  a textura da foto é mantida, que era o que aquele pedido queria;
- o tipo de cabelo não é parâmetro de nenhum modelo: o schema do Nano Banana 2.1 na
  Replicate não tem campo de textura (seção 9). Ele vira frase da instrução. Nada como
  `hair_texture`, `curl_pattern`, `seed` ou `temperature` foi acrescentado ao envio, e a
  conferência do schema publicado antes de cada geração continua valendo.

### A instrução por prioridades, com a textura no lugar do "cabelo natural"

1. **A pessoa.** Como antes, com a abertura "This is an edit of an existing photograph, not
   a new image" e a lista do que não muda (identidade, idade aparente, formato da cabeça,
   expressão, pele, roupa, fundo, luz, enquadramento; sem retoque no rosto).
2. **A textura.**
   - *Manter* (padrão): "keep the client's natural hair texture exactly as in the photo",
     seguida da descrição do que preservar (o mesmo padrão de onda, cacho ou mola, o
     tamanho, a densidade, o volume) e dos desvios que esse tipo de modelo comete (abrir,
     esticar, alisar). Termina com "This takes priority over any texture mentioned in the
     descriptions below": um corte descrito como "liso e alinhado" num cabelo 3C não alisa
     o cabelo. A exceção da versão anterior ("a não ser que o corte peça outra textura")
     saiu: quem quer outra textura agora escolhe o tipo.
   - *Trocar*: "change the hair texture to {tipo}. Apply this texture to all of the hair,
     with a realistic, consistent pattern and the volume and natural shrinkage this texture
     has, and keep the same hair density as in the photo", e a mesma frase de prioridade.
3. **A mudança pedida.** O corte e a cor, cada um só quando pedido:
   - a descrição livre vai **inteira**, entre aspas, como foi escrita, com os termos técnicos
     em inglês ao lado (`glossario.termos_em_ingles`). Nada é resumido nem trocado por um
     nome de corte;
   - descrição livre de corte: "Follow every detail of this description, such as length,
     fringe, layers, volume, ends and sides, and keep any part it says to keep. Do not add
     details that were not asked for";
   - descrição livre de cor: "Follow every detail of this description, including where each
     color goes (roots, lengths, ends, strands around the face, the under-layer or only some
     highlights) and any part it says to keep. Keep localized changes local: do not spread
     them to the whole hair, and do not add colors that were not asked for." É o que impede
     "mechas só nas pontas" de virar mechas no cabelo todo;
   - o gênero do corte novo: feminino, masculino ou "It is a gender-neutral haircut, not
     styled as typically feminine or masculine";
   - o corte é moldado "with the chosen texture" ou "with the client's own hair texture";
   - o comprimento, por caso: sem corte e sem troca de textura, "exatamente o mesmo"; sem
     corte e com troca de textura, "não é cortado nem alongado", e o encolhimento de uma
     textura mais fechada é esperado; com corte, muda só o que o corte exige;
   - a cor "não muda o padrão nem a textura definidos na prioridade 2".
4. **A naturalidade.** Fios individuais, linha do cabelo natural, cor com profundidade, luz
   da foto original; sem aspecto de peruca, plástico ou pintura.

A instrução continua sem prometer o impossível: pede preservação e fidelidade, mas o modelo
pode não obedecer em tudo (seção 9, "partial instruction following").

Cada tipo vai com a descrição de salão em inglês, com o tamanho do cacho comparado a objetos
comuns, que é o que diferencia 3A de 3C (`instrucoes.TEXTURA_EM_INGLES`):

| Tipo | Na tela | Na instrução |
|---|---|---|
| 1A | Muito fino, sem volume | very fine, completely straight and flat, with little volume |
| 1B | Liso com mais corpo | straight, with a little more body and volume |
| 1C | Grosso, quase ondulado | straight but thicker and coarser, with a slight tendency to bend |
| 2A | Ondas leves e abertas | loose, open, gentle waves |
| 2B | Ondas definidas em S | well-defined S-shaped waves |
| 2C | Ondas fortes, quase cachos | deep, voluminous S-shaped waves, close to curls |
| 3A | Cachos largos e soltos | large, loose spiral curls, about as wide as a thick marker |
| 3B | Cachos médios e definidos | medium, well-defined springy curls, about as wide as a finger |
| 3C | Cachos pequenos e fechados | small, tight, voluminous corkscrew curls, about as wide as a pencil |
| 4A | Molas pequenas e definidas | small, tightly wound, defined S-shaped coils |
| 4B | Zigue-zague em Z | a Z-shaped zigzag pattern with sharp angles and little curl definition |
| 4C | Bem fechado, encolhe muito | very tight zigzag coils with very little definition, strong shrinkage |

Revisão da nomenclatura sugerida no pedido: o 1C deixa claro que ainda é liso ("quase
ondulado", e não ondulado); o 4A passa a "molas", porque é o primeiro tipo crespo, e não um
cacho do tipo 3; o 4B fica no "zigue-zague em Z".

### Glossário por campo

Alguns termos mudam de sentido conforme o campo (`glossario.TERMOS_DA_COR`): "degradê" é
`fade` no corte e `ombre gradient, blended from roots to ends` na cor; "comprimento" é
`lengths` (a parte entre a raiz e as pontas) na cor. Entraram termos de região e de técnica:
`face-framing` (ao redor do rosto), `ends` (pontas), `long layers`, `lighter, softly thinned
ends`, `balayage`, `babylights`, `brunette balayage` (morena iluminada), `californian
highlights`, `fine` e `chunky highlights`, `money piece`, `under-layer (peekaboo)`, `ashy`,
`toned` e `all-over`.

### Caminho especializado (Kontext)

O `change-haircut` não tem campo de textura: com um tipo escolhido, o pedido vai direto ao
modelo de edição por texto, com a frase "New hair texture: {tipo}". Sem tipo escolhido, o
caminho e a instrução são os mesmos de antes.

### Cenários

| Cenário | Pedido | O que a instrução garante |
|---|---|---|
| A | corte, cor e tipo novos | troca de textura (prioridade 2) e corte e cor (prioridade 3), com o corte moldado na textura escolhida |
| B | só a cor | textura, corte e comprimento mantidos; cor fiel às regiões descritas |
| C | só o corte | textura e cor mantidas; corte moldado na textura da própria cliente |
| D | corte novo, textura mantida | a preservação vence qualquer textura citada no corte |
| E | só o tipo de cabelo | corte e cor mantidos; comprimento não cortado nem alongado (encolhimento esperado) |

Os cinco têm teste automático em `tests/test_preservacao_capilar.py` e um pedido pronto
para o experimento pago em `scripts/pedidos_estilo_e_cor.json`:

```
.venv\Scripts\python scripts\comparar_simulacoes.py --fotos C:\fotos-teste --pedidos scripts\pedidos_estilo_e_cor.json --estrategias nano
```

Com 4 fotos: 20 chamadas, cerca de US$ 0,67 em 1K. O comando acima é o ensaio (não chama
nada); só gera com `--confirmar-custo`.

### Limitações

- trocar a textura é a mudança mais difícil para o modelo: ele pode alterar o volume, o
  comprimento aparente ou a linha do cabelo junto. A instrução pede densidade igual e
  encolhimento natural, mas não há medição ainda;
- o resultado varia entre execuções (sem semente);
- nesta etapa o schema da Replicate não foi consultado de novo (nenhuma chamada à Replicate
  foi feita). A conferência automática antes de cada geração para o envio se o schema
  mudar.
