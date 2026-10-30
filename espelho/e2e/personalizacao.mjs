/**
 * Verifica no navegador a etapa "Estilo e cor", a revisão e a geração.
 *
 *  1  a etapa abre com a foto da etapa anterior, o guia "Como preencher" e os passos
 *     "A preencher"; "Revisar pedido" começa bloqueado e o rodapé diz o que falta;
 *  2  exemplos de corte e de cor em texto (em alta e clássicos), sem botões de opção;
 *     escrever o corte e a cor muda o selo do passo e o rodapé; gênero do corte com
 *     "Não especificar" marcado, e a troca para "Feminino";
 *  3  "Manter o atual": o campo some, o texto volta ao desmarcar, os dois mantidos bloqueiam;
 *  4  validação na hora (marcação, limite de 300 com contagem) e selo "Corrigir";
 *  5  revisão: foto, corte, gênero, cor, como será gerado (exemplo exato e descrição livre),
 *     "Não mudar" e "Editar"; nada de referência nem de pedido falado;
 *  6  geração: um envio só mesmo com toque duplo; o resultado mostra o pedido e a instrução;
 *  7  erros: sem conexão (escolhas preservadas, nova tentativa com a mesma chave),
 *     credencial recusada (sem "Tentar novamente"), pedido recusado (volta às escolhas);
 *  8  responsividade (320, 390 e 1280 px), alvos de toque e console sem erros.
 *
 * Pré-requisitos: API (AI_PROVIDER=fake) e `expo start --web` no ar, carga de demonstração
 * recriada. O provedor local não é IA: a imagem sai com aviso. O que se verifica aqui é a
 * interface e o contrato.
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
// Nome em texto é exato ("Não mudar: cor" não pode casar com "Não mudar: corte").
const botao = (nome) =>
  page.getByRole('button', { name: nome, exact: typeof nome === 'string' }).filter({ visible: true }).first();
const campo = (rotulo) => page.getByLabel(rotulo, { exact: true }).filter({ visible: true }).first();
const caixa = (inicio) => page.getByRole('checkbox', { name: new RegExp(`^${inicio}`) }).filter({ visible: true }).first();
const passo = (numero) =>
  page.getByRole('heading', { name: new RegExp(`^Passo ${numero}:`) }).filter({ visible: true }).first();
const nomeDoPasso = async (numero) => (await passo(numero).getAttribute('aria-label')) ?? '';
const desabilitado = async (localizador) =>
  (await localizador.getAttribute('aria-disabled')) === 'true' || (await localizador.isDisabled().catch(() => false));
const genero = (rotulo) => page.getByRole('button', { name: rotulo, exact: true }).filter({ visible: true }).first();
const generoMarcado = async () => {
  const marcados = [];
  for (const rotulo of ['Feminino', 'Masculino', 'Não especificar']) {
    if ((await genero(rotulo).getAttribute('aria-selected')) === 'true') marcados.push(rotulo);
  }
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
    if (/Como será gerado/.test(await corpo())) return;
  }
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
    conferir(
      /Como preencher/.test(tela) &&
        /1\.\s*Corte: escolha o gênero e escreva o novo corte/.test(tela) &&
        /2\.\s*Cor: escreva a nova cor/.test(tela) &&
        /3\.\s*Toque em "Revisar pedido"/.test(tela),
      '1. o guia "Como preencher" explica os três passos',
      tela.slice(0, 600)
    );
    conferir(/muda só o cabelo/.test(tela), '1. o guia diz que só o cabelo muda', '');
    conferir(
      (await nomeDoPasso(1)) === 'Passo 1: Corte, a preencher' && (await nomeDoPasso(2)) === 'Passo 2: Cor, a preencher',
      '1. os dois passos começam "A preencher" (título lido como "Passo N")',
      `${await nomeDoPasso(1)} | ${await nomeDoPasso(2)}`
    );
    conferir(await desabilitado(botao('Revisar pedido')), '1. "Revisar pedido" começa bloqueado', '');
    conferir(/Passo 1: escreva o novo corte ou marque "Manter o corte atual"/.test(tela), '1. o rodapé diz o que falta', tela.slice(-300));
  }

  // --- 2. exemplos em texto e preenchimento -----------------------------------------
  {
    const tela = await corpo();
    conferir(
      /Exemplos de corte que você pode escrever/i.test(tela) &&
        /Em alta: Long bob estruturado, Bob texturizado, Butterfly, Shaggy com franja, Chanel de bico, Degradê, Mullet moderno, Texturizado curto\./.test(tela) &&
        /Clássicos: Chanel, Pixie, Camadas longas, Franja reta, Corte social, Caesar\./.test(tela),
      '2. exemplos de corte em texto: em alta e clássicos',
      tela.slice(0, 1200)
    );
    conferir(
      /Exemplos de cor que você pode escrever/i.test(tela) &&
        /Em alta: Loiro manteiga, Loiro mel, Morena iluminada, Chocolate quente, Cobre canela, Vermelho bordô\./.test(tela) &&
        /Clássicos: Preto natural, Castanho-escuro, Castanho-claro, Loiro, Ruivo, Grisalho\./.test(tela),
      '2. exemplos de cor em texto: em alta e clássicos',
      ''
    );
    const opcoes = await page.evaluate(
      () => [...document.querySelectorAll('[role="radio"],[role="button"]')].filter((e) => /^(Chanel|Pixie|Butterfly|Loiro mel|Ruivo|Ver mais|Outra cor)$/.test((e.getAttribute('aria-label') ?? e.textContent ?? '').trim())).length
    );
    conferir(opcoes === 0, '2. nenhum exemplo é botão ou opção de toque', `${opcoes} encontrados`);
    conferir((await page.getByRole('radio').count()) === 0, '2. sem paleta de cores', '');
    conferir(/Tons bem claros, como loiro claro, platinado e grisalho/.test(tela), '2. o aviso de tons claros fica à vista no passo da cor', '');
  }
  {
    const grupo = page.getByRole('radiogroup', { name: 'Gênero do corte' }).filter({ visible: true });
    conferir((await grupo.count()) === 1 && /Gênero/i.test(await corpo()), '2. o passo do corte tem a escolha de gênero', '');
    conferir(
      JSON.stringify(await generoMarcado()) === JSON.stringify(['Não especificar']),
      '2. gênero começa em "Não especificar" (padrão do modelo)',
      JSON.stringify(await generoMarcado())
    );
    await genero('Feminino').click();
    await espera(300);
    conferir(JSON.stringify(await generoMarcado()) === JSON.stringify(['Feminino']), '2. tocar em "Feminino" marca só ele', JSON.stringify(await generoMarcado()));
    const altura = (await genero('Feminino').boundingBox())?.height ?? 0;
    conferir(altura >= 44, '2. as opções de gênero têm alvo de toque de 44 px', String(altura));
  }
  await campo('Novo corte').fill('Chanel');
  await espera(300);
  conferir((await nomeDoPasso(1)) === 'Passo 1: Corte, pronto', '2. corte escrito: o passo 1 fica "Pronto"', await nomeDoPasso(1));
  conferir(/Passo 2: escreva a nova cor/.test(await corpo()), '2. o rodapé passa para o que falta no passo 2', '');
  await campo('Nova cor').fill('Loiro mel');
  await espera(300);
  conferir((await nomeDoPasso(2)) === 'Passo 2: Cor, pronto', '2. cor escrita: o passo 2 fica "Pronto"', await nomeDoPasso(2));
  conferir(!(await desabilitado(botao('Revisar pedido'))), '2. com corte e cor, "Revisar pedido" libera', '');
  conferir(/Pedido completo/.test(await corpo()), '2. e o rodapé confirma que está completo', '');
  await foto('02-preenchido');

  // --- 3. manter o atual ----------------------------------------------------------
  {
    const manterCor = caixa('Manter a cor atual');
    await manterCor.click();
    conferir((await manterCor.getAttribute('aria-checked')) === 'true', '3. "Manter a cor atual" marcado', '');
    conferir((await page.getByLabel('Nova cor', { exact: true }).filter({ visible: true }).count()) === 0, '3. com a cor mantida, o campo e os exemplos somem', '');
    conferir((await nomeDoPasso(2)) === 'Passo 2: Cor, sem mudança', '3. o passo 2 fica "Sem mudança"', await nomeDoPasso(2));
    conferir(/A cor fica como está na foto/.test(await corpo()), '3. e a tela diz o que acontece com a cor', '');
    await manterCor.click();
    conferir((await campo('Nova cor').inputValue()) === 'Loiro mel', '3. desmarcar devolve o texto escrito antes', '');
    const manterCorte = caixa('Manter o corte atual');
    await manterCorte.click();
    await manterCor.click();
    conferir(await desabilitado(botao('Revisar pedido')), '3. manter os dois bloqueia (nada a simular)', '');
    conferir(/Nada a simular/.test(await corpo()), '3. e o rodapé explica', '');
    await manterCor.click();
    await manterCorte.click();
    conferir((await campo('Novo corte').inputValue()) === 'Chanel', '3. o corte escrito volta ao desmarcar', '');
  }

  // --- 4. validação ---------------------------------------------------------------
  await campo('Novo corte').fill('<b>bob</b>');
  await espera(300);
  conferir(/Use só letras, números e pontuação comum/.test(await corpo()), '4. marcação é recusada na hora, no campo', '');
  conferir((await nomeDoPasso(1)) === 'Passo 1: Corte, corrigir', '4. o passo 1 fica "Corrigir"', await nomeDoPasso(1));
  conferir(await desabilitado(botao('Revisar pedido')), '4. com texto inválido, não segue', '');
  await campo('Novo corte').fill('a'.repeat(320));
  conferir((await campo('Novo corte').inputValue()).length === 300, '4. o campo para em 300 caracteres', String((await campo('Novo corte').inputValue()).length));
  conferir(/300\/300/.test(await corpo()), '4. a contagem aparece ao lado do rótulo', '');
  await campo('Novo corte').fill('Chanel');

  // --- 5. revisão -----------------------------------------------------------------
  await revisar();
  await foto('03-revisao-exemplos');
  {
    const tela = await corpo();
    conferir(/Revisar pedido/.test(tela), '5. abre a revisão', tela.slice(0, 200));
    conferir((await page.getByLabel('Foto do cliente que será enviada').count()) === 1, '5. mostra a foto original que será usada', '');
    conferir(/Chanel/.test(tela) && /Loiro mel/.test(tela), '5. mostra corte e cor', '');
    conferir(/Gênero\s*Feminino/i.test(tela), '5. mostra o gênero escolhido', tela.slice(0, 600));
    conferir(!/referência/i.test(tela) && !/falad/i.test(tela), '5. sem referência e sem pedido falado', '');
    conferir(/Troca de corte e cor com as opções do modelo especializado/.test(tela) && /change-haircut/.test(tela), '5. exemplos exatos vão às opções do modelo principal', tela.slice(-700));
    conferir(/modo local, sem serviço de IA/.test(tela), '5. avisa que o servidor está no modo local', '');
    await botao('Ver o que vai para o modelo').click();
    conferir(/haircut=Bob; hair_color=Honey Blonde; gender=female/.test(await corpo()), '5. mostra o que vai para o modelo, com o gênero', '');
    conferir(await semRolagemLateral(), '5. revisão sem rolagem lateral em 390 px', '');
  }
  await botao('Editar: corte').click();
  await espera(1200);
  await campo('Novo corte').fill('Chanel na altura do queixo, com franja leve');
  await revisar();
  {
    const tela = await corpo();
    conferir(/Edição a partir da descrição escrita/.test(tela) && /flux-kontext-pro/.test(tela), '5. descrição livre vai ao modelo de texto', tela.slice(-600));
    await botao('Não mudar: cor').click();
    await espera(1500);
    conferir(/Cor atual/.test(await corpo()), '5. "Não mudar" a cor vale na hora', '');
    conferir((await botao('Não mudar: corte').count()) === 0, '5. com a cor mantida, o corte não pode deixar de mudar', '');
    await foto('04-revisao-descricao');
    await botao('Editar: corte').click();
    await espera(1200);
    conferir(/Estilo e cor/.test(await corpo()) && (await campo('Novo corte').inputValue()) === 'Chanel na altura do queixo, com franja leve', '5. "Editar" volta à etapa com tudo preenchido', '');
    conferir((await caixa('Manter a cor atual').getAttribute('aria-checked')) === 'true', '5. o "Não mudar" da revisão aparece na etapa', '');
    conferir(JSON.stringify(await generoMarcado()) === JSON.stringify(['Feminino']), '5. o gênero escolhido continua marcado ao voltar', JSON.stringify(await generoMarcado()));
  }

  // --- 6. geração: um envio só -------------------------------------------------------
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
    await foto('05-resultado');
    conferir(envios.length === 1, `6. toque duplo gera um envio só (${envios.length})`, envios.length);
    conferir(/aproximação visual/.test(resultado), '6. a simulação conclui e o resultado abre', resultado.slice(0, 200));
    conferir(/Corte:\s*Chanel na altura do queixo, com franja leve/.test(resultado) && /Cor:\s*Cor atual/.test(resultado), '6. o resultado mostra o pedido', resultado.slice(0, 400));
    await botao('Ver o que foi pedido ao modelo').click();
    conferir(/Edit only the hair/.test(await corpo()), '6. o resultado mostra a instrução usada', '');
    await page.unroute('**/api/v1/simulacoes');
    const envio = envios[0] ?? '';
    conferir(
      /name="corte"\r\n\r\nChanel na altura do queixo, com franja leve/.test(envio) &&
        /name="manterCor"\r\n\r\ntrue/.test(envio) &&
        /name="genero"\r\n\r\nfemale/.test(envio) &&
        /name="chaveEnvio"/.test(envio) &&
        !/name="(referencia|audio)"/.test(envio),
      '6. o envio leva a foto, o pedido (com o gênero) e a chave, e mais nada',
      envio.slice(0, 300)
    );
  }

  // --- 7. erros -----------------------------------------------------------------------
  {
    await botao(/^Refazer/).click();
    await espera(1500);
    conferir((await campo('Novo corte').inputValue()) === 'Chanel na altura do queixo, com franja leve', '7. "Refazer" volta às escolhas preenchidas', '');

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
    await foto('06-sem-conexao');
    let tela = await corpo();
    conferir(/Sem conexão com o servidor/.test(tela), '7. sem conexão: a tela diz o que houve', tela.slice(0, 200));
    conferir(/Chanel na altura do queixo, com franja leve/.test(tela) && /Cor atual/.test(tela), '7. e mostra que as escolhas continuam guardadas', '');
    derrubar = false;
    await botao('Tentar novamente').click();
    for (let i = 0; i < 20; i++) {
      await espera(1000);
      tela = await corpo();
      if (/aproximação visual/.test(tela)) break;
    }
    conferir(/aproximação visual/.test(tela), '7. a nova tentativa conclui sem preencher nada de novo', tela.slice(0, 200));
    conferir(chaves.length === 2 && chaves[0] && chaves[0] === chaves[1], '7. e reaproveita a chave de envio (não paga duas vezes)', JSON.stringify(chaves));
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
    conferir(/A chave do serviço de IA foi recusada/.test(tela) && (await botao('Tentar novamente').count()) === 0, '7. credencial recusada: explica e não oferece repetir', tela.slice(0, 200));
    await page.unroute('**/api/v1/simulacoes');

    // Pedido recusado pelo servidor: volta às escolhas com o motivo.
    await botao('Mudar o pedido').click();
    await espera(1200);
    await page.route('**/api/v1/simulacoes', (rota) =>
      rota.request().method() === 'POST'
        ? rota.fulfill({
            status: 422,
            contentType: 'application/json',
            body: JSON.stringify({ erro: { codigo: 'descricao_invalida', mensagem: 'Use só letras, números e pontuação comum na descrição.' } }),
          })
        : rota.continue()
    );
    await revisar();
    await botao('Gerar simulação').click();
    await espera(2500);
    tela = await corpo();
    conferir(/Estilo e cor/.test(tela) && /Use só letras, números e pontuação comum/.test(tela), '7. pedido recusado: volta às escolhas com o motivo', tela.slice(0, 300));
    await page.unroute('**/api/v1/simulacoes');
  }

  // --- 8. responsividade, alvos de toque e console -----------------------------------
  conferir(await semRolagemLateral(), '8. "Estilo e cor" sem rolagem lateral em 390 px', '');
  await caixa('Manter a cor atual').click();
  await espera(400);
  await page.setViewportSize({ width: 320, height: 640 });
  await espera(800);
  conferir(await semRolagemLateral(), '8. sem rolagem lateral em 320 px', '');
  await foto('07-estreito');
  await page.setViewportSize({ width: 1280, height: 900 });
  await espera(800);
  conferir(await semRolagemLateral(), '8. sem rolagem lateral em 1280 px', '');
  await foto('08-largo');
  const alvos = await page.evaluate(() =>
    [...document.querySelectorAll('[role="checkbox"]')]
      .filter((e) => e.offsetParent !== null)
      .map((e) => e.getBoundingClientRect())
      .filter((r) => r.height < 44).length
  );
  conferir(alvos === 0, '8. caixas de marcar com alvo de toque de 44 px ou mais', `${alvos} pequenos`);
  const reais = errosDoConsole.filter((e) => !/Failed to load resource|net::ERR_INTERNET_DISCONNECTED|status of (422|502)/.test(e));
  conferir(reais.length === 0, '8. console sem erros de execução', reais.slice(0, 3).join(' | '));
} catch (e) {
  falha('execução', e instanceof Error ? e.message.split('\n')[0] : String(e));
  await page.screenshot({ path: `${TELAS}/erro.png` }).catch(() => undefined);
} finally {
  await navegador.close();
}

console.log(`\n${passos.length - erros.length} verificações ok, ${erros.length} falhas`);
fs.writeFileSync(path.join(TELAS, 'resultado.txt'), passos.join('\n') + '\n');
process.exit(erros.length ? 1 : 0);
