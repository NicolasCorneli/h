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

/**
 * Data de nascimento digitada (dd/mm/aaaa), sem regras rígidas durante a digitação.
 *
 * - digitando no fim, as barras entram sozinhas ("04052000" vira "04/05/2000"), e uma barra
 *   digitada depois de um número só completa o zero ("4/" vira "04/");
 * - apagando ou corrigindo no meio, o texto fica exatamente como a pessoa deixou: nada é
 *   reorganizado, e por isso o cursor não pula para o fim;
 * - colar uma data inteira ("04/05/2000" ou "04052000") a organiza;
 * - só números e barras entram, até 10 caracteres.
 *
 * Substitui as "casas fixas" da versão anterior, que marcavam casas apagadas com "_" e
 * controlavam o cursor: nos testes com usuários, isso travava o começo da digitação e a
 * data saía quebrada. Se a data é válida, quem diz é `situacaoDataCurta`, e só no fim.
 */
export function digitarData(anterior: string, digitado: string): string {
  const texto = digitado.replace(/[^\d/]/g, '').replace(/\/{2,}/g, '/');
  const acrescentouNoFim = texto.length > anterior.length && texto.startsWith(anterior);
  if (!acrescentouNoFim) {
    // Oito números sem nenhuma barra só aparecem quando se cola uma data inteira (com ou
    // sem pontos ou traços): é organizada. Apagar ou corrigir no meio fica como está.
    const numeros = digitos(texto);
    return numeros.length === 8 && !texto.includes('/') ? mascaraData(numeros) : texto.slice(0, 10);
  }
  // Dia e mês com um número só, fechados por uma barra digitada, ganham o zero à esquerda.
  const partes = texto.split('/');
  for (let i = 0; i < Math.min(2, partes.length - 1); i += 1) {
    if (partes[i].length === 1) partes[i] = `0${partes[i]}`;
  }
  const formatado = mascaraData(partes.join('').slice(0, 8));
  // A barra que a pessoa acabou de digitar fica visível (ela já está no lugar certo).
  return texto.endsWith('/') && (formatado.length === 2 || formatado.length === 5) ? `${formatado}/` : formatado;
}

/**
 * Ao sair do campo, aceita as formas comuns de escrever uma data e a deixa em dd/mm/aaaa:
 * "4/5/2000", "04052000" e "0405/2000" viram "04/05/2000". O que não tiver essa forma
 * fica como está, para a pessoa ver e corrigir.
 */
export function normalizarDataDigitada(texto: string): string {
  const limpo = texto.trim();
  const partes = limpo.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (partes) return `${partes[1].padStart(2, '0')}/${partes[2].padStart(2, '0')}/${partes[3]}`;
  // Oito números em qualquer arrumação ("04052000", ou "0405/2000" com uma barra apagada).
  if (digitos(limpo).length === 8 && /^[\d/]+$/.test(limpo)) return mascaraData(digitos(limpo));
  return limpo;
}
