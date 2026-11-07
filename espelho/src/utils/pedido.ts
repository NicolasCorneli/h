/**
 * Regras do pedido de personalização (etapa "Estilo e cor"), sem interface.
 *
 * São as mesmas do servidor (`backend/app/services/ai/pedido.py`): aqui servem para a tela
 * dizer na hora o que falta, sem esperar o envio. A validação que vale continua sendo a do
 * servidor, que recusa com 422 e o mesmo texto.
 */

import type { CategoriaCurvatura, Curvatura, Genero, TipoCurvatura } from '@/data/tipos';

export const MAX_DESCRICAO = 300;

export const CORTE_MANTIDO = 'Corte atual';
export const COR_MANTIDA = 'Cor atual';

export type EscolhasPedido = {
  corte: string;
  manterCorte: boolean;
  cor: string;
  manterCor: boolean;
};

/** Sem escolha, vale o padrão do modelo: é o que valia antes de a tela ter a opção. */
export const GENERO_PADRAO: Genero = 'none';

/** Opções de gênero da tela: o rótulo em português e o valor que vai ao modelo. */
export const OPCOES_DE_GENERO: readonly { valor: Genero; rotulo: string }[] = [
  { valor: 'female', rotulo: 'Feminino' },
  { valor: 'male', rotulo: 'Masculino' },
  { valor: 'none', rotulo: 'Não especificar' },
];

/** Como o gênero aparece na revisão. Valor desconhecido conta como não especificado. */
export function rotuloGenero(genero: Genero): string {
  return (OPCOES_DE_GENERO.find((opcao) => opcao.valor === genero) ?? OPCOES_DE_GENERO[2]).rotulo;
}

export type CampoPedido = 'corte' | 'cor' | 'pedido';

export type Pendencia = { campo: CampoPedido; mensagem: string };

/** Mesmo conjunto do servidor: letras, números, espaço e pontuação de uma frase comum. */
const PERMITIDO = /^[\p{L}\p{N}\p{M}_\s.,;:!?()'"/+&%ºª°-]*$/u;

/** Espaços repetidos viram um; pontas aparadas. */
export function limparTexto(texto: string): string {
  return texto.replace(/\s+/g, ' ').trim();
}

function problemaDoTexto(texto: string, campo: 'corte' | 'cor'): Pendencia | null {
  if (texto.length > MAX_DESCRICAO) {
    return { campo, mensagem: `Use até ${MAX_DESCRICAO} caracteres. Resuma o essencial.` };
  }
  if (!PERMITIDO.test(texto)) {
    return { campo, mensagem: 'Use só letras, números e pontuação comum na descrição.' };
  }
  if ((texto.match(/\p{L}/gu) ?? []).length < 2) {
    return { campo, mensagem: 'Descreva com palavras o que você quer.' };
  }
  return null;
}

/** O que impede o pedido de seguir. Vazio quando está pronto para revisar. */
export function pendencias(escolhas: EscolhasPedido): Pendencia[] {
  const lista: Pendencia[] = [];
  const corte = limparTexto(escolhas.corte);
  const cor = limparTexto(escolhas.cor);

  if (!escolhas.manterCorte && !corte) {
    lista.push({ campo: 'corte', mensagem: 'Passo 1: escreva o novo corte ou marque "Manter o corte atual".' });
  } else if (!escolhas.manterCorte) {
    const problema = problemaDoTexto(corte, 'corte');
    if (problema) lista.push(problema);
  }

  if (!escolhas.manterCor && !cor) {
    lista.push({ campo: 'cor', mensagem: 'Passo 2: escreva a nova cor ou marque "Manter a cor atual".' });
  } else if (!escolhas.manterCor) {
    const problema = problemaDoTexto(cor, 'cor');
    if (problema) lista.push(problema);
  }

  if (escolhas.manterCorte && escolhas.manterCor) {
    lista.push({ campo: 'pedido', mensagem: 'Nada a simular: mude o corte, a cor ou os dois.' });
  }
  return lista;
}

/** Como o corte aparece na revisão e no histórico. */
export function rotuloCorte(escolhas: EscolhasPedido): string {
  return !escolhas.manterCorte && limparTexto(escolhas.corte) ? limparTexto(escolhas.corte) : CORTE_MANTIDO;
}

/** Como a cor aparece na revisão e no histórico. */
export function rotuloCor(escolhas: EscolhasPedido): string {
  return !escolhas.manterCor && limparTexto(escolhas.cor) ? limparTexto(escolhas.cor) : COR_MANTIDA;
}

/**
 * Padrão natural de curvatura (opcional), em duas etapas: primeiro a categoria, depois,
 * se a pessoa souber, o tipo de 1A a 4C. As descrições são as de salão, sem jargão.
 * Os valores são os do servidor (`CURVATURAS` em `services/ai/pedido.py`); viram uma frase
 * da instrução ao modelo, para ajudar a manter os cachos e o volume como são. A foto
 * continua sendo a referência principal.
 */
export const OPCOES_DE_CURVATURA: readonly {
  valor: CategoriaCurvatura;
  rotulo: string;
  descricao: string;
  tipos: readonly { valor: TipoCurvatura; descricao: string }[];
}[] = [
  {
    valor: 'liso',
    rotulo: 'Liso',
    descricao: 'Fios retos, sem ondas',
    tipos: [
      { valor: '1A', descricao: 'fino e bem liso' },
      { valor: '1B', descricao: 'liso, com um pouco de corpo' },
      { valor: '1C', descricao: 'liso grosso, com leve ondulação' },
    ],
  },
  {
    valor: 'ondulado',
    rotulo: 'Ondulado',
    descricao: 'Ondas em forma de S',
    tipos: [
      { valor: '2A', descricao: 'ondas leves e soltas' },
      { valor: '2B', descricao: 'ondas marcadas a partir do meio' },
      { valor: '2C', descricao: 'ondas fortes desde a raiz' },
    ],
  },
  {
    valor: 'cacheado',
    rotulo: 'Cacheado',
    descricao: 'Cachos em espiral',
    tipos: [
      { valor: '3A', descricao: 'cachos largos e soltos' },
      { valor: '3B', descricao: 'cachos médios, da largura de um dedo' },
      { valor: '3C', descricao: 'cachos fechados, da largura de um lápis' },
    ],
  },
  {
    valor: 'crespo',
    rotulo: 'Crespo',
    descricao: 'Fios bem fechados, em molas ou zigue-zague',
    tipos: [
      { valor: '4A', descricao: 'molinhas fechadas e definidas' },
      { valor: '4B', descricao: 'zigue-zague, pouca definição' },
      { valor: '4C', descricao: 'muito fechado, encolhe bastante' },
    ],
  },
];

/** A categoria de uma curvatura (a própria, ou a do tipo 1A a 4C). */
export function categoriaDaCurvatura(curvatura: Curvatura | null): CategoriaCurvatura | null {
  if (curvatura === null) return null;
  const opcao = OPCOES_DE_CURVATURA.find(
    (o) => o.valor === curvatura || o.tipos.some((tipo) => tipo.valor === curvatura)
  );
  return opcao?.valor ?? null;
}

/** Como a curvatura aparece na revisão e no histórico. */
export function rotuloCurvatura(curvatura: Curvatura | null): string {
  const categoria = OPCOES_DE_CURVATURA.find((o) => o.valor === categoriaDaCurvatura(curvatura));
  if (!categoria) return 'Não informado';
  const tipo = categoria.tipos.find((t) => t.valor === curvatura);
  return tipo ? `${categoria.rotulo} ${tipo.valor} (${tipo.descricao})` : categoria.rotulo;
}
