/**
 * Verifica no navegador as correções de agendamentos, agenda e atendimentos:
 *
 *  1-3  duração opcional, digitada, e recusa de duração inválida;
 *  4-5  criar volta à agenda, sem "Sair sem salvar?", com o agendamento à vista;
 *  6-7  o "+" usa o dia selecionado na agenda, nunca um dia passado;
 *  8    botão da câmera dentro da barra e "Cancelar consentimento" centralizado;
 *  9-11 conclusão com data, hora e serviço previstos, "Outro" e dados corrigidos salvos;
 *  12-14 registro direto pelo perfil, no histórico certo, sem agendamento fictício;
 *  15   alinhamentos em três tamanhos de tela;
 *  e clique duplo em salvar sem duplicar.
 *
 * Cada verificação de gravação confere o servidor (API), não só a tela.
 * Pré-requisitos: API e `expo start --web` no ar, carga de demonstração recriada.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';
const TELAS = path.join(AQUI, 'telas-atendimentos');
fs.mkdirSync(TELAS, { recursive: true });

const EMAIL = 'carolina@salaoexemplo.com.br';
const SENHA = 'espelho-demo-2026';

const passos = [];
const erros = [];
let n = 0;
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

// --- API (para conferir o que foi gravado) ---------------------------------------
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
const contexto = await navegador.newContext({
  viewport: { width: 420, height: 900 },
  locale: 'pt-BR',
  timezoneId: 'America/Sao_Paulo',
});
const page = await contexto.newPage();
const dialogos = [];

const botao = (nome) => page.getByRole('button', { name: nome }).filter({ visible: true }).first();
const corpo = () => page.locator('body').innerText();
const espera = (ms = 1200) => page.waitForTimeout(ms);
const foto = async (nome) => {
  n += 1;
  await page.screenshot({ path: `${TELAS}/${String(n).padStart(2, '0')}-${nome}.png` });
};
const valorDe = (placeholder, i = 0) => page.locator(`input[placeholder="${placeholder}"]:visible`).nth(i).inputValue();
async function preencher(placeholder, valor, i = 0) {
  const campo = page.locator(`input[placeholder="${placeholder}"]:visible`).nth(i);
  await campo.fill('');
  await campo.type(valor);
  await espera(300);
}
async function sairDoCampo() {
  await page.locator('body').click({ position: { x: 5, y: 5 } }).catch(() => undefined);
  await page.keyboard.press('Tab');
  await espera(300);
}
/** O chip com esse texto está marcado como selecionado? */
const chipSelecionado = (texto) =>
  page.evaluate(
    (t) =>
      [...document.querySelectorAll('[role="button"][aria-selected="true"]')].some(
        (el) => el.textContent.trim() === t && el.offsetParent !== null
      ),
    texto
  );
const temSairSemSalvar = async () => /Sair sem salvar\?/.test(await corpo());

/** dd/mm/aaaa de hoje + `dias` no fuso do navegador. */
const dataBr = (dias) =>
  page.evaluate((d) => {
    const x = new Date();
    x.setDate(x.getDate() + d);
    return x.toLocaleDateString('pt-BR');
  }, dias);
