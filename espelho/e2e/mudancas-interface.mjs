/**
 * Verifica, no navegador, as mudanças de fluxo e de interface desta etapa.
 *
 * Cada bloco corresponde a um critério de aceitação: ícone da simulação, horário
 * digitado, Início sem ações duplicadas, entrada única da simulação, ação contextual do
 * termo, visualização individual separada da comparação, e a opção "Outro".
 *
 * Precisa da API e do `expo start --web` no ar, com a carga de demonstração recriada.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const TELAS = path.join(AQUI, 'telas-mudancas');
fs.mkdirSync(TELAS, { recursive: true });

const EMAIL = 'carolina@salaoexemplo.com.br';
const SENHA = 'espelho-demo-2026';

const passos = [];
const erros = [];
let n = 0;

const ok = (d, extra = '') => {
  passos.push(`[ok ] ${d}${extra ? ` — ${extra}` : ''}`);
  console.log(passos.at(-1));
};
const falha = (d, detalhe) => {
  passos.push(`[FALHA] ${d} — ${detalhe}`);
  erros.push(`${d}: ${detalhe}`);
  console.log(passos.at(-1));
};

const navegador = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--no-sandbox'],
});
const contexto = await navegador.newContext({ viewport: { width: 420, height: 900 }, locale: 'pt-BR' });
const page = await contexto.newPage();
const consoleErros = [];
page.on('console', (m) => {
  if (m.type() === 'error' || m.type() === 'warning') consoleErros.push(`${m.type()}: ${m.text().slice(0, 200)}`);
});

const botao = (nome, exato = false) =>
  page.getByRole('button', { name: nome, exact: exato }).filter({ visible: true }).first();
const texto = (t) => page.getByText(t, { exact: false }).filter({ visible: true }).first();
const foto = async (nome) => {
  n += 1;
  await page.screenshot({ path: `${TELAS}/${String(n).padStart(2, '0')}-${nome}.png` });
};
const corpo = () => page.locator('body').innerText();

try {
  // --- entrar ------------------------------------------------------------
  await page.goto(APP, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  if (/Já tenho conta/.test(await corpo())) {
    await botao('Já tenho conta').click();
    await page.waitForTimeout(1200);
  }
  await page.getByRole('textbox').filter({ visible: true }).first().fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await botao('Entrar').click();
  await page.waitForTimeout(4000);
  await foto('inicio');

  // --- 2.3: Início sem ações duplicadas ----------------------------------
  {
    const inicio = await corpo();
    const temSimular = /\bSimular\b/.test(inicio);
    const temRegistrar = /\bRegistrar\b/.test(inicio);
    const temAtalhoSimulacao = /Escolher cliente, fotografar/.test(inicio);
    const temVerAgenda = /Ver agenda/.test(inicio);

    if (!temSimular && !temRegistrar) ok('cartão do próximo atendimento sem Simular e sem Registrar');
    else falha('ações do cartão', `Simular=${temSimular} Registrar=${temRegistrar}`);

    if (!temAtalhoSimulacao) ok('atalho duplicado de nova simulação removido do Início');
    else falha('atalho de simulação', 'ainda presente na tela Início');

    if (!temVerAgenda) ok('botão "Ver agenda" removido (a aba já está na barra inferior)');
    else falha('ver agenda', 'ainda presente');

    const temPerfil = /Ver perfil do cliente/.test(inicio);
    const semProximo = /Nenhum atendimento à frente/.test(inicio);
    if (temPerfil || semProximo) ok('o cartão mantém a ação de abrir o perfil');
    else falha('ação do cartão', 'nem perfil nem estado sem próximo atendimento');
  }

  // --- 2.4: entrada única da simulação -----------------------------------
  {
    await page.goto(`${APP}/(tabs)/clientes`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await texto('Marina').click();
    await page.waitForTimeout(2500);
    await foto('perfil');
    const perfil = await corpo();

    if (!/Nova simulação/.test(perfil)) ok('perfil não oferece mais iniciar simulação');
    else falha('entrada da simulação', 'o perfil ainda tem "Nova simulação"');

    if (/Simulações salvas/.test(perfil)) ok('perfil mantém as simulações já salvas');
    else falha('simulações salvas', 'seção ausente');

    // A entrada existe na barra inferior, a partir das abas.
    await page.goto(`${APP}/(tabs)`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    const visivel = await botao('Nova simulação').isVisible().catch(() => false);
    if (visivel) ok('a barra inferior mantém o botão de simulação');
    else falha('barra inferior', 'botão de simulação não encontrado');

    await botao('Nova simulação').click();
    await page.waitForTimeout(2500);
    await foto('escolher-cliente');
    if (/cliente/i.test(await corpo())) ok('a simulação começa pedindo o cliente');
    else falha('escolha de cliente', 'tela não pediu o cliente');
  }

  // --- 2.5: ação contextual do termo -------------------------------------
  {
    // Marina aceitou: a ação tem de ser consultar.
    await page.goto(`${APP}/(tabs)/clientes`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await texto('Marina').click();
    await page.waitForTimeout(2500);
    const comAceite = await corpo();
    const temVer = /Ver termo/.test(comAceite);
    const temApresentar = /Apresentar ao cliente/.test(comAceite);
    const temResponder = /Responder ao termo/.test(comAceite);
    if (temVer && !temApresentar && !temResponder) {
      ok('cliente com decisão registrada: só "Ver termo"');
    } else {
      falha('ação do termo (com decisão)', `ver=${temVer} apresentar=${temApresentar} responder=${temResponder}`);
    }

    // Beatriz nunca respondeu: a ação tem de ser responder.
    await page.goto(`${APP}/(tabs)/clientes`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    const semDecisao = await page.getByText(/pendente/i).filter({ visible: true }).first();
    await semDecisao.click().catch(() => {});
    await page.waitForTimeout(2500);
    await foto('perfil-pendente');
    const pendente = await corpo();
    if (/Responder ao termo/.test(pendente) && !/Apresentar ao cliente/.test(pendente)) {
      ok('cliente sem decisão: só "Responder ao termo"');
    } else if (/Ver termo/.test(pendente) && !/Responder ao termo/.test(pendente)) {
      falha('ação do termo (sem decisão)', 'ofereceu "Ver termo" para quem não respondeu');
    } else {
      falha('ação do termo (sem decisão)', pendente.slice(0, 160).replace(/\n/g, ' '));
    }
  }

  // --- 2.6: imagem individual e comparação separadas ----------------------
  {
    await page.goto(`${APP}/(tabs)/clientes`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await texto('Marina').click();
    await page.waitForTimeout(3000);

    const temComparar = /Comparar simulações/.test(await corpo());
    if (temComparar) ok('perfil oferece "Comparar simulações" como ação explícita');
    else falha('comparar', 'ação não encontrada no perfil');

    // Tocar na miniatura tem de abrir a imagem, não a comparação.
    const miniatura = page.getByRole('button', { name: /Abrir a simulação/i }).filter({ visible: true }).first();
    const achou = await miniatura.isVisible().catch(() => false);
    if (achou) {
      await miniatura.click();
      await page.waitForTimeout(2500);
      await foto('simulacao-individual');
      const aberta = await corpo();
      const ehComparacao = /comparar simulações/i.test(aberta) && /à esquerda/i.test(aberta);
      if (!ehComparacao && /gerada em|situação/i.test(aberta)) {
        ok('tocar na miniatura abre a imagem individual, não a comparação');
      } else {
        falha('visualização individual', aberta.slice(0, 160).replace(/\n/g, ' '));
      }
      // Volta pelo caminho do usuário, e não por histórico do navegador: o botão de
      // voltar do cabeçalho é o que existe no aparelho.
      await botao('Voltar').click().catch(() => {});
      await page.waitForTimeout(1500);
      const voltou = /Simulações salvas/.test(await corpo());
      if (voltou) ok('o botão voltar da imagem retorna ao perfil');
      else falha('retorno da imagem', 'não voltou ao perfil');
    } else {
      falha('miniatura', 'nenhuma simulação clicável no perfil');
    }

    if (!/Comparar simulações/.test(await corpo())) {
      await page.goto(`${APP}/(tabs)/clientes`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(2500);
      await texto('Marina').click();
      await page.waitForTimeout(3000);
    }
    // O nome acessível do botão é mais descritivo que o rótulo visível
    // ("Comparar duas simulações de X lado a lado"), então procura-se pelo começo.
    await page.getByRole('button', { name: /^Comparar/i }).filter({ visible: true }).first().click();
    await page.waitForTimeout(2500);
    await foto('comparacao');
    const comparacao = await corpo();
    if (/à esquerda/i.test(comparacao) && /à direita/i.test(comparacao)) {
      ok('comparação permite escolher as duas posições');
    } else if (/Ainda não há o que comparar/.test(comparacao)) {
      ok('comparação explica o que falta quando não há duas simulações');
    } else {
      falha('comparação', comparacao.slice(0, 160).replace(/\n/g, ' '));
    }
  }

  // --- 2.2 e 2.8: horário digitado e serviço "Outro" ----------------------
  {
    await page.goto(`${APP}/agendamento/novo`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await foto('agendamento');
    const formulario = await corpo();

    if (/Outro/.test(formulario)) ok('"Outro" aparece entre os serviços previstos');
    else falha('serviço Outro', 'opção não encontrada');

    const campoHora = page.locator('input[placeholder="HH:MM"]').first();
    const temCampo = await campoHora.isVisible().catch(() => false);
    if (temCampo) ok('o horário é um campo digitável no formato HH:MM');
    else falha('campo de hora', 'campo digitável não encontrado');

    if (temCampo) {
      await campoHora.fill('');
      await campoHora.type('2599');
      await page.waitForTimeout(800);
      const invalido = await corpo();
      if (/Horário inválido/.test(invalido)) ok('horário fora da faixa é recusado com mensagem clara');
      else falha('validação de hora', invalido.slice(0, 160).replace(/\n/g, ' '));

      await campoHora.fill('');
      await campoHora.type('09');
      await page.waitForTimeout(800);
      if (/Horário incompleto/.test(await corpo())) ok('horário incompleto é apontado como incompleto');
      else falha('validação de hora incompleta', 'mensagem não apareceu');

      await campoHora.fill('');
      await campoHora.type('0930');
      await page.waitForTimeout(800);
      const valido = await corpo();
      const valorAtual = await campoHora.inputValue();
      if (valorAtual === '09:30' && !/Horário inválido|Horário incompleto/.test(valido)) {
        ok('horário válido é aceito e formatado', valorAtual);
      } else {
        falha('horário válido', `valor=${valorAtual}`);
      }
    }

    await botao('Outro').click();
    await page.waitForTimeout(1000);
    if (/qual serviço/i.test(await corpo())) ok('"Outro" abre o campo para descrever o serviço');
    else falha('descrição do Outro', 'campo não apareceu');
  }

  // --- console -----------------------------------------------------------
  {
    const relevantes = consoleErros.filter((m) => !/ERR_CONNECTION|Failed to fetch|net::ERR/i.test(m));
    if (relevantes.length === 0) ok('nenhum erro ou aviso relevante no console');
    else falha('console', relevantes.join(' | ').slice(0, 400));
  }
} catch (erro) {
  falha('exceção na bateria', String(erro).slice(0, 300));
} finally {
  await navegador.close();
}

console.log('\n--- resumo ---');
console.log(passos.join('\n'));
console.log('\nFALHAS:', erros.length ? erros : 'nenhuma');
process.exit(erros.length ? 1 : 0);
