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
