/**
 * Regressões da auditoria de QA (docs/historico/RELATORIO_QA_E_MELHORIAS.md), no navegador.
 *
 *  1  sem sessão, um endereço interno (/agenda, /cliente/x) leva à abertura, não à tela vazia;
 *  2  conta nova: o botão "Cadastrar primeiro cliente" aparece inteiro e não fica coberto;
 *  3  cliente com data de nascimento: salva (antes falhava sempre com "Confira os dados
 *     enviados", mostrado embaixo do nome), e a data gravada é a digitada;
 *  4  cliente menor de idade: o perfil acusa "menor de idade";
 *  5  nascimento no futuro: recusado no campo certo, antes de enviar;
 *  6  falha de rede ao renovar a sessão: o profissional continua conectado;
 *  7  sessão encerrada pelo servidor no meio do uso (conta excluída em outro aparelho):
 *     o aplicativo volta para a abertura em vez de seguir mostrando telas vazias;
 *  8  histórico: um atendimento registrado com dados errados pode ser corrigido, e o
 *     avulso registrado por engano pode ser excluído (antes, nenhuma das duas coisas);
 *  9  busca de clientes sem acento: "julia" acha "Júlia";
 * 10  painel: "agendados" conta horários, não clientes (a mesma cliente com dois horários
 *     contava um);
 * 11  imagem que não carrega (arquivo ausente no servidor) mostra "Imagem indisponível"
 *     em vez de um quadro vazio.
 *
 * Pré-requisitos: API e `expo start --web` no ar. Cria contas próprias; não depende da
 * carga de demonstração.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';
const TELAS = path.join(AQUI, 'telas-auditoria');
fs.mkdirSync(TELAS, { recursive: true });
const SENHA = 'senha-auditoria-2026';

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

async function criarConta(nome) {
  const email = `auditoria.${Date.now()}.${Math.random().toString(36).slice(2, 7)}@exemplo.com.br`;
  const resposta = await fetch(`${API}/auth/registrar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nome, email, senha: SENHA }),
  });
  const sessao = await resposta.json();
  const cabecalhos = { Authorization: `Bearer ${sessao.tokens.accessToken}`, 'Content-Type': 'application/json' };
  await fetch(`${API}/usuarios/me/ciencia`, { method: 'POST', headers: cabecalhos });
  return { sessao, cabecalhos };
}

/** Entra como o aplicativo guarda a sessão na web (AsyncStorage sobre localStorage). */
async function entrarComTokens(page, tokens) {
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await page.evaluate(
    ([acesso, renovacao]) => {
      localStorage.setItem('espelho.token.acesso', acesso);
      localStorage.setItem('espelho.token.renovacao', renovacao);
    },
    [tokens.accessToken, tokens.refreshToken]
  );
  await page.goto(`${APP}/`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
}

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

// 1. Sem sessão ---------------------------------------------------------------
for (const rota of ['/agenda', '/cliente/00000000-0000-0000-0000-000000000000', '/meus-dados']) {
  await page.goto(`${APP}${rota}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  conferir(page.url().endsWith('/onboarding'), `1. sem sessão, ${rota} leva à abertura`, page.url());
}

// 2. Conta nova: estado vazio do Início ----------------------------------------
const { sessao } = await criarConta('Auditoria Vazia');
await entrarComTokens(page, sessao.tokens);
const cadastrarPrimeiro = botao('Cadastrar primeiro cliente');
await cadastrarPrimeiro.waitFor({ timeout: 10000 });
const caixaBotao = await cadastrarPrimeiro.boundingBox();
const coberto = await page.evaluate(({ x, y }) => {
  const alvo = document.elementFromPoint(x, y);
  return alvo ? !alvo.closest('[role="button"]')?.textContent?.includes('Cadastrar primeiro cliente') : true;
}, { x: caixaBotao.x + caixaBotao.width / 2, y: caixaBotao.y + caixaBotao.height / 2 });
conferir(!coberto, '2. "Cadastrar primeiro cliente" não fica coberto pelo aviso');
const tituloVazio = await page.getByText('Sua carteira começa aqui').boundingBox();
const aviso = await page.getByText(/funcionam mesmo quando o serviço/).boundingBox();
conferir(
  tituloVazio && aviso && caixaBotao.y + caixaBotao.height <= aviso.y,
  '2. o aviso vem depois do botão, sem sobrepor',
  JSON.stringify({ botao: caixaBotao, aviso })
);
await page.screenshot({ path: `${TELAS}/01-inicio-conta-nova.png` });

// 3. Cliente com data de nascimento --------------------------------------------
try {
  await cadastrarPrimeiro.click({ timeout: 5000 });
} catch {
  // Coberto pelo aviso (o defeito do item 2): segue pelo endereço, para testar o resto.
  await page.goto(`${APP}/cliente/editar`, { waitUntil: 'networkidle' });
}
await page.waitForTimeout(1500);
await caixa(0).fill('Helena Duarte');
await caixa(1).fill('(55) 99777-3344');
await caixa(2).fill('12/03/1990');
await botao('Salvar cliente').click();
await page.waitForTimeout(2500);
const listaApi = await (await fetch(`${API}/clientes`, { headers: { Authorization: `Bearer ${sessao.tokens.accessToken}` } })).json();
const helena = listaApi.find((c) => c.nome === 'Helena Duarte');
conferir(Boolean(helena), '3. cliente com data de nascimento é salvo', JSON.stringify(listaApi).slice(0, 200));
conferir(helena?.dataNascimento === '1990-03-12', '3. a data gravada é a digitada (12/03/1990)', helena?.dataNascimento);
await page.screenshot({ path: `${TELAS}/02-cliente-salvo.png` });

// 4. Menor de idade ------------------------------------------------------------
const hoje = new Date();
const nascimentoMenor = `15/06/${hoje.getFullYear() - 10}`;
await page.goto(`${APP}/cliente/editar`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
await caixa(0).fill('Lia Duarte');
await caixa(1).fill('(55) 99777-5566');
await caixa(2).fill(nascimentoMenor);
await botao('Salvar cliente').click();
await page.waitForTimeout(2500);
const corpoMenor = await page.locator('body').innerText();
conferir(/menor de idade/i.test(corpoMenor), '4. o perfil da cliente de 10 anos acusa "menor de idade"', corpoMenor.slice(0, 200));

// 5. Nascimento no futuro ----------------------------------------------------------
await page.goto(`${APP}/cliente/editar`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
await caixa(0).fill('Futuro Teste');
await caixa(1).fill('(55) 99777-7788');
await caixa(2).fill(`01/01/${hoje.getFullYear() + 1}`);
await botao('Salvar cliente').click();
await page.waitForTimeout(1200);
const corpoFuturo = await page.locator('body').innerText();
conferir(/não pode estar no futuro/i.test(corpoFuturo), '5. nascimento no futuro é apontado no campo da data');
conferir(page.url().includes('/cliente/editar'), '5. o formulário continua aberto para corrigir');
await page.screenshot({ path: `${TELAS}/03-nascimento-futuro.png` });

// 6. Falha de rede na renovação --------------------------------------------------
await page.route('**/auth/renovar', (rota) => rota.abort('internetdisconnected'));
await page.evaluate(() => localStorage.setItem('espelho.token.acesso', 'token-vencido'));
await page.goto(`${APP}/`, { waitUntil: 'networkidle' });
await page.waitForTimeout(3500);
const renovacaoGuardada = await page.evaluate(() => localStorage.getItem('espelho.token.renovacao'));
conferir(Boolean(renovacaoGuardada), '6. sem rede na renovação, a sessão continua guardada');
conferir(!page.url().endsWith('/onboarding'), '6. e o aplicativo não manda para a abertura', page.url());
await page.screenshot({ path: `${TELAS}/04-renovacao-sem-rede.png` });
await page.unroute('**/auth/renovar');
await page.getByRole('button', { name: 'Tentar de novo' }).filter({ visible: true }).first().click().catch(() => {});
await page.waitForTimeout(3000);
const acessoNovo = await page.evaluate(() => localStorage.getItem('espelho.token.acesso'));
conferir(
  acessoNovo && acessoNovo !== 'token-vencido' && !/Sem conexão/.test(await page.locator('body').innerText()),
  '6. com a rede de volta, "Tentar de novo" renova a sessão e abre o aplicativo'
);

// 7. Sessão encerrada pelo servidor no meio do uso --------------------------------
const outra = await criarConta('Auditoria Excluida');
await fetch(`${API}/clientes`, {
  method: 'POST',
  headers: outra.cabecalhos,
  body: JSON.stringify({ nome: 'Otávio Prates', telefone: '(55) 99111-2233' }),
});
await entrarComTokens(page, outra.sessao.tokens);
await page.getByRole('tab', { name: 'Clientes' }).click();
await page.waitForTimeout(1500);
conferir(/Otávio Prates/.test(await page.locator('body').innerText()), '7. a segunda conta entra e vê a carteira');
// A conta é excluída em outro aparelho; este continua aberto, com o token na memória.
await fetch(`${API}/usuarios/me`, {
  method: 'DELETE',
  headers: outra.cabecalhos,
  body: JSON.stringify({ senha: SENHA }),
});
// Próxima ação que vai ao servidor: abrir o perfil do cliente (carrega as decisões).
await page.getByText('Otávio Prates').filter({ visible: true }).first().click();
await page.waitForTimeout(3500);
conferir(page.url().endsWith('/onboarding'), '7. sessão recusada no meio do uso: volta para a abertura', page.url());
await page.screenshot({ path: `${TELAS}/05-sessao-encerrada.png` });
const tokensDepois = await page.evaluate(() => localStorage.getItem('espelho.token.renovacao'));
conferir(!tokensDepois, '7. e não sobra token guardado no aparelho');
await page.goto(`${APP}/agenda`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
conferir(page.url().endsWith('/onboarding'), '7. recarregar numa tela interna também leva à abertura', page.url());

// 8. Corrigir e excluir atendimento -------------------------------------------------
const cab1 = { Authorization: `Bearer ${sessao.tokens.accessToken}`, 'Content-Type': 'application/json' };
const ontem = new Date(Date.now() - 26 * 3600 * 1000).toISOString();
const avulso = await (
  await fetch(`${API}/atendimentos`, {
    method: 'POST',
    headers: cab1,
    body: JSON.stringify({ clienteId: helena.id, descricao: 'Corte', realizadoEm: ontem, observacoes: '' }),
  })
).json();
await entrarComTokens(page, sessao.tokens);
await page.goto(`${APP}/cliente/${helena.id}`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
await page.getByRole('button', { name: /^Corrigir o atendimento Corte/ }).filter({ visible: true }).first().click();
await page.waitForTimeout(1500);
conferir(page.url().includes(`/atendimento/editar/${avulso.id}`), '8. "Corrigir" abre a correção do atendimento', page.url());
await page.getByPlaceholder(/O que foi feito/).fill('Corrigido na auditoria');
await botao('Salvar correção').click();
await page.waitForTimeout(2000);
const corrigido = await (await fetch(`${API}/atendimentos/${avulso.id}`, { headers: cab1 })).json();
conferir(corrigido.observacoes === 'Corrigido na auditoria', '8. a correção é gravada no servidor', corrigido.observacoes);
conferir(corrigido.realizadoEm?.slice(0, 16) === ontem.slice(0, 16), '8. o horário que ninguém mexeu continua o mesmo', corrigido.realizadoEm);
conferir(/Corrigido na auditoria/.test(await page.locator('body').innerText()), '8. o histórico mostra a correção');
await page.screenshot({ path: `${TELAS}/06-historico-corrigido.png` });
await page.getByRole('button', { name: /^Corrigir o atendimento Corte/ }).filter({ visible: true }).first().click();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${TELAS}/07-correcao-avulso.png` });
await botao('Excluir atendimento').click();
await page.waitForTimeout(800);
await page.screenshot({ path: `${TELAS}/08-confirmar-exclusao.png` });
// O botão da página e o do diálogo têm o mesmo nome: o do diálogo é o que fica acima.
const candidatos = page.getByRole('button', { name: 'Excluir atendimento' }).filter({ visible: true });
const posicoes = await Promise.all(
  Array.from({ length: await candidatos.count() }, async (_, i) => (await candidatos.nth(i).boundingBox()).y)
);
await candidatos.nth(posicoes.indexOf(Math.min(...posicoes))).click();
await page.waitForTimeout(2000);
const situacao = (await fetch(`${API}/atendimentos/${avulso.id}`, { headers: cab1 })).status;
conferir(situacao === 404, '8. o avulso excluído sai do servidor', situacao);
conferir(page.url().endsWith(`/cliente/${helena.id}`), '8. e a tela volta para o perfil', page.url());
conferir(!/Corrigido na auditoria/.test(await page.locator('body').innerText()), '8. e some do histórico na tela');

// 9. Busca sem acento ---------------------------------------------------------------
await fetch(`${API}/clientes`, {
  method: 'POST',
  headers: cab1,
  body: JSON.stringify({ nome: 'Júlia Teixeira', telefone: '(55) 99000-1122' }),
});
await page.goto(`${APP}/`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2500);
await page.getByRole('tab', { name: 'Clientes' }).click();
await page.waitForTimeout(1200);
await page.getByPlaceholder('Buscar por nome ou telefone').fill('julia');
await page.waitForTimeout(800);
const corpoBusca = await page.locator('body').innerText();
conferir(/Júlia Teixeira/.test(corpoBusca), '9. buscar "julia" acha "Júlia Teixeira"');
conferir(!/Helena Duarte/.test(corpoBusca), '9. e só ela');
await page.screenshot({ path: `${TELAS}/09-busca-sem-acento.png` });

// 10. Painel: horários, não clientes ------------------------------------------------
const clientesDoPainel = await (await fetch(`${API}/clientes`, { headers: cab1 })).json();
const julia = clientesDoPainel.find((c) => c.nome === 'Júlia Teixeira');
const daquiDias = (dias, hora) => {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  d.setHours(hora, 0, 0, 0);
  return d.toISOString();
};
for (const [cliente, dias, hora] of [[julia, 2, 10], [julia, 4, 15], [helena, 3, 11]]) {
  const agendamento = await (
    await fetch(`${API}/agendamentos`, {
      method: 'POST',
      headers: cab1,
      body: JSON.stringify({ clienteId: cliente.id, dataHora: daquiDias(dias, hora), servico: 'Corte' }),
    })
  ).json();
  await fetch(`${API}/agendamentos/${agendamento.id}/confirmar`, { method: 'POST', headers: cab1 });
}
await page.goto(`${APP}/`, { waitUntil: 'networkidle' });
await page.waitForTimeout(3000);
const rotulosPainel = await page.evaluate(() =>
  [...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label'))
);
const agendadosPainel = rotulosPainel.find((r) => /horários? marcados?, de hoje em diante/.test(r ?? ''));
conferir(
  agendadosPainel?.startsWith('3 '),
  '10. três horários confirmados, dois da mesma cliente: o painel mostra 3',
  agendadosPainel
);
await page.screenshot({ path: `${TELAS}/10-painel-horarios.png` });

// 11. Imagem que não carrega ----------------------------------------------------------
await fetch(`${API}/clientes/${julia.id}/consentimentos`, {
  method: 'POST',
  headers: cab1,
  body: JSON.stringify({ decisao: 'aceito', formaObtencao: 'tela_dispositivo', confirmadoPor: 'Júlia Teixeira', observacao: '' }),
});
const formulario = new FormData();
formulario.append('clienteId', julia.id);
formulario.append('corte', 'Bob curto');
formulario.append('cor', 'Ruivo intenso');
formulario.append('foto', new Blob([fs.readFileSync(path.join(AQUI, 'retrato-sintetico.jpg'))], { type: 'image/jpeg' }), 'foto.jpg');
const simulacao = await (
  await fetch(`${API}/simulacoes`, { method: 'POST', headers: { Authorization: cab1.Authorization }, body: formulario })
).json();
for (let i = 0; i < 30; i += 1) {
  const estado = await (await fetch(`${API}/simulacoes/${simulacao.id}`, { headers: cab1 })).json();
  if (estado.status !== 'processando') break;
  await page.waitForTimeout(500);
}
// O servidor responde 404, como quando o arquivo some do storage.
await page.route('**/api/v1/imagens/**', (rota) => rota.fulfill({ status: 404, body: '' }));
await page.goto(`${APP}/cliente/${julia.id}`, { waitUntil: 'networkidle' });
await page.waitForTimeout(3000);
conferir(
  /Imagem indisponível/.test(await page.locator('body').innerText()),
  '11. imagem ausente no servidor aparece como "Imagem indisponível"'
);
await page.screenshot({ path: `${TELAS}/11-imagem-indisponivel.png` });
await page.unroute('**/api/v1/imagens/**');

conferir(consoleErros.length === 0, 'nenhum erro de página durante a bateria', consoleErros.join(' | '));
await navegador.close();

console.log(`\n${aprovados} verificações ok, ${erros.length} falhas`);
process.exit(erros.length ? 1 : 0);
