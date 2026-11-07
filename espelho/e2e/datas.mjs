/**
 * Calendário da agenda e campos de data e hora na web.
 *
 * 1. Calendário: em larguras de 320 a 1280 px, cada semana tem 7 colunas, os sábados
 *    ficam sob "sáb" e a página não rola de lado. No Android a grade antiga (cada dia em
 *    100/7 %, com quebra de linha) empurrava o sábado para a linha de baixo.
 * 2. Data na web: apagar um número só esvazia aquele segmento (o resto da data fica), a
 *    tela avisa que está incompleta e redigitar o ano dígito a dígito completa a data. O
 *    campo com máscara antigo deslocava os dígitos seguintes ("01/12/026").
 * 3. Data de nascimento (opcional): o mesmo campo, e pela metade a tela avisa.
 *
 * Rodar com a API e o `expo start --web` no ar, com os dados de demonstração recriados.
 */
import { mkdirSync } from 'node:fs';

import { chromium } from 'playwright';

const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000';
const SAIDA = new URL('./telas-datas', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
mkdirSync(SAIDA, { recursive: true });
const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const resultados = [];
const ok = (nome, cond, extra = '') => { const l = `${cond ? 'ok  ' : 'FALHA'} ${nome} ${cond ? '' : extra}`; resultados.push(l); console.log(l); };

async function entrar(page) {
  await page.goto(APP, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  if (/Já tenho conta/.test(await page.locator('body').innerText())) {
    await page.getByRole('button', { name: 'Já tenho conta' }).first().click();
    await page.waitForTimeout(1200);
  }
  await page.getByRole('textbox').filter({ visible: true }).first().fill('carolina@salaoexemplo.com.br');
  await page.locator('input[type="password"]:visible').first().fill('espelho-demo-2026');
  await page.getByRole('button', { name: 'Entrar' }).filter({ visible: true }).first().click();
  await page.waitForTimeout(4000);
}

// 1. Calendário: o sábado na coluna do "sáb", em várias larguras.
for (const largura of [320, 360, 412, 768, 1280]) {
  const ctx = await b.newContext({ viewport: { width: largura, height: 900 }, locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
  const page = await ctx.newPage();
  await entrar(page);
  await page.goto(`${APP}/agenda?dia=2026-11-06`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  const medida = await page.evaluate(() => {
    const centro = (el) => { const r = el.getBoundingClientRect(); return r.left + r.width / 2; };
    const textos = [...document.querySelectorAll('div')].filter((d) => d.children.length === 0);
    const sab = textos.find((d) => d.textContent === 'sáb');
    const dom = textos.find((d) => d.textContent === 'dom');
    const dias = Object.fromEntries(
      [...document.querySelectorAll('[aria-label^="Dia "]')].map((d) => [d.getAttribute('aria-label').replace(/\D+/g, ''), d])
    );
    const caixa = document.querySelector('[aria-label^="Dia 1"]')?.parentElement?.parentElement?.getBoundingClientRect();
    return {
      sab: sab && centro(sab), dom: dom && centro(dom),
      d7: dias['7'] && centro(dias['7']), d28: dias['28'] && centro(dias['28']), d1: dias['1'] && centro(dias['1']),
      larguraPagina: document.documentElement.scrollWidth,
    };
  });
  const alinhado = Math.abs(medida.d7 - medida.sab) < 3 && Math.abs(medida.d28 - medida.sab) < 3 && Math.abs(medida.d1 - medida.dom) < 3;
  ok(`calendário ${largura}px: sábados (7, 28) sob "sáb" e dia 1 sob "dom"`, alinhado, JSON.stringify(medida));
  ok(`calendário ${largura}px: sem rolagem lateral`, medida.larguraPagina <= largura, `scrollWidth=${medida.larguraPagina}`);
  if (largura === 320 || largura === 412) await page.screenshot({ path: `${SAIDA}/agenda-${largura}.png` });
  await ctx.close();
}

// 2. Campo de data na web: apagar um número não quebra a data.
const ctx = await b.newContext({ viewport: { width: 600, height: 950 }, locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
const page = await ctx.newPage();
await entrar(page);
const login = await fetch(`${API}/api/v1/auth/login`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'carolina@salaoexemplo.com.br', senha: 'espelho-demo-2026' }),
}).then((r) => r.json());
const token = login.accessToken ?? login.access_token ?? login.tokens?.accessToken;
const clientes = await fetch(`${API}/api/v1/clientes`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json());
const idCliente = (Array.isArray(clientes) ? clientes : clientes.itens ?? clientes.clientes)[0].id;
await page.goto(`${APP}/atendimento/novo?clienteId=${idCliente}`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2500);
const data = page.locator('input[type="date"]').first();
ok('atendimento: campo de data do navegador', (await data.count()) === 1);
ok('atendimento: campo de horário do navegador', (await page.locator('input[type="time"]').count()) === 1);
await data.fill('2026-12-01');
await page.waitForTimeout(300);
ok('data completa aceita', (await data.inputValue()) === '2026-12-01' && !/Data incompleta/.test(await page.locator('body').innerText()));
// Apaga um segmento (neste Chromium o clique cai no ano).
await data.click({ position: { x: 8, y: 10 } });
await page.keyboard.press('Backspace');
await page.waitForTimeout(300);
const corpo = await page.locator('body').innerText();
ok('apagar um número: avisa que está incompleta', /Data incompleta: preencha dia, mês e ano/.test(corpo));
const segmentos = await data.evaluate((el) => ({ valor: el.value, incompleta: el.validity.badInput }));
ok('apagar um número: o resto da data continua lá', segmentos.valor === '' && segmentos.incompleta, JSON.stringify(segmentos));
await page.screenshot({ path: `${SAIDA}/data-incompleta.png` });
for (const tecla of '2027') { await page.keyboard.press(tecla); await page.waitForTimeout(150); }
await page.waitForTimeout(300);
ok('redigitar o ano dígito a dígito completa a data', (await data.inputValue()) === '2027-12-01' && !/Data incompleta/.test(await page.locator('body').innerText()), await data.inputValue());
await page.screenshot({ path: `${SAIDA}/data-corrigida.png` });

// 3. Data de nascimento (opcional) no cadastro de cliente.
await page.goto(`${APP}/cliente/editar`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2500);
const nasc = page.locator('input[type="date"]').first();
ok('cadastro: nascimento com campo de data do navegador', (await nasc.count()) === 1);
await nasc.fill('1990-05-20');
await nasc.click({ position: { x: 8, y: 10 } });
await page.keyboard.press('Backspace');
await page.waitForTimeout(300);
ok('cadastro: nascimento pela metade avisa', /Data incompleta: preencha dia, mês e ano/.test(await page.locator('body').innerText()));

console.log(resultados.join('\n'));
await b.close();

const falhas = resultados.filter((l) => l.startsWith('FALHA')).length;
console.log(`
${resultados.length - falhas} verificações ok, ${falhas} falhas`);
process.exitCode = falhas ? 1 : 0;
