/**
 * Ampliação das imagens e tipo de cabelo desejado, no navegador.
 *
 *  1  "Estilo e cor" pergunta o tipo de cabelo desejado: começa em "Manter meu tipo de
 *     cabelo atual"; escolher "Cacheado" mostra os tipos 3A a 3C, cada um com ilustração;
 *  2  a revisão mostra "Tipo de cabelo: Cacheado 3C"; o envio leva o tipo, que o servidor
 *     grava na simulação (campo `textura`);
 *  3  no resultado, a foto original e a simulação abrem em tela cheia com zoom (botões de
 *     zoom, "1,5x"), e fecham pelo botão e pela tecla Esc;
 *  4  na tela da simulação, a imagem também amplia; console sem erros.
 *
 * Pré-requisitos: API (AI_PROVIDER=fake) e `expo start --web` no ar, carga de demonstração
 * recriada. Gestos de pinça não se testam no navegador: o zoom é conferido pelos botões,
 * que usam o mesmo cálculo.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000';
const TELAS = path.join(AQUI, 'telas-ampliacao');
fs.mkdirSync(TELAS, { recursive: true });
const RETRATO = path.join(AQUI, 'retrato-sintetico.jpg');
const EMAIL = 'carolina@salaoexemplo.com.br';
const SENHA = 'espelho-demo-2026';

let falhas = 0;
let total = 0;
const conferir = (cond, nome, detalhe = '') => {
  total += 1;
  if (!cond) falhas += 1;
  console.log(`${cond ? '[ok ]' : '[FALHA]'} ${nome}${cond ? '' : `: ${String(detalhe).slice(0, 300)}`}`);
};

const navegador = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const page = await (await navegador.newContext({ viewport: { width: 390, height: 844 }, locale: 'pt-BR' })).newPage();
const errosDoConsole = [];
page.on('console', (m) => m.type() === 'error' && errosDoConsole.push(m.text()));
page.on('pageerror', (e) => errosDoConsole.push(String(e)));
const corpo = () => page.locator('body').innerText();
const espera = (ms = 1200) => page.waitForTimeout(ms);
const botao = (nome) =>
  page.getByRole('button', { name: nome, exact: typeof nome === 'string' }).filter({ visible: true }).first();
const opcao = (nome) =>
  page.getByRole('radio', { name: nome, exact: typeof nome === 'string' }).filter({ visible: true }).first();
const marcado = async (nome) => (await opcao(nome).getAttribute('aria-checked')) === 'true';

try {
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await espera(2500);
  await page.getByRole('textbox').filter({ visible: true }).first().fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await botao(/^Entrar$/).click();
  await espera(4000);

  // --- 1. Tipo de cabelo desejado ------------------------------------------------
  await page.goto(`${APP}/simulacao/cliente`, { waitUntil: 'networkidle' });
  await espera(2500);
  await page.getByRole('button', { name: /^Simular para Marina/ }).first().click();
  await espera(3500);
  const escolha = page.waitForEvent('filechooser');
  await botao(/Escolher foto da galeria/).click();
  await (await escolha).setFiles(RETRATO);
  await espera(3000);

  let tela = await corpo();
  conferir(/Qual tipo de cabelo você deseja na simulação\?/.test(tela), '1. a etapa pergunta o tipo de cabelo desejado', tela.slice(0, 300));
  conferir(await marcado('Manter meu tipo de cabelo atual'), '1. começa em "Manter meu tipo de cabelo atual"');
  await opcao('Cacheado: Cachos em espiral').click();
  await espera(400);
  tela = await corpo();
  conferir(/Cachos largos e soltos/.test(tela) && /Cachos pequenos e fechados/.test(tela) && /Qual cacheado você deseja\?/.test(tela), '1. "Cacheado" mostra os tipos 3A a 3C');
  conferir(
    (await page.getByRole('radio', { name: /^3[ABC]: / }).filter({ visible: true }).locator('svg').count()) === 3,
    '1. cada tipo tem a sua ilustração'
  );
  conferir(await marcado('Cacheado: Cachos em espiral') && !(await marcado('3C: Cachos pequenos e fechados')), '1. só a categoria fica marcada até escolher um tipo');
  await opcao('3C: Cachos pequenos e fechados').click();
  await espera(300);
  conferir(await marcado('3C: Cachos pequenos e fechados'), '1. o tipo 3C fica marcado');
  await page.screenshot({ path: `${TELAS}/01-tipo-de-cabelo.png`, fullPage: true });

  await page.getByLabel('Descrição do corte', { exact: true }).filter({ visible: true }).first().fill('Chanel');
  await page.getByLabel('Descrição da cor', { exact: true }).filter({ visible: true }).first().fill('Ruivo');
  await espera(400);

  // --- 2. Revisão e envio ------------------------------------------------------
  await botao('Revisar pedido').click();
  for (let i = 0; i < 10 && !/Ver a instrução enviada à IA/.test(await corpo()); i++) await espera(500);
  tela = await corpo();
  conferir(/Tipo de cabelo[\s\S]{0,40}Cacheado 3C/i.test(tela), '2. a revisão mostra "Cacheado 3C"', tela.slice(0, 600));

  await botao('Gerar simulação').click();
  for (let i = 0; i < 30 && !/aproximação visual/.test(await corpo()); i++) await espera(700);
  tela = await corpo();
  conferir(/aproximação visual/.test(tela), '2. a simulação conclui', tela.slice(0, 200));

  const login = await fetch(`${API}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, senha: SENHA }),
  }).then((r) => r.json());
  const lista = await fetch(`${API}/api/v1/simulacoes`, {
    headers: { Authorization: `Bearer ${login.tokens.accessToken}` },
  }).then((r) => r.json());
  const recente = [...lista].sort((a, b) => b.criadoEm.localeCompare(a.criadoEm))[0];
  conferir(recente?.parametros?.textura === '3C', '2. o servidor gravou o tipo de cabelo 3C', JSON.stringify(recente?.parametros));
  conferir(/type 3C curly hair/.test(recente?.instrucaoIa ?? ''), '2. a instrução gravada leva o tipo 3C', (recente?.instrucaoIa ?? '').slice(0, 300));

  // --- 3. Ampliar no resultado -------------------------------------------------
  for (const [rotulo, titulo] of [['Foto original: ampliar', 'Foto original'], ['Simulação: ampliar', 'Simulação']]) {
    await botao(rotulo).click();
    await espera(1500);
    const fechar = botao('Fechar a imagem ampliada');
    conferir(await fechar.isVisible().catch(() => false), `3. "${titulo}" abre em tela cheia`);
    const aberta = await corpo();
    conferir(aberta.includes(titulo) && /Pinça ou toque duplo para ampliar/.test(aberta), `3. "${titulo}": imagem carregada, com título e dica`, aberta.slice(0, 200));
    await botao('Aumentar o zoom').click();
    await espera(400);
    conferir(/1,5x/.test(await corpo()), `3. "${titulo}": o botão de zoom amplia para 1,5x`);
    if (titulo === 'Simulação') await page.screenshot({ path: `${TELAS}/02-ampliada.png` });
    if (titulo === 'Foto original') {
      await fechar.click();
    } else {
      await page.keyboard.press('Escape');
    }
    await espera(800);
    conferir(!(await botao('Fechar a imagem ampliada').isVisible().catch(() => false)), `3. "${titulo}": fecha e volta ao resultado`);
  }

  // --- 4. Tela da simulação ----------------------------------------------------
  await page.goto(`${APP}/simulacao/imagem/${recente.id}`, { waitUntil: 'networkidle' });
  await espera(2500);
  tela = await corpo();
  conferir(/Tipo de cabelo[\s\S]{0,40}Cacheado 3C/i.test(tela), '4. a ficha da simulação mostra o tipo de cabelo', tela.slice(0, 500));
  await botao('Simulação: ampliar').click();
  await espera(1500);
  conferir(await botao('Fechar a imagem ampliada').isVisible().catch(() => false), '4. a imagem da ficha amplia');
  await botao('Fechar a imagem ampliada').click();
  await espera(500);

  conferir(errosDoConsole.length === 0, 'console sem erros', errosDoConsole.slice(0, 3).join(' | '));
} catch (erro) {
  conferir(false, 'execução', erro.message);
} finally {
  await navegador.close();
}

console.log(`\n${total - falhas} verificações ok, ${falhas} falhas`);
process.exit(falhas ? 1 : 0);
