/**
 * Comparação de texto para as buscas de cliente.
 *
 * No celular é comum digitar sem acento: "julia" precisa achar "Júlia", e "joao" achar
 * "João". Antes a busca comparava os textos como vieram e não encontrava.
 */
export function normalizarBusca(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

/** true quando o nome contém o termo, ignorando acentos, maiúsculas e espaços nas pontas. */
export function nomeCorresponde(nome: string, termo: string): boolean {
  return normalizarBusca(nome).includes(normalizarBusca(termo));
}
