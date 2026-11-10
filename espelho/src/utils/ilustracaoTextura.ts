/**
 * Desenho de cada tipo de cabelo, como mechas vistas de perto (função pura, sem interface).
 *
 * Por que desenho, e não foto: as 12 fotos precisariam mostrar o mesmo enquadramento, a
 * mesma luz e a textura certa de cada subtipo, com licença para uso no aplicativo. Um banco
 * de imagens não garante as três coisas, e uma foto errada ensina o tipo errado. O desenho
 * sai de uma regra só, com o mesmo enquadramento e a mesma cor em todos os tipos: muda
 * apenas o que distingue um tipo do outro (o formato do fio, o tamanho da onda ou do cacho,
 * a espessura, a densidade e o encolhimento). Ocupa poucos bytes e não depende de rede.
 *
 * Cada mecha é uma curva:
 * - liso: reta (o 1C dobra de leve na ponta);
 * - ondulado: senoide, com amplitude maior e onda mais curta de 2A a 2C;
 * - cacheado e 4A: trocoide (o traço de um ponto num círculo que rola), que desenha laços
 *   como uma espiral vista de lado; o raio e o passo diminuem de 3A a 4A;
 * - 4B e 4C: zigue-zague de ângulos agudos, mais fechado e mais curto (encolhimento) no 4C.
 */

import type { Textura } from '@/data/tipos';

/** Área do desenho: quadrado de 72 por 72. */
export const LADO = 72;
const RAIZ = 7;

export type Mecha = { d: string; espessura: number; tom: number };

type Regra =
  | { forma: 'reta'; fios: number; espessura: number; comprimento: number; dobra?: number }
  | { forma: 'onda'; fios: number; espessura: number; comprimento: number; amplitude: number; onda: number }
  | { forma: 'cacho'; fios: number; espessura: number; comprimento: number; raio: number; passo: number }
  | { forma: 'zigue'; fios: number; espessura: number; comprimento: number; amplitude: number; passo: number };

/** O que distingue cada tipo. Tamanhos em unidades do quadrado de 72. */
const REGRAS: Record<Exclude<Textura, 'liso' | 'ondulado' | 'cacheado' | 'crespo'>, Regra> = {
  '1A': { forma: 'reta', fios: 9, espessura: 1.1, comprimento: 58 },
  '1B': { forma: 'reta', fios: 7, espessura: 1.9, comprimento: 58 },
  '1C': { forma: 'onda', fios: 6, espessura: 2.8, comprimento: 58, amplitude: 1.1, onda: 64 },
  '2A': { forma: 'onda', fios: 6, espessura: 2, comprimento: 58, amplitude: 2, onda: 32 },
  '2B': { forma: 'onda', fios: 5, espessura: 2.2, comprimento: 57, amplitude: 3.6, onda: 22 },
  '2C': { forma: 'onda', fios: 5, espessura: 2.4, comprimento: 55, amplitude: 4.8, onda: 15 },
  '3A': { forma: 'cacho', fios: 3, espessura: 2.2, comprimento: 54, raio: 6.6, passo: 2.5 },
  '3B': { forma: 'cacho', fios: 4, espessura: 2, comprimento: 50, raio: 4.6, passo: 1.6 },
  '3C': { forma: 'cacho', fios: 5, espessura: 1.8, comprimento: 46, raio: 3.3, passo: 1.05 },
  '4A': { forma: 'cacho', fios: 6, espessura: 1.6, comprimento: 42, raio: 2.4, passo: 0.72 },
  '4B': { forma: 'zigue', fios: 6, espessura: 1.7, comprimento: 38, amplitude: 3, passo: 3.2 },
  '4C': { forma: 'zigue', fios: 8, espessura: 1.8, comprimento: 30, amplitude: 2.3, passo: 2 },
};

/** A categoria mostra um fio de cada tipo dela, lado a lado: dá a ideia da família toda. */
const TIPOS_DA_CATEGORIA = {
  liso: ['1A', '1B', '1C'],
  ondulado: ['2A', '2B', '2C'],
  cacheado: ['3A', '3B', '3C'],
  crespo: ['4A', '4B', '4C'],
} as const;

const n = (valor: number) => Number(valor.toFixed(1));

function caminho(pontos: [number, number][]): string {
  return pontos.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${n(x)} ${n(y)}`).join(' ');
}

/** Uma mecha da regra, com o centro em `x`. `fase` evita que as mechas fiquem idênticas. */
function mecha(regra: Regra, x: number, fase: number): string {
  const fim = RAIZ + regra.comprimento;
  switch (regra.forma) {
    case 'reta': {
      if (!regra.dobra) return `M${n(x)} ${RAIZ} L${n(x)} ${n(fim)}`;
      const lado = fase % 2 === 0 ? 1 : -1;
      return `M${n(x)} ${RAIZ} L${n(x)} ${n(fim - 12)} Q${n(x)} ${n(fim - 2)} ${n(x + lado * regra.dobra)} ${n(fim)}`;
    }
    case 'onda': {
      const pontos: [number, number][] = [];
      for (let y = RAIZ; y <= fim; y += 1) {
        pontos.push([x + regra.amplitude * Math.sin(((y - RAIZ) / regra.onda) * 2 * Math.PI + fase), y]);
      }
      return caminho(pontos);
    }
    case 'cacho': {
      // Trocoide em pé: ao longo do fio, avança `passo * t` e recua `raio * sen(t)`; de lado,
      // vai e volta `raio * cos(t)`. Com raio maior que o passo, o traço dá laços.
      const pontos: [number, number][] = [];
      // O laço passa até um raio abaixo do ponto em que está: desconta para caber no quadro.
      const total = (regra.comprimento - regra.raio) / regra.passo;
      for (let t = 0; t <= total; t += 0.12) {
        const y = RAIZ + regra.passo * t - regra.raio * Math.sin(t + fase) + regra.raio * Math.sin(fase);
        pontos.push([x + regra.raio * Math.cos(t + fase), Math.max(RAIZ, y)]);
      }
      return caminho(pontos);
    }
    case 'zigue': {
      const pontos: [number, number][] = [[x, RAIZ]];
      let lado = fase % 2 === 0 ? 1 : -1;
      for (let y = RAIZ + regra.passo / 2; y <= fim; y += regra.passo) {
        pontos.push([x + lado * regra.amplitude, y]);
        lado = -lado;
      }
      return caminho(pontos);
    }
  }
}

function distribuir(fios: number, folga: number): number[] {
  const inicio = folga;
  const fim = LADO - folga;
  if (fios === 1) return [LADO / 2];
  return Array.from({ length: fios }, (_, i) => inicio + ((fim - inicio) * i) / (fios - 1));
}

/** As mechas do desenho de um tipo de cabelo, ou de uma categoria (um fio de cada tipo). */
export function mechasDaTextura(textura: Textura): Mecha[] {
  if (textura in TIPOS_DA_CATEGORIA) {
    const tipos = TIPOS_DA_CATEGORIA[textura as keyof typeof TIPOS_DA_CATEGORIA];
    return tipos.map((tipo, i) => {
      const regra = REGRAS[tipo];
      return { d: mecha(regra, 16 + i * 20, i), espessura: Math.max(regra.espessura, 2), tom: i % 3 };
    });
  }
  const regra = REGRAS[textura as keyof typeof REGRAS];
  const folga = regra.forma === 'cacho' ? regra.raio + 6 : regra.forma === 'onda' ? regra.amplitude + 8 : 10;
  return distribuir(regra.fios, folga).map((x, i) => ({ d: mecha(regra, x, i * 1.3), espessura: regra.espessura, tom: i % 3 }));
}
