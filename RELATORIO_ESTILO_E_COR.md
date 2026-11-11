# Relatório: reestruturação da etapa 3/3, "Estilo e cor"

Feita em 2026-11-10 sobre a `main` em `74f0a94`. Nada foi enviado ao GitHub, implantado ou
gerado na Replicate: as mudanças estão na cópia local, à espera de autorização para o
commit. A única migration aplicada foi no banco **local** de desenvolvimento.

> Complemento de 2026-11-11: o termo do cliente passou à versão 1.2.2 (migration
> `d4b7a2e9f150`), que acrescenta o tipo de cabelo desejado à lista do que vai com a foto e
> chama o gênero do corte de "estilo do corte", como na tela. Quem aceitou a 1.2 ou a 1.2.1
> não precisa decidir de novo. Os textos do aplicativo sobre o envio (`servicoExterno.ts`)
> foram atualizados da mesma forma.

## 1. Resumo

A etapa em que se escolhe o que muda no cabelo foi redesenhada para quem não é técnico e
para qualquer tamanho de tela. As três decisões (corte, cor e tipo de cabelo) viraram três
seções com a mesma estrutura: uma pergunta em linguagem simples, a escolha entre mudar e
manter, e os detalhes só quando a pessoa quer mudar.

A mudança de maior impacto é de **significado**: a pergunta sobre textura deixou de ser
"como é o seu cabelo natural" (um apoio para a IA ler a foto) e passou a ser "qual tipo de
cabelo você deseja na simulação". O tipo escolhido é aplicado na imagem; "Manter meu tipo
de cabelo atual", que já vem marcado, é uma instrução explícita de preservar a textura da
foto. Cada um dos 12 tipos (1A a 4C) tem uma ilustração própria.

## 2. Arquivos

### Novos

| Arquivo | Para quê |
|---|---|
| `espelho/src/components/EscolhaSegmentada.tsx` | escolha única entre opções curtas (mudar ou manter; feminino, masculino ou neutro), reaproveitada em três lugares |
| `espelho/src/components/IlustracaoTextura.tsx` | ilustração vetorial de um tipo de cabelo ou de uma categoria |
| `espelho/src/utils/ilustracaoTextura.ts` | a geometria das ilustrações (função pura, testada) |
| `backend/migrations/versions/c7d3f9a1e64b_tipo_de_cabelo_desejado.py` | coluna opcional `simulacoes.textura` (só acrescenta) |
| `backend/scripts/pedidos_estilo_e_cor.json` | os cenários A a E prontos para o experimento pago |
| `RELATORIO_ESTILO_E_COR.md` | este relatório |

### Alterados

| Arquivo | O que mudou |
|---|---|
| `espelho/app/simulacao/parametros.tsx` | a tela inteira, redesenhada (seções 3 a 5) |
| `espelho/app/simulacao/revisao.tsx` | resumo simples com "Alterar"; instrução técnica recolhida |
| `espelho/app/simulacao/resultado.tsx`, `imagem/[id].tsx` | mostram o tipo de cabelo pedido |
| `espelho/app/simulacao/processando.tsx` | `textura_invalida` volta às escolhas com o motivo |
| `espelho/src/utils/pedido.ts` | regras do pedido: tipo de cabelo, "Neutro", conflitos, seleção |
| `espelho/src/data/tipos.ts`, `data/rascunho.tsx`, `services/api/index.ts` | `curvatura` virou `textura` no tipo, no rascunho e no envio |
| `espelho/src/components/Icone.tsx` | ícone de textura |
| `backend/app/services/ai/pedido.py` | `textura` (validada), "Neutro" na mensagem, campo da alteração (corte ou cor), pedido só de textura |
| `backend/app/services/ai/instrucoes.py` | instrução do Nano Banana reorganizada (seção 7) |
| `backend/app/services/ai/glossario.py` | termos por campo e termos de região e técnica de cor |
| `backend/app/services/ai/planos.py` | com tipo escolhido, o caminho especializado usa o modelo de texto |
| `backend/app/models/simulacao.py`, `schemas/simulacao.py`, `services/simulacao.py`, `api/v1/simulacoes.py` | `textura` do formulário ao banco e de volta |
| `backend/scripts/comparar_simulacoes.py` | pedidos com `textura`; a estratégia `nano-curvatura` saiu |
| Testes: `backend/tests/test_preservacao_capilar.py` (reescrito), `test_nano_banana.py`, `test_comparar_simulacoes.py`, `test_personalizacao.py`, `test_simulacoes.py`; `espelho/testes/pedido.mjs`; `espelho/e2e/personalizacao.mjs` (reescrito), `ampliacao-e-tipo-de-cabelo.mjs` (renomeado de `ampliacao-e-curvatura.mjs`), `fluxo-completo.mjs` | seção 8 |
| `docs/NANO_BANANA.md` (seção 10 nova), `docs/DOCUMENTACAO.md` (13.5 nova), `DEPLOY.md`, `espelho/e2e/README.md`, `qa.sh`, `RELATORIO_UX_E_SIMULACAO.md` (nota de atualização) | documentação |

