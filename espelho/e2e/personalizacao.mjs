/**
 * Verifica no navegador a etapa "Estilo e cor", a revisão e a geração.
 *
 *  1  a etapa abre com a foto da etapa anterior e as três seções (corte, cor e tipo de
 *     cabelo); o rodapé diz o que falta, e "Revisar pedido" com algo faltando não avança:
 *     leva até a seção e mostra o erro no campo;
 *  2  ideias de corte e de cor recolhidas (em texto, nunca botões); "Estilo do corte" com
 *     "Neutro" marcado, e a troca para "Feminino"; escrever muda o selo e o rodapé;
 *  3  "Manter o atual" com texto já escrito pede uma decisão (usar a descrição ou apagar);
 *     manter os três não é pedido; mudar só o tipo de cabelo é;
 *  4  tipo de cabelo: "Manter meu tipo de cabelo atual" marcado no início, categoria e
 *     depois tipo, cada tipo com ilustração própria, troca de categoria sem resto;
 *  5  validação na hora (marcação, limite de 300 com contagem) e selo "Corrigir";
 *  6  revisão: resumo simples (corte, estilo, cor, tipo de cabelo), "Alterar", instrução
 *     recolhida; exemplo exato vai às opções do modelo; tipo de cabelo vai ao modelo de texto;
 *  7  geração: um envio só mesmo com toque duplo; o envio leva o tipo de cabelo;
 *  8  erros: sem conexão (escolhas preservadas, nova tentativa com a mesma chave),
 *     credencial recusada (sem "Tentar novamente"), pedido recusado (volta às escolhas);
 *  9  responsividade (320, 390 e 1280 px), rodapé sem cobrir conteúdo, alvos de toque e
 *     console sem erros.
 *
 * Pré-requisitos: API (AI_PROVIDER=fake, AI_ESTRATEGIA=especializado) e `expo start --web`
 * no ar, carga de demonstração recriada. O provedor local não é IA: a imagem sai com aviso.
 * O que se verifica aqui é a interface e o contrato.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const TELAS = path.join(AQUI, 'telas-personalizacao');
fs.mkdirSync(TELAS, { recursive: true });
const RETRATO = path.join(AQUI, 'retrato-sintetico.jpg');

const EMAIL = 'carolina@salaoexemplo.com.br';
const SENHA = 'espelho-demo-2026';

const passos = [];
const erros = [];
const ok = (d) => {
  passos.push(`[ok ] ${d}`);
  console.log(passos.at(-1));
};
const falha = (d, detalhe) => {
  passos.push(`[FALHA] ${d}: ${String(detalhe).slice(0, 300)}`);
  erros.push(d);
  console.log(passos.at(-1));
};
const conferir = (c, d, detalhe = '') => (c ? ok(d) : falha(d, detalhe));

const navegador = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const contexto = await navegador.newContext({
  viewport: { width: 390, height: 844 },
  locale: 'pt-BR',
  timezoneId: 'America/Sao_Paulo',
});
const page = await contexto.newPage();
const errosDoConsole = [];
page.on('console', (m) => {
  if (m.type() === 'error') errosDoConsole.push(m.text());
});
page.on('pageerror', (e) => errosDoConsole.push(String(e)));

const corpo = () => page.locator('body').innerText();
const espera = (ms = 1200) => page.waitForTimeout(ms);
const foto = (nome) => page.screenshot({ path: `${TELAS}/${nome}.png`, fullPage: true });
// Nome em texto é exato ("Alterar: cor" não pode casar com "Alterar: corte").
const botao = (nome) =>
  page.getByRole('button', { name: nome, exact: typeof nome === 'string' }).filter({ visible: true }).first();
const campo = (rotulo) => page.getByLabel(rotulo, { exact: true }).filter({ visible: true }).first();
const opcao = (nome) =>
  page.getByRole('radio', { name: nome, exact: typeof nome === 'string' }).filter({ visible: true }).first();
const marcada = async (nome) => (await opcao(nome).getAttribute('aria-checked')) === 'true';
const secao = (rotulo) => page.getByRole('heading', { name: new RegExp(`^${rotulo},`) }).filter({ visible: true }).first();
const situacao = async (rotulo) => ((await secao(rotulo).getAttribute('aria-label')) ?? '').split('.')[0];
const generoMarcado = async () => {
  const marcados = [];
  for (const rotulo of ['Feminino', 'Masculino', 'Neutro']) if (await marcada(rotulo)) marcados.push(rotulo);
  return marcados;
};
const semRolagemLateral = () =>
  page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);

/** Abre a câmera da Marina (autorizada na carga de demonstração) e escolhe a foto. */
async function irParaEstiloECor() {
  await page.goto(`${APP}/simulacao/cliente`, { waitUntil: 'networkidle' });
  await espera(2500);
  await page.getByRole('button', { name: /^Simular para Marina/ }).first().click();
  await espera(3500);
  const escolha = page.waitForEvent('filechooser');
  await botao(/Escolher foto da galeria/).click();
  await (await escolha).setFiles(RETRATO);
  await espera(3000);
}

