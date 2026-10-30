import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

import type { Genero } from '@/data/tipos';
import type { FotoCapturada, ProblemaFoto } from '@/services/simulacaoService';
import { GENERO_PADRAO } from '@/utils/pedido';

/**
 * Estado da simulação em andamento: vive só na memória, entre as telas de captura,
 * personalização, revisão, processamento e resultado.
 *
 * A foto fica aqui até ser enviada: o aparelho não guarda imagem de cliente em disco
 * próprio. Depois do envio, a simulação passa a existir no servidor e é identificada por
 * `simulacaoId`; as telas leem os dados dela pelo store.
 *
 * As escolhas sobrevivem a erros e a "Refazer": uma nova tentativa não obriga a preencher
 * tudo de novo.
 */
export type Rascunho = {
  clienteId: string | null;
  foto: FotoCapturada | null;
  /** Problemas detectados na pré-checagem local, ou devolvidos pelo servidor. */
  problemas: ProblemaFoto[];
  /** Descrição do corte, escrita pelo profissional. */
  corte: string;
  manterCorte: boolean;
  /** Descrição da cor, escrita pelo profissional. */
  cor: string;
  manterCor: boolean;
  /** Gênero do corte, com o valor que vai ao modelo ("none" é não especificar). */
  genero: Genero;
  /** Anotação para o histórico. Não vai para o serviço de IA. */
  observacoes: string;
  /** Preenchido quando o servidor aceita a simulação (resposta 202). */
  simulacaoId: string | null;
  /**
   * Identifica um envio. Repetir o mesmo envio (voltar e tocar em "Gerar" de novo, ou a
   * rede cair depois de o servidor receber) devolve a mesma simulação em vez de pagar
   * outra geração. Zera quando o pedido muda ou quando a tentativa termina.
   */
  chaveEnvio: string | null;
  /**
   * Motivo de um envio que nem chegou a virar simulação (cota, credencial recusada, sem
   * conexão). Falhas da geração em si ficam na própria simulação (`erroCodigo`).
   */
  falhaEnvio: { codigo: string; mensagem: string } | null;
  /**
   * Atalhos de demonstração para a apresentação do TCC. Viajam até o servidor, que só os
   * honra quando está em modo demo: o aplicativo não finge resultado nenhum.
   */
  demoRecusarFoto: boolean;
  demoFalharIa: boolean;
};

const inicial: Rascunho = {
  clienteId: null,
  foto: null,
  problemas: [],
  corte: '',
  manterCorte: false,
  cor: '',
  manterCor: false,
  genero: GENERO_PADRAO,
  observacoes: '',
  simulacaoId: null,
  chaveEnvio: null,
  falhaEnvio: null,
  demoRecusarFoto: false,
  demoFalharIa: false,
};

/** Mudar qualquer um destes é pedir outra coisa: o envio anterior não vale mais. */
const CAMPOS_DO_PEDIDO: (keyof Rascunho)[] = [
  'foto',
  'corte',
  'manterCorte',
  'cor',
  'manterCor',
  'genero',
  'clienteId',
];

type Contexto = {
  rascunho: Rascunho;
  atualizar: (parcial: Partial<Rascunho>) => void;
  iniciar: (clienteId: string | null) => void;
  limpar: () => void;
};

const RascunhoContext = createContext<Contexto | null>(null);

export function RascunhoProvider({ children }: { children: ReactNode }) {
  const [rascunho, setRascunho] = useState<Rascunho>(inicial);

  const valor = useMemo<Contexto>(
    () => ({
      rascunho,
      atualizar: (parcial) =>
        setRascunho((atual) => {
          const mudouPedido =
            !('chaveEnvio' in parcial) &&
            CAMPOS_DO_PEDIDO.some((campo) => campo in parcial && parcial[campo] !== atual[campo]);
          return mudouPedido ? { ...atual, ...parcial, chaveEnvio: null } : { ...atual, ...parcial };
        }),
      iniciar: (clienteId) => setRascunho({ ...inicial, clienteId }),
      limpar: () => setRascunho(inicial),
    }),
    [rascunho]
  );

  return <RascunhoContext.Provider value={valor}>{children}</RascunhoContext.Provider>;
}

export function useRascunho(): Contexto {
  const ctx = useContext(RascunhoContext);
  if (!ctx) throw new Error('useRascunho precisa estar dentro de <RascunhoProvider>');
  return ctx;
}
