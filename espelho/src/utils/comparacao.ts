/**
 * Escolha das duas simulações da tela de comparação, sem interface (`testes/comparacao.mjs`).
 *
 * Cada lado é uma posição fixa. Tocar numa simulação marcada a tira do lado dela; tocar
 * numa desmarcada a põe no primeiro lado vago (esquerda, depois direita) e, com os dois
 * ocupados, no lugar da direita. Nada troca de lado sozinho: antes, escolher à esquerda a
 * simulação que estava à direita invertia as duas sem aviso.
 */

export type Posicoes = { esquerda: string | null; direita: string | null };

export function escolherParaComparar(atual: Posicoes, id: string): Posicoes {
  if (atual.esquerda === id) return { ...atual, esquerda: null };
  if (atual.direita === id) return { ...atual, direita: null };
  if (atual.esquerda === null) return { ...atual, esquerda: id };
  return { ...atual, direita: id };
}