/** Abre a revisão e espera a prévia do plano. */
async function revisar() {
  await botao('Revisar pedido').click();
  for (let i = 0; i < 10; i++) {
    await espera(500);
    if (/Ver a instrução enviada à IA/.test(await corpo())) return;
  }
}

/** Abre a instrução recolhida da revisão e devolve o texto da tela. */
async function verInstrucao() {
  await botao('Ver a instrução enviada à IA').click();
  await espera(300);
  return corpo();
}

try {
  // --- login --------------------------------------------------------------------
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await espera(2500);
  await page.getByRole('textbox').filter({ visible: true }).first().fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await page.getByRole('button', { name: /^Entrar$/ }).filter({ visible: true }).first().click();
  await espera(4000);

  // --- 1. abertura --------------------------------------------------------------
  await irParaEstiloECor();
  await foto('01-estilo-e-cor');
  {
    const tela = await corpo();
    conferir(/Estilo e cor/.test(tela) && /Etapa 3 de 3/.test(tela), '1. a etapa 3 abre depois da foto', tela.slice(0, 200));
    const miniatura = page.getByLabel('Foto do cliente que será usada').first();
    const src = await miniatura.evaluate((e) => e.getAttribute('src') ?? e.querySelector('img')?.getAttribute('src') ?? getComputedStyle(e).backgroundImage).catch(() => '');
    conferir(/blob:|data:|url\(/.test(src ?? ''), '1. a foto capturada chega à etapa (miniatura no cabeçalho)', src);
    conferir(/Rosto, roupa e fundo continuam como estão na foto/.test(tela), '1. a tela diz que só o cabelo muda', '');
    conferir(!/Como preencher/.test(tela), '1. sem o guia longo de instruções', '');
    conferir(
      /Como você quer que seu cabelo fique\?/.test(tela) &&
        /Qual cor você deseja no seu cabelo\?/.test(tela) &&
        /Qual tipo de cabelo você deseja na simulação\?/.test(tela),
      '1. as três perguntas: corte, cor e tipo de cabelo',
      tela.slice(0, 900)
    );
    conferir(
      (await situacao('Corte')) === 'Corte, a preencher' &&
        (await situacao('Cor')) === 'Cor, a preencher' &&
        (await situacao('Tipo de cabelo')) === 'Tipo de cabelo, sem mudança',
      '1. selos: corte e cor "A preencher", tipo de cabelo "Sem mudança"',
      `${await situacao('Corte')} | ${await situacao('Cor')} | ${await situacao('Tipo de cabelo')}`
    );
    conferir(/Corte: descreva o corte desejado ou escolha "Manter o corte atual"/.test(tela), '1. o rodapé diz o que falta', tela.slice(-300));
    conferir(!/Falta preencher/.test(tela) && !/^Descreva o corte desejado/m.test(tela), '1. campo vazio não aparece como erro antes de tentar seguir', '');
    await botao('Revisar pedido').click();
    await espera(800);
    const depois = await corpo();
    conferir(/Estilo e cor/.test(depois) && !/O que vai mudar/.test(depois), '1. com algo faltando, "Revisar pedido" não avança', '');
    conferir((await situacao('Corte')) === 'Corte, falta preencher', '1. e marca a seção que falta', await situacao('Corte'));
    // No campo, a mensagem começa com maiúscula; no rodapé, vem depois de "Corte: ".
    conferir(/(^|[^:] )Descreva o corte desejado ou escolha "Manter o corte atual"/m.test(depois), '1. e mostra o erro no próprio campo', depois.slice(0, 700));
    const topo = (await secao('Corte').boundingBox())?.y ?? -1;
    conferir(topo >= 0 && topo < 844, '1. a seção que falta fica à vista', String(topo));
  }

  // --- 2. ideias recolhidas, estilo do corte e preenchimento ---------------------------
  {
    let tela = await corpo();
    conferir(/Sem ideias\? Veja cortes populares/.test(tela) && /Sem ideias\? Veja cores populares/.test(tela), '2. ideias de corte e de cor começam recolhidas', '');
    conferir(!/Em alta: Long bob estruturado/.test(tela), '2. recolhidas, as ideias não ocupam a tela', '');
    await botao('Sem ideias? Veja cortes populares').click();
    await botao('Sem ideias? Veja cores populares').click();
    await espera(300);
    tela = await corpo();
    conferir(
      /Em alta: Long bob estruturado, Bob texturizado, Butterfly, Shaggy com franja, Chanel de bico, Degradê, Mullet moderno, Texturizado curto\./.test(tela) &&
        /Clássicos: Chanel, Pixie, Camadas longas, Franja reta, Corte social, Caesar\./.test(tela),
      '2. ideias de corte em texto: em alta e clássicos',
      tela.slice(0, 1200)
    );
    conferir(
      /Em alta: Loiro manteiga, Loiro mel, Morena iluminada, Chocolate quente, Cobre canela, Vermelho bordô\./.test(tela) &&
        /Clássicos: Preto natural, Castanho-escuro, Castanho-claro, Loiro, Ruivo, Grisalho\./.test(tela),
      '2. ideias de cor em texto: em alta e clássicas',
      ''
    );
    conferir(/São só ideias: escreva do seu jeito/.test(tela), '2. a tela diz que as ideias não limitam', '');
    const tocaveis = await page.evaluate(
      () => [...document.querySelectorAll('[role="radio"],[role="button"]')].filter((e) => /^(Chanel|Pixie|Butterfly|Loiro mel|Ruivo|Ver mais|Outra cor)$/.test((e.getAttribute('aria-label') ?? e.textContent ?? '').trim())).length
    );
    conferir(tocaveis === 0, '2. nenhuma ideia é botão ou opção de toque', `${tocaveis} encontrados`);
    await botao('Esconder ideias de cortes').click();
    await botao('Esconder ideias de cores').click();
  }
  {
    const grupo = page.getByRole('radiogroup', { name: /^Estilo do corte/ }).filter({ visible: true });
    conferir((await grupo.count()) === 1, '2. a seção do corte tem "Estilo do corte"', '');
    conferir(JSON.stringify(await generoMarcado()) === JSON.stringify(['Neutro']), '2. "Neutro" começa marcado', JSON.stringify(await generoMarcado()));
    conferir(/Neutro é um corte sem gênero definido/.test(await corpo()), '2. a tela explica o que é "Neutro"', '');
    conferir(!/Não especificar/.test(await corpo()), '2. "Não especificar" não existe mais', '');
    await opcao('Feminino').click();
    await espera(300);
    conferir(JSON.stringify(await generoMarcado()) === JSON.stringify(['Feminino']), '2. tocar em "Feminino" marca só ele', JSON.stringify(await generoMarcado()));
    const altura = (await opcao('Feminino').boundingBox())?.height ?? 0;
    conferir(altura >= 44, '2. as opções de estilo têm alvo de toque de 44 px', String(altura));
  }
  {
    const placeholder = await campo('Descrição do corte').getAttribute('placeholder');
    conferir(/^Ex\.: Quero manter o comprimento, adicionar camadas longas, uma franja cortininha/.test(placeholder ?? ''), '2. o campo do corte traz o exemplo de descrição livre', placeholder);
    conferir(/Descreva do seu jeito!/.test(await corpo()), '2. e o texto de ajuda do corte', '');
    const placeholderCor = await campo('Descrição da cor').getAttribute('placeholder');
    conferir(/^Ex\.: Quero manter a raiz castanho escuro, com mechas caramelo suaves/.test(placeholderCor ?? ''), '2. o campo da cor traz o exemplo de cor por regiões', placeholderCor);
    conferir(/mechas, luzes, reflexos, degradês/.test(await corpo()), '2. e o texto de ajuda da cor', '');
  }
  await campo('Descrição do corte').fill('Chanel');
  await espera(300);
  conferir((await situacao('Corte')) === 'Corte, pronto', '2. corte escrito: a seção fica "Pronto"', await situacao('Corte'));
  conferir(/Cor: descreva a cor desejada/.test(await corpo()), '2. o rodapé passa para o que falta na cor', '');
  conferir(!/Tons bem claros/.test(await corpo()), '2. sem tom claro, sem o aviso de tons claros', '');
  await campo('Descrição da cor').fill('Loiro mel');
  await espera(300);
  conferir((await situacao('Cor')) === 'Cor, pronto', '2. cor escrita: a seção fica "Pronto"', await situacao('Cor'));
  conferir(/Tons bem claros, como loiro claro, platinado e grisalho/.test(await corpo()), '2. pedir loiro mostra o aviso de tons claros', '');
  conferir(/Tudo pronto/.test(await corpo()), '2. e o rodapé confirma que está completo', '');
  await foto('02-preenchido');

  // --- 3. manter o atual, conflitos e "nada a simular" -----------------------------------
  {
    await opcao('Manter a cor atual').click();
    await espera(300);
    let tela = await corpo();
    conferir(await marcada('Manter a cor atual'), '3. "Manter a cor atual" marcado', '');
    conferir(/Você já escreveu uma descrição/.test(tela) && /“Loiro mel”/.test(tela), '3. com texto escrito, a tela mostra o texto e pede uma decisão', tela.slice(-900));
    conferir((await situacao('Cor')) === 'Cor, decidir', '3. a seção fica "Decidir"', await situacao('Cor'));
    conferir(/Cor: você escreveu uma descrição, mas escolheu "Manter a cor atual"/.test(tela), '3. o rodapé explica o conflito', '');
    await botao('Revisar pedido').click();
    await espera(600);
    conferir(!/O que vai mudar/.test(await corpo()), '3. com conflito, não avança', '');
    await botao('Usar a descrição').click();
    await espera(300);
    conferir(await marcada('Quero mudar'), '3. "Usar a descrição" volta para "Quero mudar"', '');
    conferir((await campo('Descrição da cor').inputValue()) === 'Loiro mel', '3. com o texto intacto', '');
    await opcao('Manter a cor atual').click();
    await botao('Manter a cor atual e apagar o texto').click();
    await espera(300);
    tela = await corpo();
    conferir(/A cor fica como está na foto/.test(tela) && !/Você já escreveu/.test(tela), '3. apagar o texto confirma a cor mantida', '');
    conferir((await situacao('Cor')) === 'Cor, sem mudança', '3. a seção fica "Sem mudança"', await situacao('Cor'));
    // Manter o corte também (apagando "Chanel"): manter tudo não é pedido.
    await page.getByRole('radio', { name: 'Manter o corte atual', exact: true }).first().click();
    await botao('Manter o corte atual e apagar o texto').click();
    await espera(300);
    conferir(/Nada a simular: mude o corte, a cor ou o tipo de cabelo/.test(await corpo()), '3. manter corte, cor e tipo: nada a simular', '');
  }

  // --- 4. tipo de cabelo ---------------------------------------------------------------
  {
    conferir(await marcada('Manter meu tipo de cabelo atual'), '4. "Manter meu tipo de cabelo atual" começa marcado', '');
    conferir(!/Não sei informar/.test(await corpo()), '4. "Não sei informar" não existe mais', '');
    conferir(/Vai para a simulação:\s*manter o tipo de cabelo atual/.test(await corpo()), '4. a tela diz o que vai para a simulação', '');
    const categorias = ['Liso: Fios retos', 'Ondulado: Ondas em S', 'Cacheado: Cachos em espiral', 'Crespo: Molas e zigue-zague'];
    const tipos = {
      'Liso: Fios retos': ['1A: Muito fino, sem volume', '1B: Liso com mais corpo', '1C: Grosso, quase ondulado'],
      'Ondulado: Ondas em S': ['2A: Ondas leves e abertas', '2B: Ondas definidas em S', '2C: Ondas fortes, quase cachos'],
      'Cacheado: Cachos em espiral': ['3A: Cachos largos e soltos', '3B: Cachos médios e definidos', '3C: Cachos pequenos e fechados'],
      'Crespo: Molas e zigue-zague': ['4A: Molas pequenas e definidas', '4B: Zigue-zague em Z', '4C: Bem fechado, encolhe muito'],
    };
    const desenhos = new Set();
    let todos = true;
    for (const categoria of categorias) {
      await opcao(categoria).click();
      await espera(250);
      todos &&= await marcada(categoria);
      todos &&= !(await marcada('Manter meu tipo de cabelo atual'));
      for (const tipo of tipos[categoria]) {
        const ladrilho = opcao(tipo);
        const desenho = await ladrilho.evaluate((e) => e.querySelector('svg')?.innerHTML ?? '');
        if (desenho) desenhos.add(desenho);
        await ladrilho.click();
        await espera(150);
        todos &&= await marcada(tipo);
        const codigo = tipo.slice(0, 2);
        todos &&= new RegExp(`Vai para a simulação:\\s*\\S+ ${codigo}:`).test(await corpo());
      }
    }
    conferir(todos, '4. cada categoria e cada tipo de 1A a 4C pode ser escolhido, e a tela diz o valor final', '');
    conferir(desenhos.size === 12, `4. os 12 tipos têm ilustrações diferentes (${desenhos.size})`, '');
    // Troca de categoria sem resto: o tipo da anterior some.
    await opcao('Ondulado: Ondas em S').click();
    await opcao('2B: Ondas definidas em S').click();
    await opcao('Crespo: Molas e zigue-zague').click();
    await espera(300);
    let tela = await corpo();
    conferir(!/2B/.test(tela) && /Qual crespo você deseja\?/.test(tela) && /Vai para a simulação:\s*Crespo\b/.test(tela), '4. trocar de categoria descarta o tipo da outra', tela.slice(-600));
    await opcao('4B: Zigue-zague em Z').click();
    await opcao('4B: Zigue-zague em Z').click();
    await espera(200);
    conferir(/Vai para a simulação:\s*Crespo\b/.test(await corpo()) && !(await marcada('4B: Zigue-zague em Z')), '4. tocar de novo no tipo desmarca e volta à categoria', '');
    conferir(/Tudo pronto/.test(await corpo()) && (await situacao('Tipo de cabelo')) === 'Tipo de cabelo, novo tipo', '4. mudar só o tipo de cabelo é um pedido válido', await situacao('Tipo de cabelo'));
    await foto('03-tipo-de-cabelo');
    await opcao('Manter meu tipo de cabelo atual').click();
    await espera(300);
    tela = await corpo();
    conferir(!/Qual crespo você deseja\?/.test(tela) && !(await marcada('Crespo: Molas e zigue-zague')), '4. "Manter meu tipo" desfaz a categoria e esconde os tipos', '');
    // Volta ao pedido de corte e cor por escrito.
    await page.getByRole('radio', { name: 'Quero mudar', exact: true }).nth(0).click();
    await page.getByRole('radio', { name: 'Quero mudar', exact: true }).nth(1).click();
    await campo('Descrição do corte').fill('Chanel');
    await campo('Descrição da cor').fill('Loiro mel');
    await espera(300);
    conferir(JSON.stringify(await generoMarcado()) === JSON.stringify(['Feminino']), '4. o estilo do corte escolhido continua guardado', JSON.stringify(await generoMarcado()));
  }

  // --- 5. validação ---------------------------------------------------------------
  await campo('Descrição do corte').fill('<b>bob</b>');
  await espera(300);
  conferir(/Use só letras, números e pontuação comum/.test(await corpo()), '5. marcação é recusada na hora, no campo', '');
  conferir((await situacao('Corte')) === 'Corte, corrigir', '5. a seção fica "Corrigir"', await situacao('Corte'));
  await botao('Revisar pedido').click();
  await espera(600);
  conferir(!/O que vai mudar/.test(await corpo()), '5. com texto inválido, não segue', '');
  await campo('Descrição do corte').fill('a'.repeat(320));
  conferir((await campo('Descrição do corte').inputValue()).length === 300, '5. o campo para em 300 caracteres', String((await campo('Descrição do corte').inputValue()).length));
  conferir(/300\/300/.test(await corpo()), '5. a contagem aparece ao lado do rótulo', '');
  await campo('Descrição do corte').fill('Chanel');

  // --- 6. revisão -----------------------------------------------------------------
  await revisar();
  await foto('04-revisao-exemplos');
  {
    const tela = await corpo();
    conferir(/Revisar pedido/.test(tela) && /O que vai mudar/.test(tela), '6. abre a revisão com o resumo', tela.slice(0, 200));
    conferir((await page.getByLabel('Foto do cliente que será enviada').count()) === 1, '6. mostra a foto original que será usada', '');
    // Os rótulos são etiquetas em caixa alta: o texto da página vem como "CORTE".
    conferir(/Corte\s*Chanel/i.test(tela) && /Cor\s*Loiro mel/i.test(tela), '6. mostra corte e cor', tela.slice(0, 900));
    conferir(/Estilo do corte\s*Feminino/i.test(tela), '6. mostra o estilo do corte', '');
    conferir(/Tipo de cabelo\s*Manter o tipo atual/i.test(tela), '6. mostra que o tipo de cabelo fica', '');
    conferir(!/referência/i.test(tela) && !/falad/i.test(tela), '6. sem referência e sem pedido falado', '');
    conferir(!/change-haircut/.test(tela) && !/Modelo:/.test(tela), '6. sem termos técnicos no resumo (modelo recolhido)', '');
    conferir(/modo local, sem serviço de IA/.test(tela), '6. avisa que o servidor está no modo local', '');
    const aberta = await verInstrucao();
    conferir(/haircut=Bob; hair_color=Honey Blonde; gender=female/.test(aberta) && /change-haircut/.test(aberta), '6. exemplos exatos vão às opções do modelo principal, com o gênero', aberta.slice(-700));
    conferir(await semRolagemLateral(), '6. revisão sem rolagem lateral em 390 px', '');
  }
  await botao('Alterar: corte').click();
  await espera(1200);
  await campo('Descrição do corte').fill('Chanel na altura do queixo, com franja leve');
  await opcao('Cacheado: Cachos em espiral').click();
  await opcao('3B: Cachos médios e definidos').click();
  await opcao('Manter a cor atual').click();
  await botao('Manter a cor atual e apagar o texto').click();
  await revisar();
  {
    const tela = await corpo();
    conferir(/Tipo de cabelo\s*Cacheado 3B: cachos médios e definidos/i.test(tela), '6. o tipo escolhido aparece por extenso', tela.slice(0, 900));
    conferir(/Cor\s*Manter a cor atual/i.test(tela), '6. a cor mantida aparece como manutenção', '');
    const aberta = await verInstrucao();
    conferir(
      /New hair texture: type 3B curly hair/.test(aberta) && /flux-kontext-pro/.test(aberta) && /Chanel na altura do queixo, com franja leve/.test(aberta),
      '6. com tipo de cabelo, vai ao modelo de texto com a frase da textura e a descrição como foi escrita',
      aberta.slice(-900)
    );
    await foto('05-revisao-tipo');
    await botao('Alterar: tipo de cabelo').click();
    await espera(1200);
    conferir(
      /Estilo e cor/.test(await corpo()) && (await campo('Descrição do corte').inputValue()) === 'Chanel na altura do queixo, com franja leve',
      '6. "Alterar" volta à etapa com tudo preenchido',
      ''
    );
    conferir(await marcada('3B: Cachos médios e definidos') && await marcada('Manter a cor atual'), '6. o tipo e a cor mantida continuam marcados ao voltar', '');
    conferir(JSON.stringify(await generoMarcado()) === JSON.stringify(['Feminino']), '6. o estilo do corte continua marcado ao voltar', JSON.stringify(await generoMarcado()));
  }

  // --- 7. geração: um envio só -------------------------------------------------------
  {
    // Interceptado (e seguido adiante) para ler o corpo: com a foto em multipart, o evento
    // comum de requisição do navegador não traz o corpo.
    const envios = [];
    await page.route('**/api/v1/simulacoes', (rota) => {
      if (rota.request().method() === 'POST') envios.push(rota.request().postDataBuffer()?.toString('latin1') ?? '');
      return rota.continue();
    });
    await revisar();
    await botao('Gerar simulação').dblclick();
    let resultado = '';
    for (let i = 0; i < 30; i++) {
      await espera(1000);
      resultado = await corpo();
      if (/aproximação visual/.test(resultado)) break;
    }
    await foto('06-resultado');
    conferir(envios.length === 1, `7. toque duplo gera um envio só (${envios.length})`, envios.length);
    conferir(/aproximação visual/.test(resultado), '7. a simulação conclui e o resultado abre', resultado.slice(0, 200));
    conferir(
      /Corte:\s*Chanel na altura do queixo, com franja leve/.test(resultado) &&
        /Cor:\s*Cor atual/.test(resultado) &&
        /Tipo de cabelo:\s*Cacheado 3B/.test(resultado),
      '7. o resultado mostra o pedido, com o tipo de cabelo',
      resultado.slice(0, 500)
    );
    await botao('Ver o que foi pedido ao modelo').click();
    conferir(/Edit only the hair/.test(await corpo()) && /New hair texture/.test(await corpo()), '7. o resultado mostra a instrução usada', '');
    await page.unroute('**/api/v1/simulacoes');
    const envio = envios[0] ?? '';
    conferir(
      /name="corte"\r\n\r\nChanel na altura do queixo, com franja leve/.test(envio) &&
        /name="manterCor"\r\n\r\ntrue/.test(envio) &&
        /name="cor"\r\n\r\n\r\n/.test(envio) &&
        /name="genero"\r\n\r\nfemale/.test(envio) &&
        /name="textura"\r\n\r\n3B/.test(envio) &&
        /name="chaveEnvio"/.test(envio) &&
        !/name="(referencia|audio|curvatura)"/.test(envio),
      '7. o envio leva a foto, o pedido (gênero e tipo de cabelo) e a chave, e mais nada',
      envio.slice(0, 400)
    );
  }

  // --- 8. erros -----------------------------------------------------------------------
  {
    await botao(/^Refazer/).click();
    await espera(1500);
    conferir((await campo('Descrição do corte').inputValue()) === 'Chanel na altura do queixo, com franja leve', '8. "Refazer" volta às escolhas preenchidas', '');

    // Sem conexão no envio: a tela de falha guarda as escolhas e a nova tentativa usa a mesma chave.
    const chaves = [];
    let derrubar = true;
    await page.route('**/api/v1/simulacoes', async (rota) => {
      if (rota.request().method() !== 'POST') return rota.continue();
      chaves.push((rota.request().postDataBuffer()?.toString('latin1') ?? '').match(/name="chaveEnvio"\r\n\r\n([0-9a-f-]+)/)?.[1]);
      if (derrubar) return rota.abort('internetdisconnected');
      return rota.continue();
    });
    await revisar();
    await botao('Gerar simulação').click();
    await espera(3500);
    await foto('07-sem-conexao');
    let tela = await corpo();
    conferir(/Sem conexão com o servidor/.test(tela), '8. sem conexão: a tela diz o que houve', tela.slice(0, 200));
    conferir(/Chanel na altura do queixo, com franja leve/.test(tela) && /Cor atual/.test(tela), '8. e mostra que as escolhas continuam guardadas', '');
    derrubar = false;
    await botao('Tentar novamente').click();
    for (let i = 0; i < 20; i++) {
      await espera(1000);
      tela = await corpo();
      if (/aproximação visual/.test(tela)) break;
    }
    conferir(/aproximação visual/.test(tela), '8. a nova tentativa conclui sem preencher nada de novo', tela.slice(0, 200));
    conferir(chaves.length === 2 && chaves[0] && chaves[0] === chaves[1], '8. e reaproveita a chave de envio (não paga duas vezes)', JSON.stringify(chaves));
    await page.unroute('**/api/v1/simulacoes');

    // Credencial recusada: não oferece "Tentar novamente".
    await botao(/^Refazer/).click();
    await espera(1200);
    await page.route('**/api/v1/simulacoes', (rota) =>
      rota.request().method() === 'POST'
        ? rota.fulfill({
            status: 502,
            contentType: 'application/json',
            body: JSON.stringify({ erro: { codigo: 'credencial_invalida', mensagem: 'Credencial do provedor de IA recusada.' } }),
          })
        : rota.continue()
    );
    await revisar();
    await botao('Gerar simulação').click();
    await espera(3000);
    tela = await corpo();
    conferir(/A chave do serviço de IA foi recusada/.test(tela) && (await botao('Tentar novamente').count()) === 0, '8. credencial recusada: explica e não oferece repetir', tela.slice(0, 200));
    await page.unroute('**/api/v1/simulacoes');

    // Pedido recusado pelo servidor: volta às escolhas com o motivo.
    await botao('Mudar o pedido').click();
    await espera(1200);
    await page.route('**/api/v1/simulacoes', (rota) =>
      rota.request().method() === 'POST'
        ? rota.fulfill({
            status: 422,
            contentType: 'application/json',
            body: JSON.stringify({ erro: { codigo: 'textura_invalida', mensagem: 'Tipo de cabelo inválido: escolha liso, ondulado, cacheado, crespo, um tipo de 1A a 4C, ou manter o tipo atual.' } }),
          })
        : rota.continue()
    );
    await revisar();
    await botao('Gerar simulação').click();
    await espera(2500);
    tela = await corpo();
    conferir(/Estilo e cor/.test(tela) && /Tipo de cabelo inválido/.test(tela), '8. pedido recusado: volta às escolhas com o motivo', tela.slice(0, 300));
    await page.unroute('**/api/v1/simulacoes');
  }

  // --- 9. responsividade, rodapé, alvos de toque e console --------------------------------
  /** O fim do conteúdo rolado até o fundo fica acima do rodapé (o rodapé não cobre nada). */
  const rodapeNaoCobre = () =>
    page.evaluate(() => {
      const ultimo = [...document.querySelectorAll('div')].find((d) => d.textContent?.startsWith('Vai para a simulação:') && d.children.length <= 2);
      const botaoRevisar = [...document.querySelectorAll('[role="button"]')].find((b) => /Revisar pedido$/.test(b.textContent?.trim() ?? ''));
      if (!ultimo || !botaoRevisar) return 'sem elementos';
      // A área que rola é o ancestral do fim do conteúdo com rolagem própria.
      let rolagem = ultimo.parentElement;
      while (rolagem && !(rolagem.scrollHeight > rolagem.clientHeight + 5 && /auto|scroll/.test(getComputedStyle(rolagem).overflowY))) {
        rolagem = rolagem.parentElement;
      }
      if (!rolagem) return 'sem rolagem';
      rolagem.scrollTop = rolagem.scrollHeight;
      const fim = ultimo.getBoundingClientRect().bottom;
      const area = rolagem.getBoundingClientRect().bottom;
      const botao = botaoRevisar.getBoundingClientRect().top;
      // O fim do conteúdo aparece dentro da área de rolagem, e a área termina antes do rodapé.
      return fim <= area + 1 && area <= botao + 1 ? true : `fim ${fim}, área ${area}, botão ${botao}`;
    });
  const colunasDasCategorias = () =>
    page.evaluate(() => {
      const ys = ['Liso: Fios retos', 'Ondulado: Ondas em S', 'Cacheado: Cachos em espiral', 'Crespo: Molas e zigue-zague'].map(
        (nome) => document.querySelector(`[role="radio"][aria-label="${nome}"]`)?.getBoundingClientRect().top ?? -1
      );
      return ys.filter((y) => Math.abs(y - ys[0]) < 2).length;
    });
  await opcao('Ondulado: Ondas em S').click();
  await espera(300);
  conferir(await semRolagemLateral(), '9. "Estilo e cor" sem rolagem lateral em 390 px', '');
  conferir(await colunasDasCategorias() === 2, '9. em 390 px, as categorias ficam em duas colunas', String(await colunasDasCategorias()));
  conferir((await rodapeNaoCobre()) === true, '9. em 390 px, o rodapé não cobre o fim do conteúdo', await rodapeNaoCobre());
  await page.setViewportSize({ width: 320, height: 640 });
  await espera(800);
  conferir(await semRolagemLateral(), '9. sem rolagem lateral em 320 px', '');
  conferir((await rodapeNaoCobre()) === true, '9. em 320 px, o rodapé não cobre o fim do conteúdo', await rodapeNaoCobre());
  {
    const recortados = await page.evaluate(() =>
      [...document.querySelectorAll('[role="radio"]')]
        .filter((e) => e.offsetParent !== null)
        .filter((e) => e.scrollWidth > e.clientWidth + 1).length
    );
    conferir(recortados === 0, '9. em 320 px, nenhuma opção tem texto cortado na largura', `${recortados} recortadas`);
  }
  await foto('08-estreito');
  await page.setViewportSize({ width: 1280, height: 900 });
  await espera(800);
  conferir(await semRolagemLateral(), '9. sem rolagem lateral em 1280 px', '');
  conferir(await colunasDasCategorias() === 4, '9. em tela larga, as quatro categorias ficam numa linha', String(await colunasDasCategorias()));
  await foto('09-largo');
  const alvos = await page.evaluate(() =>
    [...document.querySelectorAll('[role="radio"]')]
      .filter((e) => e.offsetParent !== null)
      .map((e) => e.getBoundingClientRect())
      .filter((r) => r.height < 44 || r.width < 44).length
  );
  conferir(alvos === 0, '9. todas as opções com alvo de toque de 44 px ou mais', `${alvos} pequenos`);
  const reais = errosDoConsole.filter((e) => !/Failed to load resource|net::ERR_INTERNET_DISCONNECTED|status of (422|502)/.test(e));
  conferir(reais.length === 0, '9. console sem erros de execução', reais.slice(0, 3).join(' | '));
} catch (e) {
  falha('execução', e instanceof Error ? e.message.split('\n')[0] : String(e));
  await page.screenshot({ path: `${TELAS}/erro.png` }).catch(() => undefined);
} finally {
  await navegador.close();
}

console.log(`\n${passos.length - erros.length} verificações ok, ${erros.length} falhas`);
fs.writeFileSync(path.join(TELAS, 'resultado.txt'), passos.join('\n') + '\n');
process.exit(erros.length ? 1 : 0);
