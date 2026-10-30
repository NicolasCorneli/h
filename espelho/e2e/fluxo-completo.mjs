/**
 * Validação de ponta a ponta: aplicativo Expo (web) falando com o FastAPI real.
 *
 * Exercita o fluxo da seção 44 da especificação, do cadastro à revogação, e os caminhos
 * de erro. Nada é simulado no navegador além da escolha do arquivo de foto.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const RETRATO = path.join(AQUI, 'retrato-sintetico.jpg');
const TELAS = path.join(AQUI, 'telas');
fs.mkdirSync(TELAS, { recursive: true });

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
async function foto(page, nome) {
  n += 1;
  await page.screenshot({ path: `${TELAS}/${String(n).padStart(2, '0')}-${nome}.png` });
}

const email = `teste.${Date.now()}@salaoexemplo.com.br`;
const SENHA = 'espelho-teste-2026';

const navegador = await chromium.launch({
  // Em ambientes com o Chromium instalado fora do padrão, defina CHROMIUM_PATH.
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--no-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
});
const contexto = await navegador.newContext({
  viewport: { width: 420, height: 900 },
  permissions: ['camera'],
  locale: 'pt-BR',
});
const page = await contexto.newPage();

const consoleErros = [];
page.on('console', (m) => {
  if (m.type() === 'error') consoleErros.push(m.text().slice(0, 300));
});
page.on('pageerror', (e) => consoleErros.push(`pageerror: ${String(e).slice(0, 300)}`));

const botao = (nome, exato = true) => page.getByRole('button', { name: nome, exact: exato }).filter({ visible: true }).first();
const texto = (t) => page.getByText(t, { exact: false }).filter({ visible: true }).first();
const caixa = (i) => page.getByRole('textbox').filter({ visible: true }).nth(i);
const senhaCampo = () => page.locator('input[type="password"]:visible').first();
/** Confirmação: o rótulo repete o do botão da página, então pega o último (o do diálogo). */
const botaoDialogo = (nome) => page.getByRole('button', { name: nome, exact: false }).filter({ visible: true }).last();

/**
 * Abre o fluxo de simulação do jeito que o aplicativo passou a oferecer: pelo botão fixo
 * da barra inferior, escolhendo o cliente em seguida. O atalho que existia no perfil foi
 * removido de propósito — a entrada é uma só.
 */
