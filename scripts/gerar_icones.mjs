// Gera os ícones do Salão em Dia a partir de um único desenho em SVG, com o Chromium do
// Playwright (dependência de desenvolvimento do aplicativo).
//
// Uso, da raiz do repositório:
//   node scripts/gerar_icones.mjs espelho espelho
// Escreve espelho/assets/{icon,android-icon-*,splash-icon,favicon}.png e
// espelho/public/{icon-192,icon-512,apple-touch-icon}.png. O desenho de referência fica em
// espelho/assets/marca.svg; o mesmo símbolo é desenhado na interface por Marca.tsx.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const [saida, raizApp] = process.argv.slice(2);
const require = createRequire(path.resolve(raizApp, 'package.json'));
const { chromium } = require('playwright');

const AMEIXA = '#6B2D5C';
const TINTA = '#1C1620';
const MARFIM = '#FBF7F2';
const CHAMPANHE = '#D9B77E';

/**
 * O símbolo: a folha de uma agenda (corpo marfim, faixa champanhe, duas argolas) com a
 * marca de concluído: "em dia". Desenhado numa grade de 1024, centrado, ocupando a área
 * delimitada por `escala` (1 = 560px de largura).
 */
function simbolo({ escala = 1, mono = false } = {}) {
  const w = 560 * escala;
  const h = 520 * escala;
  const x = 512 - w / 2;
  const y = 512 - h / 2 + 24 * escala;
  const r = 104 * escala;
  const faixa = 136 * escala;
  const corpo = mono ? '#FFFFFF' : MARFIM;
  const corFaixa = mono ? '#FFFFFF' : CHAMPANHE;
  const argW = 52 * escala;
  const argH = 132 * escala;
  const argY = y - 64 * escala;
  const argX1 = 512 - 148 * escala - argW / 2;
  const argX2 = 512 + 148 * escala - argW / 2;
  const traco = 68 * escala;
  const cx = 512;
  const cy = y + faixa + (h - faixa) / 2;
  const p = (dx, dy) => `${cx + dx * escala},${cy + dy * escala}`;
  const marca = `${p(-136, 18)} ${p(-56, 98)} ${p(88, -46)}`;
  // Brilho de quatro pontas: o cuidado com a aparência, ao lado do "em dia".
  const bx = cx + 156 * escala;
  const by = cy - 96 * escala;
  const br = 56 * escala;
  const brilho = `M ${bx} ${by - br} Q ${bx} ${by} ${bx + br} ${by} Q ${bx} ${by} ${bx} ${by + br} Q ${bx} ${by} ${bx - br} ${by} Q ${bx} ${by} ${bx} ${by - br} Z`;
  const id = `s${Math.round(escala * 1000)}${mono ? 'm' : ''}`;
  // No monocromático, "vazado" é transparente: o Android usa só o canal alfa.
  const vazado = mono ? '#000' : AMEIXA;
  const argola = (ax) =>
    `<rect x="${ax}" y="${argY}" width="${argW}" height="${argH}" rx="${argW / 2}" fill="${corpo}" stroke="${vazado}" stroke-width="${20 * escala}"/>`;
  const desenho = `
    <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${corpo}"/>
    ${
      mono
        ? `<rect x="${x}" y="${y + faixa - 9 * escala}" width="${w}" height="${18 * escala}" fill="#000" clip-path="url(#${id}c)"/>`
        : `<rect x="${x}" y="${y}" width="${w}" height="${faixa}" fill="${corFaixa}" clip-path="url(#${id}c)"/>`
    }
    ${argola(argX1)}${argola(argX2)}
    <polyline points="${marca}" fill="none" stroke="${vazado}" stroke-width="${traco}" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="${brilho}" fill="${vazado}"/>
  `;
  const recorte = `<clipPath id="${id}c"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}"/></clipPath>`;
  if (!mono) return `<defs>${recorte}</defs>${desenho}`;
  return `<defs>${recorte}<mask id="${id}m" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024">${desenho}</mask></defs>
    <rect width="1024" height="1024" fill="#FFFFFF" mask="url(#${id}m)"/>`;
}

const svg = (conteudo, fundo) => `<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  ${fundo ? `<rect width="1024" height="1024" fill="${fundo}"/>` : ''}
  ${conteudo}
</svg>`;

const ARQUIVOS = {
  // iOS e lojas: quadrado cheio, sem transparência. O sistema arredonda os cantos.
  'icon.png': { svg: svg(simbolo({ escala: 1.1 }), AMEIXA), tamanho: 1024 },
  // Android adaptativo: o primeiro plano precisa caber no círculo seguro (66% do quadro).
  'android-icon-foreground.png': { svg: svg(simbolo({ escala: 0.78 })), tamanho: 1024 },
  'android-icon-background.png': { svg: svg('', AMEIXA), tamanho: 1024 },
  'android-icon-monochrome.png': { svg: svg(simbolo({ escala: 0.78, mono: true })), tamanho: 1024 },
  // Abertura do app: só o símbolo, sobre a cor de fundo definida no app.json.
  'splash-icon.png': { svg: svg(simbolo({ escala: 1 })), tamanho: 1024 },
  // Navegador: favicon com fundo, para não sumir em abas escuras ou claras.
  'favicon.png': { svg: svg(`<rect x="0" y="0" width="1024" height="1024" rx="224" fill="${AMEIXA}"/>${simbolo({ escala: 1.18 })}`), tamanho: 48 },
};

// PWA e atalho na tela inicial (web): ícones quadrados cheios.
const WEB = {
  'icon-192.png': { svg: ARQUIVOS['icon.png'].svg, tamanho: 192 },
  'icon-512.png': { svg: ARQUIVOS['icon.png'].svg, tamanho: 512 },
  'apple-touch-icon.png': { svg: ARQUIVOS['icon.png'].svg, tamanho: 180 },
  // "maskable": o Android recorta em círculo; o símbolo fica na zona segura de 80%.
  'icon-maskable-512.png': { svg: svg(simbolo({ escala: 0.78 }), AMEIXA), tamanho: 512 },
};

const navegador = await chromium.launch();
const pagina = await navegador.newPage();
async function render(svgTexto, tamanho, destino, transparente) {
  await pagina.setViewportSize({ width: tamanho, height: tamanho });
  const dados = Buffer.from(svgTexto).toString('base64');
  await pagina.setContent(
    `<html><body style="margin:0;background:transparent"><img src="data:image/svg+xml;base64,${dados}" width="${tamanho}" height="${tamanho}" style="display:block"></body></html>`
  );
  await pagina.screenshot({ path: destino, omitBackground: transparente, clip: { x: 0, y: 0, width: tamanho, height: tamanho } });
}

fs.mkdirSync(path.join(saida, 'assets'), { recursive: true });
fs.mkdirSync(path.join(saida, 'public'), { recursive: true });
for (const [nome, { svg: s, tamanho }] of Object.entries(ARQUIVOS)) {
  await render(s, tamanho, path.join(saida, 'assets', nome), true);
}
for (const [nome, { svg: s, tamanho }] of Object.entries(WEB)) {
  await render(s, tamanho, path.join(saida, 'public', nome), false);
}
fs.writeFileSync(path.join(saida, 'assets', 'marca.svg'), ARQUIVOS['icon.png'].svg);
await navegador.close();
console.log('ok');
