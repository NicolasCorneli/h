/**
 * Verifica, no navegador, a ligação do "Entrar com Google" sem usar conta real.
 *
 * Pré-requisitos: API com `GOOGLE_CLIENT_IDS=teste-web.apps.googleusercontent.com` e
 * `expo start --web` com `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` igual.
 *
 * O que se confere:
 * - o botão aparece no login, no cadastro e no Perfil;
 * - o pedido aberto na janela do Google leva o ID de cliente, pede um ID token, manda um
 *   `nonce` e volta para o endereço do aplicativo;
 * - um token que não foi assinado pelo Google é recusado pelo servidor, e a tela mostra
 *   a mensagem, sem entrar.
 *
 * A janela do Google é interceptada: nenhum acesso ao Google acontece. O login com uma
 * conta Google de verdade depende das credenciais do Google Cloud do autor (ver
 * docs/GUIA_LOGIN_GOOGLE.md) e não é simulado aqui.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const ID_CLIENTE = process.env.GOOGLE_WEB_CLIENT_ID ?? 'teste-web.apps.googleusercontent.com';
const TELAS = path.join(AQUI, 'telas-google');
fs.mkdirSync(TELAS, { recursive: true });

const passos = [];
const erros = [];
const ok = (d) => {
  passos.push(`[ok ] ${d}`);
  console.log(passos.at(-1));
};
const falha = (d, detalhe) => {
  passos.push(`[FALHA] ${d}: ${detalhe}`);
  erros.push(d);
  console.log(passos.at(-1));
};
const conferir = (c, d, detalhe) => (c ? ok(d) : falha(d, detalhe));

const navegador = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const contexto = await navegador.newContext({ viewport: { width: 420, height: 900 }, locale: 'pt-BR' });
const page = await contexto.newPage();
const corpo = () => page.locator('body').innerText();
const espera = (ms = 1200) => page.waitForTimeout(ms);
const botao = (nome) => page.getByRole('button', { name: nome }).filter({ visible: true }).first();

// Qualquer janela que tente ir ao Google é respondida aqui, devolvendo ao aplicativo um
// token forjado, como faria um atacante. O servidor precisa recusá-lo.
let pedidoGoogle = null;
await contexto.route('https://accounts.google.com/**', async (rota) => {
  const url = new URL(rota.request().url());
  pedidoGoogle = url;
  const volta = url.searchParams.get('redirect_uri');
  const estado = url.searchParams.get('state');
  const forjado = [
    Buffer.from(JSON.stringify({ alg: 'RS256', kid: 'x', typ: 'JWT' })).toString('base64url'),
    Buffer.from(
      JSON.stringify({ iss: 'https://accounts.google.com', aud: ID_CLIENTE, sub: '1', email: 'a@gmail.com', email_verified: true, exp: 9999999999, iat: 1 })
    ).toString('base64url'),
    'assinatura-falsa',
  ].join('.');
  await rota.fulfill({
    status: 302,
    headers: { location: `${volta}#id_token=${forjado}&state=${estado}` },
  });
});

try {
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await espera(3000);
  conferir(/Entrar com Google/.test(await corpo()), 'o login mostra "Entrar com Google"', 'botão ausente');
  conferir(!/Recuperar senha/.test(await corpo()), 'o botão "Recuperar senha", que não fazia nada, saiu', 'ainda presente');
  await page.screenshot({ path: `${TELAS}/01-login.png` });

  const [janela] = await Promise.all([page.waitForEvent('popup', { timeout: 15000 }), botao('Entrar com Google').click()]);
  await janela.waitForLoadState().catch(() => undefined);
  await espera(4000);

  if (pedidoGoogle) {
    const p = pedidoGoogle.searchParams;
    conferir(p.get('client_id') === ID_CLIENTE, 'o pedido leva o ID de cliente configurado', p.get('client_id'));
    conferir(p.get('response_type') === 'id_token', 'o pedido é por ID token', p.get('response_type'));
    conferir(!!p.get('nonce'), 'o pedido manda um nonce', 'sem nonce');
    conferir((p.get('scope') ?? '').includes('openid') && (p.get('scope') ?? '').includes('email'), 'escopos openid e e-mail', p.get('scope'));
    conferir(p.get('redirect_uri') === new URL(APP).origin, 'volta para o endereço do aplicativo', p.get('redirect_uri'));
  } else {
    falha('janela do Google', 'nenhum pedido interceptado');
  }

  await espera(3000);
  const depois = await corpo();
  conferir(/Não foi possível confirmar sua conta Google|Não foi possível falar com o Google/.test(depois), 'token forjado é recusado e a tela explica', depois.slice(0, 300));
  conferir(/Entrar/.test(depois) && !/Bom dia|Boa tarde|Boa noite/.test(depois), 'o token forjado não abre sessão', depois.slice(0, 200));
  await page.screenshot({ path: `${TELAS}/02-token-recusado.png` });

  await page.goto(`${APP}/cadastro`, { waitUntil: 'networkidle' });
  await espera(2500);
  conferir(/Criar conta com Google/.test(await corpo()), 'o cadastro mostra "Criar conta com Google"', 'botão ausente');
  await page.screenshot({ path: `${TELAS}/03-cadastro.png` });

  // Perfil de uma conta com senha: oferece conectar.
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await espera(2500);
  await page.getByRole('textbox').filter({ visible: true }).first().fill('carolina@salaoexemplo.com.br');
  await page.locator('input[type="password"]:visible').first().fill('espelho-demo-2026');
  await botao(/^Entrar$/).click();
  await espera(4000);
  await page.goto(`${APP}/perfil`, { waitUntil: 'networkidle' });
  await espera(2500);
  const perfil = await corpo();
  conferir(/Conectar conta Google/.test(perfil), 'o Perfil oferece conectar a conta Google', 'sem opção');
  conferir(!/em breve/i.test(perfil), 'o Perfil não tem mais itens "em breve" sem função', 'ainda há');
  await page.screenshot({ path: `${TELAS}/04-perfil.png`, fullPage: true });
} catch (e) {
  falha('execução', e instanceof Error ? e.message.split('\n')[0] : String(e));
} finally {
  await navegador.close();
}

console.log(`\n${passos.length - erros.length} verificações ok, ${erros.length} falhas`);
fs.writeFileSync(path.join(TELAS, 'resultado.txt'), passos.join('\n') + '\n');
process.exit(erros.length ? 1 : 0);
