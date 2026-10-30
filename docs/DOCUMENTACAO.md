# Espelho — documentação da interface

Documento de apoio ao TCC *Aplicativo Mobile com Inteligência Artificial para Simulação
Capilar e Gestão de Clientes em Serviços de Beleza* (Nícolas Marin Corneli, Sistemas de
Informação, Faculdade Antônio Meneghetti). Descreve a interface do aplicativo: telas,
decisões de design, divergências em relação ao pré-projeto e ao design original, e a
revisão de usabilidade e acessibilidade.

> **Nota desta versão.** Quando este documento foi escrito, o aplicativo funcionava
> sozinho, com dados fictícios e serviços simulados. O sistema já está integrado a um
> back-end real — FastAPI, PostgreSQL, storage de objetos e provedor de IA. O que mudou
> está em [`DOCUMENTACAO-BACKEND.md`](DOCUMENTACAO-BACKEND.md); a auditoria que precedeu
> a integração, em [`DIAGNOSTICO-E-ARQUITETURA.md`](historico/DIAGNOSTICO-E-ARQUITETURA.md); e as
> instruções de execução, em [`backend/README.md`](../backend/README.md). As seções a seguir
> descrevem a interface, que foi preservada; onde um trecho vale apenas para a versão
> anterior, há um aviso como este.

---

## 1. Resumo do que foi implementado

Esta etapa entrega **apenas a camada de apresentação** do aplicativo — as 22 telas
desenhadas no Claude Design, funcionando como aplicativo real (navegação, formulários,
câmera, persistência local), com dados fictícios no lugar do back-end.

O aplicativo cobre o fluxo completo descrito na seção 5.7 do pré-projeto:

consentimento (T0) → autenticação (T1) → dashboard (T2) → cliente (T3/T4) →
captura (T5) → parâmetros (T6) → processamento → resultado (T7) → registro do
atendimento com vínculo à simulação → agenda (T8).

Funcionalidades operantes no protótipo:

