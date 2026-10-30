/**
 * Verifica no navegador as mudanças desta etapa:
 *
 *  1-2  tela Clientes: "DE A a Z", sem contagem de simulações, selos "uso de imagem ...";
 *  3    foto do cliente: uma foto grande (18 MB, acima do limite de envio) é reduzida no
 *       aparelho e salva; aparece no perfil; "Remover foto" remove (conferido na API);
 *  4    foto do profissional em Meus dados: adicionar, aparecer no Perfil, remover;
 *  5    câmera sem permissão: botão "Liberar câmera" centralizado;
 *  6    câmera: sem "Luz de frente"; sem rosto, pede para enquadrar; com um rosto no
 *       vídeo da câmera, o servidor confirma e aparece "Rosto dentro do guia";
 *  7    histórico: sem "Agendado para", com "Marcado pela agenda";
 *  8    simulação: resultado, foto original e lado a lado;
 *  9    com a foto escolhida, a câmera fica na pilha mas fora de vista: a conferência do
 *       enquadramento para; de volta à câmera, religa.
 *
 * Pré-requisitos: API e `expo start --web` no ar, carga de demonstração recriada. As mídias
 * de teste são geradas na hora por `e2e/gerar_midia.py` (Python do backend).
 */
import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://localhost:8081';
const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';
const TELAS = path.join(AQUI, 'telas-fotos');
fs.mkdirSync(TELAS, { recursive: true });
const MIDIA = fs.mkdtempSync(path.join(os.tmpdir(), 'midia-e2e-'));
execFileSync(path.join(AQUI, '..', '..', 'backend', '.venv', 'bin', 'python'), [path.join(AQUI, 'gerar_midia.py'), MIDIA]);
const FOTO_GRANDE = path.join(MIDIA, 'foto-grande.jpg');
const VIDEO_COM_ROSTO = path.join(MIDIA, 'camera-com-rosto.mjpeg');
const RETRATO = path.join(AQUI, 'retrato-sintetico.jpg');

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
const clientes = await api('/clientes');
const marina = clientes.find((c) => c.nome.startsWith('Marina'));
const bruno = clientes.find((c) => c.nome.startsWith('Bruno'));

async function abrir(args = []) {
  const navegador = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', ...args] });
  // Com a câmera de mentira, a permissão também é concedida no contexto. Desde o Chromium
  // 141, aceitar o vídeo (--use-fake-ui-for-media-stream) não muda mais o estado que
  // `navigator.permissions` informa, e a câmera do Expo na web decide por ele: sem isto, a
  // tela ficava em "Câmera não liberada" (o código anterior falhava igual neste navegador).
  const permissions = args.some((a) => a.includes('fake-ui')) ? ['camera'] : [];
  const contexto = await navegador.newContext({ viewport: { width: 390, height: 844 }, locale: 'pt-BR', timezoneId: 'America/Sao_Paulo', permissions });
  const page = await contexto.newPage();
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.getByRole('textbox').filter({ visible: true }).first().fill(EMAIL);
  await page.locator('input[type="password"]:visible').first().fill(SENHA);
  await page.getByRole('button', { name: /^Entrar$/ }).filter({ visible: true }).first().click();
  await page.waitForTimeout(4000);
  return { navegador, contexto, page };
}
const ferramentas = (page) => ({
  botao: (nome) => page.getByRole('button', { name: nome }).filter({ visible: true }).first(),
  corpo: () => page.locator('body').innerText(),
  espera: (ms = 1200) => page.waitForTimeout(ms),
  foto: (nome) => page.screenshot({ path: `${TELAS}/${nome}.png` }),
});
/** Largura e altura de um JPEG, lidas do cabeçalho (marcador SOF). */
function larguraAlturaJpeg(dados) {
  let i = 2;
  while (i < dados.length) {
    const marcador = dados[i + 1];
    const tamanho = dados.readUInt16BE(i + 2);
    if (marcador >= 0xc0 && marcador <= 0xc3) return [dados.readUInt16BE(i + 7), dados.readUInt16BE(i + 5)];
    i += 2 + tamanho;
  }
  return null;
}

