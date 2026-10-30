import { createContext, useContext } from 'react';

/**
 * Sobre que fundo um componente está desenhado.
 *
 * A base do aplicativo é escura e o conteúdo fica em folhas claras. Componentes que
 * aparecem nos dois lugares (cabeçalho, botão de ícone) leem este contexto para escolher
 * as cores de texto que mantêm o contraste.
 */
export type Superficie = 'clara' | 'escura';

export const SuperficieContext = createContext<Superficie>('clara');

export function useSuperficie(): Superficie {
  return useContext(SuperficieContext);
}
