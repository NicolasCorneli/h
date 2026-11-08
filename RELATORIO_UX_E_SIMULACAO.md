# Relatório: UX/UI, acessibilidade e preservação capilar na simulação

Rodada de evolução a partir dos testes com usuários de novembro de 2026. Feita sobre a
`main` em `81b55ec`, sem alterações locais pendentes no início. **Nada foi commitado,
enviado ao GitHub ou implantado**, e nenhuma migration rodou contra a produção (só contra o
banco local de desenvolvimento e o de testes). Nenhuma chamada paga à Replicate foi feita:
a única consulta real foi a leitura do schema publicado, que não gera cobrança.

## A. Resumo executivo

| Problema relatado | O que foi feito | Situação |
|---|---|---|
| Travessões nos termos | Termo 1.2.1 sem travessões (revisão só de redação, sem nova aceitação para quem aceitou a 1.2); verificador passou a conferir o termo vigente | implementado e testado |
| Barra inferior colada nos botões do Android; câmera apertada | Folga acima da área do sistema; coluna própria para o botão da câmera | implementado; confirmação em aparelho pendente |
| Data de nascimento só no calendário | Campo digitado dd/mm/aaaa, barras automáticas, sem regra rígida durante a digitação, validação de calendário no fim, colar; calendário mantido como botão (segunda versão, 2026-11-08) | implementado e testado (unidade e navegador); teclado do aparelho a confirmar |
| Fotos pequenas no resultado | Visualizador em tela cheia com zoom, aberto pelas imagens do resultado, da ficha e da comparação | implementado e testado no navegador; pinça a confirmar em aparelho |
| "A IA abriu meus cachos e aumentou o comprimento" | Instrução do Nano Banana reorganizada por prioridades, com preservação da curvatura, textura, volume e comprimento; pergunta opcional "Cabelo natural"; experimento ampliado | implementado e testado (montagem); **qualidade não medida** (sem fotos autorizadas nem autorização de gasto) |

## B. Diagnóstico inicial

- O código aberto foi tomado como fonte de verdade. Divergências com o pedido:
  - a web **não** usa mais máscara na data de nascimento: desde o commit `81b55ec`, usa o
    campo de data do navegador, que já se digita por segmentos. Foi mantido;
  - **não existe imagem de referência do corte**: ela saiu do escopo na migration
    `c6a2f9d41b87` (escopo e custo). Não foi recriada no aplicativo;
  - a tela que abre a simulação inteira já existia (`simulacao/imagem/[id]`), mas limitada a
    520 px, sem zoom; o resultado e a comparação não abriam nada ao toque.
- `scripts/verificar_travessoes.py` existia e estava no `qa.sh`, mas deixava todos os termos
  de fora; o termo 1.2 tinha 4 travessões.
- A barra de abas já usava `useSafeAreaInsets`, mas com `max(inset, 12)`: sem folga acima
  dos botões do sistema.
- A instrução do Nano Banana não dizia nada sobre o próprio cabelo (curvatura, volume,
  comprimento), só sobre o que fica fora dele.

## C. Arquivos

**Criados**

| Arquivo | O que é |
|---|---|
| `backend/migrations/versions/b5c8e1d3a742_curvatura_do_cabelo.py` | coluna opcional `simulacoes.curvatura` |
| `backend/migrations/versions/c8f2a6d4e913_termo_1_2_1_sem_travessoes.py` | termo 1.2.1 (cliente e profissional) |
| `backend/scripts/pedidos_cacheados.json` | 6 pedidos para avaliar cabelos cacheados e crespos |
| `backend/tests/test_preservacao_capilar.py` | 44 testes: regras da instrução, curvatura de ponta a ponta, referências |
| `backend/tests/test_termo_1_2_1.py` | 6 testes: só a pontuação mudou, regra de versão, sem revalidação para quem aceitou a 1.2 |
| `espelho/src/components/VisualizadorImagem.tsx` | tela cheia com zoom |
| `espelho/testes/data-digitada.mjs` | 37 casos da data digitada |
| `espelho/e2e/ampliacao-e-curvatura.mjs` | bateria do navegador (19 verificações) |