const isoDia = (dias) =>
  page.evaluate((d) => {
    const x = new Date();
    x.setDate(x.getDate() + d);
    return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`;
  }, dias);

async function irParaAgenda() {
  await page.goto(`${APP}/agenda`, { waitUntil: 'networkidle' });
  await espera(2500);
}
async function abrirDiaDaAgenda(dias) {
  const { dia, deslocamentoMes } = await page.evaluate((d) => {
    const x = new Date();
    const hoje = new Date();
    x.setDate(x.getDate() + d);
    return {
      dia: x.getDate(),
      deslocamentoMes: (x.getFullYear() - hoje.getFullYear()) * 12 + x.getMonth() - hoje.getMonth(),
    };
  }, dias);
  for (let i = 0; i < Math.abs(deslocamentoMes); i++) {
    await botao(deslocamentoMes > 0 ? 'Próximo mês' : 'Mês anterior').click();
    await espera(500);
  }
  await page.getByRole('button', { name: new RegExp(`^Dia ${dia}(,|$)`) }).first().click();
  await espera(600);
}
async function escolherCliente(nome) {
  await botao('Escolher cliente').click();
  await espera(700);
  await botao(new RegExp(`Escolher ${nome}`)).click();
  await espera(500);
}

page.on('dialog', (d) => {
  dialogos.push(d.message());
  void d.dismiss();
});

try {
  // --- entrar ----------------------------------------------------------------------
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await espera(2500);
  await page.getByRole('textbox').filter({ visible: true }).first().fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await botao(/^Entrar$/).click();
  await espera(4000);

  const agendaAntes = await api('/agendamentos');

  // --- 6, 1, 4, 5: dia futuro, sem duração, volta à agenda ---------------------------
  await irParaAgenda();
  await abrirDiaDaAgenda(2);
  await botao('Novo agendamento').click();
  await espera(1800);
  {
    const data = await valorDe('dd/mm/aaaa');
    conferir(data === (await dataBr(2)), '6. o "+" abre o formulário no dia futuro selecionado', `veio ${data}`);
    const duracao = await valorDe('Ex.: 1h30');
    conferir(duracao === '', '1. a duração começa vazia (nada presumido)', `veio "${duracao}"`);
    const tela = await corpo();
    conferir(!/\b30 min\b.*\b45 min\b/s.test(tela), 'os botões de duração fixa saíram', 'ainda há chips de duração');
  }
  await escolherCliente('Bruno');
  await preencher('HH:MM', '10:00');
  await foto('novo-sem-duracao');
  await botao('Criar agendamento').click();
  await espera(2500);
  conferir(!(await temSairSemSalvar()), '4. criar não mostra "Sair sem salvar?"', 'o alerta apareceu');
  conferir(/\/agenda/.test(page.url()), '4. depois de criar, volta à agenda', page.url());
  {
    const tela = await corpo();
    conferir(/Bruno Tavares/.test(tela) && /10:00/.test(tela), '5. o agendamento novo aparece na agenda, no dia dele', tela.slice(0, 300));
    await foto('agenda-depois-de-criar');
    const criado = (await api('/agendamentos')).find(
      (a) => !agendaAntes.some((b) => b.id === a.id) && a.servico === 'Coloração'
    );
    conferir(criado && criado.duracaoMin === null, '1. gravado no servidor sem duração (null)', JSON.stringify(criado));
    const diaGravado = criado && new Date(criado.dataHora).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    conferir(diaGravado === (await dataBr(2)), '6. gravado no dia selecionado na agenda', diaGravado);
  }

  // --- 2: duração digitada ---------------------------------------------------------
  await botao('Novo agendamento').click();
  await espera(1800);
  await escolherCliente('Bruno');
  await preencher('HH:MM', '11:30');
  await preencher('Ex.: 1h30', '1 hora e 30 minutos');
  await sairDoCampo();
  conferir(/Fica registrado como 1h30/.test(await corpo()), '2. a duração digitada é entendida e mostrada normalizada', '');
  await botao('Criar agendamento').click();
  await espera(2500);
  {
    const lista = await api('/agendamentos');
    const comDuracao = lista.find((a) => a.duracaoMin === 90 && !agendaAntes.some((b) => b.id === a.id));
    conferir(!!comDuracao, '2. gravado no servidor como 90 minutos', '');
    conferir(/1h30/.test(await corpo()), '2. a agenda mostra a duração (1h30)', '');
  }

  // --- 3: duração inválida + clique duplo ---------------------------------------------
  await botao('Novo agendamento').click();
  await espera(1800);
  await escolherCliente('Bruno');
  await preencher('HH:MM', '13:00');
  await preencher('Ex.: 1h30', 'umas duas');
  await sairDoCampo();
  {
    const tela = await corpo();
    conferir(/Não entendi essa duração/.test(tela), '3. duração inválida mostra mensagem clara', tela.slice(0, 200));
    const antes = (await api('/agendamentos')).length;
    await botao('Criar agendamento').click();
    await espera(1500);
    const depois = (await api('/agendamentos')).length;
    conferir(depois === antes && /Criar agendamento/.test(await corpo()), '3. com duração inválida não salva e continua no formulário', `${antes} -> ${depois}`);
    await foto('duracao-invalida');

    // Corrige deixando em branco (opcional) e salva com dois cliques seguidos.
    await preencher('Ex.: 1h30', '');
    await page.locator('input[placeholder="Ex.: 1h30"]:visible').first().fill('');
    await espera(300);
    const salvar = botao('Criar agendamento');
    await salvar.dblclick();
    await espera(2500);
    const finais = (await api('/agendamentos')).length;
    conferir(finais === antes + 1, 'clique duplo em "Criar agendamento" grava uma vez só', `${antes} -> ${finais}`);
  }

  // --- 7: dia passado selecionado ----------------------------------------------------
  await irParaAgenda();
  await abrirDiaDaAgenda(-1);
  await botao('Novo agendamento').click();
  await espera(1800);
  {
    const data = await valorDe('dd/mm/aaaa');
    conferir(data === (await dataBr(0)), '7. com dia passado selecionado, o formulário abre em hoje', `veio ${data}`);
  }
  // A proteção continua valendo quando há algo preenchido de verdade.
  await page.locator('textarea:visible').first().fill('rascunho');
  await botao('Voltar').click();
  await espera(800);
  conferir(await temSairSemSalvar(), '"Sair sem salvar?" continua aparecendo quando há alteração', '');
  await botao('Sair sem salvar').click();
  await espera(1000);

  // --- 9, 10, 11: conclusão -----------------------------------------------------------
  const agenda = await api('/agendamentos');
  const julia = agenda.find((a) => a.servico === 'Penteado para festa');
  const aline = agenda.find((a) => a.servico === 'Retoque de cor');

  await page.goto(`${APP}/agendamento/concluir/${aline.id}`, { waitUntil: 'networkidle' });
  await espera(2500);
  {
    const marcado = new Date(aline.dataHora);
    const esperadoData = marcado.toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    const esperadoHora = marcado.toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit' });
    const data = await valorDe('dd/mm/aaaa');
    const horaCampo = await valorDe('HH:MM');
    conferir(data === esperadoData && horaCampo === esperadoHora, '9. a conclusão abre com a data e o horário marcados', `${data} ${horaCampo} (esperado ${esperadoData} ${esperadoHora})`);
    conferir(await chipSelecionado('Retoque de cor'), '9. o serviço previsto (da lista) vem selecionado', '');
    conferir(/Outro/.test(await corpo()), '10. a opção "Outro" aparece na conclusão', '');
    const duracao = await valorDe('Ex.: 1h30');
    conferir(duracao === '1h30', 'a duração prevista vem preenchida e editável', `veio "${duracao}"`);
  }
  await foto('concluir-servico-da-lista');

  await page.goto(`${APP}/agendamento/concluir/${julia.id}`, { waitUntil: 'networkidle' });
  await espera(2500);
  {
    conferir(await chipSelecionado('Outro'), '10. serviço fora da lista abre em "Outro"', '');
    const descricao = await page.locator('input[placeholder="Por exemplo: penteado para festa"]:visible').first().inputValue();
    conferir(descricao === 'Penteado para festa', '10. a descrição personalizada vem preenchida com o texto original', `veio "${descricao}"`);
    const duracao = await valorDe('Ex.: 1h30');
    conferir(duracao === '', 'agendamento sem duração conclui com a duração vazia', `veio "${duracao}"`);
    await foto('concluir-outro');

    // 11: corrige o que de fato aconteceu: ontem, 18h15, "Escova", 40 min.
    await preencher('dd/mm/aaaa', await dataBr(-1));
    await preencher('HH:MM', '18:15');
    await botao('Escova').click();
    await espera(300);
    await preencher('Ex.: 1h30', '40 min');
    await botao('Concluir e salvar no histórico').click();
    await espera(3000);
    conferir(!(await temSairSemSalvar()), 'concluir não mostra "Sair sem salvar?"', '');
    const atendimentos = await api(`/atendimentos?clienteId=${julia.clienteId}`);
    const gravado = atendimentos.find((a) => a.agendamentoId === julia.id);
    const quando = gravado && new Date(gravado.realizadoEm).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    conferir(
      gravado && gravado.descricao === 'Escova' && gravado.duracaoMin === 40 && quando?.includes(await dataBr(-1)) && quando?.includes('18:15'),
      '11. o atendimento grava o que foi realizado (Escova, ontem 18:15, 40 min)',
      JSON.stringify(gravado)
    );
    const origem = (await api('/agendamentos')).find((a) => a.id === julia.id);
    conferir(origem.servico === 'Penteado para festa' && origem.status === 'concluido', '11. o agendamento original mantém o serviço previsto', JSON.stringify(origem));
    const perfil = await corpo();
    conferir(/Escova/.test(perfil) && /previsto: Penteado para festa/.test(perfil), '11. o histórico mostra o realizado e o previsto', perfil.slice(0, 300));
    await foto('historico-apos-conclusao');
  }

  // --- 12, 13, 14: registrar direto pelo perfil ---------------------------------------
  const clientes = await api('/clientes');
  const bruno = clientes.find((c) => c.nome.startsWith('Bruno'));
  const agendaAntesDoAvulso = (await api('/agendamentos')).length;
  const historicoAntes = (await api(`/atendimentos?clienteId=${bruno.id}`)).length;

  await page.goto(`${APP}/cliente/${bruno.id}`, { waitUntil: 'networkidle' });
  await espera(2500);
  await botao('Registrar atendimento').click();
  await espera(2000);
  {
    const tela = await corpo();
    conferir(/Bruno Tavares/.test(tela) && /Quando o atendimento aconteceu/i.test(tela), '12. o registro abre com o cliente preenchido', tela.slice(0, 200));
    const data = await valorDe('dd/mm/aaaa');
    conferir(data === (await dataBr(0)), '12. o registro começa com a data de hoje', `veio ${data}`);
    conferir(/Outro/.test(tela) && (await page.locator('input[placeholder="Ex.: 1h30"]:visible').count()) === 1, '12. tem os mesmos campos do agendamento (serviços com Outro, duração)', '');
    conferir(await chipSelecionado('Corte'), '12. sugere um serviço visível (Corte), como a tela antiga', '');
    await foto('registrar-atendimento');
  }
  await preencher('dd/mm/aaaa', await dataBr(-2));
  await preencher('HH:MM', '10:20');
  await botao('Outro').click();
  await espera(300);
  await page.locator('input[placeholder="Por exemplo: penteado para festa"]:visible').first().fill('Barba e sobrancelha');
  await preencher('Ex.: 1h30', '30 min');
  await page.locator('textarea:visible').first().fill('Chegou sem marcar.');
  await botao('Salvar atendimento').dblclick();
  await espera(3000);
  {
    conferir(!(await temSairSemSalvar()), 'registrar não mostra "Sair sem salvar?"', '');
    const tela = await corpo();
    conferir(/Atendimento registrado/.test(tela) && /Barba e sobrancelha/.test(tela), 'a confirmação mostra o que foi gravado', tela.slice(0, 300));
    await foto('registro-salvo');
    const historico = await api(`/atendimentos?clienteId=${bruno.id}`);
    const novos = historico.length - historicoAntes;
    const gravado = historico.find((a) => a.descricao === 'Barba e sobrancelha');
    conferir(novos === 1, '14. clique duplo em salvar grava um atendimento só', `${novos} novos`);
    conferir(
      gravado && gravado.agendamentoId === null && gravado.duracaoMin === 30 && gravado.observacoes === 'Chegou sem marcar.' && gravado.dataServico === (await isoDia(-2)),
      '13. o atendimento avulso foi gravado no cliente certo, com dia, duração e observações',
      JSON.stringify(gravado)
    );
    const agendaDepois = (await api('/agendamentos')).length;
    conferir(agendaDepois === agendaAntesDoAvulso, '14. nenhum agendamento fictício foi criado', `${agendaAntesDoAvulso} -> ${agendaDepois}`);
  }
  await botao('Voltar ao perfil do cliente').click();
  await espera(2500);
  {
    const perfil = await corpo();
    conferir(/Barba e sobrancelha/.test(perfil) && /Registrado sem agendamento/.test(perfil), '13. aparece no histórico do perfil, como registro sem agendamento', perfil.slice(0, 400));
    await foto('perfil-com-avulso');
  }

  // --- 8 e 15: alinhamentos em três tamanhos -----------------------------------------
  const marina = clientes.find((c) => c.nome.startsWith('Marina'));
  for (const [largura, altura] of [
    [360, 640],
    [390, 844],
    [820, 1180],
  ]) {
    await page.setViewportSize({ width: largura, height: altura });
    await page.goto(`${APP}/agenda`, { waitUntil: 'networkidle' });
    await espera(2000);
    const medida = await page.evaluate(() => {
      const camera = document.querySelector('[aria-label="Nova simulação"]');
      const aba = document.querySelector('[role="tab"]');
      // A barra é o ancestral comum que tem fundo pintado.
      let barra = camera?.parentElement;
      while (barra && getComputedStyle(barra).backgroundColor === 'rgba(0, 0, 0, 0)') barra = barra.parentElement;
      const c = camera.getBoundingClientRect();
      const b = barra.getBoundingClientRect();
      const t = aba.getBoundingClientRect();
      return { cTop: c.top, cBottom: c.bottom, cMeio: (c.top + c.bottom) / 2, bTop: b.top, bBottom: b.bottom, tMeio: (t.top + t.bottom) / 2 };
    });
    conferir(
      medida.cTop >= medida.bTop - 0.5 && medida.cBottom <= medida.bBottom + 0.5,
      `8. ${largura}x${altura}: botão da câmera inteiro dentro da barra`,
      JSON.stringify(medida)
    );
    conferir(Math.abs(medida.cMeio - medida.tMeio) <= 2, `8. ${largura}x${altura}: câmera no mesmo eixo das abas`, JSON.stringify(medida));
    if (largura === 390) await foto('barra-inferior');

    await page.goto(`${APP}/cliente/${marina.id}`, { waitUntil: 'networkidle' });
    await espera(2000);
    const centro = await page.evaluate(() => {
      const el = [...document.querySelectorAll('[role="button"]')].find((b) => b.textContent.trim() === 'Cancelar consentimento');
      if (!el) return null;
      let cartao = el.parentElement;
      while (cartao && getComputedStyle(cartao).borderTopWidth === '0px') cartao = cartao.parentElement;
      const b = el.getBoundingClientRect();
      const c = cartao.getBoundingClientRect();
      return { botao: (b.left + b.right) / 2, cartao: (c.left + c.right) / 2, largura: b.width, cartaoLargura: c.width };
    });
    conferir(
      centro && Math.abs(centro.botao - centro.cartao) <= 1.5 && centro.largura < centro.cartaoLargura,
      `8. ${largura}x${altura}: "Cancelar consentimento" centralizado, com o tamanho de antes`,
      JSON.stringify(centro)
    );
    if (largura === 390) await foto('cancelar-consentimento');
    const rolagem = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    conferir(!rolagem, `15. ${largura}x${altura}: sem rolagem horizontal`, '');
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