async function escolherArquivo(page, rotulo, arquivo) {
  const [seletor] = await Promise.all([
    page.waitForEvent('filechooser', { timeout: 15000 }),
    page.getByRole('button', { name: rotulo }).filter({ visible: true }).first().click(),
  ]);
  await seletor.setFiles(arquivo);
}

let atual;
try {
  // ===================================================== telas sem câmera
  atual = await abrir();
  {
    const { page } = atual;
    const { botao, corpo, espera, foto } = ferramentas(page);

    // --- 1 e 2: Clientes ---------------------------------------------------------
    await page.goto(`${APP}/clientes`, { waitUntil: 'networkidle' });
    await espera(2500);
    const tela = await corpo();
    conferir(/CLIENTES · DE A a Z/.test(tela), '1. a lista mostra "DE A a Z" com o "a" do meio minúsculo', tela.slice(0, 200));
    conferir(!/\d+ simulaç(ão|ões)/.test(tela), '2. a lista não mostra mais a quantidade de simulações', '');
    conferir(/uso de imagem autorizado/.test(tela) && /uso de imagem pendente/.test(tela) && /uso de imagem recusado/.test(tela), '2. os selos dizem "uso de imagem autorizado/pendente/recusado"', tela.slice(0, 600));
    await foto('01-clientes');

    // --- 3: foto do cliente --------------------------------------------------------
    await page.goto(`${APP}/cliente/editar?id=${bruno.id}`, { waitUntil: 'networkidle' });
    await espera(2500);
    const respostas = [];
    page.on('response', (r) => {
      if (/\/clientes\/[^/]+\/foto$/.test(new URL(r.url()).pathname)) respostas.push(r);
    });
    await escolherArquivo(page, 'Adicionar foto', FOTO_GRANDE);
    await espera(1500);
    await botao(/^Salvar/).click();
    await espera(5000);
    {
      const envio = respostas.find((r) => r.request().method() === 'POST');
      // Passar pelo servidor já indica a redução: 18 MB excedem o limite de 12 MB por envio.
      conferir(envio && envio.status() === 200, '3. a foto grande (18 MB) foi enviada e aceita pelo servidor', envio ? envio.status() : 'nenhum envio');
      const doServidor = (await api(`/clientes/${bruno.id}`)).fotoUri;
      const dimensoes = doServidor ? larguraAlturaJpeg(Buffer.from(await (await fetch(doServidor)).arrayBuffer())) : null;
      conferir(
        dimensoes && Math.max(...dimensoes) <= 1024,
        `3. a foto foi reduzida no aparelho antes do envio (salva com ${dimensoes?.join('x')} px; o original tem 4000x4000)`,
        JSON.stringify(dimensoes)
      );
      conferir(!!doServidor, '3. a foto ficou salva no cliente (API)', '');
      const temImagem = await page.evaluate(() => [...document.querySelectorAll('img')].some((i) => i.src.includes('/api/v1/imagens/') && i.naturalWidth > 0));
      conferir(/\/cliente\//.test(page.url()) && temImagem, '3. a foto aparece no perfil do cliente', page.url());
      conferir(!/Sem conexão/.test(await corpo()), '3. nenhum aviso de "Sem conexão"', '');
      await foto('02-perfil-com-foto');
    }
    await page.goto(`${APP}/cliente/editar?id=${bruno.id}`, { waitUntil: 'networkidle' });
    await espera(2500);
    conferir(/Remover foto/.test(await corpo()), '3. o cadastro oferece "Remover foto"', '');
    await botao('Remover foto').click();
    await espera(500);
    await botao(/^Salvar/).click();
    await espera(3500);
    conferir((await api(`/clientes/${bruno.id}`)).fotoUri === null, '3. "Remover foto" remove a foto (API)', '');

    // --- 4: foto do profissional -----------------------------------------------------
    await page.goto(`${APP}/meus-dados`, { waitUntil: 'networkidle' });
    await espera(2500);
    await escolherArquivo(page, 'Adicionar foto', FOTO_GRANDE);
    await espera(5000);
    conferir(!!(await api('/usuarios/me')).fotoUri, '4. a foto do profissional foi salva (API)', '');
    conferir(/Foto atualizada/.test(await corpo()) || /Trocar foto/.test(await corpo()), '4. a tela confirma e passa a oferecer "Trocar foto"', '');
    await foto('03-meus-dados-com-foto');
    await page.goto(`${APP}/perfil`, { waitUntil: 'networkidle' });
    await espera(2500);
    const noPerfil = await page.evaluate(() => [...document.querySelectorAll('img')].some((i) => i.src.includes('/api/v1/imagens/') && i.naturalWidth > 0));
    conferir(noPerfil, '4. a foto aparece no Perfil', '');
    await foto('04-perfil-profissional');
    await page.goto(`${APP}/meus-dados`, { waitUntil: 'networkidle' });
    await espera(2500);
    await botao('Remover foto').click();
    await espera(700);
    conferir(/Remover sua foto\?/.test(await corpo()), '4. remover pede confirmação', '');
    // O botão do diálogo tem o mesmo nome do botão da tela: o do diálogo é o último.
    await page.getByRole('button', { name: 'Remover foto' }).filter({ visible: true }).last().click();
    await espera(2500);
    conferir((await api('/usuarios/me')).fotoUri === null, '4. a foto do profissional foi removida (API)', '');

    // --- 7: histórico ------------------------------------------------------------------
    await page.goto(`${APP}/cliente/${bruno.id}`, { waitUntil: 'networkidle' });
    await espera(2500);
    {
      const perfil = await corpo();
      conferir(/Marcado pela agenda/.test(perfil) && !/Agendado para/.test(perfil), '7. o histórico mostra a origem, sem "Agendado para"', perfil.slice(-500));
      await foto('05-historico');
    }

    // --- 8: foto original da simulação -------------------------------------------------
    const simulacao = (await api(`/clientes/${marina.id}/simulacoes`))[0];
    await page.goto(`${APP}/simulacao/imagem/${simulacao.id}`, { waitUntil: 'networkidle' });
    await espera(2500);
    const imagens = () =>
      page.evaluate(() =>
        [...document.querySelectorAll('img')]
          .filter((i) => i.src.includes('/api/v1/imagens/') && i.naturalWidth > 0 && i.getBoundingClientRect().width > 50)
          .map((i) => new URL(i.src).pathname)
      );
    const idDe = (uri) => new URL(uri).pathname;
    conferir((await imagens()).includes(idDe(simulacao.imgSaidaUri)), '8. abre mostrando a simulação', JSON.stringify(await imagens()));
    await page.getByRole('tab', { name: 'Foto original' }).click();
    await espera(1500);
    conferir((await imagens()).includes(idDe(simulacao.imgEntradaUri)), '8. "Foto original" mostra a foto usada na simulação', JSON.stringify(await imagens()));
    await foto('06-foto-original');
    await page.getByRole('tab', { name: 'Lado a lado' }).click();
    await espera(1500);
    {
      const vistas = await imagens();
      conferir(vistas.includes(idDe(simulacao.imgEntradaUri)) && vistas.includes(idDe(simulacao.imgSaidaUri)), '8. "Lado a lado" mostra as duas juntas', JSON.stringify(vistas));
      conferir(/ANTES/.test(await corpo()) && /DEPOIS/.test(await corpo()), '8. lado a lado identifica antes e depois', '');
      await foto('07-lado-a-lado');
    }
  }
  await atual.navegador.close();

  // ===================================================== câmera sem permissão
  atual = await abrir();
  {
    const { page } = atual;
    const { espera, foto } = ferramentas(page);
    await page.goto(`${APP}/simulacao/cliente`, { waitUntil: 'networkidle' });
    await espera(2500);
    await page.getByRole('button', { name: /^Simular para Marina/ }).first().click();
    await espera(3500);
    const m = await page.evaluate(() => {
      const b = [...document.querySelectorAll('[role="button"]')].find((e) => e.textContent.trim() === 'Liberar câmera');
      const t = [...document.querySelectorAll('div')].find((e) => e.textContent.trim() === 'Câmera não liberada');
      if (!b || !t) return null;
      const r = b.getBoundingClientRect();
      const c = t.getBoundingClientRect();
      return { botao: (r.left + r.right) / 2, titulo: (c.left + c.right) / 2 };
    });
    conferir(m && Math.abs(m.botao - m.titulo) <= 1.5, '5. "Liberar câmera" centralizado', JSON.stringify(m));
    await foto('08-camera-sem-permissao');
  }
  await atual.navegador.close();

  // ===================================================== câmera sem rosto
  atual = await abrir(['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream']);
  {
    const { page } = atual;
    const { corpo, espera, foto } = ferramentas(page);
    const conferencias = [];
    page.on('response', async (r) => {
      if (r.url().includes('/simulacoes/enquadramento')) conferencias.push(await r.json().catch(() => null));
    });
    await page.goto(`${APP}/simulacao/cliente`, { waitUntil: 'networkidle' });
    await espera(2500);
    await page.getByRole('button', { name: /^Simular para Marina/ }).first().click();
    await espera(7000);
    const tela = await corpo();
    conferir(!/Luz de frente/.test(tela), '6. o aviso "Luz de frente" saiu', '');
    conferir(/Enquadre o rosto no guia para um melhor resultado/.test(tela) && !/Rosto dentro do guia/.test(tela), '6. sem rosto no vídeo, pede para enquadrar (e não confirma)', tela.slice(0, 300));
    conferir(conferencias.length >= 2 && conferencias.every((c) => c && c.rostoNoGuia === false), `6. a tela consulta o servidor ao vivo (${conferencias.length} conferências, todas sem rosto)`, JSON.stringify(conferencias));
    await foto('09-camera-sem-rosto');

    // A tela da câmera continua montada na pilha depois que a foto segue adiante. Antes,
    // ela seguia tirando miniaturas e chamando o servidor durante todo o pedido.
    const escolha = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: /Escolher foto da galeria/ }).filter({ visible: true }).first().click();
    await (await escolha).setFiles(RETRATO);
    await espera(2500);
    conferir(/Estilo e cor/.test(await corpo()), '9. a foto da galeria leva a "Estilo e cor"', (await corpo()).slice(0, 200));
    const aoSair = conferencias.length;
    await espera(6000);
    const foraDeVista = conferencias.length - aoSair;
    conferir(foraDeVista === 0, `9. com a câmera fora de vista, nenhuma conferência de enquadramento (${foraDeVista} em 6 s)`, foraDeVista);
    await page.getByRole('button', { name: 'Voltar', exact: true }).filter({ visible: true }).first().click();
    await espera(5000);
    const deVolta = conferencias.length - aoSair - foraDeVista;
    conferir(
      /Enquadre o rosto no guia/.test(await corpo()) && deVolta >= 2,
      `9. de volta à câmera, a conferência religa (${deVolta} conferências em 5 s)`,
      deVolta
    );
  }
  await atual.navegador.close();

  // ===================================================== câmera com rosto
  atual = await abrir(['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', `--use-file-for-fake-video-capture=${VIDEO_COM_ROSTO}`]);
  {
    const { page } = atual;
    const { corpo, espera, foto } = ferramentas(page);
    await page.goto(`${APP}/simulacao/cliente`, { waitUntil: 'networkidle' });
    await espera(2500);
    await page.getByRole('button', { name: /^Simular para Marina/ }).first().click();
    let confirmou = false;
    for (let i = 0; i < 12 && !confirmou; i++) {
      await espera(1000);
      confirmou = /Rosto dentro do guia/.test(await corpo());
    }
    conferir(confirmou, '6. com um rosto centralizado no vídeo, o servidor confirma "Rosto dentro do guia"', (await corpo()).slice(0, 300));
    await foto('10-camera-com-rosto');
  }
} catch (e) {
  falha('execução', e instanceof Error ? e.message.split('\n')[0] : String(e));
  await atual?.page.screenshot({ path: `${TELAS}/erro.png` }).catch(() => undefined);
} finally {
  await atual?.navegador.close().catch(() => undefined);
  fs.rmSync(MIDIA, { recursive: true, force: true });
}

console.log(`\n${passos.length - erros.length} verificações ok, ${erros.length} falhas`);
fs.writeFileSync(path.join(TELAS, 'resultado.txt'), passos.join('\n') + '\n');
process.exit(erros.length ? 1 : 0);