**Alterados (principais)**

| Arquivo | Mudança |
|---|---|
| `backend/app/services/ai/instrucoes.py` | `prompt_detalhado` por prioridades; a anterior guardada como `prompt_detalhado_original`; descrições de curvatura; papéis das imagens |
| `backend/app/services/ai/pedido.py` | `curvatura` (validada) e `referencias` no pedido |
| `backend/app/services/ai/planos.py` | variante da instrução (só o script usa a "original"); referências na lista `image_input` |
| `backend/app/services/ai/base.py`, `replicate.py` | referências passam pelo mesmo tratamento da foto (reduzidas, sem EXIF) |
| `backend/app/services/catalogo.py` | descrições de corte sem palavras de textura ("straight", "smooth") |
| `backend/app/models/simulacao.py`, `schemas/simulacao.py`, `services/simulacao.py`, `api/v1/simulacoes.py` | curvatura do formulário ao processamento em segundo plano |
| `backend/app/services/regras_consentimento.py`, `services/auth.py` | revalidação compara só "maior.menor" (consentimento e ciência) |
| `backend/scripts/comparar_simulacoes.py` | estratégias `nano-original`, `nano`, `nano-curvatura`, `nano-textura`, `nano-referencia`, `nano-etapas`, `atual`; critérios de avaliação novos |
| `scripts/verificar_travessoes.py` | confere o termo vigente de cada tipo |
| `espelho/app/(tabs)/_layout.tsx` | barra inferior e botão da câmera |
| `espelho/src/components/Campo.tsx` | opção `acessorio` (botão do calendário) |
| `espelho/src/components/CampoData.tsx` | data de nascimento digitada no celular |
| `espelho/src/utils/mascaras.ts`, `datas.ts` | `digitarData`, `normalizarDataDigitada` e `situacaoDataCurta` |
| `espelho/src/components/ImagemSimulada.tsx` | `ampliavel` abre o visualizador |
| `espelho/app/simulacao/parametros.tsx`, `revisao.tsx`, `processando.tsx`, `imagem/[id].tsx`, `resultado.tsx`, `comparar.tsx` | pergunta "Cabelo natural", revisão, envio, ficha e ampliação |
| `espelho/src/utils/pedido.ts`, `data/rascunho.tsx`, `data/tipos.ts`, `services/api/index.ts` | curvatura no rascunho, no tipo e no envio |
| testes antigos | `test_nano_banana`, `test_simulacoes`, `test_comparar_simulacoes`, `test_termo_1_2`, `test_personalizacao_api`: acompanham a instrução nova, o campo novo e a vigência da 1.2.1 |
| `qa.sh`, `espelho/e2e/README.md` | testes novos incluídos |
| `espelho/e2e/auditoria.mjs` | já estava quebrada desde `81b55ec` (digitava "12/03/1990" no campo de data do navegador, que só aceita AAAA-MM-DD); passou a converter a data. Não era regressão desta rodada |
| `espelho/e2e/fotos-e-camera.mjs` | chamava o Python em `.venv/bin/python`, que só existe no Linux; passou a usar `Scripts/python.exe` no Windows, e rodou pela primeira vez nesta máquina |
| `docs/NANO_BANANA.md` (seção 9), `docs/DOCUMENTACAO.md` (seções 8.7 e 13), `DEPLOY.md` (seção 12) | documentação |

## D. UX/UI

Detalhes em `docs/DOCUMENTACAO.md`, seção 13.

- **Barra inferior:** margem de baixo = área do sistema + 8 px (antes, exatamente a área);
  12 px sem área do sistema (navegador). Botão da câmera com coluna própria (54 px + 16 px
  de cada lado); as abas dividem o resto, com alvo de 44 px. Nenhuma biblioteca nova.