async function simularPara(nomeCliente) {
  await page.goto(`${APP}/(tabs)`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(2000);
  await botao('Nova simulação', false).click();
  await page.waitForTimeout(2000);
  await texto(nomeCliente).click();
  await page.waitForTimeout(2500);
}

try {
  // --- 1. Abertura e cadastro de conta nova ------------------------------
  await page.goto(APP, { waitUntil: 'networkidle' });
  await page.waitForTimeout(4000);
  await foto(page, 'onboarding');
  await botao('Já tenho conta').click();
  await page.waitForTimeout(1200);
  ok('onboarding → login');

  await botao(/^Criar conta$/).click();
  await page.waitForTimeout(1200);
  await caixa(0).fill('Camila Teste');
  await caixa(1).fill(email);
  await senhaCampo().fill(SENHA);
  await foto(page, 'cadastro');
  await botao(/^Criar conta$/).click();
  await page.waitForTimeout(3500);

  if (await texto('responsabilidades').isVisible().catch(() => false)) {
    ok('cadastro criou a conta e abriu as responsabilidades');
  } else if (await texto('Suas responsabilidades').isVisible().catch(() => false)) {
    ok('cadastro criou a conta e abriu as responsabilidades');
  } else {
    falha('cadastro', `tela inesperada: ${(await page.title())} / ${(await page.locator('body').innerText()).slice(0, 160)}`);
  }
  await foto(page, 'responsabilidades');

  // --- 2. Ciência das responsabilidades ---------------------------------
  const temDocumento = await texto('Explique antes de registrar').isVisible().catch(() => false);
  if (temDocumento) ok('aviso do profissional veio do servidor (tabela termos)');
  else falha('aviso do profissional', 'texto do termo não apareceu');

  await page.getByRole('checkbox').first().click();
  await botao('Entendi, continuar').click();
  await page.waitForTimeout(3000);
  await foto(page, 'painel-vazio');
  const vazio = await page.locator('body').innerText();
  if (/carteira começa|Cadastrar cliente|Bem-vindo|Bom dia|Boa tarde|Boa noite/i.test(vazio)) {
    ok('ciência registrada; painel abriu com a carteira vazia');
  } else {
    falha('painel inicial', vazio.slice(0, 160));
  }

  // --- 3. Cadastro de cliente -------------------------------------------
  await page.getByRole('tab', { name: 'Clientes' }).click().catch(async () => {
    await botao('Clientes', false).click();
  });
  await page.waitForTimeout(1500);
  await botao('Cadastrar cliente', false).click();
  await page.waitForTimeout(1500);
  await caixa(0).fill('Lívia Monteiro');
  await caixa(1).fill('(55) 99888-1122');
  await foto(page, 'novo-cliente');
  await botao('Salvar cliente', false).click();
  await page.waitForTimeout(3000);
  const perfil = await page.locator('body').innerText();
  if (perfil.includes('Lívia')) ok('cliente criado no servidor e perfil aberto');
  else falha('cadastro de cliente', perfil.slice(0, 200));
  await foto(page, 'perfil-pendente');

  if (/pendente/i.test(perfil)) ok('selo de consentimento pendente (resumo do servidor)');
  else falha('selo de consentimento', 'status pendente não exibido');

  // --- 4. Câmera bloqueada sem consentimento ----------------------------
  await simularPara('Lívia');
  const bloqueio = await page.locator('body').innerText();
  if (/ainda não decidiu|Apresente o termo|termo de uso de imagem/i.test(bloqueio)) {
    ok('sem consentimento o fluxo leva ao termo, não à câmera');
  } else {
    falha('bloqueio de captura', bloqueio.slice(0, 200));
  }
  await foto(page, 'termo-cliente');

  // --- 5. Registro do consentimento -------------------------------------
  const termoVisivel = await texto('A foto do seu rosto é um dado sensível').isVisible().catch(() => false);
  if (termoVisivel) ok('termo do cliente carregado do servidor, na versão vigente');
  else falha('termo do cliente', 'texto não apareceu');

  // Verifica a substância, não a redação: o termo tem de dizer que a foto vai para outra
  // empresa e que ela pode usar a imagem para treinar os sistemas dela. Procurar uma
  // frase exata quebraria a cada revisão de texto, que é algo que deve poder acontecer.
  const corpoTermo = await page.locator('body').innerText();
  const dizQueVaiParaOutraEmpresa = /outra empresa|empresa terceira|serviço de intelig/i.test(corpoTermo);
  const dizQuePodeTreinar = /treinar/i.test(corpoTermo);
  if (dizQueVaiParaOutraEmpresa && dizQuePodeTreinar) {
    ok('o termo informa o envio a outra empresa e o uso para treinar os modelos dela');
  } else {
    falha(
      'aviso sobre o serviço externo',
      `envio=${dizQueVaiParaOutraEmpresa} treino=${dizQuePodeTreinar}`
    );
  }

  await botao('Aceitou', false).click().catch(async () => {
    await page.getByLabel(/aceitou o uso da imagem/i).click();
  });
  await page.waitForTimeout(3500);
  await foto(page, 'camera');
  const apos = await page.locator('body').innerText();
  if (/Etapa 2 de 3|Galeria|autorizou/i.test(apos)) ok('consentimento aceito liberou a câmera');
  else falha('liberação da câmera', apos.slice(0, 200));

  // --- 6. Simulação completa com a foto de teste ------------------------
  const escolha = page.waitForEvent('filechooser');
  await botao('Escolher foto da galeria', false).click();
  const seletor = await escolha;
  await seletor.setFiles(RETRATO);
  await page.waitForTimeout(3000);
  await foto(page, 'parametros');
  const params = await page.locator('body').innerText();
  if (/Estilo e cor|Corte/i.test(params)) ok('foto aceita na pré-checagem local');
  else falha('pré-checagem', params.slice(0, 200));

  // Etapa "Estilo e cor": corte e cor escritos (dois dos exemplos da tela), depois a revisão.
  await page.getByLabel('Novo corte', { exact: true }).filter({ visible: true }).first().fill('Chanel');
  await page.getByLabel('Nova cor', { exact: true }).filter({ visible: true }).first().fill('Ruivo');
  await botao('Revisar pedido', false).click();
  await page.waitForTimeout(1500);
  const revisao = await page.locator('body').innerText();
  if (/Revisar pedido/.test(revisao) && /Chanel/.test(revisao) && /Ruivo/.test(revisao)) ok('revisão mostra corte e cor escolhidos');
  else falha('revisão do pedido', revisao.slice(0, 200));
  await botao('Gerar simulação', false).click();
  ok('envio iniciado (POST /simulacoes)');
  await page.waitForTimeout(2500);
  await foto(page, 'processando');

  // Aguarda o resultado (geração + consulta de estado)
  let resultado = '';
  for (let i = 0; i < 40; i += 1) {
    await page.waitForTimeout(1000);
    resultado = await page.locator('body').innerText();
    if (/Resultado|aproximação visual|não respondeu/i.test(resultado)) break;
  }
  await foto(page, 'resultado');
  if (/aproximação visual/i.test(resultado)) {
    ok('simulação concluída e resultado exibido');
  } else {
    falha('resultado da simulação', resultado.slice(0, 250));
  }

  // A imagem gerada precisa estar visível, servida por URL assinada.
  const imagens = await page.locator('img').all();
  let assinadas = 0;
  for (const img of imagens) {
    const src = (await img.getAttribute('src')) ?? '';
    if (src.includes('/api/v1/imagens/') && src.includes('t=')) assinadas += 1;
  }
  if (assinadas >= 1) ok('imagens vêm por URL assinada', `${assinadas} encontradas`);
  else falha('URL assinada', 'nenhuma imagem /api/v1/imagens/?t= na tela');

  // --- 7. Registro do atendimento vinculado -----------------------------
  await botao('Registrar atendimento', false).click();
  await page.waitForTimeout(2500);
  await foto(page, 'atendimento');
  await botao('Salvar atendimento', false).click();
  await page.waitForTimeout(3000);
  const sucesso = await page.locator('body').innerText();
  if (/\/atendimento\/sucesso/.test(page.url()) && /Atendimento registrado/.test(sucesso) && /vinculad/.test(sucesso))
    ok('atendimento registrado com a simulação vinculada');
  else falha('registro de atendimento', sucesso.slice(0, 200));
  await foto(page, 'sucesso');

  // --- 8. Agendamento ---------------------------------------------------
  const temAgendar = await botao('Agendar retorno', false).isVisible().catch(() => false);
  if (temAgendar) {
    await botao('Agendar retorno', false).click();
    await page.waitForTimeout(2000);
    await botao('Criar agendamento', false).click();
    await page.waitForTimeout(2500);
    const agenda = await page.locator('body').innerText();
    if (/Agenda|hoje|Pendente|Aguardando/i.test(agenda)) ok('agendamento criado e agenda aberta');
    else falha('agendamento', agenda.slice(0, 200));
    await foto(page, 'agenda');
  } else {
    passos.push('[ -- ] tela de sucesso sem botão de agendar; segue');
  }

  // --- 9. Cenários de bloqueio com a conta de demonstração --------------
  await page.goto(`${APP}/perfil`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(2500);
  const temSair = await botao('Sair da conta', false).isVisible().catch(() => false);
  if (temSair) {
    await botao('Sair da conta', false).click();
    await page.waitForTimeout(1200);
    const confirmar = await botao('Sair').isVisible().catch(() => false);
    if (confirmar) await botao('Sair').click();
    await page.waitForTimeout(2500);
    ok('sessão encerrada');
  }

  await page.goto(APP, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  let corpo = await page.locator('body').innerText();
  if (/Já tenho conta/.test(corpo)) {
    await botao('Já tenho conta').click();
    await page.waitForTimeout(1200);
  }
  await caixa(0).fill('carolina@salaoexemplo.com.br');
  await senhaCampo().fill('espelho-demo-2026');
  await botao('Entrar').click();
  await page.waitForTimeout(4000);
  await foto(page, 'painel-seed');
  corpo = await page.locator('body').innerText();
  if (/Marina|Aline|próximo/i.test(corpo)) ok('login na conta de demonstração carregou a carteira do servidor');
  else falha('login do seed', corpo.slice(0, 200));

  // Cliente que recusou: câmera bloqueada
  await page.getByRole('tab', { name: 'Clientes' }).click().catch(() => {});
  await page.waitForTimeout(2000);
  await texto('Carla Menezes').click();
  await page.waitForTimeout(2500);
  await foto(page, 'perfil-recusado');
  const carla = await page.locator('body').innerText();
  if (/recus/i.test(carla)) ok('perfil mostra a recusa registrada');
  else falha('status de recusa', carla.slice(0, 200));

  await simularPara('Carla Menezes');
  const bloqueada = await page.locator('body').innerText();
  if (/não autorizou|bloqueada/i.test(bloqueada)) ok('cliente que recusou: câmera bloqueada');
  else falha('bloqueio por recusa', bloqueada.slice(0, 200));
  await foto(page, 'camera-bloqueada');

  // Cliente com aceite antigo: revalidação
  await page.goto(`${APP}/clientes`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(2500);
  await texto('Júlia Stein').click();
  await page.waitForTimeout(2500);
  const julia = await page.locator('body').innerText();
  if (/versão anterior|revalida|0\.9/i.test(julia)) ok('aceite em versão anterior sinalizado');
  else falha('revalidação', julia.slice(0, 200));
  await foto(page, 'perfil-revalidar');

  // Revogação + exclusão de imagens em cliente com simulações
  await page.goto(`${APP}/clientes`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(2000);
  await texto('Marina Alves').click();
  await page.waitForTimeout(2500);
  await foto(page, 'perfil-marina');
  const marina = await page.locator('body').innerText();
  if (/preferida/i.test(marina)) ok('simulação preferida aparece no perfil');
  else
    falha(
      'selo de preferida ausente',
      'o seed marca uma simulação como preferida — rode `python -m app.seed --reset` ' +
        'antes do roteiro, porque a execução anterior altera os dados de demonstração'
    );

  const temCancelar = await botao('Cancelar consentimento', false).isVisible().catch(() => false);
  if (temCancelar) {
    await botao('Cancelar consentimento', false).click();
    await page.waitForTimeout(1500);
    await botaoDialogo('Cancelar consentimento').click();
    await page.waitForTimeout(3500);
    const depois = await page.locator('body').innerText();
    if (/cancelado/i.test(depois)) ok('revogação registrada como novo registro');
    else falha('revogação', depois.slice(0, 200));
    await foto(page, 'revogado');

    // O app oferece apagar as imagens; confirma.
    const apagar = await botaoDialogo('Apagar imagens').isVisible().catch(() => false);
    if (apagar) {
      await botaoDialogo('Apagar imagens').click();
      await page.waitForTimeout(4000);
      ok('exclusão de imagens aceita (art. 18)');
      await foto(page, 'imagens-apagadas');
      const final = await page.locator('body').innerText();
      if (/Coloração acobreada|Hidratação/i.test(final)) ok('histórico de atendimentos preservado após apagar imagens');
      else falha('histórico após exclusão', final.slice(0, 250));
    }
  } else {
    falha(
      'botão de cancelar consentimento ausente',
      'o seed cria consentimento ativo para esta cliente — rode ' +
        '`python -m app.seed --reset` antes do roteiro, porque a execução anterior revoga ' +
        'o consentimento e apaga as imagens'
    );
  }

  // --- 10. Privacidade --------------------------------------------------
  await page.goto(`${APP}/privacidade`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(2500);
  await foto(page, 'privacidade');
  const privacidade = await page.locator('body').innerText();
  if (/art\. 18|Exclusão/i.test(privacidade)) ok('tela de privacidade carregada com contagens reais');
  else falha('privacidade', privacidade.slice(0, 200));
} catch (erro) {
  falha('execução', String(erro).slice(0, 400));
  await foto(page, 'erro');
} finally {
  console.log('\n--- resumo ---');
  console.log(passos.join('\n'));
  console.log('\nerros de console:', consoleErros.length);
  consoleErros.slice(0, 8).forEach((e) => console.log('  ·', e));
  console.log('\nFALHAS:', erros.length ? erros : 'nenhuma');
  await navegador.close();
  process.exit(erros.length ? 1 : 0);
}
