/**
 * Percorre todas as telas do aplicativo, guarda uma foto de cada uma em dois tamanhos
 * (celular e tablet) e mede o contraste de cada texto visível contra o fundo real sobre o
 * qual ele está desenhado.
 *
 * O fundo é calculado subindo pela árvore até o primeiro elemento com cor de fundo
 * (compondo as transparências). Critério WCAG 2.1 AA: 4,5:1 para texto comum, 3:1 para
 * texto grande (24px, ou 18,66px em negrito). Imagens de fundo não entram no cálculo.
 *
 * Pré-requisitos: API e `expo start --web` no ar, carga de demonstração recriada.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';
const TELAS = path.join(AQUI, 'telas-visual');
fs.mkdirSync(TELAS, { recursive: true });

const EMAIL = 'carolina@salaoexemplo.com.br';
const SENHA = 'espelho-demo-2026';

// --- identificadores reais da carga de demonstração ---------------------------
const sessao = await (
  await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, senha: SENHA }),
  })
).json();
const cab = { Authorization: `Bearer ${sessao.tokens.accessToken}` };
const obter = async (rota) => (await fetch(`${API}${rota}`, { headers: cab })).json();
const clientes = await obter('/clientes');
const marina = clientes.find((c) => c.nome.startsWith('Marina'));
const agendamentos = await obter('/agendamentos');
const aberto = agendamentos.find((a) => a.status === 'pendente' || a.status === 'confirmado');
const simulacoes = await obter(`/clientes/${marina.id}/simulacoes`);

const PUBLICAS = [
  ['inicio-publico', '/onboarding'],
  ['login', '/login'],
  ['cadastro', '/cadastro'],
];
const PRIVADAS = [
  ['aba-inicio', '/'],
  ['aba-clientes', '/clientes'],
  ['aba-agenda', '/agenda'],
  ['aba-perfil', '/perfil'],
  ['cliente-perfil', `/cliente/${marina.id}`],
  ['cliente-editar', `/cliente/editar?id=${marina.id}`],
  ['cliente-novo', '/cliente/editar'],
  ['agendamento-novo', '/agendamento/novo'],
  ['agendamento-editar', `/agendamento/editar/${aberto.id}`],
  ['agendamento-concluir', `/agendamento/concluir/${aberto.id}`],
  ['atendimento-novo', `/atendimento/novo?clienteId=${marina.id}`],
  ['simulacao-cliente', '/simulacao/cliente'],
  ['simulacao-imagem', `/simulacao/imagem/${simulacoes[0].id}`],
  ['simulacao-comparar', `/simulacao/comparar?clienteId=${marina.id}`],
  ['termo', `/termo/${marina.id}`],
  ['consentimento', `/consentimento/${marina.id}`],
  ['privacidade', '/privacidade'],
  ['responsabilidades', '/responsabilidades'],
  ['meus-dados', '/meus-dados'],
  ['seguranca', '/seguranca'],
  ['excluir-conta', '/excluir-conta'],
];

const medirContraste = () => {
  const rgba = (texto) => {
    const m = texto.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const [r, g, b, a = '1'] = m[1].split(',').map((x) => x.trim());
    return [Number(r), Number(g), Number(b), Number(a)];
  };
  const compor = (frente, atras) => {
    const a = frente[3];
    return [0, 1, 2].map((i) => frente[i] * a + atras[i] * (1 - a)).concat(1);
  };
  const fundoDe = (el) => {
    const camadas = [];
    for (let no = el; no && no.nodeType === 1; no = no.parentElement) {
      const cor = rgba(getComputedStyle(no).backgroundColor);
      if (cor && cor[3] > 0) {
        camadas.push(cor);
        if (cor[3] >= 1) break;
      }
    }
    let resultado = [255, 255, 255, 1];
    for (const camada of camadas.reverse()) resultado = compor(camada, resultado);
    return resultado;
  };
  const luminancia = ([r, g, b]) => {
    const canal = (v) => {
      const c = v / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b);
  };
  const razao = (a, b) => {
    const [l1, l2] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
    return (l1 + 0.05) / (l2 + 0.05);
  };

  const problemas = [];
  const vistos = new Set();
  for (const el of document.querySelectorAll('body *')) {
    const proprio = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!proprio) continue;
    const caixa = el.getBoundingClientRect();
    if (caixa.width === 0 || caixa.height === 0 || caixa.bottom < 0 || caixa.top > innerHeight) continue;
    const estilo = getComputedStyle(el);
    if (estilo.visibility === 'hidden' || Number(estilo.opacity) === 0) continue;
    // Elementos dentro de imagens/fotos ou de camadas semitransparentes de decoração
    // ficam de fora: o fundo deles não é uma cor sólida.
    let opacidade = 1;
    for (let no = el; no && no.nodeType === 1; no = no.parentElement) opacidade *= Number(getComputedStyle(no).opacity);
    const cor = rgba(estilo.color);
    if (!cor) continue;
    const fundo = fundoDe(el);
    const frente = compor([cor[0], cor[1], cor[2], cor[3] * opacidade], fundo);
    const valor = razao(frente, fundo);
    const tamanho = parseFloat(estilo.fontSize);
    const negrito = Number(estilo.fontWeight) >= 700 || /Bold|SemiBold/.test(estilo.fontFamily);
    const grande = tamanho >= 24 || (tamanho >= 18.66 && negrito);
    // Ícones (fonte de ícones) são elementos gráficos: o mínimo é 3:1 (WCAG 1.4.11).
    const icone = /feather|ionicons|material/i.test(estilo.fontFamily);
    const minimo = grande || icone ? 3 : 4.5;
    const texto = icone ? `(ícone) ${el.closest('[aria-label]')?.getAttribute('aria-label') ?? ''}`.slice(0, 50) : el.textContent.trim().slice(0, 40);
    // Componentes desabilitados ficam fora do critério (WCAG 1.4.3, exceção).
    if (el.closest('[aria-disabled="true"]')) continue;
    if (valor < minimo && !vistos.has(texto)) {
      vistos.add(texto);
      problemas.push({ texto, razao: Math.round(valor * 100) / 100, minimo, cor: estilo.color, fundo: `rgb(${fundo.slice(0, 3).map(Math.round).join(',')})` });
    }
  }
  return problemas;
};

const navegador = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const resumo = [];
let totalProblemas = 0;
let largas = 0;

for (const [largura, altura, sufixo] of [
  [390, 844, 'celular'],
  [820, 1180, 'tablet'],
]) {
  const contexto = await navegador.newContext({ viewport: { width: largura, height: altura }, locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
  const page = await contexto.newPage();

  const visitar = async (nome, rota) => {
    await page.goto(`${APP}${rota}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2200);
    await page.screenshot({ path: `${TELAS}/${sufixo}-${nome}.png` });
    const problemas = await page.evaluate(medirContraste);
    const rolagem = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    if (rolagem) largas += 1;
    totalProblemas += problemas.length;
    const linha = `${sufixo.padEnd(8)} ${nome.padEnd(22)} ${problemas.length ? `${problemas.length} texto(s) abaixo do mínimo` : 'contraste ok'}${rolagem ? ' · ROLAGEM HORIZONTAL' : ''}`;
    resumo.push(linha);
    console.log(linha);
    for (const p of problemas) console.log(`           "${p.texto}" ${p.razao}:1 (mín. ${p.minimo}) ${p.cor} sobre ${p.fundo}`);
  };

  for (const [nome, rota] of PUBLICAS) await visitar(nome, rota);

  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.getByRole('textbox').filter({ visible: true }).first().fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await page.getByRole('button', { name: /^Entrar$/ }).filter({ visible: true }).first().click();
  await page.waitForTimeout(4000);

  for (const [nome, rota] of PRIVADAS) await visitar(nome, rota);
  await contexto.close();
}
await navegador.close();

console.log(`\n${totalProblemas} texto(s) abaixo do contraste mínimo; ${largas} tela(s) com rolagem horizontal`);
fs.writeFileSync(path.join(TELAS, 'resultado.txt'), resumo.join('\n') + '\n');
process.exit(totalProblemas || largas ? 1 : 0);
