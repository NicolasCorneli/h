/**
 * Senha e sessões (revisão de prontidão para produção), no navegador.
 *
 *  1  o Perfil leva à tela "Senha e sessões";
 *  2  a tela confere os campos antes de enviar (nova senha curta, confirmação diferente);
 *  3  senha atual errada: o erro aparece no campo "Senha atual" e nada muda;
 *  4  trocar a senha mantém este aparelho conectado e desconecta o outro (o token de
 *     renovação dele passa a ser recusado pelo servidor);
 *  5  a senha nova entra e a antiga não;
 *  6  "Sair de todos os aparelhos" pede confirmação, encerra esta sessão e volta para a
 *     abertura (como qualquer fim de sessão; ver a guarda de rotas em app/_layout.tsx).
 *
 * Pré-requisitos: API e `expo start --web` no ar (ou o build estático, com APP_URL). Cria a
 * própria conta; não depende da carga de demonstração.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';
const TELAS = path.join(AQUI, 'telas-seguranca');
fs.mkdirSync(TELAS, { recursive: true });
const SENHA = 'senha-seguranca-2026';
const NOVA = 'senha-nova-seguranca-2026';

const erros = [];
let aprovados = 0;
const conferir = (condicao, descricao, detalhe = '') => {
  if (condicao) {
    aprovados += 1;
    console.log(`[ok ] ${descricao}`);
  } else {
    erros.push(descricao);
    console.log(`[FALHA] ${descricao}${detalhe ? `: ${String(detalhe).slice(0, 300)}` : ''}`);
  }
};

async function entrarPelaApi(email, senha) {
  const resposta = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, senha }),
  });
  return { status: resposta.status, corpo: resposta.ok ? await resposta.json() : null };
}

const email = `seguranca.${Date.now()}.${Math.random().toString(36).slice(2, 7)}@exemplo.com.br`;
const registro = await fetch(`${API}/auth/registrar`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ nome: 'Profissional Segurança', email, senha: SENHA }),
});
const sessao = await registro.json();
await fetch(`${API}/usuarios/me/ciencia`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${sessao.tokens.accessToken}` },
});
// Um "outro aparelho": uma segunda sessão da mesma conta.
const outroAparelho = (await entrarPelaApi(email, SENHA)).corpo.tokens;

const navegador = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const contexto = await navegador.newContext({
  viewport: { width: 390, height: 844 },
  locale: 'pt-BR',
  timezoneId: 'America/Sao_Paulo',
});
const page = await contexto.newPage();
const consoleErros = [];
page.on('pageerror', (e) => consoleErros.push(`pageerror: ${String(e).slice(0, 300)}`));
const botao = (nome) => page.getByRole('button', { name: nome }).filter({ visible: true }).first();
const caixa = (i) => page.getByRole('textbox').filter({ visible: true }).nth(i);

await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
await page.evaluate(
  ([acesso, renovacao]) => {
    localStorage.setItem('espelho.token.acesso', acesso);
    localStorage.setItem('espelho.token.renovacao', renovacao);
  },
  [sessao.tokens.accessToken, sessao.tokens.refreshToken]
);

// 1. Perfil → Senha e sessões --------------------------------------------------------
await page.goto(`${APP}/perfil`, { waitUntil: 'networkidle' });
await botao('Senha e sessões').click({ timeout: 15000 });
await page.getByText('Trocar senha').first().waitFor({ timeout: 10000 });
conferir(page.url().endsWith('/seguranca'), '1. o Perfil abre "Senha e sessões"', page.url());
await page.screenshot({ path: `${TELAS}/01-senha-e-sessoes.png` });

// 2. Validação local ----------------------------------------------------------------
await caixa(0).fill(SENHA);
await caixa(1).fill('curta');
await caixa(2).fill('outra');
await botao('Trocar senha').click();
conferir(
  await page.getByText(/ao menos 8 caracteres/).isVisible(),
  '2. nova senha curta é recusada antes de enviar'
);
await caixa(1).fill(NOVA);
await botao('Trocar senha').click();
conferir(
  await page.getByText('As duas senhas não são iguais.').isVisible(),
  '2. confirmação diferente é recusada antes de enviar'
);

// 3. Senha atual errada ---------------------------------------------------------------
await caixa(0).fill('senha-que-nao-e-a-atual');
await caixa(2).fill(NOVA);
await botao('Trocar senha').click();
await page.getByText('Senha atual incorreta.').waitFor({ timeout: 10000 }).catch(() => undefined);
conferir(
  await page.getByText('Senha atual incorreta.').isVisible(),
  '3. senha atual errada aparece no campo certo'
);
conferir((await entrarPelaApi(email, SENHA)).status === 200, '3. a senha não mudou');

// 4. Troca de verdade ------------------------------------------------------------------
await caixa(0).fill(SENHA);
await botao('Trocar senha').click();
await page.getByText(/Senha trocada/).waitFor({ timeout: 10000 }).catch(() => undefined);
await page.waitForTimeout(1500);
conferir(page.url().endsWith('/perfil'), '4. depois de trocar, volta ao Perfil conectado', page.url());
const renovacaoDoOutro = await fetch(`${API}/auth/renovar`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refreshToken: outroAparelho.refreshToken }),
});
conferir(renovacaoDoOutro.status === 401, '4. o outro aparelho foi desconectado', renovacaoDoOutro.status);
await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
conferir(page.url().endsWith('/perfil'), '4. este aparelho continua conectado depois de recarregar', page.url());

// 5. Senha nova entra; antiga não --------------------------------------------------------
conferir((await entrarPelaApi(email, NOVA)).status === 200, '5. a senha nova entra');
conferir((await entrarPelaApi(email, SENHA)).status === 401, '5. a senha antiga não entra');

// 6. Sair de todos os aparelhos ---------------------------------------------------------
await page.goto(`${APP}/seguranca`, { waitUntil: 'networkidle' });
await botao('Sair de todos os aparelhos').click({ timeout: 10000 });
// Nome exato: o botão de fundo, coberto pelo diálogo, também começa com "Sair de todos".
await page.getByRole('button', { name: 'Sair de todos', exact: true }).click({ timeout: 5000 });
await page.waitForURL(/\/onboarding$/, { timeout: 10000 }).catch(() => undefined);
conferir(page.url().endsWith('/onboarding'), '6. "Sair de todos" volta para a abertura', page.url());
await page.screenshot({ path: `${TELAS}/02-depois-de-sair-de-todos.png` });
const tokenGuardado = await page.evaluate(() => localStorage.getItem('espelho.token.acesso'));
conferir(tokenGuardado === null, '6. os tokens saíram do aparelho');

conferir(consoleErros.length === 0, 'console sem erros de página', consoleErros.join(' | '));
await navegador.close();

console.log(`\n${aprovados} verificações ok, ${erros.length} falhas`);
process.exit(erros.length ? 1 : 0);
