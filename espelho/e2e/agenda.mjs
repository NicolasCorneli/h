/**
 * Verifica, no navegador, os fluxos da agenda: opções por situação, confirmar, editar,
 * cancelar com motivo, concluir gerando o atendimento no histórico, e a recusa de datas
 * passadas na criação e na edição.
 *
 * Precisa da API e do `expo start --web` no ar, com a carga de demonstração recriada
 * (`python -m app.seed --reset`). O navegador roda no fuso de Brasília.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const TELAS = path.join(AQUI, 'telas-agenda');
fs.mkdirSync(TELAS, { recursive: true });

const EMAIL = 'carolina@salaoexemplo.com.br';
const SENHA = 'espelho-demo-2026';

const passos = [];
const erros = [];
let n = 0;

const ok = (d, extra = '') => {
  passos.push(`[ok ] ${d}${extra ? ` (${extra})` : ''}`);
  console.log(passos.at(-1));
};
const falha = (d, detalhe) => {
  passos.push(`[FALHA] ${d}: ${detalhe}`);
  erros.push(`${d}: ${detalhe}`);
  console.log(passos.at(-1));
};
const conferir = (condicao, descricao, detalhe) => (condicao ? ok(descricao) : falha(descricao, detalhe));

const navegador = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--no-sandbox'],
});
const contexto = await navegador.newContext({
  viewport: { width: 420, height: 900 },
  locale: 'pt-BR',
  timezoneId: 'America/Sao_Paulo',
});
const page = await contexto.newPage();
const consoleErros = [];
page.on('console', (m) => {
  if (m.type() === 'error') consoleErros.push(m.text().slice(0, 200));
});

const botao = (nome, exato = false) =>
  page.getByRole('button', { name: nome, exact: exato }).filter({ visible: true }).first();
const foto = async (nome) => {
  n += 1;
  await page.screenshot({ path: `${TELAS}/${String(n).padStart(2, '0')}-${nome}.png` });
};
const corpo = () => page.locator('body').innerText();
const espera = (ms = 1200) => page.waitForTimeout(ms);

/** dd/mm/aaaa de hoje + `dias`, no fuso do navegador (Brasília). */
const dataBr = async (dias) =>
  page.evaluate((d) => {
    const x = new Date();
    x.setDate(x.getDate() + d);
    return x.toLocaleDateString('pt-BR');
  }, dias);
const diaDoMes = async (dias) =>
  page.evaluate((d) => {
    const x = new Date();
    x.setDate(x.getDate() + d);
    return { dia: x.getDate(), mesmoMes: x.getMonth() === new Date().getMonth() };
  }, dias);

async function irParaAgenda() {
  await page.goto(`${APP}/agenda`, { waitUntil: 'networkidle' });
  await espera(2500);
}
async function abrirDia(dias) {
  const { dia, mesmoMes } = await diaDoMes(dias);
  if (!mesmoMes) {
    await botao('Próximo mês').click();
    await espera(600);
  }
  await page.getByRole('button', { name: new RegExp(`^Dia ${dia}(,|$)`) }).first().click();
  await espera(600);
}
async function abrirCompromisso(nome) {
  await page.getByRole('button', { name: new RegExp(nome) }).filter({ visible: true }).first().click();
  await espera(800);
}
async function preencher(placeholder, valor, indice = 0) {
  const campo = page.locator(`input[placeholder="${placeholder}"]:visible`).nth(indice);
  await campo.fill('');
  await campo.type(valor);
  await espera(400);
}