- **Data de nascimento (celular e web):** digitada, teclado numérico no celular, barras
  automáticas, sem regra rígida durante a digitação (apagar ou corrigir no meio não
  reorganiza nada; "4/5/2000" é aceito e organizado ao sair do campo), colar com ou sem
  barras. Validação de calendário pela mesma função que converte para o servidor
  (`isoDeDataCurta`), só no fim: "Essa data não existe" (completa e impossível) e "Data
  incompleta" (ao sair do campo). A primeira versão, com casas fixas e cursor controlado,
  foi rígida demais num teste de uso (o 0 inicial não aparecia) e foi substituída em
  2026-11-08. Calendário continua num botão ao lado. Formato da API e do banco inalterado
  (`AAAA-MM-DD`, `DATE`); idade, menores e responsável legal inalterados.
- **Imagens ampliadas:** um visualizador só (`VisualizadorImagem`), aberto pelo
  `ImagemSimulada` no resultado (foto original e simulação), na ficha e na comparação.
  Proporção original, pinça até 4x, arrastar, toque duplo, botões de zoom, fecha pelo
  botão, pelo voltar do Android e pela tecla Esc; carregando e erro; a mesma URL assinada
  da miniatura (nenhum pedido novo, nenhum endereço permanente).
- **Travessões:** termo 1.2.1 e verificador estendido (seção A).

## E. Nano Banana 2.1

Detalhes e fontes em `docs/NANO_BANANA.md`, seção 9.

- **Pesquisa complementar:** o schema da Replicate não mudou e não tem nenhum controle de
  textura, máscara, semente ou temperatura (o Google confirma que `seed`, `temperature`,
  `topK` e `topP` dão erro nesse modelo). A única alavanca é a instrução. O Google recomenda
  o padrão de "máscara semântica" ("change only… keep everything else exactly the same"),
  especificidade, contexto, e nomear o papel de cada imagem pela posição. O model card
  declara "partial instruction following" e consistência de personagem "not always
  perfect"; não fala de cabelo.
- **Instrução nova:** quatro prioridades (pessoa, cabelo natural, mudança pedida,
  naturalidade); preservação explícita de curvatura, tamanho do cacho, densidade, volume,
  frizz e definição; comprimento preservado sem corte e nunca aumentado sem pedido
  explícito; comprimento lido com o encolhimento natural; a única exceção de textura é um
  corte que a peça (escova, permanente). Regras condicionais para não haver contradição.
- **Curvatura opcional:** decidida pela avaliação (a única informação de textura que cabe
  no que o modelo aceita; não é parâmetro; a foto continua mandando). Implementada de
  ponta a ponta, com coluna nova. Eficácia não medida.
- **Referências (textura e corte) e edição em etapas:** só no experimento, como hipóteses.
- **Schema:** nenhum parâmetro novo; a validação dinâmica contra o schema publicado foi
  mantida e cobre as referências (lista `image_input`).
- **Idioma:** mantida a estratégia `pt_com_termos`; não houve como medir alternativas.

## F. Testes experimentais

**Não executados.** São chamadas pagas, e o projeto não tem as fotos autorizadas de
pessoas com cabelo liso, ondulado, cacheado e crespo que o protocolo exige. A estrutura
está pronta e testada com HTTP simulado (7 testes do script):

| | |
|---|---|
| Comando (ensaio, sem custo) | `.venv\Scripts\python scripts\comparar_simulacoes.py --fotos C:\fotos-cacheados --pedidos scripts\pedidos_cacheados.json --estrategias nano-original,nano,nano-curvatura` |
| Para valer | o mesmo com `--confirmar-custo` |
| Custo estimado | 4 fotos x 6 pedidos x 3 estratégias = 72 chamadas, cerca de US$ 2,42 em 1K |
| Tempo de referência | 14 a 17 s por simulação em 1K (medido em 2026-11-05) |
| Critérios | identidade, curvatura, textura, comprimento, volume, corte, cor, naturalidade (1 a 5) |