## 3. Melhorias visuais

**Antes:** um quadro "Como preencher" com três instruções abria a tela; a pergunta de
textura vinha antes do corte, em chips de texto; o corte e a cor usavam caixas de marcar com
rótulos longos ("Manter o corte atual (mudar só a cor)"); os exemplos ocupavam um bloco fixo
em cada passo; e o rodapé dizia "Passo 1: ...".

**Agora:**

- uma frase curta no topo ("Escolha o que muda no cabelo. Rosto, roupa e fundo continuam
  como estão na foto") no lugar do guia;
- três seções com o mesmo desenho: etiqueta com ícone (Corte, Cor, Tipo de cabelo), selo de
  situação (A preencher, Pronto, Sem mudança, Decidir, Corrigir), a pergunta como título e
  a escolha "Quero mudar" ou "Manter..." em dois botões lado a lado;
- os textos sugeridos no pedido: "Como você quer que seu cabelo fique?", "Descreva do seu
  jeito!...", "Qual cor você deseja no seu cabelo?", "Qual tipo de cabelo você deseja na
  simulação?", e os dois exemplos longos como texto de exemplo dos campos;
- "Estilo do corte" com Feminino, Masculino e Neutro, e a explicação "Neutro é um corte sem
  gênero definido";
- ideias de cortes e cores recolhidas ("Sem ideias? Veja cortes populares"), com o aviso de
  que são só ideias;
- o aviso de tons claros aparece só quando a cor descrita tem loiro, platinado, grisalho ou
  claro;
- tipo de cabelo escolhido por imagem: um cartão "Manter meu tipo de cabelo atual" com a
  foto do cliente, as quatro categorias com ilustração e, dentro da categoria, os três
  tipos; a opção escolhida ganha borda, fundo e um visto, e a linha "Vai para a simulação:"
  diz o valor final por extenso ("Ondulado 2B: ondas definidas em S");
- revisão com um cartão "O que vai mudar": Corte, Estilo do corte (só com corte novo), Cor e
  Tipo de cabelo, cada um com ícone e "Alterar"; manutenções em tom mais leve; a instrução
  em inglês e o nome do modelo ficam em "Ver a instrução enviada à IA".

**Ilustrações em vez de fotos.** O pedido preferia fotografias reais com licença. Não usei
fotos porque não havia como garantir, para 12 imagens, a classificação correta de cada
subtipo, o mesmo enquadramento e a mesma luz, e a licença de uso, sem baixar e avaliar
material de terceiros; uma foto mal classificada ensina o tipo errado. As ilustrações saem
de uma regra só (`utils/ilustracaoTextura.ts`): mesmo quadro e mesma cor, e muda apenas o
que distingue os tipos (reta, senoide, espiral ou zigue-zague; tamanho da onda ou do cacho;
espessura; densidade; encolhimento). São vetoriais (poucos bytes, sem rede) e o teste
confere que os 12 desenhos são diferentes e cabem no quadro. Se o projeto conseguir fotos
licenciadas, a troca fica restrita ao componente `IlustracaoTextura`.

## 4. Responsividade

- nenhuma largura ou altura fixa no conteúdo: grades de colunas iguais que quebram em
  linhas, com a quantidade de colunas medida pela largura real da seção (`onLayout`):
  categorias em 2 colunas no celular e 4 a partir de ~470 px; tipos sempre em 3;
- ilustrações com proporção, e não tamanho: mais baixas nas categorias e nos tipos em tela
  larga, quadradas nos tipos no celular;
- textos podem quebrar linha dentro dos botões ("Manter o corte atual" em duas linhas a
  320 px), sem corte na largura;
- toda opção tem pelo menos 44 por 44 px de área de toque, inclusive a linha do rodapé;
- o rodapé fica fora da área de rolagem e dentro da área segura inferior (`Tela`, já com
  `SafeAreaView`), e o conteúdo rola até o fim acima dele;
- o teclado continua tratado por `EvitaTeclado`.

Verificado no navegador em 320 por 640, 390 por 844 e 1280 por 900 px: sem rolagem lateral,
sem texto cortado nas opções, rodapé sem cobrir o fim do conteúdo, categorias em 2 ou 4
colunas conforme a largura.

## 5. Lógica do tipo de cabelo e das escolhas

- **Valor único e inequívoco.** O pedido guarda um só valor: nulo (manter), uma categoria
  ("ondulado") ou um tipo ("2B"). Categoria sem tipo é válida ("um ondulado comum").
- **Seleção.** Tocar numa categoria escolhe a categoria; tocar de novo nela não apaga o
  tipo já escolhido; trocar de categoria descarta o tipo da anterior; tocar de novo num tipo
  volta à categoria; "Manter meu tipo" desfaz tudo. As regras ficam em funções puras
  (`escolherCategoria`, `escolherTipo`), testadas.
- **Manter com texto escrito.** Escolher "Manter o corte atual" (ou a cor) com uma descrição
  já escrita não apaga nada: a seção mostra o texto entre aspas e pergunta qual vale ("Usar a
  descrição" ou "Manter o corte atual e apagar o texto"). Enquanto não decide, o pedido não
  segue. Na revisão e no envio, o texto de um campo mantido nunca vai.
- **Pedido mínimo.** Manter corte, cor e tipo ao mesmo tempo não é pedido ("Nada a simular:
  mude o corte, a cor ou o tipo de cabelo"). Mudar só o tipo de cabelo é.
- **"Revisar pedido".** Fica sempre ativo. Com algo faltando, não avança: leva até a seção,
  marca o selo como "Falta preencher", mostra o erro no campo e anuncia a mensagem ao leitor
  de tela. O rodapé diz o que falta e quantos itens restam, e "Ver" leva até lá. Um campo
  vazio não aparece como erro antes de a pessoa tentar seguir.
- **Compatibilidade.** O APK antigo manda o campo `curvatura`; o servidor o ignora, e a
  textura da foto é mantida. A coluna antiga continua no banco com os valores já gravados.

## 6. Como as escolhas viram instruções para o Nano Banana 2.1

O Nano Banana 2.1 na Replicate só aceita texto e imagens (`prompt`, `image_input`,
`aspect_ratio`, `resolution`, `google_search`, `image_search`, `output_format`): não existe
parâmetro de textura, gênero ou semente. Tudo vira uma instrução em inglês, montada pelo
servidor (`instrucoes.prompt_detalhado`), em quatro prioridades:

| Escolha na tela | Na instrução |
|---|---|
| Manter meu tipo de cabelo atual | prioridade 2: "keep the client's natural hair texture exactly as in the photo", o que preservar, os desvios a evitar e "This takes priority over any texture mentioned in the descriptions below" |
| Um tipo (por exemplo 3B) | prioridade 2: "change the hair texture to type 3B curly hair: medium, well-defined springy curls, about as wide as a finger", aplicada no cabelo todo, com densidade igual e encolhimento natural |
| Descrição do corte | prioridade 3: o texto inteiro entre aspas, os termos técnicos em inglês e "Follow every detail... Do not add details that were not asked for" |
| Descrição da cor | prioridade 3: o texto inteiro, os termos e "Keep localized changes local: do not spread them to the whole hair" |
| Feminino, Masculino, Neutro | "It is a women's haircut.", "It is a men's haircut.", "It is a gender-neutral haircut, not styled as typically feminine or masculine." (só com corte novo) |
| Manter o corte | "Keep the current haircut exactly as it is" e o comprimento exato |
| Manter a cor | "Keep the current hair color exactly as it is, including highlights, roots and gray hairs" |

Exemplo real (cenário B, cor localizada), trecho da prioridade 3:

> New hair color: "Quero manter a raiz castanho escuro, com mechas caramelo suaves no
> comprimento e pontas um pouco mais claras" (described in Brazilian Portuguese; key terms:
> roots, dark brown, highlights, caramel, soft, lengths, ends). Follow every detail of this
> description, including where each color goes (roots, lengths, ends, strands around the
> face, the under-layer or only some highlights) and any part it says to keep. Keep
> localized changes local: do not spread them to the whole hair, and do not add colors that
> were not asked for.

No caminho especializado (o antigo, com o `change-haircut`), um tipo de cabelo escolhido
manda o pedido ao modelo de texto, porque o `change-haircut` não tem onde recebê-lo.

## 7. Melhorias na instrução

- **textura com sentido novo**: preservação explícita ou troca explícita, sempre com
  prioridade sobre o que as descrições disserem; saiu a exceção antiga ("a não ser que o
  corte peça outra textura"), que deixava a decisão ao modelo;
- **fidelidade à descrição livre**: a descrição vai inteira, sem resumo e sem virar nome de
  corte; frases próprias para seguir cada detalhe, manter o que a pessoa disse para manter e
  não inventar;
- **localização**: a cor respeita raiz, comprimento, pontas, mechas do rosto e camada de
  baixo; mudança local não vira global;
- **glossário por campo**: "degradê" é fade no corte e transição de tons na cor; entraram
  termos de região (pontas, ao redor do rosto, comprimento) e de técnica (balayage,
  babylights, morena iluminada, luzes californianas, money piece, acinzentado, matizado);
- **gênero neutro** como instrução, e não ausência;
- **comprimento** com regra para a troca de textura (o encolhimento de uma textura mais
  fechada é esperado; o cabelo não é cortado nem alongado);
- **qualidade**: abertura "This is an edit of an existing photograph, not a new image",
  idade aparente e formato da cabeça na lista do que não muda, e a naturalidade (sem
  aspecto de peruca, plástico ou pintura), sem prometer preservação absoluta.

## 8. Testes e resultados

| Bateria | Resultado |
|---|---|
| Servidor, `pytest` (685 testes) | 684 passaram; 1 falha ambiental conhecida desta máquina Windows (`WinError 10106` num subprocesso), sem relação com a mudança |
| `tests/test_preservacao_capilar.py` | 59 testes: prioridades, manter e trocar textura, os 16 valores, cenários A a E, gênero neutro, descrição livre de corte e de cor, glossário por campo, caminho especializado, validação, do formulário à instrução gerada em segundo plano, campo antigo ignorado, prévia do plano |
| Banco: `alembic check` | modelos e migrations coincidem |
| Aplicativo: `tsc --noUnusedLocals` | sem erros |
| Aplicativo: `eslint` | sem erros; os avisos que restam são de arquivos que esta mudança não tocou |
| Unidade: `testes/pedido.mjs` | 75 verificações (pendências, conflitos, pedido só de textura, rótulos, seleção, os 16 desenhos diferentes e dentro do quadro); as outras baterias de unidade também passaram |
| Travessões na interface | nenhum |
| `e2e/personalizacao.mjs` (navegador) | 97 verificações, 0 falhas |
| `e2e/ampliacao-e-tipo-de-cabelo.mjs` | 21 verificações, 0 falhas (inclui o tipo 3C gravado no servidor e na instrução) |
| Demais baterias de navegador (fluxo completo, interface, agenda, datas, atendimentos, painel, fotos e câmera, contraste, auditoria, segurança) | ver seção 8.1 |

O que o `e2e/personalizacao.mjs` cobre: as três seções e seus selos; "Revisar pedido" com
algo faltando (não avança, leva à seção, mostra o erro no campo); ideias recolhidas que não
são botões; "Neutro" marcado no início; os textos sugeridos; conflito entre manter e texto
escrito, nos dois sentidos; "nada a simular" e pedido só de textura; todas as categorias e
todos os 12 tipos escolhidos um a um, com a linha "Vai para a simulação" conferida e os 12
desenhos diferentes; troca de categoria sem resto; validação de marcação e do limite de 300
caracteres; revisão com o resumo simples e a instrução recolhida (exemplo exato vai às
opções do `change-haircut`; tipo de cabelo vai ao modelo de texto com a frase da textura);
um envio só com toque duplo, e o envio com `textura=3B`, sem `curvatura`; resultado com o
tipo de cabelo; sem conexão, credencial recusada e pedido recusado; 320, 390 e 1280 px;
áreas de toque; console sem erros.

### 8.1 Bateria completa

As etapas do `qa.sh --interface`, rodadas no Windows com a carga de demonstração recriada
antes de cada bateria de navegador (API local com `AI_PROVIDER=fake`):

| Bateria | Resultado |
|---|---|
| fluxo completo, interface, mudanças de interface | nenhuma falha |
| agenda | 27 verificações, 0 falhas |
| datas | 26 verificações, 0 falhas |
| ampliação e tipo de cabelo | 21 verificações, 0 falhas |
| atendimentos | 49 verificações, 0 falhas |
| painel e comparação | 48 verificações, 0 falhas |
| fotos e câmera | 28 verificações, 0 falhas |
| personalização | 97 verificações, 0 falhas |
| contraste visual (todas as telas, celular e tablet) | nenhum texto abaixo do contraste mínimo, nenhuma tela com rolagem horizontal |
| auditoria | 29 verificações, 0 falhas |
| segurança | 13 verificações, 0 falhas |

Não testado: um aparelho Android ou iPhone de verdade (o navegador não reproduz teclado,
área segura nem gestos do sistema) e a qualidade das imagens geradas (as chamadas são pagas;
o servidor local usa um provedor que não é IA).

## 9. Pontos pendentes

1. **Experimento de qualidade (pago).** Ainda não há evidência de que o Nano Banana troca a
   textura com fidelidade. `scripts/pedidos_estilo_e_cor.json` tem os cenários A a E; com 4
   fotos são 20 chamadas, cerca de US$ 0,67 em 1K. Precisa da sua autorização e de fotos de
   pessoas que autorizaram o uso (`docs/NANO_BANANA.md`, seção 10).
2. **Commit, implantação e APK.** Nada foi enviado. Na implantação, a migration
   `c7d3f9a1e64b` roda sozinha (só acrescenta uma coluna). O APK atual continua funcionando
   com o servidor novo; a tela nova no Android exige um APK novo.
3. **Aparelho real.** Conferir a tela em pelo menos um Android e um iPhone (teclado sobre a
   descrição, rodapé com a barra de gestos, toque nas ilustrações).
4. **Fotos reais dos tipos (opcional).** Se o projeto obtiver fotos licenciadas e
   consistentes, a troca fica restrita a `IlustracaoTextura`.
5. **Schema da Replicate.** Não foi consultado de novo nesta etapa (nenhuma chamada à
   Replicate). A conferência automática antes de cada geração interrompe o envio se o schema
   mudar.
