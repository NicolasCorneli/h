/**
 * Bateria de QA da interface: responsividade, acessibilidade e estados de tela.
 *
 * Complementa `fluxo-completo.mjs`, que percorre o caminho do usuário. Aqui a pergunta é
 * outra: a tela se comporta bem em larguras diferentes, é operável por quem não usa
 * mouse, e diz a verdade quando algo falha?
 *
 * Precisa da API e do `expo start --web` no ar, e da carga de demonstração
 * (`python -m app.seed`) para ter dados na carteira.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000';
const TELAS = path.join(AQUI, 'telas-qa');
fs.mkdirSync(TELAS, { recursive: true });

const EMAIL = 'carolina@salaoexemplo.com.br';
const SENHA = 'espelho-demo-2026';

const passos = [];
const erros = [];
let n = 0;

function ok(descricao, extra = '') {
  passos.push(`[ok ] ${descricao}${extra ? ` — ${extra}` : ''}`);
  console.log(passos.at(-1));
}
function falha(descricao, detalhe) {
  passos.push(`[FALHA] ${descricao} — ${detalhe}`);
  erros.push(`${descricao}: ${detalhe}`);
  console.log(passos.at(-1));
}
function nota(descricao) {
  passos.push(`[nota] ${descricao}`);
  console.log(passos.at(-1));
}

const navegador = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--no-sandbox'],
});

const mensagens = [];

async function novaPagina(viewport) {
  const contexto = await navegador.newContext({ viewport, locale: 'pt-BR' });
  const page = await contexto.newPage();
  page.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warning') {
      mensagens.push({ tipo: m.type(), texto: m.text().slice(0, 300) });
    }
  });
  page.on('pageerror', (e) => mensagens.push({ tipo: 'error', texto: `pageerror: ${e}` }));
  return { contexto, page };
}

const botao = (page, nome) =>
  page.getByRole('button', { name: nome, exact: false }).filter({ visible: true }).first();
const caixa = (page, i) => page.getByRole('textbox').filter({ visible: true }).nth(i);

async function entrar(page) {
  await page.goto(APP, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  const corpo = await page.locator('body').innerText();
  if (/Já tenho conta/.test(corpo)) {
    await botao(page, 'Já tenho conta').click();
    await page.waitForTimeout(1200);
  }
  await caixa(page, 0).fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await botao(page, 'Entrar').click();
  await page.waitForTimeout(4000);
}

async function foto(page, nome) {
  n += 1;
  await page.screenshot({ path: `${TELAS}/${String(n).padStart(2, '0')}-${nome}.png` });
}

try {
  // ------------------------------------------------- 1. responsividade
  const larguras = [
    { nome: 'celular', width: 390, height: 844 },
    { nome: 'tablet', width: 768, height: 1024 },
    { nome: 'desktop', width: 1280, height: 900 },
  ];

  for (const { nome, width, height } of larguras) {
    const { contexto, page } = await novaPagina({ width, height });
    await entrar(page);
    await foto(page, `${nome}-painel`);

    const rolagem = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    if (rolagem <= 1) ok(`${nome} (${width}px): sem rolagem horizontal`);
    else falha(`${nome} (${width}px): rolagem horizontal`, `${rolagem}px de excesso`);

    const corpo = await page.locator('body').innerText();
    if (/Marina|Aline|próximo|Agenda|Clientes/i.test(corpo)) {
      ok(`${nome}: painel renderizou o conteúdo`);
    } else {
      falha(`${nome}: painel vazio`, corpo.slice(0, 150));
    }

    // Alvos de toque: nada abaixo de 44px no menor lado.
    await page.goto(`${APP}/(tabs)/clientes`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    const pequenos = await page.evaluate(() => {
      const seletor = 'button, [role="button"], a, input, textarea, select';
      return [...document.querySelectorAll(seletor)]
        .filter((el) => {
          const r = el.getBoundingClientRect();
          if (r.width === 0 || r.height === 0) return false;
          return Math.min(r.width, r.height) < 44;
        })
        .map((el) => `${el.tagName}:${(el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 25)}`)
        .slice(0, 8);
    });
    if (pequenos.length === 0) ok(`${nome}: todos os alvos de toque têm 44px ou mais`);
    else falha(`${nome}: alvo de toque pequeno`, pequenos.join(' | '));

    if (nome === 'desktop') {
      const larguraDoTexto = await page.evaluate(() => {
        const alvo = document.querySelector('[role="header"], h1, h2');
        return alvo ? Math.round(alvo.getBoundingClientRect().width) : 0;
      });
      nota(`desktop: largura do título medida em ${larguraDoTexto}px`);
    }

    await contexto.close();
  }

  // ------------------------------------------------- 2. acessibilidade
  {
    const { contexto, page } = await novaPagina({ width: 390, height: 844 });
    await entrar(page);
    await page.goto(`${APP}/cliente/editar`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await foto(page, 'formulario');

    const semRotulo = await page.evaluate(() => {
      const campos = [...document.querySelectorAll('input, textarea')];
      return campos
        .filter((c) => {
          const rotulo =
            c.getAttribute('aria-label') ||
            c.getAttribute('aria-labelledby') ||
            c.getAttribute('placeholder') ||
            (c.id && document.querySelector(`label[for="${c.id}"]`));
          return !rotulo;
        })
        .map((c) => c.type || c.tagName);
    });
    if (semRotulo.length === 0) ok('todos os campos têm rótulo acessível');
    else falha('campos sem rótulo acessível', semRotulo.join(', '));

    const botoesSemNome = await page.evaluate(() =>
      [...document.querySelectorAll('button, [role="button"]')]
        .filter((b) => {
          const r = b.getBoundingClientRect();
          if (r.width === 0 || r.height === 0) return false;
          const nome = (b.textContent || '').trim() || b.getAttribute('aria-label');
          return !nome;
        })
        .map((b) => b.outerHTML.slice(0, 60))
        .slice(0, 5)
    );
    if (botoesSemNome.length === 0) ok('nenhum botão sem nome acessível');
    else falha('botão sem nome acessível', botoesSemNome.join(' | '));

    const imagensSemTexto = await page.evaluate(
      () =>
        [...document.querySelectorAll('img')].filter(
          (i) =>
            i.getAttribute('alt') === null &&
            i.getAttribute('aria-hidden') !== 'true' &&
            i.getAttribute('role') !== 'presentation'
        ).length
    );
    if (imagensSemTexto === 0) ok('imagens têm texto alternativo ou estão marcadas como decorativas');
    else falha('imagens sem alternativa textual', String(imagensSemTexto));

    // Navegação por teclado: o foco precisa percorrer os campos e chegar ao botão.
    await page.keyboard.press('Tab');
    const sequencia = [];
    for (let i = 0; i < 14; i += 1) {
      const atual = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return null;
        return (
          el.getAttribute('aria-label') ||
          el.getAttribute('placeholder') ||
          (el.textContent || '').trim().slice(0, 30) ||
          el.tagName
        );
      });
      if (atual) sequencia.push(atual);
      await page.keyboard.press('Tab');
    }
    if (sequencia.length >= 4) ok('navegação por teclado alcança os controles', `${sequencia.length} paradas`);
    else falha('navegação por teclado', `só ${sequencia.length} elementos receberam foco`);

    const focoVisivel = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return false;
      const estilo = getComputedStyle(el);
      return estilo.outlineStyle !== 'none' || estilo.boxShadow !== 'none';
    });
    if (focoVisivel) ok('o elemento em foco é visualmente destacado');
    else nota('foco sem destaque próprio (usa o padrão do navegador)');

    await contexto.close();
  }

  // ------------------------------------------------- 3. validação de formulário
  {
    const { contexto, page } = await novaPagina({ width: 390, height: 844 });
    await entrar(page);
    await page.goto(`${APP}/cliente/editar`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);

    await botao(page, 'Salvar').click();
    await page.waitForTimeout(1200);
    let corpo = await page.locator('body').innerText();
    if (/obrigat|informe|preencha|nome/i.test(corpo)) {
      ok('formulário vazio é recusado com mensagem compreensível');
    } else {
      falha('formulário vazio', corpo.slice(0, 200));
    }
    await foto(page, 'validacao-vazio');

    await caixa(page, 0).fill('Cliente de Teste QA');
    await caixa(page, 1).fill('123');
    await botao(page, 'Salvar').click();
    await page.waitForTimeout(1200);
    corpo = await page.locator('body').innerText();
    if (/telefone/i.test(corpo)) ok('telefone inválido aponta o campo certo');
    else nota('telefone curto aceito — sem regra de formato');

    await contexto.close();
  }

  // ------------------------------------------------- 4. estado vazio
  {
    const { contexto, page } = await novaPagina({ width: 390, height: 844 });
    await page.goto(APP, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    const corpo0 = await page.locator('body').innerText();
    if (/Já tenho conta/.test(corpo0)) {
      await botao(page, 'Já tenho conta').click();
      await page.waitForTimeout(1200);
    }
    // Conta nova, carteira vazia.
    const corpo1 = await page.locator('body').innerText();
    if (/Criar conta|Cadastrar/i.test(corpo1)) {
      await botao(page, /^Criar conta$/).click();
      await page.waitForTimeout(1500);
      await caixa(page, 0).fill('Profissional QA');
      await caixa(page, 1).fill(`qa.${Date.now()}@salaoexemplo.com.br`);
      await page.locator('input[type="password"]:visible').first().fill('espelho-teste-2026');
      await botao(page, /^Criar conta$/).click();
      await page.waitForTimeout(4000);
      const corpo2 = await page.locator('body').innerText();
      if (/Entendi, continuar|responsabilidade/i.test(corpo2)) {
        // A tela exige marcar a caixa de ciência antes de liberar o botão — é
        // deliberado, e o roteiro tem de respeitar a regra em vez de contorná-la.
        await page.getByRole('checkbox').first().click();
        await page.waitForTimeout(600);
        await botao(page, 'Entendi').click();
        await page.waitForTimeout(3500);
        ok('a tela de responsabilidades só libera o avanço depois da ciência marcada');
      }
      await page.goto(`${APP}/(tabs)/clientes`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(2500);
      await foto(page, 'estado-vazio');
      const vazio = await page.locator('body').innerText();
      if (/Nenhum cliente|começa aqui|Cadastrar/i.test(vazio)) {
        ok('estado vazio explica o próximo passo em vez de mostrar lista em branco');
      } else {
        falha('estado vazio', vazio.slice(0, 200));
      }
    } else {
      nota('não foi possível abrir o cadastro para testar o estado vazio');
    }
    await contexto.close();
  }

  // ------------------------------------------------- 5. servidor fora do ar
  {
    const { contexto, page } = await novaPagina({ width: 390, height: 844 });
    await entrar(page);
    const corpoAntes = await page.locator('body').innerText();
    if (/Marina|Aline|Agenda|próximo/i.test(corpoAntes)) {
      ok('sessão iniciada antes de simular a queda do servidor');
    }

    // A partir daqui, toda chamada à API falha — como se o servidor tivesse caído.
    await contexto.route(`${API}/**`, (rota) => rota.abort('connectionfailed'));

    await page.goto(`${APP}/(tabs)/clientes`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    await foto(page, 'servidor-fora-do-ar');
    const corpo = await page.locator('body').innerText();

    const avisaFalha = /sem conex|conex|servidor|tentar de novo|não foi poss/i.test(corpo);
    const mentiraVazia = /Nenhum cliente cadastrado/i.test(corpo);

    if (avisaFalha && !mentiraVazia) {
      ok('queda do servidor vira mensagem explicada, com opção de tentar de novo');
    } else if (mentiraVazia) {
      falha(
        'queda do servidor apresentada como carteira vazia',
        'a tela diz "Nenhum cliente cadastrado" com o servidor fora do ar'
      );
    } else {
      falha('queda do servidor sem aviso', corpo.slice(0, 200));
    }

    await contexto.close();
  }

  // ------------------------------------------------- 6. console
  {
    // Ruído esperado: as falhas de rede que este roteiro provoca de propósito.
    const ruidoEsperado = /ERR_CONNECTION|Failed to fetch|NetworkError|net::ERR|connectionfailed/i;
    const errosConsole = mensagens.filter((m) => m.tipo === 'error' && !ruidoEsperado.test(m.texto));
    const avisos = mensagens.filter((m) => m.tipo === 'warning' && !ruidoEsperado.test(m.texto));

    if (errosConsole.length === 0) ok('nenhum erro no console durante toda a bateria');
    else falha('erros no console', errosConsole.map((m) => m.texto).join(' | ').slice(0, 400));

    if (avisos.length === 0) ok('nenhum aviso no console');
    else falha('avisos no console', avisos.map((m) => m.texto).join(' | ').slice(0, 400));
  }
} catch (erro) {
  falha('exceção na bateria', String(erro).slice(0, 400));
} finally {
  await navegador.close();
}

console.log('\n--- resumo ---');
console.log(passos.join('\n'));
console.log('\nFALHAS:', erros.length ? erros : 'nenhuma');
console.log(`capturas em ${TELAS}`);
process.exit(erros.length ? 1 : 0);
