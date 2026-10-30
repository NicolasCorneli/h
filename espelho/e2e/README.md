# Verificação de ponta a ponta

São duas baterias, ambas em navegador real contra a API em funcionamento.

`fluxo-completo.mjs` percorre o fluxo inteiro do sistema — do cadastro da conta à
revogação do consentimento com exclusão das imagens. É a verificação que sustenta as
afirmações da documentação: nada aqui usa mock.

`qa-interface.mjs` faz a outra pergunta: a tela se comporta bem em larguras diferentes, é
operável por quem não usa mouse, e diz a verdade quando algo falha? Verifica
responsividade em 390, 768 e 1280 px, alvos de toque, rótulos acessíveis, nomes de botão,
alternativas textuais de imagem, navegação por teclado com foco visível, validação de
formulário, estado vazio, o comportamento com a API derrubada no meio da sessão, e a
limpeza do console.

## O que ele exercita

1. onboarding → cadastro de conta → ciência das responsabilidades;
2. cadastro de cliente e selo de consentimento pendente vindo do servidor;
3. tentativa de simular sem consentimento → o fluxo leva ao termo, não à câmera;
4. termo do cliente carregado da tabela `termos`, com o aviso sobre a empresa terceira;
5. registro do aceite → câmera liberada;
6. envio da foto, validação no servidor, geração e exibição do resultado por URL assinada;
7. registro do atendimento vinculado à simulação e criação de agendamento;
8. troca de conta: cliente que recusou (câmera bloqueada), cliente com aceite em versão
   anterior (revalidação) e cliente com simulações (revogação + exclusão das imagens com
   o histórico de atendimentos preservado).

## Como rodar

O caminho curto, da raiz do repositório, que já recria a carga de demonstração e roda as
duas baterias:

```bash
./qa.sh --interface
```

Ou à mão, com o back-end e o `expo start --web` no ar:

```bash
# O roteiro altera os dados de demonstração — revoga consentimento e apaga imagens,
# porque é isso que ele verifica. Recrie a carga antes de cada execução, ou dois passos
# falharão por falta de pré-condição.
cd backend && .venv/bin/python -m app.seed --reset

cd ../espelho
npm install                        # o Playwright já é dependência de desenvolvimento
npx playwright install chromium    # baixa o navegador, se necessário
node e2e/fluxo-completo.mjs
node e2e/qa-interface.mjs
```

Em ambientes onde o Chromium está fora do caminho padrão, defina `CHROMIUM_PATH`.

Variáveis opcionais: `APP_URL` (padrão `http://localhost:8081`) e `CHROMIUM_PATH`, para
apontar um Chromium já instalado.

As capturas de tela de cada etapa ficam em `e2e/telas/` (fora do versionamento).

## Todas as baterias

O `./qa.sh --interface` roda as onze (a do Google, a décima segunda, só com os IDs configurados), recriando a carga de demonstração antes das que dependem dela:

| Roteiro | O que verifica |
| --- | --- |
| `fluxo-completo.mjs` | do cadastro da conta à revogação com exclusão das imagens |
| `qa-interface.mjs` | larguras, teclado, alvos de toque, estados vazio e de erro, console |
| `mudancas-interface.mjs` | mudanças de fluxo da etapa anterior (câmera, horário digitado, serviço "Outro") |
| `agenda.mjs` | editar, confirmar, cancelar, concluir, datas passadas |
| `atendimentos.mjs` | conclusão pela agenda e atendimento avulso |
| `painel-e-comparacao.mjs` | painel inicial e comparação de simulações |
| `fotos-e-camera.mjs` | foto do cliente e do profissional, câmera falsa com e sem rosto, câmera fora de vista sem conferir o enquadramento |
| `personalizacao.mjs` | etapa "Estilo e cor": guia "Como preencher", selos dos passos, exemplos em texto (sem botões), "manter o atual", validação, revisão (exemplo exato e descrição livre), envio único, erros com escolhas preservadas, larguras de 320 a 1280 px |
| `visual-contraste.mjs` | 24 telas em celular e tablet: contraste WCAG AA e rolagem horizontal |
| `auditoria.mjs` | regressões da auditoria de QA: guarda de rotas sem sessão, estado vazio do Início, cliente com data de nascimento, menor de idade, renovação sem rede, sessão recusada no meio do uso, correção e exclusão de atendimento, busca sem acento, painel contando horários, imagem indisponível |
| `seguranca.mjs` | "Senha e sessões": validação do formulário, senha atual errada, troca de senha desconectando o outro aparelho e mantendo este, "sair de todos os aparelhos" |
| `google.mjs` | "Entrar com Google" sem conta real (só com os IDs de cliente configurados) |

`auditoria.mjs` e `seguranca.mjs` criam contas próprias e não dependem da carga de
demonstração. `seguranca.mjs` erra a senha de propósito, e o freio de login da API conta
essas falhas (10 por endereço em 5 minutos): rode-a por último, como o `qa.sh` faz.

As baterias também rodam contra o build de produção servido como site estático: gere com
`npm run build:web`, sirva `dist/` com fallback para `index.html` e defina `APP_URL`.

## Sobre o retrato usado

`retrato-sintetico.jpg` **não é fotografia de pessoa alguma**: é um desenho gerado por
código (`backend/tests/fabricas.py`, função `retrato_valido`), com proporções suficientes
para a cascata de Haar reconhecer um rosto frontal. É o que permite exercitar o caminho
aprovado da validação — inclusive a detecção de rosto — sem usar a imagem de ninguém.