try {
  await page.goto(APP, { waitUntil: 'networkidle' });
  await espera(3500);
  if (/Já tenho conta/.test(await corpo())) {
    await botao('Já tenho conta').click();
    await espera(1200);
  }
  await page.getByRole('textbox').filter({ visible: true }).first().fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await botao('Entrar').click();
  await espera(4000);

  // --- opções de um compromisso pendente --------------------------------
  await irParaAgenda();
  await abrirDia(5);
  await abrirCompromisso('Sofia');
  await foto('opcoes-pendente');
  {
    const folha = await corpo();
    conferir(!/Nova simulação/.test(folha), 'a folha não oferece "Nova simulação"', 'opção ainda presente');
    conferir(!/Registrar atendimento/.test(folha), 'a folha não oferece "Registrar atendimento"', 'ainda presente');
    for (const opcao of [
      'Confirmar agendamento',
      'Atendimento concluído',
      'Editar agendamento',
      'Abrir perfil do cliente',
      'Cancelar agendamento',
    ]) {
      conferir(folha.includes(opcao), `pendente oferece "${opcao}"`, 'opção ausente');
    }
  }

  // --- confirmar ---------------------------------------------------------
  await botao('Confirmar agendamento').click();
  await espera(1500);
  {
    const lista = await corpo();
    conferir(/Agendamento confirmado/.test(lista) || /Confirmado/.test(lista), 'confirmar muda a situação', lista.slice(0, 200));
  }
  await abrirCompromisso('Sofia');
  {
    const folha = await corpo();
    conferir(!/Confirmar agendamento/.test(folha), 'confirmado não oferece "Confirmar" de novo', 'opção presente');
    conferir(/Editar agendamento/.test(folha), 'confirmado continua editável', 'sem editar');
  }

  // --- editar: carrega os dados, recusa o passado, salva ------------------
  await botao('Editar agendamento').click();
  await espera(1800);
  await foto('editar');
  {
    const tela = await corpo();
    conferir(/Sofia/.test(tela) && /Hidratação/.test(tela), 'a edição abre com cliente e serviço atuais', tela.slice(0, 200));
    const hora = await page.locator('input[placeholder="HH:MM"]:visible').first().inputValue();
    conferir(hora === '15:00', 'a edição abre com o horário atual', `veio ${hora}`);
  }
  await preencher('dd/mm/aaaa', await dataBr(-1));
  {
    const tela = await corpo();
    conferir(/Escolha uma data a partir de hoje/.test(tela), 'data de ontem é recusada na edição', 'sem mensagem');
  }
  await preencher('dd/mm/aaaa', await dataBr(5));
  await preencher('HH:MM', '16:30');
  await botao('Salvar alterações').click();
  await espera(2000);
  {
    const lista = await corpo();
    conferir(/16:30/.test(lista) && !/Salvar alterações/.test(lista), 'edição salva volta para a agenda com o novo horário', lista.slice(0, 200));
  }

  // --- proteção contra sair sem salvar -----------------------------------
  await abrirCompromisso('Sofia');
  await botao('Editar agendamento').click();
  await espera(1500);
  await page.locator('textarea:visible').first().fill('anotação que não será salva');
  await botao('Voltar').click();
  await espera(800);
  {
    const tela = await corpo();
    conferir(/Sair sem salvar\?/.test(tela), 'voltar com alterações pede confirmação', 'saiu direto');
    await foto('sair-sem-salvar');
    await botao('Continuar editando').click();
    await espera(500);
    conferir(/Salvar alterações/.test(await corpo()), '"Continuar editando" mantém na tela', 'saiu da tela');
    await botao('Voltar').click();
    await espera(600);
    await botao('Sair sem salvar').click();
    await espera(1200);
  }

  // --- cancelar com motivo -----------------------------------------------
  await irParaAgenda();
  await abrirDia(3);
  await abrirCompromisso('Aline');
  await botao('Cancelar agendamento').click();
  await espera(800);
  await foto('cancelar');
  {
    const dialogo = await corpo();
    conferir(/Cancelar este agendamento\?/.test(dialogo), 'cancelar pede confirmação', 'sem diálogo');
  }
  await page.locator('input[placeholder^="Por exemplo: cliente pediu"]:visible').fill('Viagem de última hora');
  await botao('Cancelar agendamento').click();
  await espera(1800);
  {
    const lista = await corpo();
    conferir(/Cancelado/.test(lista) && /Viagem de última hora/.test(lista), 'cancelado continua na agenda, com o motivo', lista.slice(0, 300));
    await foto('cancelado');
  }
  await abrirCompromisso('Aline');
  {
    const folha = await corpo();
    conferir(
      /Abrir perfil do cliente/.test(folha) && !/Editar agendamento|Confirmar agendamento|Atendimento concluído/.test(folha),
      'cancelado só oferece abrir o perfil',
      folha.slice(0, 200)
    );
    await page.keyboard.press('Escape');
    await espera(500);
  }

  // --- concluir: gera o atendimento no histórico --------------------------
  await irParaAgenda();
  await abrirDia(0);
  await abrirCompromisso('Marina');
  await botao('Atendimento concluído').click();
  await espera(1800);
  await foto('concluir');
  {
    const tela = await corpo();
    conferir(/Horário marcado/i.test(tela) && /14:30/.test(tela) && /Coloração \+ corte/.test(tela), 'a conclusão mostra o horário marcado e o serviço previsto', tela.slice(0, 200));
  }
  // A conclusão começa no horário marcado (14h30); rodando antes disso, ele ainda está no
  // futuro. Informa um horário de hoje que já passou, como faria quem concluiu cedo.
  await preencher('dd/mm/aaaa', await dataBr(0));
  await preencher('HH:MM', '00:00');
  await page.getByRole('radio', { name: /Médio em camadas/ }).first().click();
  await page.locator('textarea:visible').first().fill('Tom dois pontos abaixo do simulado.');
  await botao('Concluir e salvar no histórico').click();
  await espera(2500);
  await foto('historico-apos-concluir');
  {
    const perfil = await corpo();
    conferir(/Marina/.test(perfil) && /Tom dois pontos abaixo do simulado/.test(perfil), 'concluir leva ao perfil com o atendimento no histórico', perfil.slice(0, 300));
  }
  {
    const perfil = await corpo();
    conferir(/Marcado pela agenda/.test(perfil) && !/Agendado para/.test(perfil), 'o histórico mostra a origem (agenda), sem a data marcada que confundia', 'linha ausente');
    conferir(/Simulação usada/.test(perfil), 'o histórico mostra a simulação usada', 'sem simulação');
    await page.getByRole('button', { name: /Ver a simulação usada/ }).first().click();
    await espera(2000);
    conferir(/simulacao\/imagem\//.test(page.url()), 'a simulação do histórico abre a imagem', page.url());
    await foto('simulacao-do-historico');
  }

  await irParaAgenda();
  await abrirDia(0);
  await abrirCompromisso('Marina');
  {
    const folha = await corpo();
    conferir(!/Atendimento concluído\n/.test(folha) && !/Editar agendamento/.test(folha), 'concluído não pode ser concluído nem editado de novo', folha.slice(0, 200));
    await page.keyboard.press('Escape');
  }

  // --- criar no passado é recusado ----------------------------------------
  await page.goto(`${APP}/agendamento/novo`, { waitUntil: 'networkidle' });
  await espera(2500);
  await botao('Escolher cliente').click();
  await espera(800);
  await botao(/Escolher Bruno/).click();
  await espera(600);
  await preencher('dd/mm/aaaa', await dataBr(-1));
  conferir(/Escolha uma data a partir de hoje/.test(await corpo()), 'criação recusa a data de ontem', 'sem mensagem');
  await preencher('dd/mm/aaaa', await dataBr(0));
  await preencher('HH:MM', '00:01');
  await botao('Criar agendamento').click();
  await espera(1200);
  conferir(/Esse horário já passou/.test(await corpo()), 'criação recusa um horário de hoje que já passou', 'sem mensagem');
  await foto('passado-recusado');
} catch (e) {
  falha('execução', e instanceof Error ? e.message.split('\n')[0] : String(e));
  await foto('erro').catch(() => undefined);
} finally {
  await navegador.close();
}

if (consoleErros.length) console.log(`\nerros de console (${consoleErros.length}):\n  ${consoleErros.slice(0, 8).join('\n  ')}`);
console.log(`\n${passos.length - erros.length} verificações ok, ${erros.length} falhas`);
fs.writeFileSync(path.join(TELAS, 'resultado.txt'), passos.join('\n') + '\n');
process.exit(erros.length ? 1 : 0);
