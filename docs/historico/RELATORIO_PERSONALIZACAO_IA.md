# Etapa "Estilo e cor": personalização, integração com a Replicate e validação

Relatório da reformulação da etapa 3 de 3 da simulação, feita em duas rodadas:

1. **Primeira rodada:** etapa redesenhada (corte e cor descritos, "manter o atual",
   revisão), integração com a Replicate revista, foto de referência e pedido por voz.
2. **Segunda rodada (estado atual):** a foto de referência e o pedido por voz foram
   **retirados por inteiro**, por custo e por complexidade desnecessária para um protótipo
   de TCC; a tela passou a guiar o preenchimento em dois passos e a mostrar exemplos de
   corte e de cor em texto, no lugar dos botões de sugestão e da paleta. O que saiu, por
   quê, a pesquisa dos exemplos e os testes estão em [M](#m-segunda-rodada-simplificação).

Base: o ZIP `salao-em-dia-auditado-v2` (último commit `3130cd7`). Nada foi commitado.

Sumário: [A](#a-resumo-executivo) · [B](#b-diagnóstico-inicial) · [C](#c-alterações-implementadas) ·
[D](#d-decisões-técnicas) · [E](#e-arquivos-modificados) · [F](#f-testes-executados) ·
[G](#g-testes-não-executados) · [H](#h-configuração-necessária-para-o-seu-teste) ·
[I](#i-limitações-conhecidas) · [J](#j-roteiro-para-o-seu-feedback) ·
[K](#k-custos-e-riscos-operacionais) · [L](#l-critérios-de-conclusão) ·
[M](#m-segunda-rodada-simplificação)

---

## A. Resumo executivo

**O problema.** A etapa "Estilo e cor" era uma escolha entre seis cortes (com amostras
hachuradas, sem imagem real) e seis cores. Não havia como descrever o pedido nem manter o
corte ou a cor. Além disso, os indícios públicos sobre o modelo
`flux-kontext-apps/change-haircut` mostram que os campos `haircut` e `hair_color` são
**listas fechadas de opções**, e o servidor enviava descrições em inglês fora dessas listas
("short textured crop", "copper brown"). Se isso se confirmar no schema real, toda geração
real seria recusada pela Replicate (ver [B.1](#b1-o-que-impedia-a-geração-real)).

**Como ficou.**

1. A etapa é um roteiro em dois passos, **1. Corte** e **2. Cor**, com um guia "Como
   preencher" no topo. Cada passo tem o campo de texto (até 300 caracteres), a opção
   "manter o atual", exemplos em texto (em alta e clássicos) e um selo que mostra se o
   passo está "A preencher", "Pronto", "Sem mudança" ou "Corrigir". O rodapé diz, em uma
   frase, o que falta para seguir.
2. Tela de revisão: foto, corte, cor, como o pedido será gerado (modo, modelo e o texto que
   vai ao modelo) e as ações "Editar" e "Não mudar".
3. O servidor escolhe o modelo conforme o pedido e **confere cada campo e cada valor no
   schema publicado do modelo antes de gastar**:
   - exemplo com equivalente nas opções do modelo → `change-haircut` (o modelo principal);
   - descrição livre, ou exemplo sem equivalente → `black-forest-labs/flux-kontext-pro`
     (instrução em texto + imagem).
4. Integração com a Replicate revista: schema ao vivo, data URI até 1 MB e API de arquivos
   acima disso (apagando o arquivo depois), fallback para modelos não oficiais, cancelamento
   da predição esgotada, logs sem imagem embutida, erros com motivo próprio.
5. Envio único: a mesma `chaveEnvio` devolve a simulação já criada (toque duplo, rede que
   cai depois de o servidor receber, voltar e gerar de novo).
6. Comando `python -m app.diagnostico_ia`, que confere os dois modelos configurados sem
   criar predição, para você validar o schema real antes do primeiro teste.

**Defeito anterior corrigido.** Os testes desta rodada expuseram um defeito que já existia
no commit: o detector de rosto do servidor, usado ao mesmo tempo pela validação da foto e
pela conferência do enquadramento, podia recusar uma foto válida ou derrubar a API. Foi
corrigido com uma trava e um teste próprio. Depois, a seu pedido, a conferência do
enquadramento passou a rodar só com a câmera à vista ([M.7](#m7-defeito-anterior-encontrado-nos-testes-detector-de-rosto)).

**Estado.** Tudo implementado e testado com o provedor local e com um servidor que imita a
Replicate. **Nenhuma geração real foi feita**: não há chave neste ambiente e o domínio da
Replicate esteve bloqueado pela rede dele. A qualidade visual e o comportamento real dos
modelos dependem do seu teste ([H](#h-configuração-necessária-para-o-seu-teste) e
[J](#j-roteiro-para-o-seu-feedback)).

---

## B. Diagnóstico inicial

### B.0 Auditoria do fluxo existente

| Item pedido | O que havia |
| --- | --- |
| Tecnologia | App Expo SDK 57 (React Native 0.86, expo-router, TypeScript), API FastAPI + SQLAlchemy 2 + Alembic, PostgreSQL 16 |
| Tela da etapa 3 | `espelho/app/simulacao/parametros.tsx` |
| Foto da etapa anterior | Fica só na memória, em `src/data/rascunho.tsx` (`foto: {uri, width, height}`); não é gravada no aparelho |
| Navegação | `cliente` → `captura` (etapa 2) → `parametros` (etapa 3) → `processando` → `resultado` / `indisponivel` / `recusada` (pilha do expo-router) |
| Estado das escolhas | `rascunho.estilo` e `rascunho.cor`, rótulos de listas fixas em `src/data/catalogo.ts` |
| Chamada à Replicate | `backend/app/services/ai/replicate.py`, em tarefa de segundo plano após `POST /simulacoes` (202); o app consulta `GET /simulacoes/{id}` |
| Envio e guarda de imagens | Multipart para a API; a API valida, re-codifica em JPEG (sem EXIF), guarda no storage (disco ou S3) e serve por URL assinada de curta duração; ao provedor, a foto ia como data URI |
| Resultado | Imagem de saída guardada no storage, `status=concluida`, exibida por URL assinada |
| Variáveis e serviços | `AI_PROVIDER`, `AI_API_KEY`, `AI_MODELO`, `AI_TIMEOUT_S`, `AI_BASE_URL`, `AI_INTERVALO_CONSULTA_S`, `SIMULACAO_MAX_POR_HORA`; serviço externo: Replicate |
| Testes e ferramentas | 439 testes do servidor (PostgreSQL real), servidor de mentira da Replicate, testes de unidade do app, 10 baterias de navegador (Playwright), `qa.sh` |

### B.1 O que impedia a geração real

1. **Campos de opções fechadas recebendo texto fora da lista (indício forte, não confirmado).**
   A página de API do modelo mostra `hair_color` sem tipo declarado (como a Replicate
   mostra campos de opções), e descrições públicas falam em "31 opções de cor" e "90+
   estilos predefinidos". O servidor enviava `haircut: "short textured crop"` e
   `hair_color: "copper brown"`, que não estão entre esses valores. Como a Replicate valida a
   entrada contra o schema, a criação da predição seria recusada (422) e a tela diria "O
   serviço de simulação não respondeu". **Não consegui confirmar no schema real**: o
   domínio da Replicate esteve bloqueado neste ambiente. Por isso a correção não depende da
   hipótese: o servidor lê o schema publicado e se adapta a ele (texto livre ou opções), e
   o comando de diagnóstico mostra o que a Replicate publica.
2. **Sem conferência de schema.** Nomes de campo e valores estavam fixos no código.

### B.2 Outros problemas encontrados no fluxo

| # | Problema | Efeito |
| --- | --- | --- |
| 1 | A foto da simulação não era reduzida no aparelho antes do envio | foto de galeria acima de 4096 px é recusada pelo servidor; envios grandes demoram |
| 2 | O servidor mandava a foto inteira como data URI | a documentação da Replicate recomenda data URI só abaixo de 1 MB |
| 3 | O app esperava 72 s; o servidor, até `AI_TIMEOUT_S` (60 a 120 s) | geração lenta, mas dentro do prazo, aparecia como falha |
| 4 | "Parar de esperar" levava a "O serviço não respondeu" | mensagem falsa; a geração continuava e era cobrada |
| 5 | Uma única mensagem para toda falha | sem crédito, chave recusada e cota esgotada pareciam "serviço fora do ar" |
| 6 | Sem proteção no servidor contra envio repetido | toque duplo ou nova tentativa depois de a rede cair podiam pagar duas gerações |
| 7 | Tempo esgotado não cancelava a predição | o resultado podia ser cobrado sem ninguém ver |
| 8 | Erro 4xx do provedor ia para o log com até 500 caracteres do corpo | um corpo de erro que ecoasse a entrada levaria o começo da foto (base64) ao log |
| 9 | `AI_PROVIDER=replicate` sem `AI_API_KEY`: a falha do provedor não era tratada na criação | resposta 500 genérica, e a foto do cliente ficava órfã no storage |
| 10 | "Observações da simulação" era gravada mas não ia ao modelo | o campo sugeria que influenciava a imagem |
| 11 | O atendimento aberto a partir de uma simulação sugeria sempre "Coloração" | errado para simulação só de corte, que agora existe |

O item 9 foi confirmado executando o código original (ver [F.6](#f6-conferências-do-código-original)).

### B.3 Ambiente desta implementação

- `replicate.com`, `api.replicate.com` e `docs.expo.dev` responderam 403 no proxy do
  ambiente durante a primeira rodada, inclusive depois de você liberar o acesso
  (provavelmente porque a regra nova só vale para sessões criadas depois da mudança).
- A pesquisa sobre os modelos foi feita por buscador (fontes indiretas, citadas em
  [D.1](#d1-replicate-quais-modelos-e-por-quê)).

---

## C. Alterações implementadas

### C.1 Interface

**Etapa "Estilo e cor"** (`app/simulacao/parametros.tsx`), de cima para baixo:

- **Guia "Como preencher"**: uma frase sobre o que a tela faz ("Escreva com suas palavras o
  que o cliente quer. A simulação muda só o cabelo. Rosto, roupa e fundo continuam os da
  foto.") e os três passos numerados: corte, cor e "Revisar pedido" (a imagem só é gerada
  depois da revisão).
- **Passo 1, Corte**: número, título e selo de situação ("A preencher", "Pronto", "Sem
  mudança" ou "Corrigir"); uma frase que diz o que fazer; a caixa "Manter o corte atual
  (mudar só a cor)"; o campo "Novo corte" (multilinha, contador 0/300, exemplo no
  placeholder e uma dica: "Pode ser só o nome do corte, ou o nome com detalhes de
  comprimento, franja e camadas"); e o quadro "Exemplos de corte que você pode escrever",
  com uma linha "Em alta" e uma linha "Clássicos". Marcada a caixa, o campo e os exemplos
  somem e a frase passa a dizer que o corte fica como está na foto; desmarcada, o texto
  escrito antes volta.
- **Passo 2, Cor**: a mesma estrutura ("Manter a cor atual (mudar só o corte)", campo "Nova
  cor", dica sobre tom, reflexos e mechas, exemplos em alta e clássicos) e o aviso fixo de
  que tons bem claros (loiro claro, platinado, grisalho) sobre cabelo escuro tendem a sair
  menos fiéis.
- **Rodapé**: a primeira pendência, escrita como instrução ("Passo 1: escreva o novo corte
  ou marque "Manter o corte atual"."), ou "Pedido completo. Confira tudo na próxima tela
  antes de gerar."; e o botão "Revisar pedido", bloqueado enquanto houver pendência. Campo
  vazio não é erro enquanto a pessoa não escreve; texto inválido aparece no próprio campo,
  na hora.
- **Acessibilidade**: o título de cada passo é lido como "Passo 1: Corte, pronto" (o número
  desenhado fica oculto para o leitor de tela); as caixas de marcar têm papel de checkbox
  e alvo de toque de 44 px; o rodapé é região viva.

**Revisão** (`app/simulacao/revisao.tsx`, nova): foto do cliente; corte e cor, cada um com
"Editar" e, quando os dois mudam, "Não mudar"; "Como será gerado" (modo, modelo, aviso
quando o servidor está no modo local e "Ver o que vai para o modelo", com a instrução
exata); aviso do que é enviado; anotação para o histórico (que não vai ao modelo); "Gerar
simulação".

**Processamento, falha e resultado**:

- Foto reduzida no aparelho a 1536 px antes do envio.
- Chave de envio por tentativa; espera de até cerca de 150 s.
- "Parar de esperar" diz a verdade: a geração continua no servidor, e "Tentar novamente"
  retoma a mesma simulação, sem gerar outra.
- Tela de falha com motivo próprio para 17 códigos (chave ausente ou recusada, sem crédito,
  cota, provedor ocupado, tempo, filtro de segurança, resultado inválido, parâmetros
  recusados, modelo inexistente ou incompatível, sem conexão, interrompida...), "Tentar
  novamente" só quando faz sentido, "Mudar o pedido" e as escolhas visíveis e preservadas.
- Erros do pedido (descrição inválida ou longa, descrição livre desligada, pedido vazio)
  voltam direto à etapa, com o motivo.
- Resultado com "Corte:" e "Cor:" por extenso, o modelo usado e "Ver o que foi pedido ao
  modelo". "Refazer" volta às escolhas preenchidas.

**Outros pontos**: textos longos não vazam mais em selos e na comparação; o atendimento
aberto de uma simulação só de corte sugere "Corte".

### C.2 Serviços do aplicativo

- `src/utils/pedido.ts`: regras puras do pedido (as mesmas do servidor) e os rótulos da
  revisão e do histórico. Testado em Node.
- `src/data/catalogo.ts`: os exemplos de corte e de cor (`EXEMPLOS_DE_CORTE`,
  `EXEMPLOS_DE_COR`, cada um com `emAlta` e `classicos`) e os serviços.
- `src/services/api/index.ts`: contrato novo de envio e `plano` (prévia da revisão).

### C.3 Servidor

- `services/ai/pedido.py`: `PedidoCapilar` (corte e cor como `Alteracao` ou "manter"),
  limpeza e validação do texto, reconhecimento dos exemplos do catálogo.
- `services/ai/planos.py`: escolha do modelo (regra em [D.1](#d1-replicate-quais-modelos-e-por-quê)),
  montagem da entrada e conferência no schema.
- `services/ai/esquema.py`: leitura do OpenAPI publicado (segue `$ref`/`allOf`).
- `services/ai/instrucoes.py` e `glossario.py`: instruções em texto e termos em inglês.
- `services/ai/replicate.py`: reescrito (schema, arquivos, versão, cancelamento, logs
  seguros).
- `services/ai/fake.py`: mesmas regras de escolha; recolore com a amostra da cor quando ela
  é um dos exemplos.
- `services/catalogo.py`: os exemplos (em alta e clássicos), cada um com a descrição em
  inglês e, quando há, o valor equivalente nas opções do modelo principal.
- `services/simulacao.py`: criação com pedido e chave de envio; o plano é conferido no
  provedor **antes** de gravar e de contar na cota.
- `api/v1/simulacoes.py`: `POST /simulacoes` com o contrato novo e `POST /simulacoes/plano`.
- `diagnostico_ia.py`: conferência dos modelos sem custo.

### C.4 Contrato de dados

Envio (`POST /simulacoes`, multipart):

| Campo | Significado |
| --- | --- |
| `clienteId`, `foto` | como antes |
| `corte`, `manterCorte` | descrição do corte, ou manter o atual |
| `cor`, `manterCor` | descrição da cor, ou manter a atual |
| `chaveEnvio` | UUID da tentativa; repetir devolve a mesma simulação |
| `observacoes` | anotação para o histórico; não vai ao modelo |

O identificador do modelo **não** existe no contrato do app: só na configuração do servidor.

Resposta (`SimulacaoOut`): `parametros.estilo` e `parametros.cor` passam a ser a descrição
(ou "Corte atual", "Cor atual"); entra `instrucaoIa` (o que foi pedido ao modelo, sem a
imagem).

Prévia (`POST /simulacoes/plano`, JSON com `corte`, `manterCorte`, `cor`, `manterCor`):
devolve `provedor`, `modo`, `descricaoModo`, `modelo`, `instrucao`, `estilo` e `cor`. Não
envia foto e não gasta crédito.

### C.5 Banco de dados

Migration `b9d4e1f27c35_personalizacao_do_pedido` (reversível):

- `simulacoes.estilo` e `simulacoes.cor`: de 60 para 300 caracteres;
- `simulacoes.instrucao_ia` (texto, opcional);
- `simulacoes.chave_envio` (UUID, opcional) com índice único parcial por conta;
- `simulacoes.usou_referencia`, retirada na migration seguinte.

Migration `c6a2f9d41b87_remove_referencia_da_simulacao` (segunda rodada, reversível): apaga
`usou_referencia`. A volta recria a coluna e a preenche a partir do que ficou gravado em
`instrucao_ia` (a instrução do modelo de duas imagens sempre dizia que a segunda imagem era
só referência), sem inventar dado.

A volta da primeira se recusa se houver descrição acima de 60 caracteres, em vez de cortar o
texto. Nenhum campo espelha estado de tela.

### C.6 Configuração

Variáveis novas no `backend/.env.example` e no `docker-compose.yml`: `AI_MODELO_TEXTO`
(vazio desliga a descrição livre), `AI_INSTRUCAO_IDIOMA`, `AI_LIMITE_DATA_URI_KB`,
`AI_LADO_MAXIMO_ENVIO`, `AI_CACHE_ESQUEMA_MIN`. Os identificadores de modelo são validados
no formato `dono/nome`.

Nenhuma dependência nova no app nem no servidor: `package.json` e `package-lock.json` estão
iguais aos do commit `3130cd7`.

---

## D. Decisões técnicas

### D.1 Replicate: quais modelos e por quê

**Fontes.** O site da Replicate não abriu neste ambiente. Usei o buscador, que trouxe as
páginas de API de versões do `change-haircut` e páginas de terceiros. O que ficou
estabelecido e o que não:

| Fato | Situação |
| --- | --- |
| `change-haircut`: `input_image`, `haircut`, `hair_color`, `gender`, `aspect_ratio`, `output_format`, `seed`, `safety_tolerance` | dado por você e coerente com as fontes |
| `haircut` e `hair_color` são listas fechadas (≈ 90 cortes, 31 cores) | indício forte (página da API e descrições), **não confirmado** |
| Valores exatos das listas (ex.: "Pixie Cut", "Honey Blonde") | **não confirmados**; o servidor os confere no schema real |
| Data URI recomendado só abaixo de 1 MB; acima, `POST /v1/files` e `urls.get` | guia "Input files" (a referência HTTP antiga cita 256 KB) |

**Regra de escolha** (`planos.py`), com o schema ao vivo tendo a palavra final:

1. Corte e cor cabem nas opções do principal → `AI_MODELO` (`change-haircut`), com os
   valores exatos da lista publicada ("manter" vira `No change`).
2. Se o schema publicado do principal aceitar texto livre nesses campos → o próprio
   principal recebe a descrição.
3. Senão → `AI_MODELO_TEXTO` (`flux-kontext-pro`) com instrução em texto.

**Por quê.** O principal continua sendo usado sempre que o pedido cabe nele: é o modelo
especializado e é o que o projeto escolheu. Ele não é substituído; a descrição livre, que
ele (pelos indícios) não aceita, vai para o modelo da mesma família que aceita texto. O
`change-haircut` é, segundo a própria Replicate, uma aplicação construída sobre o FLUX.1
Kontext [pro]; usar o `flux-kontext-pro` diretamente, com instrução bem formulada, é o
caminho de menor distância técnica. Se o schema real mostrar texto livre, o passo 2 usa o
principal também para a descrição, sem mudar código. Se um exemplo não tiver equivalente
publicado, ele vai pelo texto, e nunca sai um valor inválido.

**Conferência antes de gastar.** `GET /models/{dono}/{nome}` é consulta de metadados, sem
cobrança. O schema fica guardado por 60 minutos. Campo essencial ausente ou valor fora das
opções param a geração com `modelo_incompativel` ou `parametro_fora_do_schema`, antes de
criar a predição; campo acessório ausente (proporção, formato) sai do envio.

**Modelo não oficial.** A rota `POST /models/{dono}/{nome}/predictions` só vale para
modelos oficiais. Se responder 404, o servidor repete em `POST /predictions` com a versão
lida do schema. Os dois caminhos estão implementados e testados.

### D.2 Exemplos em texto no lugar de botões

Na primeira rodada, a tela tinha 16 botões de sugestão de corte, uma paleta de 10 cores e
uma regra de "atalho" para combinar o botão com o texto digitado. Você pediu que os botões
saíssem e que a tela só citasse exemplos. A decisão:

- Os exemplos são **texto corrido**, em duas linhas por passo ("Em alta: ..." e
  "Clássicos: ..."), dentro de um quadro com o título "Exemplos de corte que você pode
  escrever". Não são tocáveis: não há estado de "selecionado", nem regra de combinação,
  nem como um toque sem querer apagar o que foi digitado.
- O que o profissional escreve é o pedido. Se escrever exatamente um exemplo ("Chanel"),
  o servidor reconhece o nome (sem diferenciar maiúsculas, acento ou hífen) e usa a
  descrição pronta em inglês e, quando existe, a opção equivalente do modelo principal.
  Qualquer outro texto vai como descrição livre.
- Os nomes são os mesmos no app e no servidor; um teste do servidor lê o arquivo do app e
  confere as quatro listas, e outro confere que todo exemplo é um pedido aceito.

A seleção dos exemplos (pesquisa e fontes) está em [M.4](#m4-pesquisa-dos-exemplos).

### D.3 Foto de referência e pedido por voz: implementados e retirados

Na primeira rodada, a foto de referência usava um segundo modelo (duas imagens), e o pedido
por voz gravava no aparelho (`expo-audio`) e transcrevia no servidor (Whisper, na
Replicate). Os dois funcionavam contra o servidor de mentira, mas:

- cada um acrescentava um modelo pago e sem preço confirmado, a referência com qualidade
  incerta (hipótese não comprovada de que o modelo transfere o corte e preserva a pessoa);
- a voz exigia permissão de microfone, uma dependência nativa e um teto próprio de uso;
- a tela ficava mais longa e mais difícil de entender para quem a vê pela primeira vez,
  que é o caso de uma banca de TCC.

Você decidiu retirá-los. A retirada foi completa (interface, serviços, rotas,
configuração, coluna do banco, dependência, textos de privacidade e testes) e está
detalhada em [M](#m-segunda-rodada-simplificação).

### D.4 Instruções e idioma

`flux-kontext-pro` recebe instrução em inglês (a documentação de prompts da Black Forest
Labs é em inglês, e o codificador de texto do FLUX foi treinado majoritariamente em
inglês). A descrição do profissional **não é traduzida nem resumida**: vai entre aspas,
como foi escrita, com os termos técnicos reconhecidos em inglês ao lado (`glossario.py`:
87 termos em inglês, reconhecidos por 197 formas em português). Exemplo real de saída:

```
Edit only the hair of the person in this photo. New haircut: "Corte degradê baixo nas
laterais, com topo médio e textura natural." (described in Brazilian Portuguese; key
terms: low fade, sides, top, medium-length, natural texture). Keep the current hair color
exactly as it is. Keep the same person: the face, identity, facial features, skin tone,
makeup, expression, head position, clothing, background and lighting must stay unchanged.
Photorealistic result with natural hair texture and a realistic hairline.
```

É uma hipótese a validar. `AI_INSTRUCAO_IDIOMA=pt` manda só o português, para comparar.
Nenhuma instrução garante fidelidade: modelos generativos interpretam o pedido de forma
aproximada.

### D.5 Arquivos

A foto é reduzida no aparelho (1536 px) e de novo no servidor antes do provedor
(`AI_LADO_MAXIMO_ENVIO`). Até 1 MB vai como data URI; acima, pela API de arquivos, com o
arquivo apagado da conta da Replicate ao fim, com sucesso ou falha. Nenhum dos dois expõe
a foto em URL pública.

### D.6 Custo e duplicidade

- Cota por conta (`SIMULACAO_MAX_POR_HORA`) vale para os dois modos.
- Problema de credencial, crédito ou schema aparece **na criação** (502 com o motivo), sem
  gravar nada nem contar na cota.
- Envio único por `chaveEnvio` (índice único no banco, conferido de novo com a conta
  travada; se duas requisições ainda chegarem juntas, a segunda bate no índice e devolve a
  simulação existente. Esse último caminho, de requisições simultâneas, não tem teste
  automatizado; o reenvio em sequência tem).
- Tempo esgotado cancela a predição.

### D.7 O que ficou de fora, de propósito

- `seed` não é enviado (padrão do modelo). `safety_tolerance` também não.
- `gender` passou a ser enviado depois deste relatório: a etapa "Estilo e cor" ganhou a
  opção "Gênero" (Feminino → `female`, Masculino → `male`, Não especificar → `none`, o
  padrão do modelo). Vai ao `change-haircut` no campo `gender`; no modelo de texto, que não
  tem o campo, vira uma frase da instrução. Fica gravado em `simulacoes.genero`.
- A "Observação" não vai ao modelo; virou "Anotação para o histórico".
- Foto de referência e pedido por voz ([D.3](#d3-foto-de-referência-e-pedido-por-voz-implementados-e-retirados)).

---

## E. Arquivos modificados

Em relação ao commit `3130cd7`.

### Criados

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/app/services/ai/pedido.py` | pedido de personalização: validação e reconhecimento dos exemplos |
| `backend/app/services/ai/planos.py` | escolha do modelo, montagem e conferência da entrada |
| `backend/app/services/ai/esquema.py` | leitura do schema publicado de cada modelo |
| `backend/app/services/ai/instrucoes.py` | instruções em texto para o modelo com `prompt` |
| `backend/app/services/ai/glossario.py` | termos de cabeleireiro em português e inglês |
| `backend/app/services/texto.py` | normalização de texto (comparação de nomes) |
| `backend/app/diagnostico_ia.py` | conferência dos modelos sem custo |
| `backend/migrations/versions/b9d4e1f27c35_personalizacao_do_pedido.py` | migration do pedido |
| `backend/migrations/versions/c6a2f9d41b87_remove_referencia_da_simulacao.py` | retirada da coluna da referência |
| `backend/tests/test_personalizacao.py` | 34 testes das regras puras |
| `backend/tests/test_personalizacao_api.py` | 12 testes das rotas, das migrations e da retirada |
| `espelho/app/simulacao/revisao.tsx` | tela de revisão do pedido |
| `espelho/src/utils/pedido.ts` | regras do pedido no app |
| `espelho/testes/pedido.mjs` | 48 verificações das regras do pedido e dos exemplos |
| `espelho/e2e/personalizacao.mjs` | bateria de navegador da etapa (60 verificações) |
| `RELATORIO_PERSONALIZACAO_IA.md` | este relatório |

### Alterados

| Arquivo | O que mudou |
| --- | --- |
| `backend/app/services/ai/replicate.py` | reescrito: schema, arquivos, versão, cancelamento, logs seguros |
| `backend/app/services/ai/base.py` | contrato do provedor: `preparar` e `gerar` com o pedido |
| `backend/app/services/ai/fake.py` | mesmas regras de escolha; cor dos exemplos |
| `backend/app/services/catalogo.py` | exemplos em alta e clássicos, ligados às opções do modelo |
| `backend/app/services/simulacao.py` | criação com pedido e chave; plano antes da cota; instrução gravada |
| `backend/app/api/v1/simulacoes.py` | contrato novo e a prévia do plano |
| `backend/app/schemas/simulacao.py` | `instrucaoIa`, pedido e plano |
| `backend/app/models/simulacao.py` | colunas novas |
| `backend/app/core/config.py` | variáveis novas e validação do formato `dono/nome` |
| `backend/app/main.py` | `/saude` lista os dois modelos |
| `backend/.env.example`, `backend/docker-compose.yml`, `backend/README.md` | configuração e documentação |
| `backend/tests/mock_provedor_ia.py` | schemas, arquivos, versões e cancelamento no servidor de mentira |
| `backend/tests/test_simulacao_com_mock_ia.py` | cenários novos com o cliente real |
| `backend/tests/test_contrato_com_aplicativo.py` | confere também o tipo `PlanoSimulacao` |
| `backend/tests/test_provedor_ia.py`, `test_simulacoes.py`, `test_limites_e_contratos.py`, `conftest.py` e mais 9 arquivos de teste | contrato novo (`corte` no lugar de `estilo`; ver [F.2](#f2-testes-existentes-que-mudaram)) |
| `espelho/app/simulacao/parametros.tsx` | tela redesenhada |
| `espelho/app/simulacao/processando.tsx` | redução da foto, chave de envio, erros por tipo, espera honesta |
| `espelho/app/simulacao/indisponivel.tsx` | motivo por código, escolhas preservadas |
| `espelho/app/simulacao/resultado.tsx` | pedido por extenso, instrução, "Refazer" com as escolhas |
| `espelho/app/simulacao/comparar.tsx`, `src/components/Basicos.tsx` | textos longos sem vazar |
| `espelho/app/atendimento/novo.tsx` | sugestão de serviço conforme a simulação |
| `espelho/src/data/rascunho.tsx`, `catalogo.ts`, `tipos.ts`, `store.tsx` | estado, exemplos, tipos e espera |
| `espelho/src/services/api/index.ts` | contrato de envio e prévia do plano |
| `espelho/src/components/Campo.tsx` | contador de caracteres (`limite`) |
| `espelho/e2e/fluxo-completo.mjs`, `e2e/auditoria.mjs`, `e2e/README.md`, `qa.sh`, `README.md`, `DOCUMENTACAO.md`, `RELATORIO_FINAL_IMPLEMENTACAO.md` | etapa nova nos roteiros, na suíte e na documentação |
| `espelho/e2e/fotos-e-camera.mjs` | concede a permissão da câmera no contexto do navegador de teste (ver F.5); confere que a câmera fora de vista não chama o servidor (M.7) |
| `espelho/app/simulacao/captura.tsx` | a conferência do enquadramento só roda com a tela em foco (M.7) |
| `backend/app/services/validacao_foto.py`, `backend/tests/test_validacao_foto.py` | trava no detector de rosto e o teste de concorrência (defeito anterior, ver [M.7](#m7-defeito-anterior-encontrado-nos-testes-detector-de-rosto)) |

Arquivos do commit apagados: nenhum. Os arquivos criados na primeira rodada e apagados na
segunda estão em [M.2](#m2-o-que-saiu).

---

## F. Testes executados

Resultados da execução final, com o código como está. "Automatizado" é executado por
máquina; "estático" é verificação sem execução; não houve teste manual em aparelho.

### F.1 Resumo

| Suíte | Tipo | Resultado |
| --- | --- | --- |
| Servidor (pytest, PostgreSQL real) | automatizado | commit: 439; primeira rodada: 527; agora: **507 passaram**, cobertura 92% |
| Tipos do app (`tsc --noEmit --noUnusedLocals`) | estático | 0 erros |
| Regras do pedido e exemplos no app (`testes/pedido.mjs`) | automatizado | 48 de 48 |
| Testes de unidade existentes do app | automatizado | todos passaram (duração 34, início do agendamento 9, painel 12, busca 9; datas 12 em cada um de dois fusos) |
| Bateria `personalizacao.mjs` (Chromium) | automatizado | **60 de 60** |
| Demais baterias de navegador | automatizado | todas passaram (F.5) |
| Travessões nos textos da interface | estático | nenhum encontrado |
| Código morto (sobras da retirada) | estático | nenhuma sobra (M.3) |

### F.2 Testes existentes que mudaram

Nenhum teste existente no commit foi removido. Foram ajustados porque o requisito mudou:

| Teste | Antes | Agora |
| --- | --- | --- |
| `test_simulacoes::test_parametros_fora_do_catalogo` | "Moicano fluorescente" recusado (`estilo_invalido`) | `test_descricao_livre_e_aceita_e_texto_invalido_recusado`: descrição livre aceita; marcação e texto longo recusados |
| `test_limites_e_contratos::test_parametros_fora_do_catalogo` | 4 casos, 2 deles "fora do catálogo" | `test_parametros_que_nao_sao_descricao`: 5 casos que continuam inválidos (vazio, script, chaves, só números, 301 caracteres) |
| `test_simulacoes::test_catalogo_publicado` | rótulos antigos | exemplos novos (em alta e clássicos) |
| `test_provedor_ia` (Replicate com HTTP simulado) | sem consulta de schema; valores em inglês livre | serve o schema; confere `haircut="Bob"`, `hair_color="Copper"` e a ordem schema → predição |
| 12 arquivos que criam simulação pela API | campo `estilo` | campo `corte` (o nome antigo deixou de ser aceito na segunda rodada) |

`test_simulacao_com_mock_ia::test_falhas_do_provedor`: o cenário `predicao_falhou`
continua esperando `falha_na_geracao` (o erro do servidor de mentira passou a ser genérico)
e entraram `bloqueio_de_seguranca`, `sem_saida` e `entrada_recusada`.

### F.3 Cenários de integração

| # | Cenário | Onde | Resultado |
| --- | --- | --- | --- |
| 1 | Foto, corte e cor descritos | `test_descricao_livre_vai_ao_modelo_de_texto_so_com_campos_dele`, bateria (passos 5 e 6) | ok |
| 2 | Exemplos com equivalente | `test_exemplos_vao_ao_principal_com_os_valores_das_opcoes`, bateria (passo 5) | ok |
| 3 | Só corte | `test_simulacao_com_descricao_livre_grava_o_pedido`, `test_manter_a_cor_e_mudar_o_corte` | ok |
| 4 | Só cor | `test_manter_corte_vai_como_no_change`, `test_manter_o_corte_e_mudar_a_cor` | ok |
| 5 | Corte e cor mantidos | `test_pedidos_invalidos[pedido_vazio]`, bateria (passo 3) | recusado, como a regra pede |
| 6 | Arquivo inválido | `test_foto_invalida_nao_chega_ao_provedor` | ok |
| 7 | Falha de comunicação com o backend | bateria, passo 7 (conexão derrubada) | ok, escolhas preservadas |
| 8 | Falha da API externa | `test_falhas_do_provedor` (12 cenários), `test_problemas_no_schema_param_antes_de_gastar` | ok |
| 9 | Predição em processamento | `test_predicao_em_andamento_e_acompanhada_ate_concluir`, `test_predicao_que_nao_termina_e_cancelada` | ok |
| 10 | Concluída sem resultado utilizável | cenários `sem_saida` e `imagem_invalida` | ok |
| 11 | Duplo clique / envio duplicado | `test_mesma_chave_...`, `test_reenvio_nao_agenda_outro_processamento`, `test_envio_repetido_gera_uma_predicao_so`, bateria (duplo clique = 1 envio) | ok |
| 12 | Nova tentativa após erro | bateria, passo 7 (mesma chave reaproveitada) | ok |
| 13 | Token ausente ou inválido | `test_replicate_sem_credencial_falha_claro`, `esquema_401`, `erro_4xx`, bateria (credencial recusada) | ok |
| 14 | Rotas e campos retirados não existem mais | `test_rotas_e_campos_removidos_nao_existem`, bateria (o envio não leva `referencia` nem `audio`) | ok |

Outros: cada modelo recebe só campos do próprio schema
(`test_cada_modelo_recebe_so_os_campos_que_aceita`); opções publicadas diferentes não
geram valor inválido; schema do principal com texto livre; modelo não oficial pela versão;
imagem grande pela API de arquivos e apagada (também quando a geração falha); credencial e
imagem fora dos logs; envio repetido não conta na cota; chave de outra conta não devolve
simulação alheia; as duas migrations vão e voltam, e a volta da primeira se recusa com
descrição longa.

### F.4 Falhas encontradas e corrigidas durante os testes

| Rodada | Onde | Falha | Correção |
| --- | --- | --- | --- |
| 1 | `test_pedidos_invalidos` | cor só com espaços era recusada como "descrição inválida", e não como "cor vazia" | `limpar_descricao` trata texto vazio depois da limpeza |
| 1 | `fluxo-completo.mjs` | depois de registrar o atendimento, o app ia para a câmera em vez da tela de sucesso | a revisão, montada na pilha, reagia à limpeza do rascunho; agora só confere ao abrir |
| 1 | `personalizacao.mjs` | o alternador "Ver o que foi pedido ao modelo" não tinha rótulo acessível próprio | rótulo acrescentado |
| 1 | Mutação | sem o filtro de log, a foto em base64 iria ao log | o teste falhou com a mutação e passou sem ela |
| 1 | Mutação | sem a guarda `if nova`, o reenvio agendaria outra geração paga | foi escrito `test_reenvio_nao_agenda_outro_processamento`, que pega |
| 2 | `test_simulacoes::test_fluxo_completo_da_simulacao` | a troca em massa de `estilo` por `corte` nos envios também trocou a chave da **resposta** (que continua `estilo`) | asserção corrigida para a resposta real |
| 2 | `e2e/auditoria.mjs` | o roteiro criava simulação direto pela API com o campo antigo `estilo`, que deixou de ser aceito | o roteiro passou a enviar `corte` |
| 2 | `test_contrato_com_aplicativo` | o tipo do app ainda declarava `usouReferencia` | tipo corrigido; o teste passou a conferir também `PlanoSimulacao` |
| 2 | `fluxo-completo.mjs`, numa execução intermediária | a foto válida do roteiro foi recusada como "Rosto não identificado"; investigado, era um defeito anterior do servidor (detector de rosto compartilhado entre threads) | trava no detector e teste de concorrência; detalhes em [M.7](#m7-defeito-anterior-encontrado-nos-testes-detector-de-rosto) |
| 2 | `personalizacao.mjs`, numa execução intermediária | o servidor de desenvolvimento do Expo, já no ar, não recarregou duas edições feitas depois (a troca de "Undercut" por "Caesar" e o tamanho da foto da revisão); a bateria acusou a lista antiga na tela | servidor reiniciado com cache limpo (`expo start --clear`), pacote servido conferido (sem "Undercut", sem voz) e a suíte inteira refeita do zero; os números de F.1 e F.5 são dessa execução |

### F.5 Regressão completa (`./qa.sh --interface`)

Executada com a API (`AI_PROVIDER=fake`, `MODO_DEMO=true`) e o `expo start --web` no ar,
recriando a carga de demonstração antes de cada bateria. A do Google não roda sem os IDs de
cliente configurados.

| Bateria | Resultado |
| --- | --- |
| Servidor, tipos, unidades do app, travessões | ok (números em F.1) |
| `fluxo-completo.mjs` | 27 de 27 |
| `qa-interface.mjs` (larguras, teclado, alvos, estados) | 22 de 22 |
| `mudancas-interface.mjs` | 21 de 21 |
| `agenda.mjs` | 27 de 27 |
| `atendimentos.mjs` | 49 de 49 |
| `painel-e-comparacao.mjs` | 18 de 18 |
| `fotos-e-camera.mjs` | 28 de 28 (3 verificações novas da câmera fora de vista) |
| `personalizacao.mjs` | 60 de 60 |
| `visual-contraste.mjs` | 46 telas (celular e tablet): 0 textos abaixo do contraste mínimo, 0 rolagens horizontais |
| `auditoria.mjs` | 29 de 29 |

O `qa.sh --interface` terminou com código 0.

**Ajuste na bateria de câmera (primeira rodada).** `fotos-e-camera.mjs` falhava nas 3
verificações da câmera ao vivo: a tela ficava em "Câmera não liberada". A causa é o
navegador deste ambiente (Chromium 141): aceitar o vídeo de mentira
(`--use-fake-ui-for-media-stream`) não muda mais o estado que `navigator.permissions`
informa, e a câmera do Expo na web decide por ele. O **código original** (commit `3130cd7`,
numa cópia temporária) falhou nas mesmas 3 verificações. A bateria concede a permissão da
câmera no contexto do navegador de teste, como um usuário faria ao aceitar o pedido. O
código da câmera não foi alterado.

### F.6 Conferências do código original

O item 9 de [B.2](#b2-outros-problemas-encontrados-no-fluxo) foi conferido executando o
código original (commit `3130cd7`, numa cópia temporária, com banco próprio, apagados
depois): com `AI_PROVIDER=replicate` e `AI_API_KEY` vazia, `POST /simulacoes` respondeu
**500 `erro_interno`** e deixou **um arquivo da foto do cliente no storage sem registro no
banco**. No código novo, o mesmo envio responde **502 `credencial_ausente`**, sem gravar
nada (`test_sem_chave_responde_o_motivo_e_nao_deixa_foto_orfa`).

---

## G. Testes não executados

| Teste | Por quê |
| --- | --- |
| Geração real em qualquer dos dois modelos | sem chave neste ambiente, e `api.replicate.com` bloqueado pela rede dele |
| Conferência do schema real (opções de `haircut` e `hair_color`) | idem; é o que `python -m app.diagnostico_ia` faz na sua máquina |
| Quais modelos são "oficiais" (rota usada) | idem; os dois caminhos estão implementados e testados contra o servidor de mentira |
| API de arquivos real (`/v1/files`) como entrada de modelo | idem; o caminho padrão (data URI até 1 MB) cobre as fotos já reduzidas |
| Tela em aparelho (Android e iOS, Expo Go) | não há aparelho neste ambiente; a tela foi verificada no Chromium em 320, 390 e 1280 px |
| Qualidade visual, preservação de identidade e fidelidade ao pedido | só com geração real e avaliação humana |
| Preços | não confirmados na página da Replicate (ver K) |

O servidor de mentira **não prova** o funcionamento real da IA: prova que o sistema fala o
protocolo descrito e reage a cada resposta como deve.

---

## H. Configuração necessária para o seu teste

### H.1 Atualizar o projeto

Na pasta `espelho` (o `expo-audio` da primeira entrega saiu; o `npm ci` o tira do seu
`node_modules`):

```bash
npm ci
npx expo start -c
```

Na pasta `backend`:

```bash
.venv/bin/pip install -r requirements.txt   # sem dependência nova; só por garantia
.venv/bin/alembic upgrade head              # migrations b9d4e1f27c35 e c6a2f9d41b87
```

(No Windows, `.venv\Scripts\python -m alembic upgrade head`.)

### H.2 `backend/.env`

```bash
AI_PROVIDER=replicate
AI_API_KEY=r8_...            # o token de https://replicate.com/account/api-tokens, sem aspas
AI_TIMEOUT_S=120
SIMULACAO_MAX_POR_HORA=3
```

Os modelos já têm padrão. `AI_MODELO_TEXTO=` (vazio) desliga a descrição livre: só os
exemplos com equivalente no modelo principal passam. Se o seu `.env` tiver sobrado da
primeira entrega com `AI_MODELO_REFERENCIA`, `AI_MODELO_TRANSCRICAO`,
`AI_TIMEOUT_TRANSCRICAO_S`, `TRANSCRICAO_MAX_POR_HORA` ou `AUDIO_MAX_BYTES`, pode apagar
essas linhas (o servidor as ignora). Nunca coloque a chave no app nem a envie em conversa.

### H.3 Conferir antes de gastar

```bash
.venv/bin/python -m app.diagnostico_ia
```

Leia a saída: para cada modelo, os campos e as opções publicadas; no principal, cada
exemplo do catálogo com o valor equivalente ("ok") ou "irá pela descrição livre". Se
aparecer "PROBLEMA" ou "ERRO", me mande a saída (ela não contém a chave).

Depois, reinicie a API e confira `GET http://localhost:8000/api/v1/saude`:
`provedorIa: "replicate"`, `credencialIa: true`, `modelosIa` com os dois modelos e
`bancoAtualizado: true`.

### H.4 Testes, do mais barato ao mais caro

Use uma cliente com uso de imagem autorizado (Marina, na carga de demonstração). Evite os
atalhos de demonstração ("Foto ruim", "Ver o que acontece se a simulação falhar").

1. **Exemplos (modelo principal).** Corte "Pixie" e cor "Loiro mel". Na revisão, "Como
   será gerado" deve dizer "Troca de corte e cor com as opções do modelo especializado" e
   a instrução `haircut=Pixie Cut; hair_color=Honey Blonde`.
2. **Só cor.** "Manter o corte atual" e cor "Ruivo".
3. **Descrição livre.** "Chanel na altura do queixo, com franja leve" e "castanho chocolate
   com reflexos caramelo". Revisão: "Edição a partir da descrição escrita", modelo
   `black-forest-labs/flux-kontext-pro`.
4. **Exemplo sem equivalente.** "Butterfly" e "Loiro manteiga": também vão pelo modelo de
   texto, com a descrição pronta em inglês.
5. **Comparação de idioma (opcional).** Repita o teste 3 com `AI_INSTRUCAO_IDIOMA=pt`.

Cada geração usa 1 da cota de 3 por hora. Os testes 1 a 4 cabem em duas horas; ou suba a
cota durante o teste e volte a 3 depois.

### H.5 Como identificar erros

| O app mostra | Código | O que fazer |
| --- | --- | --- |
| "O serviço de IA não está configurado" | `credencial_ausente` | `AI_API_KEY` vazia no servidor |
| "A chave do serviço de IA foi recusada" | `credencial_invalida` | gere outro token; sem aspas nem espaços |
| "Sem crédito no serviço de IA" | `sem_credito` | adicione crédito na Replicate |
| "Modelo não encontrado" | `modelo_inexistente` | confira `AI_MODELO` e `AI_MODELO_TEXTO` |
| "O modelo configurado não é compatível" / "Opção fora do que o modelo aceita" / "O serviço recusou os parâmetros" | `modelo_incompativel` / `parametro_fora_do_schema` / `entrada_recusada` | rode o diagnóstico e me mande a saída |
| "O filtro de segurança recusou o pedido" | `conteudo_bloqueado` | outra foto ou outra descrição |
| "A geração demorou demais" | `timeout` | tente de novo; se repetir, aumente `AI_TIMEOUT_S` |
| "O serviço está ocupado" | `limite_do_provedor` | espere um minuto |

O log da API registra o motivo de cada falha (sem chave e sem imagem). No painel da
Replicate (Predictions) aparecem as predições, com status e tempo.

---

## I. Limitações conhecidas

- O schema real dos dois modelos não foi visto; as opções do `change-haircut` usadas nos
  exemplos são suposição conferida ao vivo, e a que não existir vai pela descrição livre.
- A qualidade da descrição livre e da preservação de identidade é desconhecida até o teste
  real.
- A estratégia de idioma (português com termos em inglês) é hipótese.
- Os exemplos vêm de matérias de tendência e de portais de beleza, não de dados de venda
  de salões: não existe ranking oficial público dos cortes mais pedidos ([M.4](#m4-pesquisa-dos-exemplos)).
- A prévia ("Como será gerado") usa as regras sem consultar o provedor; a geração consulta
  o schema e pode escolher diferente (ex.: exemplo sem equivalente publicado). O resultado
  mostra o modelo usado de fato.

---

## J. Roteiro para o seu feedback

Para cada teste de H.4, anote:

1. A revisão mostrou o modo e o modelo esperados?
2. A geração concluiu? Em quantos segundos (aparece no cabeçalho do resultado)?
3. O rosto, a pele, a roupa e o fundo ficaram iguais?
4. O corte pedido apareceu? Comprimento, franja, camadas, textura?
5. A cor pedida apareceu? E, quando "manter", a cor ficou igual?
6. Algum erro? Me mande o título da tela de falha e a linha do log da API com o motivo.
7. A saída do `python -m app.diagnostico_ia`.
8. A tela "Estilo e cor" ficou clara para quem a vê pela primeira vez? Algum texto,
   selo ou exemplo confuso no celular?

---

## K. Custos e riscos operacionais

| Modelo | Uso | Preço | Situação |
| --- | --- | --- | --- |
| `flux-kontext-apps/change-haircut` | exemplos com equivalente | US$ 0,04 por imagem | informado por você a partir da página do modelo |
| `black-forest-labs/flux-kontext-pro` | descrição livre | cerca de US$ 0,04 por imagem | fontes de terceiros (uma cita US$ 0,055); **não confirmado** |
| `GET /models/...` (schema) | conferência | sem cobrança de predição | |

Riscos e proteções:

- **Crédito.** Cota de 3 gerações por conta e por hora; envio único por chave; falha de
  credencial ou schema antes de gastar; predição esgotada cancelada. Recarga automática
  desligada na Replicate continua recomendada.
- **Imagens no provedor.** A foto vai a outra empresa; os termos dela permitem uso para
  treinar modelos (já informado no termo do cliente). Arquivos enviados pela API de
  arquivos são apagados depois; data URI não cria arquivo na conta. Não há como verificar
  o que o provedor guarda internamente.
- **Imagens no sistema.** Foto do cliente e resultado seguem as regras de antes (storage,
  URL assinada, exclusão em cascata).

---

## L. Critérios de conclusão

| # | Requisito | Estado |
| --- | --- | --- |
| 1 | "Estilo e cor" reformulada e integrada ao fluxo | **concluído** |
| 2 | Foto original transmitida desde a etapa anterior | **concluído** (miniatura na etapa, foto na revisão, enviada reduzida) |
| 3 | Descrição livre de corte e cor | **concluído** |
| 4 | Escolhas convertidas nos parâmetros do modelo | **concluído** contra o servidor de mentira; **depende de confirmação** no schema real (diagnóstico) |
| 5 | Imagem de referência | **retirada** na segunda rodada, a seu pedido |
| 6 | Voz | **retirada** na segunda rodada, a seu pedido |
| 7 | Validação, erros e estados de processamento | **concluído** |
| 8 | Sem credenciais expostas e sem campos incompatíveis | **concluído** (testes de log, resposta e conferência de schema) |
| 9 | Testes executados e registrados | **concluído** (F) |
| 10 | Documentação e relatório | **concluído** |
| 11 | Você consegue iniciar e testar com a sua chave | **concluído** (H); depende do seu teste |
| 12 | Tela "Estilo e cor" autoexplicativa, com exemplos em texto no lugar dos botões | **concluído** (M) |
| 13 | Sem código morto da referência e da voz | **concluído** (M.3) |
| 14 | Defeito anterior que derrubava a API ou recusava foto válida sob uso simultâneo | **corrigido** (M.7), fora do pedido original |
| 15 | Câmera fora de vista conferindo o enquadramento | **corrigido** a seu pedido (M.7) |
| | Geração real e qualidade visual | **não executado** (sem chave e com a Replicate bloqueada neste ambiente) |

---

## M. Segunda rodada: simplificação

### M.1 O pedido

1. Remover por inteiro a foto de referência e o "falar o pedido", sem deixar elementos
   desnecessários no código.
2. Deixar a tela "Estilo e cor" mais intuitiva, para que fique claro o que há nela e como
   proceder; trocar os botões com nomes de cortes e cores por exemplos citados em texto,
   escolhidos a partir de uma pesquisa dos cortes mais pedidos hoje e dos atemporais.
3. Não prejudicar o funcionamento, não deixar código morto, testar e documentar.

### M.2 O que saiu

| Camada | Retirado |
| --- | --- |
| Tela "Estilo e cor" | painel "Falar o pedido", seção "Foto de referência", 16 botões de sugestão com "Ver mais", paleta de 10 cores com "Outra cor", regra de atalho (botão + texto digitado) |
| Revisão, falha e resultado | foto de referência ao lado da do cliente, linhas "Referência" e "Pedido falado", motivo `referencia_ausente`, selo "Com referência", envio da referência |
| Serviços e componentes do app | `src/services/voz.ts` (gravação e transcrição), `src/services/personalizacao.ts` (consulta de recursos), `src/components/Personalizacao.tsx` (caixa, sugestões, paleta, referência, painel de voz; a caixa de marcar foi para a própria tela) |
| Estado e tipos do app | `referencia` e `fala` no rascunho; `usouReferencia`, `RecursosSimulacao`, `Transcricao` e o modo `referencia` nos tipos; `recursos`, `transcrever`, `prepararArquivoParaEnvio` e o envio da referência na API do app; `entradaRef` no campo de texto; ícones de microfone e parar |
| Dependência e permissões | `expo-audio` (desinstalado com `npm uninstall`), permissão de microfone e as menções à referência nas permissões de câmera e galeria do `app.json` |
| Textos de privacidade | seção "Pedido por voz" e as menções à referência (os textos voltaram aos do commit, que coincidem com o termo de consentimento: sai "a foto do cliente e as duas escolhas do atendimento") |
| Rotas do servidor | `GET /simulacoes/recursos`, `POST /simulacoes/transcricao`, o arquivo `referencia` em `POST /simulacoes`, `comReferencia` na prévia e o nome antigo `estilo` (que só existia por compatibilidade) |
| Serviços do servidor | `services/ai/fala.py`, `services/validacao_audio.py`, `validar_referencia`, o modelo de duas imagens e a transcrição em `replicate.py`, `planos.py`, `instrucoes.py`, `fake.py` e `base.py`, o teto de transcrições em `core/protecoes.py` |
| Catálogo | os rótulos antigos aceitos por compatibilidade (nenhuma simulação nova os usa) |
| Banco | coluna `simulacoes.usou_referencia` (migration `c6a2f9d41b87`, reversível) |
| Configuração | `AI_MODELO_REFERENCIA`, `AI_MODELO_TRANSCRICAO`, `AI_TIMEOUT_TRANSCRICAO_S`, `TRANSCRICAO_MAX_POR_HORA`, `AUDIO_MAX_BYTES` (`.env.example`, `docker-compose.yml`, `config.py`, `/saude`, `diagnostico_ia.py`) |
| Testes | os testes do servidor que exercitavam referência, transcrição, voz, recursos e rótulos antigos (o total foi de 527 para 507, já contando os novos da retirada, dos exemplos e do detector de rosto); cenário de transcrição e schemas do Whisper e do modelo de duas imagens no servidor de mentira; verificações de voz, referência, atalhos e paleta nos roteiros do app |

Em linhas de código (Python e TypeScript, sem testes): o servidor passou de 8.489 para
7.842 linhas (contando a correção do detector de rosto, M.7), e o aplicativo de 14.580
para 13.587.

### M.3 Como foi verificado que nada ficou

- **Busca por nome** em todo o código, testes, roteiros e configuração: `referencia`,
  `transcri`, `whisper`, `multi-image`, `voz`, `audio`, `microfone`, `recursos`,
  `usouReferencia`, `usou_referencia`, `COMO_NA_REFERENCIA`, `SUGESTOES`, `CORES_CABELO`,
  `corDaPaleta`, `normalizarRotulo`, `aplicarAtalho`, `PainelDeVoz`, `expo-audio`. O que
  sobra são usos sem relação (data de referência em idade, hash de referência no login,
  "leia em voz alta" no termo) e o histórico das migrations, que não se altera.
- **Imports e nomes sem uso no servidor**: `ruff` com as regras do pyflakes (`F`) em `app`,
  `tests` e `migrations`: nenhum aviso.
- **Variáveis locais sem uso no app**: `tsc --noEmit --noUnusedLocals`: nenhum erro.
- **Exportações sem uso no app**: um levantamento de cada `export` de `src/` e `app/` sem
  import em outro arquivo. Nada do que foi mexido ficou sem uso; os itens que aparecem já
  existiam assim no commit.
- **Dependências**: `package.json` e `package-lock.json` ficaram idênticos aos do commit.
- **Contrato publicado**: `test_rotas_e_campos_removidos_nao_existem` lê o OpenAPI da API e
  confere que não há rota de transcrição nem de recursos e que o formulário de envio não
  tem `referencia`.

### M.4 Pesquisa dos exemplos

**Não existe ranking oficial público** dos cortes e cores mais pedidos nos salões
brasileiros. As fontes encontradas são matérias de tendência, portais de beleza e blogs de
aplicativos de simulação, em geral com base na percepção de profissionais. Os exemplos
foram escolhidos pelo que essas fontes repetem, preferindo nomes que o profissional de
salão usa no dia a dia.

**Cortes em alta**

| Exemplo | O que as fontes dizem |
| --- | --- |
| Long bob estruturado | long bob de volta entre os mais pedidos, com acabamento mais definido (Folha Vitória; YouCam: linhas limpas) |
| Bob texturizado | bob segue entre os favoritos, mais texturizado, com camadas suaves |
| Butterfly | virou febre nas redes e continua forte |
| Shaggy com franja | shaggy bob com franja citado entre os mais pedidos em salões brasileiros (YouCam) |
| Chanel de bico | modelos geométricos como o chanel com bico (Estado de Minas) |
| Degradê | o fade lateral ("corte americano") aparece como líder nas barbearias (YouCam) |
| Mullet moderno | logo atrás do fade nas barbearias (YouCam) |
| Texturizado curto | um dos mais pedidos nas barbearias brasileiras |

**Cortes clássicos**

| Exemplo | O que as fontes dizem |
| --- | --- |
| Chanel | um dos estilos mais tradicionais, na altura do queixo e com base reta |
| Pixie | corte curto e prático, popular desde os anos 50 |
| Camadas longas | mantêm o comprimento e dão movimento |
| Franja reta | opção de visual clássico e elegante |
| Corte social | as fontes falam em risca lateral (side part) e "classic taper", laterais curtas e topo penteado, apontados como cortes que nunca saem de moda; "corte social" é o nome usado no Brasil para esse corte |
| Caesar | curto, com franja reta, citado entre os clássicos masculinos em alta |

Na pesquisa da segunda rodada, o "Undercut" (que estava na lista) **não** apareceu como
clássico em nenhuma fonte e foi trocado pelo Caesar.

**Cores em alta**: loiro manteiga e morena iluminada (citadas como as apostas de 2026),
loiro mel, chocolate quente (castanho médio com reflexos dourados), cobre canela (ruivo
fechado com marrom) e vermelho bordô. As fontes também registram o movimento de fugir do
platinado extremo, por manutenção.

**Cores clássicas**: preto natural, castanho-escuro, castanho-claro, loiro, ruivo e
grisalho. São os tons de base que qualquer profissional reconhece, e todos têm equivalente
provável nas opções do modelo principal; não vieram de um ranking.

**Fontes consultadas**

- Folha Vitória, ["Cinco cortes de cabelo femininos para começar 2026 com um visual renovado"](https://www.folhavitoria.com.br/viralizou/cinco-cortes-de-cabelo-femininos-para-comecar-2026-com-um-visual-renovado-viral/)
- Jornal do Brás, ["Corte de cabelo feminino: quais os cortes serão tendência em 2026?"](https://jornaldobras.com.br/noticia/111164/corte-de-cabelo-feminino-quais-os-cortes-serao-tendencia-em-2026)
- Super Rádio Tupi, ["Cortes de cabelo femininos que vão bombar em 2026"](https://www.tupi.fm/?p=2243634)
- Estado de Minas, [Em foco](https://www.em.com.br/emfoco/?p=154987)
- YouCam, [cortes e cores em alta para mulheres](https://www.perfectcorp.com/pt/consumer/blog/hair/trendy-haircuts-color-for-woman) e [cortes masculinos em alta](https://www.perfectcorp.com/pt/consumer/blog/hair/trending-men-haircuts)
- TNH1, ["5 cortes de cabelo masculino em alta em 2026"](https://www.tnh1.com.br/noticia/nid/5-cortes-de-cabelo-masculino-em-alta-em-2026-5651/)
- Estado de Minas, ["Loiro manteiga ou morena iluminada: veja as tendências de cores de cabelo para 2026"](https://www.em.com.br/emfoco/2026/01/02/loiro-manteiga-ou-morena-iluminada-veja-as-tendencias-de-cores-de-cabelo-para-2026/)
- Elle Brasil, ["7 tendências de cores de cabelo que devem dominar o inverno 2026"](https://elle.com.br/?p=196198)
- Catraca Livre, ["As 5 colorações de cabelo que serão tendência no inverno de 2026"](https://catracalivre.com.br/saude-bem-estar/o-fim-das-cores-escuras-estas-sao-as-5-coloracoes-de-cabelo-que-serao-tendencia-no-inverno-de-2026/)
- Folha Vitória, ["5 cortes de cabelo para renovar o visual e valorizar mulheres acima dos 50"](https://www.folhavitoria.com.br/beleza/5-cortes-de-cabelo-para-renovar-o-visual-e-valorizar-mulheres-acima-dos-50-viral/)
- Super Rádio Tupi, ["Os cortes de cabelo que te deixam até 10 anos mais jovem"](https://www.tupi.fm/?p=1938340)
- YouCam, [tendências de cabelo](https://www.perfectcorp.com/pt/consumer/blog/hair/hair-trends)
- DCI, ["Cortes de cabelo 2021"](https://www.dci.com.br/industria/beleza/corte-de-cabelo-2021/)
- Correio Braziliense, ["4 cortes de cabelo masculinos clássicos em alta"](https://www.correiobraziliense.com.br/revista-do-correio/2025/11/7285299-4-cortes-de-cabelo-masculinos-classicos-em-alta.html)
- YouCam, [cortes clássicos masculinos](https://www.perfectcorp.com/pt/consumer/blog/photo-editing/classic-hairstyles-for-men)

### M.5 Outros ajustes desta rodada

- **Prévia com o provedor.** A revisão dizia "o servidor está no modo local" a partir da
  rota de recursos, que saiu. A prévia do plano (`POST /simulacoes/plano`) passou a
  devolver `provedor`, e a revisão usa esse campo.
- **Revisão.** Sem a coluna da referência, a foto do cliente ficou com a largura que tinha
  quando dividia a linha (170 px), e "Não mudar" aparece nos dois itens só quando corte e
  cor mudam.
- **Regras do pedido.** As mensagens de pendência citam o passo ("Passo 1: escreva o novo
  corte ou marque "Manter o corte atual"."), para casar com a numeração da tela.

### M.6 Testes desta rodada

Todos os números de [F](#f-testes-executados) são da execução final desta rodada. Os
testes novos ou reescritos para a simplificação:

- servidor: `test_exemplos_do_aplicativo_e_do_servidor_nao_divergem` (lê as quatro listas
  do app), `test_cada_exemplo_e_um_pedido_aceito`, `test_cada_exemplo_tem_descricao_em_ingles`,
  `test_texto_que_nao_e_exemplo_nao_e_reconhecido`, `test_rotas_e_campos_removidos_nao_existem`,
  `test_volta_da_remocao_da_referencia_recria_a_coluna_pelo_que_foi_gravado`, a migration
  que vai e volta sem a coluna, e o contrato do tipo `PlanoSimulacao`;
- app: `testes/pedido.mjs` (48 verificações: pendências, mensagens, rótulos, exemplos sem
  repetição e todos aceitos pelas regras);
- navegador: `personalizacao.mjs` reescrita (60 verificações: guia, selos dos passos,
  exemplos em texto e nenhum botão de exemplo, "manter o atual", validação, revisão com
  exemplo exato e com descrição livre, envio único sem `referencia` nem `audio`, erros
  com escolhas preservadas, 320, 390 e 1280 px, alvos de toque e console sem erros), e
  `fluxo-completo.mjs` escrevendo corte e cor em vez de tocar em botões.

### M.7 Defeito anterior encontrado nos testes: detector de rosto

**Fora do que você pediu, mas no caminho principal da simulação.** Numa execução da suíte,
o roteiro `fluxo-completo.mjs` teve a foto do cliente recusada pelo servidor como "Rosto não
identificado", com a mesma imagem que passa em todas as outras execuções. Investigado:

- O servidor usa **um único** classificador do OpenCV (`cv2.CascadeClassifier`, guardado
  com `lru_cache`) para todas as requisições. O FastAPI atende as rotas síncronas num
  conjunto de threads, então a validação da foto (`POST /simulacoes`) e a conferência do
  enquadramento (`POST /simulacoes/enquadramento`, que a câmera chama várias vezes por
  segundo) podem usar o classificador ao mesmo tempo.
- O classificador não suporta isso. Reproduzi fora da API, com 8 threads validando o
  retrato enquanto outras conferiam quadros sem rosto: o processo Python **caiu com falha
  de segmentação** em 3 de 3 execuções; sem concorrência, 160 validações e nenhuma recusa.
  Na API, o efeito é recusar uma foto válida ou derrubar o servidor.
- O arquivo (`services/validacao_foto.py`) estava igual ao do commit `3130cd7`: o defeito
  é anterior a este trabalho. Ele aparece no fluxo porque, na web, a tela da câmera
  continua montada na pilha e segue conferindo o enquadramento enquanto o profissional
  está em "Estilo e cor" e na revisão.

**Correção:** uma trava (`threading.Lock`) em volta da detecção, que leva milissegundos numa
imagem de 640 px. **Teste novo:** `test_deteccao_de_rosto_simultanea_nao_falha_nem_derruba_o_processo`
roda a mesma concorrência num processo à parte; sem a trava, falha com "o processo caiu
(código -11)"; com a trava, passa. O roteiro de reprodução, repetido 3 vezes depois da
correção: nenhuma queda e nenhuma recusa falsa.

**A causa no aplicativo, corrigida a seu pedido depois:** a conferência do enquadramento
continuava rodando enquanto a tela da câmera estava na pilha, mas fora de vista, tirando
miniaturas e chamando o servidor durante todo o pedido. Agora ela só liga com a tela em foco
(`useIsFocused`, do `expo-router`, em `app/simulacao/captura.tsx`); ao voltar para a câmera,
religa sozinha. O `active` do `CameraView`, que pararia a sessão da câmera, não foi usado
porque só vale no iOS.

Verificação nova em `fotos-e-camera.mjs`: com a câmera de mentira do Chromium, escolhe a foto
da galeria, conta as conferências durante 6 segundos em "Estilo e cor" e depois volta à
câmera. Com a tela do commit (sem a condição do foco), a bateria acusou **5 conferências em
6 s** com a câmera fora de vista; com a correção, **0**, e de volta à câmera a conferência
religou (4 em 5 s).
