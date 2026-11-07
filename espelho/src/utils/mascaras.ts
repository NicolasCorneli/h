/** Máscaras aplicadas enquanto o usuário digita, para evitar erro de formato. */

const digitos = (texto: string) => texto.replace(/\D/g, '');

/** (55) 99123-4567 */
export function mascaraTelefone(texto: string): string {
  const d = digitos(texto).slice(0, 11);
  if (d.length <= 2) return d.length ? `(${d}` : '';
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

/** dd/mm/aaaa */
export function mascaraData(texto: string): string {
  const d = digitos(texto).slice(0, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

/** hh:mm */
export function mascaraHora(texto: string): string {
  const d = digitos(texto).slice(0, 4);
  if (d.length <= 2) return d;
  return `${d.slice(0, 2)}:${d.slice(2)}`;
}

/** Posição de cada um dos 8 números em "dd/mm/aaaa". */
const CASAS_DA_DATA = [0, 1, 3, 4, 6, 7, 8, 9];
/** Casa apagada no meio da data: os outros números não andam (ver `editarData`). */
export const CASA_VAZIA = '_';

type Selecao = { start: number; end: number };

/**
 * Edição de uma data dd/mm/aaaa digitada, com casas fixas.
 *
 * A máscara simples (`mascaraData`) junta os números e os reparte de novo a cada tecla:
 * apagar um número no meio fazia todos os seguintes andarem uma casa ("11/04/2004" virava
 * "11/42/004"), e o cursor ia para o fim. Aqui cada número tem a sua casa:
 *
 * - apagar um número do meio deixa a casa vazia ("11/_4/2004"), e o resto fica no lugar;
 * - digitar preenche a casa onde está o cursor (vazia ou não), e o cursor segue;
 * - colar uma data, com ou sem barras, preenche as casas a partir do cursor;
 * - casas vazias no fim somem (apagar do fim para o começo funciona como sempre);
 * - números além do oitavo são ignorados.
 *
 * `selecaoAntes` é onde estava o cursor (ou o trecho selecionado) antes da tecla: com ele
 * se sabe exatamente qual casa a pessoa mexeu, mesmo quando o número digitado é igual ao
 * vizinho. Sem ele, a mudança é deduzida comparando os dois textos.
 *
 * Devolve o texto e a posição em que o cursor deve ficar.
 */
export function editarData(
  anterior: string,
  digitado: string,
  selecaoAntes?: Selecao
): { texto: string; cursor: number } {
  // 1. O que mudou: [inicio, fimAnterior) de `anterior` virou `inserido`.
  let inicio = 0;
  let fimAnterior = anterior.length;
  let inserido = '';
  const reconstroi = (i: number, f: number, ins: string) => anterior.slice(0, i) + ins + anterior.slice(f) === digitado;
  let achou = false;
  if (selecaoAntes) {
    const { start, end } = selecaoAntes;
    const delta = digitado.length - anterior.length + (end - start);
    if (delta > 0) {
      inicio = start;
      fimAnterior = end;
      inserido = digitado.slice(start, start + delta);
    } else if (end > start) {
      inicio = start;
      fimAnterior = end;
    } else if (start > 0 && reconstroi(start - 1, start, '')) {
      inicio = start - 1; // apagar para trás
      fimAnterior = start;
    } else {
      fimAnterior = start + 1; // apagar para frente
      inicio = start;
    }
    achou = reconstroi(inicio, fimAnterior, inserido);
  }
  if (!achou) {
    inicio = 0;
    while (inicio < anterior.length && inicio < digitado.length && anterior[inicio] === digitado[inicio]) inicio += 1;
    let fimDigitado = digitado.length;
    fimAnterior = anterior.length;
    while (fimAnterior > inicio && fimDigitado > inicio && anterior[fimAnterior - 1] === digitado[fimDigitado - 1]) {
      fimAnterior -= 1;
      fimDigitado -= 1;
    }
    inserido = digitado.slice(inicio, fimDigitado);
  }

  // 2. As casas como estavam.
  const casas: string[] = CASAS_DA_DATA.map((posicao) => anterior[posicao] ?? '').map((c) =>
    /\d/.test(c) ? c : c === CASA_VAZIA ? CASA_VAZIA : ''
  );
  const casaDaPosicao = (posicao: number) => CASAS_DA_DATA.filter((p) => p < posicao).length;
  let primeira = casaDaPosicao(inicio);
  const ultima = casaDaPosicao(fimAnterior);

  // 3. O trecho removido vira casas vazias. Apagar só uma barra apaga o número antes dela.
  if (ultima > primeira) {
    for (let i = primeira; i < ultima; i += 1) casas[i] = casas[i] ? CASA_VAZIA : '';
  } else if (!inserido && fimAnterior > inicio && primeira > 0) {
    primeira -= 1;
    if (casas[primeira]) casas[primeira] = CASA_VAZIA;
  }

  // 4. Os números digitados ou colados ocupam as casas a partir do cursor.
  let cursorCasa = primeira;
  for (const numero of digitos(inserido)) {
    if (cursorCasa >= CASAS_DA_DATA.length) break;
    casas[cursorCasa] = numero;
    cursorCasa += 1;
  }

  // 5. Casas vazias no fim somem; as do meio ficam marcadas.
  let usadas = casas.length;
  while (usadas > 0 && (casas[usadas - 1] === '' || casas[usadas - 1] === CASA_VAZIA)) usadas -= 1;
  const texto = mascaraData('0'.repeat(usadas))
    .split('')
    .map((c, i) => (c === '/' ? '/' : casas[casaDaPosicao(i + 1) - 1] || CASA_VAZIA))
    .join('');

  // 6. O cursor: ao apagar, na casa que ficou vazia (digitar a preenche); ao digitar, depois
  // do último número escrito, pulando a barra se houver texto depois dela.
  if (!inserido) {
    return { texto, cursor: cursorCasa < usadas ? CASAS_DA_DATA[cursorCasa] : texto.length };
  }
  const cursorCasaFinal = Math.min(cursorCasa, usadas);
  const cursor = cursorCasaFinal === 0 ? 0 : CASAS_DA_DATA[cursorCasaFinal - 1] + 1;
  return { texto, cursor: texto[cursor] === '/' ? cursor + 1 : Math.min(cursor, texto.length) };
}
