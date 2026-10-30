/**
 * Verifica no navegador as mudanças do painel inicial e da comparação de simulações:
 *
 *  1. o cartão do próximo atendimento mostra a data;
 *  2. "agendados" conta os horários marcados, um por agendamento (não só os de hoje) e "simulações
 *     hoje" conta só as simulações prontas de hoje, conferidos contra a API;
 *  3. "Voltar ao perfil" centralizado na comparação sem simulações suficientes;
 *  4. escolha das duas simulações numa grade: tocar inclui, tocar de novo tira, cada lado
 *     fica onde está, e com os dois ocupados a nova entra à direita;
 *  5. a comparação não marca a preferida nem oferece registrar atendimento ou agendar;
 *  6. a preferida se marca no perfil, em cada simulação (só uma), e aparece primeiro, e o
 *     resto por data;
 *  7. "Ainda hoje" mostra só os compromissos de hoje em aberto: concluídos e cancelados saem;
 *  8. cada simulação salva no perfil tem "Excluir", com confirmação; a exclusão apaga só ela
 *     e preserva o histórico de atendimentos.
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
const TELAS = path.join(AQUI, 'telas-painel');
fs.mkdirSync(TELAS, { recursive: true });

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

const sessao = await (
  await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, senha: SENHA }),
  })
).json();
const cab = { Authorization: `Bearer ${sessao.tokens.accessToken}` };
const api = async (rota) => (await fetch(`${API}${rota}`, { headers: cab })).json();

const navegador = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox'] });
const contexto = await navegador.newContext({ viewport: { width: 390, height: 844 }, locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
const page = await contexto.newPage();
const corpo = () => page.locator('body').innerText();
const espera = (ms = 1200) => page.waitForTimeout(ms);
const botao = (nome) => page.getByRole('button', { name: nome }).filter({ visible: true }).first();
let n = 0;
const foto = async (nome) => {
  n += 1;
  await page.screenshot({ path: `${TELAS}/${String(n).padStart(2, '0')}-${nome}.png` });
};

try {
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await espera(2500);
  await page.getByRole('textbox').filter({ visible: true }).first().fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await botao(/^Entrar$/).click();
  await espera(4000);

  // --- 1 e 2: painel inicial --------------------------------------------------------
  await page.goto(`${APP}/`, { waitUntil: 'networkidle' });
  await espera(3000);
  await foto('inicio');
  {
    const agenda = await api('/agendamentos');
    const simulacoes = await api('/simulacoes');
    const hoje = new Date();
    const inicioDeHoje = new Date(hoje.toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' }) + 'T00:00:00-03:00');
    const ativos = agenda.filter(
      (a) => ['pendente', 'confirmado'].includes(a.status) && new Date(a.dataHora) >= inicioDeHoje
    );
    const esperadoAgendados = ativos.length;
    const diaHoje = hoje.toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    const esperadoSimulacoes = simulacoes.filter(
      (s) => s.status === 'concluida' && new Date(s.criadoEm).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' }) === diaHoje
    ).length;

    const rotulos = await page.evaluate(() =>
      [...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label'))
    );
    const agendados = rotulos.find((r) => /horários? marcados?, de hoje em diante/.test(r ?? ''));
    conferir(
      agendados && Number(agendados.split(' ')[0]) === esperadoAgendados && esperadoAgendados > 0,
      `2. "agendados" mostra ${esperadoAgendados} (horários marcados, de hoje em diante, um por agendamento)`,
      agendados
    );
    const sims = rotulos.find((r) => /simulações hoje$/.test(r ?? ''));
    conferir(sims && Number(sims.split(' ')[0]) === esperadoSimulacoes, `2. "simulações hoje" mostra ${esperadoSimulacoes} (só as prontas de hoje)`, sims);

    const proximo = ativos.filter((a) => new Date(a.dataHora) >= hoje).sort((a, b) => a.dataHora.localeCompare(b.dataHora))[0];
    const cartao = rotulos.find((r) => /^Próximo atendimento:/.test(r ?? ''));
    const textoCartao = await corpo();
    if (proximo) {
      const dia = new Date(proximo.dataHora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo', day: 'numeric' });
      const mes = new Date(proximo.dataHora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo', month: 'long' });
      conferir(new RegExp(`${dia} de ${mes}`).test(textoCartao), `1. o próximo atendimento mostra a data (${dia} de ${mes})`, textoCartao.slice(0, 250));
      conferir(cartao && new RegExp(`${dia} de ${mes}`).test(cartao), '1. a data também está no rótulo acessível do cartão', cartao);
    } else {
      falha('1. próximo atendimento', 'a carga de demonstração deveria ter um');
    }
  }

  // --- 7: "Ainda hoje" só com o que está em aberto ---------------------------------------
  {
    const hojeBr = new Date().toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    const nomes = Object.fromEntries((await api('/clientes')).map((c) => [c.id, c.nome]));
    const abertos = (await api('/agendamentos'))
      .filter(
        (a) =>
          ['pendente', 'confirmado'].includes(a.status) &&
          new Date(a.dataHora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' }) === hojeBr
      )
      .sort((a, b) => a.dataHora.localeCompare(b.dataHora));
    const [concluir, cancelar, ...restantes] = abertos;
    const json = { ...cab, 'Content-Type': 'application/json' };
    const rConcluir = await fetch(`${API}/agendamentos/${concluir?.id}/concluir`, { method: 'POST', headers: json, body: '{}' });
    const rCancelar = await fetch(`${API}/agendamentos/${cancelar?.id}/cancelar`, {
      method: 'POST',
      headers: json,
      body: JSON.stringify({ motivo: 'teste do ainda hoje' }),
    });
    conferir(
      abertos.length >= 3 && rConcluir.ok && rCancelar.ok,
      '7. pré-condição: de 3 compromissos de hoje, um concluído e um cancelado pela API',
      `${abertos.length} em aberto, concluir ${rConcluir.status}, cancelar ${rCancelar.status}`
    );
    await page.goto(`${APP}/`, { waitUntil: 'networkidle' });
    await espera(3000);
    await foto('ainda-hoje');
    const itens = await page.evaluate(() =>
      [...document.querySelectorAll('[aria-label]')]
        .map((e) => e.getAttribute('aria-label'))
        .filter((r) => /^\d{2}:\d{2}, /.test(r ?? ''))
    );
    const descricao = (a) => `${nomes[a.clienteId]}, ${a.servico}`;
    conferir(!itens.some((r) => r.includes(descricao(concluir))), `7. o concluído (${descricao(concluir)}) sai de "Ainda hoje"`, JSON.stringify(itens));
    conferir(!itens.some((r) => r.includes(descricao(cancelar))), `7. o cancelado (${descricao(cancelar)}) sai de "Ainda hoje"`, JSON.stringify(itens));
    conferir(!itens.some((r) => /\. (Concluído|Cancelado)$/.test(r)), '7. nenhum item com selo de concluído ou cancelado', JSON.stringify(itens));
    conferir(
      itens.length === restantes.length && restantes.every((a) => itens.some((r) => r.includes(descricao(a)))),
      `7. os ${restantes.length} em aberto continuam na lista`,
      JSON.stringify(itens)
    );
  }

  // Sem nenhum horário hoje, o número não pode zerar: cancela os de hoje pela API.
  {
    const agenda = await api('/agendamentos');
    const hojeBr = new Date().toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    const deHoje = agenda.filter(
      (a) => ['pendente', 'confirmado'].includes(a.status) && new Date(a.dataHora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' }) === hojeBr
    );
    for (const a of deHoje) {
      await fetch(`${API}/agendamentos/${a.id}/cancelar`, {
        method: 'POST',
        headers: { ...cab, 'Content-Type': 'application/json' },
        body: JSON.stringify({ motivo: 'teste do painel' }),
      });
    }
    const inicioDeHoje = new Date(new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' }) + 'T00:00:00-03:00');
    const restantes = (await api('/agendamentos')).filter(
      (a) => ['pendente', 'confirmado'].includes(a.status) && new Date(a.dataHora) >= inicioDeHoje
    ).length;
    await page.goto(`${APP}/`, { waitUntil: 'networkidle' });
    await espera(3000);
    const rotulos = await page.evaluate(() => [...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label')));
    const agendados = rotulos.find((r) => /horários? marcados?, de hoje em diante/.test(r ?? ''));
    conferir(
      restantes > 0 && agendados && Number(agendados.split(' ')[0]) === restantes,
      `2. sem horário hoje, "agendados" continua mostrando os ${restantes} de outros dias (o zero era o bug)`,
      `${agendados} / esperado ${restantes}`
    );
    await foto('inicio-sem-horario-hoje');
    conferir(/Nenhum compromisso para hoje/.test(await corpo()), '7. com tudo de hoje concluído ou cancelado, "Ainda hoje" fica vazio', '');
    const cartao = await page.evaluate(() => {
      const el = [...document.querySelectorAll('[aria-label^="Próximo atendimento:"]')][0];
      return el ? el.innerText : '';
    });
    const linhas = cartao.split('\n').map((l) => l.trim().toLowerCase());
    const diaDaSemana = (linhas[1] ?? '').split(',')[0];
    conferir(
      /em \d+ dias?|em \d+h|em \d+ min/.test(cartao) && linhas.filter((l) => l === diaDaSemana).length === 0,
      '1. ao lado da hora vai só a distância ("em N dias"), sem repetir o dia da semana',
      cartao
    );
  }

  const clientes = await api('/clientes');
  const marina = clientes.find((c) => c.nome.startsWith('Marina'));
  const aline = clientes.find((c) => c.nome.startsWith('Aline'));

  // --- 3: "Voltar ao perfil" centralizado ---------------------------------------------
  for (const largura of [360, 390, 820]) {
    await page.setViewportSize({ width: largura, height: 844 });
    await page.goto(`${APP}/simulacao/comparar?clienteId=${aline.id}`, { waitUntil: 'networkidle' });
    await espera(2000);
    const m = await page.evaluate(() => {
      const b = [...document.querySelectorAll('[role="button"]')].find((e) => e.textContent.trim() === 'Voltar ao perfil');
      const titulo = [...document.querySelectorAll('div')].find((e) => e.textContent.trim() === 'Ainda não há o que comparar');
      if (!b || !titulo) return null;
      const r = b.getBoundingClientRect();
      const t = titulo.getBoundingClientRect();
      return { botao: (r.left + r.right) / 2, titulo: (t.left + t.right) / 2, larguraBotao: r.width, larguraTela: innerWidth };
    });
    conferir(m && Math.abs(m.botao - m.titulo) <= 1.5 && m.larguraBotao < m.larguraTela - 40, `3. ${largura}px: "Voltar ao perfil" centralizado`, JSON.stringify(m));
    if (largura === 390) await foto('comparar-vazio');
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${APP}/simulacao/comparar?clienteId=${aline.id}`, { waitUntil: 'networkidle' });
  await espera(1500);
  await botao('Voltar ao perfil').click();
  await espera(1500);
  conferir(!/simulacao\/comparar/.test(page.url()), '3. o botão continua funcionando (sai da comparação)', page.url());

  // --- 4 e 5: comparação com simulações ---------------------------------------------
  // Quais simulações estão em cada coluna (pela posição na tela) e como está a grade.
  const estadoComparacao = () =>
    page.evaluate(() => {
      const colunas = [...document.querySelectorAll('[aria-label^="Simulação de "]')]
        .filter((e) => /^Simulação de \d{2}\/\d{2}:/.test(e.getAttribute('aria-label')) && e.getBoundingClientRect().width > 0)
        .sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left)
        .map((e) => e.getAttribute('aria-label').split(', ').at(-1));
      const opcoes = [...document.querySelectorAll('[role="checkbox"]')].map((e) => ({
        rotulo: e.getAttribute('aria-label'),
        marcada: e.getAttribute('aria-checked') === 'true',
        altura: Math.round(e.getBoundingClientRect().height),
      }));
      return { colunas, opcoes, vagas: (document.body.innerText.match(/Toque numa simulação abaixo para colocá-la aqui/g) ?? []).length };
    });
  const marinaSims = await api(`/clientes/${marina.id}/simulacoes`);
  const cores = marinaSims.map((s) => s.parametros.cor);
  const opcao = (cor) => page.getByRole('checkbox', { name: new RegExp(`, ${cor}(, comparando|$)`) }).filter({ visible: true }).first();
  for (const largura of [320, 360, 390]) {
    await page.setViewportSize({ width: largura, height: 844 });
    await page.goto(`${APP}/simulacao/comparar?clienteId=${marina.id}`, { waitUntil: 'networkidle' });
    await espera(2500);
    const e = await estadoComparacao();
    const semRolagem = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);
    conferir(
      semRolagem && e.opcoes.length === marinaSims.length && e.opcoes.every((o) => o.altura >= 44),
      `4. ${largura}px: todas as ${marinaSims.length} simulações na grade, sem rolagem lateral, alvo de 44 px`,
      JSON.stringify({ semRolagem, opcoes: e.opcoes })
    );
    if (largura === 320) await foto('comparar-320');
  }
  {
    let e = await estadoComparacao();
    conferir(
      JSON.stringify(e.colunas) === JSON.stringify(cores.slice(0, 2)) && e.opcoes.filter((o) => o.marcada).length === 2,
      '4. abre comparando as duas primeiras (a preferida e a mais recente), marcadas na grade',
      JSON.stringify(e)
    );
    conferir(
      e.opcoes.some((o) => o.rotulo.endsWith(`${cores[0]}, comparando à esquerda`)) &&
        e.opcoes.some((o) => o.rotulo.endsWith(`${cores[1]}, comparando à direita`)),
      '4. cada marcada diz o lado em que está',
      JSON.stringify(e.opcoes.map((o) => o.rotulo))
    );
    // Tirar a da esquerda: a direita fica onde está, e a esquerda mostra a vaga.
    await opcao(cores[0]).click();
    await espera(500);
    e = await estadoComparacao();
    conferir(e.colunas.length === 1 && e.colunas[0] === cores[1] && e.vagas === 1, '4. tocar numa marcada a tira; o outro lado não se mexe', JSON.stringify(e));
    await foto('comparar-vaga');
    // A nova ocupa o lado vago.
    await opcao(cores[2]).click();
    await espera(500);
    e = await estadoComparacao();
    conferir(JSON.stringify(e.colunas) === JSON.stringify([cores[2], cores[1]]), '4. a nova ocupa o lado vago (esquerda)', JSON.stringify(e.colunas));
    // Com os dois lados ocupados, a nova entra no lugar da direita.
    await opcao(cores[0]).click();
    await espera(500);
    e = await estadoComparacao();
    conferir(JSON.stringify(e.colunas) === JSON.stringify([cores[2], cores[0]]), '4. com os dois ocupados, a nova entra à direita', JSON.stringify(e.colunas));
    await foto('comparar-escolha');
  }
  {
    const tela = await corpo();
    conferir(!/Marcar como preferida/.test(tela) && (await page.getByRole('radio').count()) === 0, '5. a comparação não marca mais a preferida', '');
    conferir(!/Registrar atendimento com a preferida/.test(tela), '5. "Registrar atendimento com a preferida" saiu da comparação', '');
    conferir(!/Agendar para depois/.test(tela), '5. "Agendar para depois" saiu da comparação', '');
  }

  // --- 6: preferida primeiro no perfil --------------------------------------------------
  const ordemNoPerfil = async () => {
    await page.goto(`${APP}/cliente/${marina.id}`, { waitUntil: 'networkidle' });
    await espera(2500);
    return page.evaluate(() =>
      [...document.querySelectorAll('[aria-label^="Abrir a simulação de"]')].map((e) => e.getAttribute('aria-label'))
    );
  };
  const sims = (await api(`/clientes/${marina.id}/simulacoes`)).sort((a, b) => a.criadoEm.localeCompare(b.criadoEm));
  const maisAntiga = sims[0];
  const rotuloAntiga = maisAntiga.parametros.cor;
  await page.setViewportSize({ width: 390, height: 844 });
  await ordemNoPerfil();
  {
    // A preferida se escolhe no perfil, em cada simulação: uma escolha única, como rádio.
    const radios = () =>
      page.evaluate(() =>
        [...document.querySelectorAll('[role="radio"][aria-label$="como preferida do cliente"]')].map((e) => ({
          rotulo: e.getAttribute('aria-label'),
          marcada: e.getAttribute('aria-checked') === 'true',
          altura: Math.round(e.getBoundingClientRect().height),
          dentro: (() => {
            const r = e.getBoundingClientRect();
            const m = e.parentElement.parentElement.getBoundingClientRect();
            return r.left >= m.left - 0.5 && r.right <= m.right + 0.5;
          })(),
        }))
      );
    const antes = await radios();
    conferir(
      antes.length === sims.length && antes.filter((r) => r.marcada).length === 1,
      `6. cada simulação do perfil tem a escolha de preferida, e só uma está marcada`,
      JSON.stringify(antes)
    );
    conferir(antes.every((r) => r.altura >= 44 && r.dentro), '6. a escolha cabe na miniatura e tem alvo de 44 px', JSON.stringify(antes));
    await page.getByRole('radio', { name: `Marcar ${rotuloAntiga} como preferida do cliente` }).first().click();
    await espera(2000);
    conferir(/marcada como preferida/.test(await corpo()), '6. avisa que marcou a preferida', '');
    const depois = await radios();
    conferir(
      depois.filter((r) => r.marcada).map((r) => r.rotulo).join() === `Marcar ${rotuloAntiga} como preferida do cliente`,
      '6. marcar uma desmarca a anterior (só uma preferida)',
      JSON.stringify(depois)
    );
  }
  {
    const ordem = await ordemNoPerfil();
    await foto('perfil-preferida-primeiro');
    const datas = ordem.slice(1).map((r) => r.match(/de (\d{2})\/(\d{2})/)).map((m) => `${m[2]}${m[1]}`);
    conferir(ordem[0]?.includes(rotuloAntiga) && ordem[0]?.endsWith('preferida'), `6. a preferida (${rotuloAntiga}, a mais antiga) aparece primeiro`, JSON.stringify(ordem));
    conferir(datas.every((d, i) => i === 0 || datas[i - 1] >= d), '6. depois dela, as outras seguem da mais recente para a mais antiga', JSON.stringify(ordem));
    const daApi = (await api(`/clientes/${marina.id}/simulacoes`)).map((s) => s.parametros.cor);
    conferir(daApi[0] === rotuloAntiga, '6. a API devolve na mesma ordem', JSON.stringify(daApi));
  }

  // --- 8: excluir uma simulação no perfil --------------------------------------------------
  {
    await page.setViewportSize({ width: 390, height: 844 });
    const antes = await api(`/clientes/${marina.id}/simulacoes`);
    const historicoAntes = await api(`/clientes/${marina.id}/historico`);
    // A que está vinculada a um atendimento: o caso que mais pesa para o histórico.
    const alvo = antes.find((s) => historicoAntes.some((h) => h.simulacaoId === s.id));
    const vinculados = historicoAntes.filter((h) => h.simulacaoId === alvo?.id).map((h) => h.id);
    conferir(alvo && vinculados.length > 0, '8. pré-condição: a carga tem simulação vinculada a atendimento', JSON.stringify(historicoAntes.map((h) => h.simulacaoId)));
    const escapar = (texto) => texto.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const excluirAlvo = page
      .getByRole('button', { name: new RegExp(`^Excluir a simulação de .*, ${escapar(alvo.parametros.cor)}$`) })
      .filter({ visible: true });
    await page.goto(`${APP}/cliente/${marina.id}`, { waitUntil: 'networkidle' });
    await espera(2500);
    const excluir = page.locator('[aria-label^="Excluir a simulação de"]').filter({ visible: true });
    conferir((await excluir.count()) === antes.length, `8. cada uma das ${antes.length} simulações salvas tem "Excluir"`, String(await excluir.count()));
    const alturas = await excluir.evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().height)));
    conferir(alturas.length > 0 && alturas.every((h) => h >= 44), '8. "Excluir" com alvo de toque de 44 px', JSON.stringify(alturas));
    conferir((await excluirAlvo.count()) === 1, `8. o "Excluir" da simulação ${alvo.parametros.cor} é identificável`, String(await excluirAlvo.count()));

    await excluirAlvo.click();
    await espera(800);
    let tela = await corpo();
    conferir(/Excluir esta simulação\?/.test(tela) && /histórico de atendimentos é preservado/.test(tela), '8. pede confirmação e diz o que acontece', tela.slice(-500));
    await foto('excluir-confirmacao');
    await page.getByRole('button', { name: 'Manter', exact: true }).filter({ visible: true }).first().click();
    await espera(1200);
    conferir((await api(`/clientes/${marina.id}/simulacoes`)).length === antes.length, '8. "Manter" não exclui nada', '');

    await excluirAlvo.click();
    await espera(800);
    await page.getByRole('button', { name: 'Excluir simulação', exact: true }).filter({ visible: true }).first().click();
    await espera(2500);
    tela = await corpo();
    const depois = await api(`/clientes/${marina.id}/simulacoes`);
    conferir(depois.length === antes.length - 1 && !depois.some((s) => s.id === alvo.id), '8. confirmar exclui só aquela simulação (conferido na API)', JSON.stringify(depois.map((s) => s.id)));
    const naTela = await page.locator('[aria-label^="Abrir a simulação de"]').filter({ visible: true }).count();
    conferir(naTela === depois.length, `8. o perfil atualiza na hora (${naTela} na tela)`, String(naTela));
    conferir(/Simulação excluída/.test(tela), '8. avisa que a simulação foi excluída', tela.slice(0, 300));
    conferir((await fetch(`${API}/simulacoes/${alvo.id}`, { headers: cab })).status === 404, '8. a simulação excluída deixa de existir no servidor', '');
    const historicoDepois = await api(`/clientes/${marina.id}/historico`);
    conferir(
      historicoDepois.length === historicoAntes.length &&
        vinculados.every((id) => historicoDepois.some((h) => h.id === id && h.simulacaoId === null)),
      `8. o histórico fica inteiro; ${vinculados.length} atendimento(s) só perde(m) o vínculo`,
      JSON.stringify(historicoDepois.map((h) => [h.id, h.simulacaoId]))
    );
    conferir(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), '8. perfil sem rolagem lateral', '');
    await foto('perfil-depois-de-excluir');

    // Já excluída em outro aparelho: a tela ainda a mostra; excluir de novo só corrige a lista.
    const outra = depois[0];
    const apagada = await fetch(`${API}/simulacoes/${outra.id}`, { method: 'DELETE', headers: cab });
    const excluirOutra = page
      .getByRole('button', { name: new RegExp(`^Excluir a simulação de .*, ${escapar(outra.parametros.cor)}$`) })
      .filter({ visible: true });
    conferir(apagada.status === 204 && (await excluirOutra.count()) === 1, '8. pré-condição: excluída pela API, ainda na tela', String(apagada.status));
    await excluirOutra.click();
    await espera(800);
    await page.getByRole('button', { name: 'Excluir simulação', exact: true }).filter({ visible: true }).first().click();
    await espera(2500);
    tela = await corpo();
    const final = await api(`/clientes/${marina.id}/simulacoes`);
    const naTelaFinal = await page.locator('[aria-label^="Abrir a simulação de"]').filter({ visible: true }).count();
    conferir(
      naTelaFinal === final.length && final.length === depois.length - 1 && !/não encontrada/i.test(tela),
      '8. excluir o que já foi excluído em outro lugar atualiza a lista, sem erro',
      `${naTelaFinal} na tela, ${final.length} na API`
    );
  }
} catch (e) {
  falha('execução', e instanceof Error ? e.message.split('\n')[0] : String(e));
  await foto('erro').catch(() => undefined);
} finally {
  await navegador.close();
}

console.log(`\n${passos.length - erros.length} verificações ok, ${erros.length} falhas`);
fs.writeFileSync(path.join(TELAS, 'resultado.txt'), passos.join('\n') + '\n');
process.exit(erros.length ? 1 : 0);