Nenhuma melhora de qualidade é afirmada sem esse resultado. A resolução continua em 1K: não
há evidência de que 2K (50% mais caro) melhore a textura.

## G. Testes de regressão

| Verificação | Resultado |
|---|---|
| `pytest` (backend inteiro) | 668 passaram, 1 falhou: `test_testes_se_recusam_a_rodar_fora_de_um_banco_de_teste`, que já falhava nesta máquina (o Windows recusa o subprocesso, WinError 10106) |
| `tsc --noEmit --noUnusedLocals` | sem erros |
| `eslint` | 0 erros; os mesmos 18 avisos de antes, em arquivos não alterados |
| Testes de unidade do app | todos passam, incluindo `data-digitada.mjs` (37 casos) |
| `scripts/verificar_travessoes.py` | 0 ocorrências (e acusa as 4 da 1.2 se a 1.2.1 for removida) |
| Build web (`expo export --platform web`) | gerado sem erros |
| Migrations | sobem e descem na suíte (`downgrade base` e `upgrade head` a cada execução); aplicadas no banco local |
| E2E (navegador, dados recriados antes de cada uma) | todas sem falhas: personalização 66, fluxo completo, interface, datas 18, agenda 27, atendimentos 49, mudanças de interface, ampliação e curvatura 19 (nova), painel e comparação 48, auditoria 29, fotos e câmera 28, segurança 13, contraste visual (0 textos abaixo do mínimo, 0 telas com rolagem lateral). Não rodada: `google.mjs`, que exige IDs do Google configurados |

Caminho especializado (change-haircut e flux-kontext-pro) e provedor `fake`: cobertos pelos
testes antigos, que passam sem mudança de comportamento; a instrução do Kontext não mudou.

## H. Banco de dados

Duas migrations, ambas aditivas e com volta:

- `b5c8e1d3a742`: `simulacoes.curvatura` (texto curto, opcional, com restrição de valores).
  Necessária porque a geração em segundo plano remonta o pedido a partir da linha gravada.
  Registros antigos ficam nulos ("Não sei informar").
- `c8f2a6d4e913`: termo 1.2.1 (cliente e profissional). A 1.2 deixa de ser vigente e
  continua no banco, intacta. Nenhum consentimento é alterado. A volta se recusa a remover a
  1.2.1 se alguém já a aceitou.

## I. Limitações

- **Qualidade da simulação não medida** (seção F): a instrução nova é uma hipótese
  fundamentada; pode não resolver o caso relatado, porque o modelo segue instruções só em
  parte e não aceita semente.
- **Não verificado em aparelho:** barra inferior com gestos e com três botões, teclado
  sobre a data e a pinça do zoom.
  O navegador não reproduz isso. Precisa de um APK novo.
- A curvatura informada pode contradizer a foto; a instrução manda a foto prevalecer.
- Referências de corte e textura e a edição em etapas existem só no experimento.
- Se o Kontext voltar a ser usado, a curvatura não tem efeito nele.

## J. Estado final

Pronto para uma nova rodada de testes com usuários **depois** de três passos que dependem
de você:

1. revisar e fazer o commit (nada foi commitado);
2. publicar no servidor (`git pull` e `docker compose up -d --build --wait`; as migrations
   rodam sozinhas) e gerar um APK novo;
3. de preferência antes da rodada, rodar o experimento da seção F com 4 a 8 fotos
   autorizadas, para saber se a instrução nova resolve o caso dos cachos.

Na rodada, vale observar em aparelho: a barra inferior (gestos e três botões), a digitação
da data de nascimento, o zoom com pinça e, nas simulações de cabelo cacheado e crespo, a
curvatura e o comprimento.