| Requisito | Situação nesta etapa |
| --- | --- |
| RF01 Autenticação | Tela e validação de formulário; sessão apenas local (mock) |
| RF02 Cadastro de clientes | CRUD completo em memória + armazenamento local |
| RF03 Histórico de atendimentos | Registro com data, serviço, observações e vínculo opcional |
| RF04 Simulação capilar | Captura real, parametrização e resultado fabricado localmente |
| RF05 Persistência da simulação | Salva no dispositivo, vinculada ao cliente |
| RF06 Agenda | Calendário mensal, criação de agendamento, status |
| RF07 Comparação | Duas simulações lado a lado, escolhidas numa grade; a preferida se marca no perfil do cliente, em cada simulação |
| RF08 Recomendação automática | Fora do escopo, como define o pré-projeto (*won't have*) |
| RNF05 Privacidade/LGPD | Consentimento por cliente, com histórico, revogação e exclusões (ver seção 8) |

Em uma segunda etapa, o fluxo de consentimento foi reestruturado: ele deixou de ser uma
declaração única do profissional e passou a ser uma decisão individual de cada cliente,
com histórico, revogação e bloqueio efetivo da câmera. A seção 8 documenta a mudança, a
fundamentação na LGPD, o modelo de dados proposto e os endpoints correspondentes.

---

## 2. Stack escolhida e justificativa

| Camada | Tecnologia | Justificativa |
| --- | --- | --- |
| Aplicativo | **React Native 0.86 + Expo SDK 57** | É a stack declarada na seção 5.4 do pré-projeto. O Expo dá acesso a câmera e galeria sem código nativo e permite rodar o mesmo código no celular (Expo Go) e no navegador, o que facilita a demonstração para a banca. |
| Linguagem | **TypeScript** (modo estrito) | Tipar as cinco entidades da seção 5.6 no front-end cria um contrato explícito com o back-end que será escrito depois em FastAPI. |
| Navegação | **expo-router** (rotas por arquivo) | A estrutura de arquivos passa a ser o mapa de telas, o que mantém a rastreabilidade com a Tabela 5 do pré-projeto. |
| Estado | **Context + `useReducer`** | O volume de dados é pequeno e o domínio é simples; uma biblioteca de estado global (Redux, Zustand) acrescentaria dependência sem ganho. |
| Persistência local | **AsyncStorage** | Permite testar com usuários reais (5 a 10 participantes, seção 5.10) antes de o back-end existir: os dados sobrevivem ao fechamento do app. |
| Câmera e galeria | **expo-camera**, **expo-image-picker** | Cobrem a tela T5 sem código nativo. |
| Tipografia | **@expo-google-fonts** (Instrument Serif, Familjen Grotesk) | São exatamente as fontes do design exportado. |
| Gradiente | **expo-linear-gradient** | Usado na tonalização que simula a troca de cor do cabelo. |

Não foi adicionada biblioteca de componentes de interface (React Native Paper, NativeBase
etc.): o design tem identidade própria, e usar um kit pronto obrigaria a sobrescrever
quase todos os estilos. Os componentes foram escritos sobre `StyleSheet`, com os tokens
de cor, tipografia e raio extraídos do arquivo de design (`src/theme/tokens.ts`).

---

## 3. Arquitetura de pastas

```
espelho/
├── app/                        rotas (expo-router) — uma tela por arquivo
│   ├── _layout.tsx             providers, carregamento de fontes
│   ├── index.tsx               redirecionamento conforme a sessão
│   ├── onboarding.tsx          boas-vindas
│   ├── login.tsx               T1 — autenticação
│   ├── responsabilidades.tsx   ciência das responsabilidades do profissional (bloqueante)
│   ├── consentimento/
│   │   └── [clienteId].tsx     termo apresentado ao cliente + registro da decisão
│   ├── termo/
│   │   └── [clienteId].tsx     consulta do termo, somente leitura (seção 8.7)
│   ├── privacidade.tsx         LGPD art. 18
│   ├── (tabs)/                 navegação principal
│   │   ├── _layout.tsx         barra de abas própria (botão central de simulação)
│   │   ├── index.tsx           T2 — dashboard (+ estado de primeiro uso)
│   │   ├── clientes.tsx        T3 — lista (+ estado vazio)
│   │   ├── agenda.tsx          T8 — calendário e compromissos do dia
│   │   └── perfil.tsx          conta do profissional
│   ├── cliente/
│   │   ├── [id].tsx            T4 — perfil do cliente
│   │   └── editar.tsx          cadastro e edição
│   ├── simulacao/
│   │   ├── cliente.tsx         escolha do cliente — primeira etapa da simulação
│   │   ├── captura.tsx         T5 — câmera, liberada só com consentimento válido
│   │   ├── recusada.tsx        recusa local da foto
│   │   ├── parametros.tsx      T6 — estilo, cor e observações
│   │   ├── processando.tsx     espera da inferência
│   │   ├── resultado.tsx       T7 — antes/depois e aviso de aproximação
│   │   ├── indisponivel.tsx    falha do provedor de IA
│   │   └── comparar.tsx        RF07 — comparação lado a lado
│   ├── atendimento/
│   │   ├── novo.tsx            RF03 — registro com vínculo à simulação
│   │   └── sucesso.tsx         confirmação
│   └── agendamento/novo.tsx    RF06 — criação de agendamento
├── src/
│   ├── components/             design system: Tela, Botao, Campo, CampoData, Cartao,
│   │                           Grupo, Selo, Avatar, Aviso, Chip, Alternador, Icone,
│   │                           Esqueleto, Feedback (toast e confirmação), FolhaAcoes,
│   │                           Cabecalho, EstadoVazio, SeloConsentimento, TermoTexto,
│   │                           Hachura, ImagemSimulada, SeletorCliente
│   ├── data/                   tipos das entidades, catálogo de estilos/cores, textos
│   │                           versionados dos termos, dados de exemplo, store (Context)
│   │                           e rascunho da simulação
│   ├── services/               authService, simulacaoService e consentService —
│   │                           fronteira com o back-end
│   ├── theme/                  tokens (cor, espaço, raio, elevação) e escala tipográfica
│   └── utils/                  datas em pt-BR e máscaras de entrada
└── DOCUMENTACAO.md (na raiz do repositório)
```

**Decisão central de arquitetura:** tudo que um dia será uma chamada de rede está isolado
em `src/services/`. As telas não sabem que os dados são falsos — elas chamam
`entrar()`, `validarFoto()` e `gerarSimulacao()`. Quando o back-end em FastAPI existir,
basta trocar o corpo dessas funções por `fetch`, sem tocar nas telas. Os pontos estão
marcados com o comentário `TODO:BACKEND` (lista na seção 7).

O mesmo vale para as regras de consentimento: nenhuma tela decide sozinha se pode abrir a
câmera — todas perguntam a `consentService.avaliarCaptura()`. Isso concentra a regra em um
único arquivo testável e evita que um caminho novo de navegação escape do bloqueio.

Os nomes de tipos e campos estão em português e espelham a Tabela 4 do pré-projeto
(`clientes`, `simulacoes`, `historico_servicos`, `agendamentos`, mais a nova entidade
`consentimentos` descrita na seção 8), justamente para manter
a rastreabilidade entre a modelagem descrita no texto e o código entregue.

---

## 4. Correspondência entre as telas do pré-projeto e as telas implementadas

O pré-projeto descreve nove telas (Tabela 5) e o design entregou 22, incluindo estados
vazios, de erro e de sucesso. Todas foram implementadas; a reestruturação do consentimento
(seção 8) acrescentou mais duas — a escolha do cliente antes da câmera e o termo
apresentado ao próprio cliente —, totalizando 24.

| Pré-projeto | Tela implementada | Arquivo |
| --- | --- | --- |
| — | Boas-vindas | `app/onboarding.tsx` |
| T1 Login | Entrar | `app/login.tsx` |
| T0 Consentimento (parte do profissional) | Ciência das responsabilidades | `app/responsabilidades.tsx` |
| T0 Consentimento (parte do cliente) | Termo de uso de imagem e registro da decisão | `app/consentimento/[clienteId].tsx` |
| — | Consulta do termo (somente leitura) | `app/termo/[clienteId].tsx` |
| T2 Dashboard | Dashboard | `app/(tabs)/index.tsx` |
| — | Dashboard de primeiro uso (vazio) | mesmo arquivo, derivado dos dados |
| T3 Lista de clientes | Clientes | `app/(tabs)/clientes.tsx` |
| — | Lista vazia | mesmo arquivo, derivado dos dados |
| — | Novo cliente / editar | `app/cliente/editar.tsx` |
| T4 Perfil do cliente | Perfil do cliente | `app/cliente/[id].tsx` |
| — | Escolha do cliente da simulação | `app/simulacao/cliente.tsx` |
| T5 Simulador: captura | Captura (com bloqueio por consentimento) | `app/simulacao/captura.tsx` |
| — | Foto recusada | `app/simulacao/recusada.tsx` |
| T6 Simulador: parâmetros | Estilo e cor: guia "Como preencher", corte e cor descritos em dois passos com exemplos em texto e "manter o atual" (ver `RELATORIO_PERSONALIZACAO_IA.md`) | `app/simulacao/parametros.tsx` |
| — | Revisão do pedido antes de gerar | `app/simulacao/revisao.tsx` |
| — | Processando | `app/simulacao/processando.tsx` |
| T7 Simulador: resultado | Resultado | `app/simulacao/resultado.tsx` |
| — | IA indisponível | `app/simulacao/indisponivel.tsx` |
| RF07 | Comparar simulações | `app/simulacao/comparar.tsx` |
| RF03 | Registrar atendimento | `app/atendimento/novo.tsx` |
| — | Atendimento registrado | `app/atendimento/sucesso.tsx` |
| T8 Agenda | Agenda | `app/(tabs)/agenda.tsx` |
| — | Novo agendamento | `app/agendamento/novo.tsx` |
| — | Perfil e ajustes | `app/(tabs)/perfil.tsx` |
| RNF05 | Privacidade e meus dados | `app/privacidade.tsx` |

---

## 5. Divergências entre a proposta do PDF e o que foi implementado

**5.1 Escopo da entrega: front-end isolado, sem back-end.**
O pré-projeto descreve um sistema de quatro camadas (aplicativo, FastAPI, PostgreSQL e
Replicate API). Esta etapa implementa só a primeira. Justificativa: permite validar o
fluxo e a usabilidade com usuários antes de investir na integração, o que é coerente com
o desenvolvimento incremental do DSDM (seção 5.2) — a primeira iteração entrega uma fatia
observável e ajustável.

**5.2 Autenticação (RF01) é simulada.**
Não há Supabase Auth nem validação de JWT. O formulário valida formato de e-mail e
tamanho de senha e cria uma sessão local. Justificativa: autenticação real exige o
provedor de identidade e o back-end que valida o token; sem eles, qualquer implementação
seria descartada depois. O ponto de troca está em `src/services/authService.ts`.

**5.3 A simulação (RF04) não usa modelo de difusão.**
A imagem "depois" é a própria foto do cliente com uma camada de cor aplicada sobre a
faixa superior do quadro, na tonalidade escolhida. **Isso não é segmentação capilar**: é
um recurso de demonstração para que o fluxo antes/depois possa ser percorrido e avaliado.
Nenhuma imagem sai do aparelho. Justificativa: a inferência depende da Replicate API, que
é responsabilidade do back-end (seção 5.8). O tempo de espera é simulado em cerca de
três segundos, contra os 8 a 25 segundos que o design anuncia.

**5.4 Persistência (RF05) é local, não em nuvem.**
Os dados ficam no `AsyncStorage` do próprio aparelho, não no PostgreSQL nem no Supabase
Storage. Não há Row-Level Security, criptografia AES-256 em repouso nem URLs assinadas —
esses são atributos do RNF03 que pertencem à infraestrutura. As telas continuam afirmando
essas garantias porque descrevem o sistema final; o texto do TCC deve deixar claro que,
nesta etapa, elas ainda não estão implementadas.

**5.5 Validação da imagem é parcial.**
O pré-projeto (seções 4.2 e 5.8) prevê rejeitar fotos escuras, com rosto encoberto ou em
ângulo. No dispositivo, sem acesso aos pixels, só é possível verificar resolução mínima
(480 px no menor lado) e proporção do enquadramento. A análise de luminância e a detecção
de rosto ficam para o pré-processamento no FastAPI. Para que o caminho de erro pudesse
ser demonstrado e avaliado, a tela de captura tem um atalho explícito
("simular foto ruim") que aciona a recusa com os dois motivos previstos no design.

**5.6 Notificação local da agenda (RF06) não é agendada.**
O interruptor "lembrete local" grava a preferência, mas nenhuma notificação é programada
(faltaria `expo-notifications`, que exige configuração de build). A intenção do usuário
fica registrada no dado.

**5.7 RF07 (comparação) foi implementado, embora seja *could have*.**
O design já entregava a tela, e ela é o que torna visível a ideia de "apoiar a decisão
estética". Como não há custo de inferência envolvido, implementar não competiu com os
*must have*.

**5.8 RF08 (recomendação automática por perfil facial) permanece fora**, como o
pré-projeto determina.

**5.9 O consentimento mudou de titular em relação ao pré-projeto.**
A Tabela 5 descreve a tela T0 como "registrar o consentimento explícito do profissional
antes do primeiro uso da câmera". Isso não corresponde à LGPD: o titular da imagem é o
cliente fotografado, e é dele que precisa partir a manifestação (art. 5º, XII). A tela T0
foi então desdobrada em duas — a ciência das responsabilidades do profissional e o termo
de uso de imagem de cada cliente —, conforme a seção 8. **Esta é a divergência mais
relevante desta etapa e deve ser incorporada ao texto final do TCC**, porque corrige um
erro conceitual do pré-projeto, e não apenas a interface.

**5.10 Contadores passaram a ser reais.**
O design mostra números fixos (48 clientes, 137 simulações). No app, todos os contadores
são calculados a partir dos dados existentes, para que não haja informação falsa na tela
durante os testes com usuários.

---

## 6. Ajustes feitos em relação ao design original

Todos os ajustes abaixo são intencionais; o restante do design foi seguido fielmente
(paleta, tipografia, espaçamentos, hierarquia e textos).

1. **Moldura de protótipo removida.** O arquivo `.dc.html` desenha um painel lateral com
   as 22 telas, a moldura de um celular e uma nota de design sob cada tela. Isso é
   andaime de apresentação, não interface: o aplicativo real é apenas o conteúdo da tela.
   As notas de design foram aproveitadas neste documento.

2. **Barra de status falsa removida.** O design desenha "9:41" e os ícones do sistema; o
   aplicativo usa a barra de status real do aparelho.

3. **Áreas de toque ampliadas.** Vários controles do design têm 36 px (botões de voltar,
   "+", alternadores). Eles mantêm o tamanho visual, mas receberam área de toque de 44 px
   via `hitSlop`, patamar recomendado pelas diretrizes de acessibilidade de iOS e Android.

4. **Rótulos para leitores de tela.** Botões representados apenas por símbolos (←, ✕, +,
   ⟲, ✳) receberam `accessibilityLabel`, e os seletores de estilo, cor e status receberam
   papéis de acessibilidade (`radio`, `switch`, `tab`) com estado de seleção. O design,
   por ser HTML estático, não tinha como expressar isso.

5. **Formulários rolam com o teclado aberto.** As telas de cadastro de cliente, registro
   de atendimento e novo agendamento usam `KeyboardAvoidingView`: no design, os campos
   eram texto fixo e a questão não aparecia.

6. **Estados vazios passaram a ser derivados dos dados.** No design, "lista vazia" e
   "primeiro uso" são telas separadas. No app, a mesma tela mostra o estado vazio quando
   não há clientes — que é como o comportamento real funciona.

7. **A comparação (RF07) trocou o arraste por seleção.** O design sugere "arraste para
   trazer a terceira simulação", interação que não estava especificada. Foi substituída
   por uma faixa de opções abaixo da comparação: toca-se na simulação que deve ocupar o
   lado direito. O resultado é o mesmo com menos ambiguidade e melhor acessibilidade.

8. **O cliente é escolhido antes da câmera, não depois do resultado.** No design, a
   simulação podia começar sem cliente e ser vinculada no fim. Como o consentimento é
   individual (seção 8), a ordem foi invertida: a escolha do cliente virou a primeira
   etapa do fluxo, e a tela de resultado deixou de ter o caminho "vincular depois".

9. **Itens de ajuste sem tela projetada ficaram inertes e marcados "em breve".** Em
   "Perfil", os itens *Dados pessoais e negócio*, *Serviços e duração padrão* e
   *Notificações e lembretes* não têm tela no design nem escopo no pré-projeto. Preferiu-se
   sinalizar a ausência a criar um link que não leva a lugar nenhum.

10. **Rótulo do próximo atendimento.** O design fixa "em 45 min". O app calcula a
    distância real e, para compromissos além de hoje, escreve "amanhã", o dia da semana ou
    a data — "em 59h16" seria informação inútil no balcão.

11. **Mensagem de erro junto do campo certo.** No formulário de agendamento, a validação
    de cliente ausente aparece ao lado do seletor de cliente.

12. **Fotos e miniaturas.** Onde o design usa retângulos hachurados como imagem de
    exemplo, o app mostra a foto real quando ela existe e mantém a hachura quando não
    existe (por exemplo, nas simulações de demonstração, que não têm imagem).

13. **A tela de consentimento do design foi desdobrada em duas.** O design tinha uma única
    tela, em que o profissional declarava obter o consentimento dos clientes. Ela virou a
    ciência das responsabilidades (dele) e o termo de uso de imagem (de cada cliente).
    O motivo está na seção 8.

14. **O selo de consentimento na tela de captura deixou de ser decorativo.** No design ele
    exibia uma data fixa; agora mostra quem autorizou, quando, por qual forma de obtenção
    e sobre qual versão do termo — e a tela inteira não abre quando a autorização não vale.

15. **A promessa "o serviço de IA não retém a foto para treino" foi removida.** Ela estava
    na tela de privacidade do design, mas é uma garantia que nem o app nem o profissional
    podem dar sobre uma empresa terceira. O texto passou a dizer exatamente o contrário:
    que não há controle sobre o uso posterior.

---

## 7. Limitações conhecidas e pontos que dependiam do back-end

> **Resolvido.** Todos os `TODO:BACKEND` listados abaixo foram implementados na etapa de
> integração; não resta nenhum marcador no código. A coluna da direita indica onde cada
> ponto foi resolvido.

| Arquivo | O que faltava | Como ficou |
| --- | --- | --- |
| `src/services/authService.ts` | Login real e envio do JWT (RF01) | arquivo removido; `src/services/api/*` fala com `POST /auth/login` e guarda o token em armazenamento seguro |
| `src/services/simulacaoService.ts` | Chamada ao FastAPI, provedor de IA, validação de luminância e rosto | o envio é `POST /simulacoes`; a validação completa roda no servidor; restou aqui a pré-checagem local |
| `src/services/consentService.ts` | Persistir as decisões e **repetir a verificação no servidor** | status, revalidação e bloqueio vêm do servidor; o módulo guarda só rótulos e cálculo de idade para exibição |
| `src/data/termos.ts` | Servir os textos pelo servidor | tabela `termos`; o módulo virou um cache com o hook `useTermo` |
| `src/components/ImagemSimulada.tsx` | Exibir a imagem gerada | exibe a imagem do servidor por URL assinada; a tonalização de demonstração foi removida |
| `src/data/seed.ts` | Substituir os dados de exemplo | arquivo removido; o seed vive no banco (`python -m app.seed`) |
| `app/login.tsx` | Cadastro de conta real | tela `app/cadastro.tsx`, com `POST /auth/registrar` |
| `app/agendamento/novo.tsx` | Sincronizar a agenda com o servidor (RF06) | agenda persistida; o disparo da notificação segue fora do escopo |
| `app/privacidade.tsx` | Exclusão no Storage e no banco (art. 18) | exclusão real de imagens e de conta, esta em tela própria com a senha reconfirmada |
| `app/(tabs)/perfil.tsx` | Telas de ajustes da conta | `GET/PATCH /usuarios/me` disponível; a tela de ajustes segue fora do escopo |

### Simplificação de fluxos (etapa posterior ao QA)

Oito decisões de navegação foram revistas para tirar ações repetidas, sob a regra de que
cada funcionalidade tem uma porta de entrada só:

| O que havia | O que passou a valer |
| --- | --- |
| Tesoura representando a simulação | Câmera — é a ação que o profissional executa. A tesoura ficou onde significa corte: a marca do aplicativo e o selo do estilo escolhido |
| Hora do agendamento no seletor nativo | Campo digitado `HH:MM`, teclado numérico, validação de faixa e mensagem distinta para incompleto e inválido. A data continua no seletor nativo |
| Cartão do próximo atendimento com Simular, Registrar e Perfil | O cartão inteiro abre o perfil. Uma ação, sem concorrência |
| Atalho de nova simulação no Início, além do botão da barra inferior | Só a barra inferior, que pede o cliente em seguida |
| "Nova simulação" também no perfil do cliente | Removido: entrada única pela barra inferior |
| Botão "Ver agenda" no Início | Removido: a aba Agenda está a um toque na mesma barra |
| "Ver termo" e "Apresentar ao cliente", lado a lado | Uma ação, escolhida pelo estado registrado: "Responder ao termo" sem decisão, "Ver termo" havendo decisão — e a tela do termo continua permitindo registrar decisão nova |
| Miniatura da simulação abrindo a comparação | Abre a imagem, em tela própria, inteira e com data, modelo e tempo de geração. Comparar virou ação explícita, com as duas posições escolhíveis |
| Serviço previsto restrito a cinco opções | Acrescentada a opção "Outro", que abre campo para descrever o serviço |

O que **não** mudou, de propósito: as simulações salvas continuam acessíveis no perfil, a
comparação continua existindo, e nenhum registro foi apagado. A restrição é sobre *iniciar*
uma simulação, não sobre consultar as que já existem.

Outras limitações desta etapa:

- ~~**Sem testes automatizados.**~~ Resolvido: 310 testes no back-end, incluindo os sete
  casos críticos de consentimento e isolamento, mais três baterias em navegador real — o
  fluxo completo contra a API e uma de responsividade, acessibilidade e estados de tela.
  Tudo roda por um comando: `./qa.sh`. O resultado da verificação de qualidade e segurança
  está em `RELATORIO_QA.md`.
- ~~**Sem multiusuário.**~~ Resolvido: cada profissional tem a própria conta, e o
  isolamento é imposto em toda consulta do servidor — não apenas tipado.
- **Data e hora no navegador.** No celular o app usa o seletor nativo; na versão web,
  onde ele não existe, são campos com máscara (`dd/mm/aaaa` e `hh:mm`).
- **Sem modo escuro.** O design define uma única identidade clara.
- **Não testado em iOS.** A verificação foi feita no navegador; Android e iOS dependem de
  execução em aparelho ou emulador com o Expo Go.
- **Valor probatório do consentimento.** O registro é feito pelo profissional no aparelho
  dele. O app guarda quem confirmou, quando, como e sobre qual versão do termo, mas não
  substitui uma assinatura eletrônica com autenticação do titular. Ver seção 8.6.

---

## 8. Consentimento de uso de imagem: fundamentação e desenho

Esta seção documenta a reestruturação feita depois da primeira entrega e substitui
qualquer descrição anterior da tela T0.

### 8.1 O problema do desenho original

Na primeira versão — e na Tabela 5 do pré-projeto — o app pedia ao **profissional**, uma
única vez após o login, que declarasse obter o consentimento dos clientes. Um aceite
liberava a câmera para toda a carteira.

Isso confunde dois atos jurídicos distintos:

1. a **manifestação do titular** dos dados, que na LGPD é o consentimento propriamente
   dito (art. 5º, XII: "manifestação livre, informada e inequívoca pela qual o titular
   concorda com o tratamento de seus dados pessoais para uma finalidade determinada");
2. a **responsabilidade do controlador**, que é do profissional e não pode ser transferida
   ao titular nem confundida com a autorização dele.

Como a imagem pertence ao cliente, o consentimento precisa ser dele, individual e
específico. No modelo antigo, um cliente que nunca foi perguntado teria a foto enviada a
um serviço externo com base em uma declaração feita por outra pessoa, meses antes.

### 8.2 Como ficou

**Consentimento por cliente**, com quatro estados e histórico completo:

| Estado | Significado | Efeito na câmera |
| --- | --- | --- |
| `pendente` | nunca respondeu | bloqueada; o termo é apresentado na hora |
| `aceito` | autorizou na versão vigente do termo | liberada |
| `recusado` | leu e não autorizou | bloqueada, com o motivo explicado |
| `revogado` | havia autorizado e cancelou depois | bloqueada, com o motivo explicado |

Cada decisão gera um registro imutável com data e hora, versão do termo aceita,
profissional que registrou, forma de obtenção, nome de quem confirmou e, quando é o caso,
o responsável legal. O estado atual do cliente é sempre o do registro mais recente; os
anteriores permanecem como trilha de auditoria (art. 37: o controlador deve manter
registro das operações de tratamento).

**Ciência das responsabilidades do profissional**, separada do consentimento: no primeiro
acesso ele precisa ler e aceitar um aviso que explica o que deve informar ao cliente,
inclusive o envio da foto a uma empresa terceira. Esse aceite não autoriza tratamento
nenhum — é o reconhecimento do papel dele.

**Versão do termo.** Quando o texto muda, os aceites anteriores não são apagados nem
continuam valendo silenciosamente: o cliente aparece como "aceito em versão anterior" e o
termo novo é apresentado antes da próxima captura. Isso preserva o requisito de
consentimento *informado* — quem concordou com um texto não concordou automaticamente com
outro.

**Revogação tão simples quanto o aceite** (art. 8º, §5º): um toque no perfil do cliente,
com confirmação. Logo em seguida o app oferece apagar as simulações já salvas daquele
cliente, atendendo ao art. 18, VI (eliminação dos dados tratados com base no
consentimento). O histórico de atendimentos é preservado, porque se apoia em outra base
legal — a execução do serviço contratado (art. 7º, V).

**Menores de idade** (art. 14). A data de nascimento é opcional no cadastro; quando
informada, o app calcula a idade e, abaixo de 18 anos, passa a exigir nome e parentesco do
responsável legal para registrar qualquer decisão. O texto diferencia criança (até 12
anos, para quem a lei exige consentimento específico e destacado de um dos pais ou do
responsável) de adolescente, para quem o app adota a mesma exigência por precaução.

**Granularidade da finalidade.** O consentimento cobre apenas a foto do rosto e a imagem
simulada dela derivada. Recusar não afeta cadastro, histórico ou agenda — isso é dito no
termo, na tela de recusa e na interface do perfil, para que "recusar" não seja lido como
"ser excluído do aplicativo".

### 8.3 Fluxo de telas

```
Login ─► Ciência das responsabilidades (bloqueante, 1ª vez) ─► Dashboard
              └─ reconsultável em Perfil › Termos e responsabilidades

Nova simulação (aba central ou dashboard)
      │
      ▼
Escolher cliente  ─ cada linha mostra o selo de consentimento
      │
      ├─ aceito e versão atual ─────────────► Câmera ─► Parâmetros ─► Resultado ─► …
      │
      ├─ pendente  ou  versão anterior ────► Termo do cliente
      │                                         ├─ aceite   ─► Câmera
      │                                         └─ recusa   ─► Perfil do cliente
      │
      └─ recusado  ou  revogado ───────────► Câmera bloqueada, com o motivo
                                                └─ "Apresentar termo ao cliente" ─► Termo

Perfil do cliente
      ├─ selo de estado + histórico de decisões
      ├─ "Ver termo completo" / "Apresentar termo ao cliente"
      └─ "Cancelar consentimento" ─► confirmação ─► oferta de apagar as imagens salvas
```

Nenhum caminho da interface leva à câmera sem passar pela avaliação. Na versão integrada,
quem avalia é o **servidor**: o resumo de consentimento chega junto do cliente, com o
motivo do bloqueio quando houver, e `POST /simulacoes` recusa com 403 de qualquer forma.
A tela de escolha, o perfil do cliente e a própria tela de captura consultam esse resumo e
mostram a explicação do bloqueio em vez de montar a câmera.

### 8.4 Modelo de dados proposto para o back-end

> **Implementado.** A proposta a seguir foi construída, com três entidades a mais do que o
> previsto aqui (`termos`, `ciencias` e `imagens`) e uma coluna de alto valor para o TCC:
> `simulacoes.consentimento_id`, que liga cada imagem gerada à decisão que a autorizou.
> O modelo final está na seção 3 de [`DOCUMENTACAO-BACKEND.md`](DOCUMENTACAO-BACKEND.md).

Duas mudanças na modelagem da seção 5.6 do pré-projeto: um campo novo em `clientes` e uma
entidade nova, `consentimentos`.

**`clientes`** — acrescentar:

| Campo | Tipo | Observação |
| --- | --- | --- |
| `data_nascimento` | `DATE NULL` | Opcional; determina a exigência de responsável legal |

**`consentimentos`** — registro imutável de cada decisão:

| Campo | Tipo | Observação |
| --- | --- | --- |
| `id` | `UUID PK` | |
| `cliente_id` | `UUID FK → clientes` | obrigatório |
| `usuario_id` | `UUID FK → usuarios` | profissional que apresentou o termo |
| `decisao` | `ENUM('aceito','recusado','revogado')` | "pendente" não é gravado: é a ausência de registros |
| `versao_termo` | `VARCHAR(16)` | versão do texto apresentado |
| `registrado_em` | `TIMESTAMPTZ` | data e hora da manifestação |
| `forma_obtencao` | `ENUM('tela_dispositivo','lido_em_voz_alta','termo_impresso')` | como o termo chegou ao cliente |
| `confirmado_por` | `VARCHAR(120)` | nome de quem confirmou (cliente ou responsável) |
| `responsavel_nome` | `VARCHAR(120) NULL` | preenchido quando o titular é menor |
| `responsavel_parentesco` | `VARCHAR(40) NULL` | idem |
| `observacao` | `TEXT` | anotação livre do profissional |

Relações e regras:

- `clientes 1:N consentimentos` — o estado atual é o registro de `registrado_em` mais
  recente. Sugere-se uma *view* `consentimento_atual` ou uma coluna materializada em
  `clientes` para consultas frequentes.
- **Nenhum `UPDATE` ou `DELETE`** em `consentimentos`: revogar é inserir uma linha nova.
  Isso preserva a trilha de auditoria exigida pelo art. 37.
- A tabela sobrevive à exclusão das imagens: apagar simulações não apaga a prova de que
  houve (ou não) consentimento. Se o cliente for excluído, os registros vão junto.
- `termos` pode virar uma tabela própria (`versao`, `titulo`, `corpo`, `publicado_em`),
  para que o texto seja corrigido sem publicar nova versão do aplicativo.

**Regra de negócio no servidor:** `POST /simulacoes` deve recusar (HTTP 403) qualquer
requisição cujo cliente não tenha consentimento `aceito` na versão vigente. A verificação
no aplicativo é conveniência de interface; o controle de acesso é do back-end.

### 8.5 Endpoints que substituiriam os mocks

> **Implementado.** Todos os endpoints propostos abaixo existem, com os mesmos caminhos.
> A lista completa da API está no [`backend/README.md`](../backend/README.md).

| Método e rota | Uso no app | Substitui |
| --- | --- | --- |
| `GET /clientes/{id}/consentimento` | estado atual + se precisa revalidar | `resumoDoCliente()` |
| `GET /clientes/{id}/consentimentos` | histórico de decisões do cliente | `historicoDoCliente()` |
| `POST /clientes/{id}/consentimentos` | registra aceite, recusa ou revogação (corpo: decisão, versão do termo, forma de obtenção, quem confirmou, responsável, observação) | `acoes.registrarConsentimento()` |
| `DELETE /clientes/{id}/simulacoes` | elimina as imagens após a revogação (art. 18, VI) | `acoes.excluirImagensDoCliente()` |
| `DELETE /simulacoes/{id}` | exclui uma simulação salva e as imagens dela ("Excluir" no perfil do cliente); o histórico de atendimentos fica | `acoes.excluirSimulacao()` |
| `GET /termos/cliente` e `GET /termos/profissional` | textos versionados | `src/data/termos.ts` |
| `POST /usuarios/me/ciencia` | registra a ciência das responsabilidades | `acoes.aceitarCiencia()` |
| `POST /simulacoes` | gera a simulação — **valida o consentimento antes de chamar a API de IA** | `gerarSimulacao()` |

### 8.6 Limitação conhecida: a API externa de simulação

A simulação depende de um provedor terceiro de inferência (no pré-projeto, a Replicate
API). O projeto **não tem como garantir** o que esse fornecedor faz com a imagem depois de
recebê-la: por quanto tempo a retém, se a utiliza para treinar modelos ou com quem a
compartilha. Essas condições são definidas pelo contrato de uso do próprio provedor e
podem mudar sem aviso.

Em vez de silenciar essa limitação, o aplicativo a comunica em três lugares:

1. **No termo do cliente**, em duas seções destacadas: uma diz que a foto é enviada a uma
   empresa terceira, e a outra afirma explicitamente que não há controle sobre o uso
   posterior feito por ela. O cliente decide sabendo disso.
2. **Na ciência do profissional**, como dever de informação: ele precisa dizer isso ao
   cliente antes de registrar qualquer decisão.
3. **Na tela de privacidade**, onde a afirmação original do design ("o serviço de IA não
   retém a foto para treino") foi substituída pelo texto correto.

Do ponto de vista metodológico, essa é uma das diretrizes de design que o TCC se propõe a
sistematizar (seção 5.1 do pré-projeto): ao integrar um serviço externo de IA generativa a
um sistema que trata dados sensíveis, **a dependência de terceiros deve ser declarada ao
titular como limitação, e não apresentada como garantia**. Mitigações possíveis para o
trabalho final, todas fora do escopo desta etapa: escolher provedores com cláusula de não
retenção auditável, hospedar o modelo em infraestrutura própria ou aplicar
pseudonimização/recorte da região capilar antes do envio, reduzindo a identificabilidade
da imagem que sai do aparelho.

### 8.7 Integridade do termo e versionamento

Na primeira versão desta tela, "Ver termo completo" abria a mesma tela usada para
registrar a decisão. O texto era exibido como texto (nunca houve campo de edição), mas
logo abaixo dele apareciam os campos "Quem confirmou a decisão" e "Observação" — e o
conjunto lia-se como um documento editável. Havia também um defeito de conformidade
mais sério: a tela mostrava sempre a **versão vigente** do termo, e não a versão que
aquele cliente efetivamente aceitou.

A correção separou os dois atos:

| Ação | Rota | O que faz |
| --- | --- | --- |
| **Consultar** | `/termo/[clienteId]` | Somente leitura. Nenhum campo de entrada. Exibe o texto da versão aceita por aquele cliente e avisa quando existe versão mais recente. |
| **Registrar decisão** | `/consentimento/[clienteId]` | Apresenta a versão vigente dentro de um bloco rotulado "Documento · não editável" e, separado dele, o formulário de registro. |

O texto dos termos vive em um **registro versionado único** (`src/data/termos.ts`), que
guarda todas as versões já publicadas, cada uma com número e data de vigência:

```ts
TERMOS_CLIENTE = [ v1.0 (vigente desde 16/09/2026), v0.9 (vigente desde 04/05/2026) ]
TERMO_CLIENTE          // versão vigente, única apresentada para novas decisões
termoClientePorVersao() // texto exato de uma versão já aceita
```

**Justificativa.** O consentimento precisa ser *informado* (LGPD, art. 5º, XII): quem
concordou com um texto não concordou automaticamente com outro. Para que o registro no
banco tenha valor probatório, o sistema precisa ser capaz de mostrar, a qualquer momento,
**o documento exato** que foi apresentado — e não a redação mais recente. Por isso:

- o texto é imutável dentro de uma versão e não pode ser alterado pela interface;
- corrigir o conteúdo significa publicar uma versão nova, que passa a exigir revalidação;
- as versões antigas continuam disponíveis para consulta;
- se o aplicativo não conhecer o texto de uma versão antiga, ele avisa explicitamente em
  vez de exibir outro texto no lugar — admitir a lacuna é preferível a induzir o
  profissional a acreditar que aquele era o documento aceito.

Uma auditoria no restante do aplicativo confirmou que não há outro conteúdo de leitura
apresentado em campo editável: todos os `TextInput` são campos de entrada legítimos
(nome, telefone, data de nascimento, observações, e-mail, senha, busca, data e hora do
agendamento).

---

## 9. Revisão de usabilidade: diagnóstico

Concluída a implementação funcional, o protótipo passou por uma avaliação heurística
antes da revisão de interface. O método foi a avaliação por heurísticas de Nielsen
(1994), complementada por medição de contraste (WCAG 2.1) e inspeção de consistência.

### 9.1 Problemas encontrados, por gravidade

| Heurística | Gravidade | Problema | Onde |
| --- | --- | --- | --- |
| 1. Visibilidade do status | Alta | Salvar cliente, atendimento ou agendamento apenas navegava, sem confirmação de gravação; nenhuma tela tinha estado de carregamento | cadastro, atendimento, agendamento |
| 3. Controle e liberdade | Alta | Sair de um formulário preenchido descartava tudo sem aviso; confirmações destrutivas usavam o diálogo do navegador | cadastro de cliente, privacidade |
| 5. Prevenção de erros | Alta | Data, hora e telefone eram texto livre, sem máscara nem seletor | agendamento, cadastro |
| 4. Consistência | Média-alta | Cinco alturas de botão, três paddings de tela, sete raios de borda, quatorze tamanhos de texto; metade das telas desenhava o próprio cabeçalho | todo o app |
| 2. Linguagem do mundo real | Média | Ícones eram glifos tipográficos (◈ ☰ ▤ ✳ ⚿), de significado obscuro e renderização variável entre plataformas | barra de abas, listas |
| 6. Reconhecer em vez de lembrar | Média | O registro de atendimento não sugeria o serviço a partir da simulação vinculada | registrar atendimento |
| 7. Flexibilidade e eficiência | Média | Registrar o atendimento do cliente que está na cadeira exigia 4 a 5 toques | dashboard, agenda |
| 9. Recuperação de erros | Média | Erros de formulário apareciam só junto do campo; em tela rolada, o toque em salvar parecia não fazer nada | formulários |
| 8. Estética e minimalismo | Baixa-média | Avisos longos em telas de uso repetido; perfil do cliente com seis cartões empilhados | escolha de cliente, perfil |
| 10. Ajuda e documentação | Baixa | "Como ler uma simulação" era texto solto, sem destino | perfil do profissional |

### 9.2 Contraste medido antes da revisão

| Cor e uso | Razão | Situação |
| --- | --- | --- |
| `#9A8F85` — rótulos, subtítulos e notas | 2,96:1 | reprova |
| `#B0A49A` — placeholders | 2,44:1 | reprova |
| `#B96A52` — terracota como texto de link (12,5px) | 3,75:1 | reprova para texto pequeno |
| `#8A7E74` — descrição de itens de lista | 3,70:1 | reprova |
| `#1B1714` sobre terracota — rótulo do botão de ação | 4,45:1 | limítrofe |

### 9.3 Outros achados

- **Alvos de toque**: corretos nos botões, mas os links textuais (12,5px, sem área
  ampliada) ficavam abaixo dos 44px recomendados.
- **Informação por cor**: o status do agendamento dependia de cor e texto em caixa alta
  pequena, sem ícone.
- **Responsividade**: não havia largura máxima; em tablet as linhas passavam de 100
  caracteres e as grades esticavam.
- **Estados de tela**: existiam estados vazios, mas não estados de carregamento nem
  confirmação de sucesso.

---

## 10. Design system e revisão de interface

A direção adotada foi **refinar a identidade do design aprovado**, não substituí-la:
Instrument Serif nos títulos, Familjen Grotesk no texto, base areia e terracota como
única cor de ação permanecem. O que mudou foi a disciplina por trás deles.

### 10.1 Tokens (`src/theme/tokens.ts` e `src/theme/textos.ts`)

**Cor.** A paleta foi reescrita para que todo par texto/fundo alcance 4.5:1. Os valores
finais, com as razões medidas:

| Token | Valor | Uso | Contraste |
| --- | --- | --- | --- |
| `texto` | `#1B1714` | texto principal | 16,7:1 |
| `textoSecundario` | `#4A423B` | texto de leitura sobre superfície | 9,2:1 |
| `textoTerciario` | `#5E554E` | corpo de apoio | 6,8:1 |
| `textoApoio` | `#6F655D` | metadados e rótulos (menor tom admitido) | 5,3:1 |
| `placeholder` | `#7A6F66` | texto de exemplo em campos | 4,9:1 |
| `acaoTexto` | `#8E4E3B` | links e ações textuais | 6,0:1 |
| `acao` | `#A85C46` | preenchimento de botões, com texto branco | 4,9:1 |
| `acaoDecorativa` | `#B96A52` | superfícies e ícones (nunca texto pequeno) | — |
| `sucessoTexto` / `alertaTexto` / `erroTexto` | `#1F5A43` / `#5E4A12` / `#9E3122` | texto dentro dos avisos | 7,0 / 7,4 / 6,1:1 |

**Tipografia.** Sete tamanhos, no lugar dos quatorze anteriores: 32 (display), 24
(título e número), 17 (seção), 15 (corpo), 13 (apoio), 12 (metadado) e 10 (etiqueta).
Cada papel tem altura de linha fixa, e as telas não declaram tamanhos próprios.

**Espaçamento, raio e elevação.** Grade de 4px (`espaco.xs` a `espaco.xxxl`), três raios
(`campo` 10, `cartao` 16, `bloco` 24) e uma única elevação para elementos flutuantes.

**Ícones.** Os glifos tipográficos foram substituídos por ícones vetoriais
(`@expo/vector-icons`, biblioteca Feather), mapeados por papel em `src/components/Icone.tsx`
— `simulacao`, `clientes`, `agenda`, `documento`, `cadeado`, `okCirculo`, e assim por
diante. O mapa é o único lugar que conhece a biblioteca usada, o que permite trocá-la
sem tocar nas telas.

### 10.2 Componentes

| Componente | Papel |
| --- | --- |
| `Tela` | Moldura de todas as telas: área segura, fundo e coluna de largura máxima |
| `Botao` | Cinco variantes (primária, ação, secundária, perigo, texto) × três tamanhos, com estado de carregamento |
| `Campo` | Entrada com rótulo permanente, marcação de obrigatório, máscara, texto de ajuda e erro com ícone |
| `CampoData` | Seletor nativo de data e hora no celular; campo com máscara no navegador |
| `Cartao`, `Grupo`, `ItemGrupo` | Superfícies e listas agrupadas |
| `Selo`, `SeloConsentimento` | Status com cor **e** ícone **e** texto |
| `Aviso` | Caixa de mensagem com tom semântico |
| `Chip`, `Alternador` | Seleção de opções e interruptores |
| `EstadoVazio` | Estado vazio com explicação e saída |
| `Esqueleto` | Bloco pulsante de carregamento |
| `Feedback` | Provedor de toast de sucesso e modal de confirmação |
| `FolhaAcoes` | Folha inferior com as ações de um item |
| `Cabecalho` | Cabeçalho único de todas as telas |
| `TermoTexto` | Corpo de um termo versionado, somente leitura |

### 10.3 Fluxos: antes e depois

| Situação | Antes | Depois | Por quê |
| --- | --- | --- | --- |
| Registrar o atendimento de quem está na cadeira | 4 a 5 toques a partir do início | 2 toques: o card do próximo atendimento tem **Simular · Registrar · Perfil** | É a tarefa mais frequente do balcão (heurística 7) |
| Agir sobre um compromisso da agenda | Abria o perfil do cliente | Folha de ações com confirmar, simular, registrar e abrir perfil | Reduz navegação para a ação mais provável |
| Salvar qualquer registro | Navegação silenciosa | Toast "Atendimento registrado", "Cliente salvo", "Agendamento criado" | Visibilidade do status (heurística 1) |
| Ação destrutiva | `window.confirm` do navegador | Modal próprio, com o verbo da ação no botão | Identidade e clareza; o diálogo do sistema não existe no celular |
| Sair de formulário preenchido | Descartava sem aviso | Pergunta antes de descartar | Prevenção de erro (heurística 5) |
| Data e hora | Texto livre | Seletor nativo no celular, máscara no navegador | Prevenção de erro |
| Escolher cliente para simular | Lista alfabética única | "Atendimentos de hoje" primeiro, depois todos | Quem está na cadeira costuma ter horário marcado |
| Decidir sobre o termo | "Registrar aceite" em botão escuro cheio; "O cliente recusou" apagado | **Dois botões de mesmo tamanho e peso**, um verde e um vermelho, lado a lado | Um aceite induzido não é manifestação livre (LGPD, art. 5º, XII) |
| Ver o termo | Abria a tela de registro | Tela somente leitura, com a versão aceita | Integridade do documento (seção 8.7) |
| Perfil do cliente | Seis cartões empilhados | Histórico de decisões recolhido atrás de um toque | Minimalismo sem perder informação |
| Tablet | Linhas de mais de 100 caracteres | Coluna centralizada com largura máxima de 560px | Conforto de leitura |

### 10.4 Decisões de acessibilidade

1. **Contraste**: todos os 16 pares texto/fundo do app foram medidos e alcançam no
   mínimo 4,5:1; ícones não textuais alcançam 3:1, conforme WCAG 1.4.3 e 1.4.11.
2. **Alvo de toque**: 44×44px como mínimo, inclusive em links textuais e botões de
   ícone, que mantêm o desenho menor e recebem área de toque ampliada.
3. **Informação não depende de cor** (WCAG 1.4.1): todo status combina cor, ícone e
   texto. Os quatro estados de consentimento têm ícones distintos — verificado
   (autorizado), relógio (pendente), proibido (recusado e cancelado) e triângulo
   (versão desatualizada).
4. **Rótulos e papéis**: todo controle tem `accessibilityRole` e `accessibilityLabel`;
   seletores usam `radio` e `switch` com estado; abas usam `tab` com seleção; campos
   obrigatórios são anunciados como tal.
5. **Regiões dinâmicas**: mensagens de erro e o toast usam `accessibilityLiveRegion`,
   para serem anunciadas sem que o usuário precise procurá-las.
6. **Dicas em vez de bloqueios silenciosos**: botões desabilitados explicam o motivo por
   `accessibilityHint` (por exemplo, "marque a caixa de ciência para continuar").
7. **Texto no lugar de ícone isolado**: nenhuma ação é representada apenas por símbolo
   sem rótulo visível ou rótulo acessível.

### 10.5 Verificação

Após a revisão, o fluxo completo foi percorrido no navegador com automação, cobrindo:
entrada e ciência, ações rápidas do dashboard, registro de atendimento, criação de
agendamento, folha de ações da agenda, simulação completa com câmera real, bloqueio por
recusa e layout em largura de tablet. Nenhum erro de console e verificação de tipos
limpa. As funcionalidades listadas no inventário continuam todas disponíveis.

**O que ficou de fora**, como sugestão para a continuidade:

- modo escuro (o design define uma única identidade clara);
- busca por voz ou atalhos de teclado em tablet com teclado acoplado;
- animações de transição entre telas (hoje só há o fade padrão);
- testes automatizados de interface, que substituiriam a verificação manual roteirizada;
- revisão do fluxo com usuários reais — a avaliação heurística aponta problemas
  prováveis, mas não substitui o teste com os 5 a 10 participantes previstos na
  seção 5.10 do pré-projeto.

---

## 11. Como rodar o projeto localmente

O aplicativo agora depende do servidor. Suba o back-end primeiro — as instruções completas
estão em [`backend/README.md`](../backend/README.md):

```bash
cd backend
cp .env.example .env          # preencha JWT_SECRET
docker compose up --build     # ou: alembic upgrade head && python -m app.seed && uvicorn app.main:app
```

Depois, o aplicativo:

```bash
cd espelho
npm install

# navegador (mais rápido para demonstrar)
npm run web

# celular: leia o QR Code com o Expo Go (mesma rede Wi-Fi)
npm start

# emuladores
npm run android
npm run ios      # requer macOS

# verificação de tipos
npm run typecheck
```

O aplicativo descobre a API pelo endereço do Metro bundler, na porta 8000; para apontar
para outro servidor, defina `EXPO_PUBLIC_API_URL`.

O aplicativo abre no onboarding. O login é real: use a conta de demonstração criada pelo
seed (`carolina@salaoexemplo.com.br` / `espelho-demo-2026`), que traz sete clientes, cinco
simulações, histórico e agenda; ou crie uma conta nova, para ver os estados de primeiro
uso. A segunda conta do seed (`diego@salaoexemplo.com.br`) serve para demonstrar que um
profissional não enxerga os clientes do outro.

Para demonstrar os caminhos de exceção sem depender de uma foto ruim ou de uma queda real
do provedor, a tela de captura tem o atalho "foto ruim" e a tela de revisão do pedido tem "ver o
que acontece se a simulação falhar". Os dois só funcionam com `MODO_DEMO=true` no servidor: quem
decide recusar a foto ou simular a falha é ele, não o aplicativo.

### 11.1 Como testar cada estado de consentimento

Os dados de exemplo já trazem um cliente para cada situação, de modo que os cinco cenários
podem ser percorridos sem preparar nada:

| Cenário | Cliente | O que fazer | O que deve acontecer |
| --- | --- | --- | --- |
| **Aceito** | Marina Alves | Clientes › Marina › "Nova simulação" | A câmera abre direto; o rodapé mostra quem autorizou, quando, como e em qual versão do termo |
| **Pendente** | Bruno Tavares | Botão central ✳ › Bruno | O termo aparece antes da câmera; ao registrar o aceite, a câmera abre em seguida |
| **Recusado** | Carla Menezes | Clientes › Carla › "Nova simulação" | A câmera não abre: aparece a explicação do bloqueio, com a opção de apresentar o termo de novo |
| **Revogado** | Rafael Prado | Clientes › Rafael | O perfil mostra "Consentimento cancelado" e o histórico com as duas decisões (aceite e cancelamento) |
| **Versão anterior** | Júlia Stein | Botão central ✳ › Júlia | O selo indica "Aceito em versão anterior" e o termo atual é apresentado antes de fotografar |
| **Menor de idade** | Sofia Ramires, 16 anos | Clientes › Sofia › "Apresentar termo" | O aviso do art. 14 aparece no topo e os campos de responsável legal tornam-se obrigatórios |

Para testar a **revogação com exclusão de imagens**: abra Marina (que tem simulações
salvas), toque em "Cancelar consentimento", confirme, e aceite a segunda pergunta. As
simulações somem, o histórico de atendimentos permanece e a próxima tentativa de
fotografar cai na tela de bloqueio.

Para voltar tudo ao estado inicial, rode `python -m app.seed --reset` no `backend/`: os
usuários de demonstração são apagados e recriados, com imagens e tudo.

---

## 12. Próximos passos sugeridos

Os três primeiros itens desta lista foram concluídos na etapa de integração:

1. ~~Implementar o back-end em FastAPI~~ — feito, com nove entidades e a API da
   seção 8.5. Ver [`DOCUMENTACAO-BACKEND.md`](DOCUMENTACAO-BACKEND.md).
2. ~~Integrar autenticação, banco e storage~~ — feito com JWT próprio, PostgreSQL 16 e
   storage de objetos atrás de uma interface (disco em desenvolvimento, S3/MinIO/Supabase
   em produção). A autorização é imposta na aplicação, em toda consulta.
3. ~~Integrar o provedor de IA e mover a validação da imagem para o servidor~~ — feito,
   com FLUX.1 Kontext em vez de SDXL img2img, por preservar a identidade do rosto. A
   validação completa (formato, dimensões, proporção, luminância e detecção de rosto)
   roda no servidor antes de qualquer chamada paga.

O que continua em aberto:

4. Executar a avaliação com 5 a 10 participantes (seção 5.10), agora com o sistema
   funcionando de ponta a ponta — o que permite medir também o tempo real da geração
   (RNF02) e a qualidade visual do resultado.
5. Rodar o aplicativo em aparelhos Android e iOS (a verificação automatizada usou a versão
   web) e publicar uma primeira distribuição de teste.
6. Implementar o disparo das notificações de lembrete e a recuperação de senha, ambos
   fora do escopo desta etapa.
