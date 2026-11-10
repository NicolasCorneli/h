/**
 * Regras do pedido de personalização (etapa "Estilo e cor"), sem interface.
 *
 * São as mesmas do servidor (`backend/app/services/ai/pedido.py`): aqui servem para a tela
 * dizer na hora o que falta, sem esperar o envio. A validação que vale continua sendo a do
 * servidor, que recusa com 422 e o mesmo texto.
 */

import type { CategoriaTextura, Genero, Textura, TipoTextura } from '@/data/tipos';

export const MAX_DESCRICAO = 300;

export const CORTE_MANTIDO = 'Corte atual';
export const COR_MANTIDA = 'Cor atual';

export type EscolhasPedido = {
  corte: string;
  manterCorte: boolean;
  cor: string;
  manterCor: boolean;
  /** Tipo de cabelo desejado. null (ou ausente) é "Manter meu tipo de cabelo atual". */
  textura?: Textura | null;
};

/** Sem escolha, vale o padrão do modelo especializado, que na tela se chama "Neutro". */
export const GENERO_PADRAO: Genero = 'none';

/**
 * Opções de gênero do corte: o rótulo em português e o valor que vai ao servidor.
 * "Neutro" é uma escolha (corte sem gênero definido) e vira instrução própria no Nano
 * Banana, e não ausência de instrução.
 */
export const OPCOES_DE_GENERO: readonly { valor: Genero; rotulo: string }[] = [
  { valor: 'female', rotulo: 'Feminino' },
  { valor: 'male', rotulo: 'Masculino' },
  { valor: 'none', rotulo: 'Neutro' },
];

/** Como o gênero aparece na revisão. Valor desconhecido conta como neutro (o padrão). */
export function rotuloGenero(genero: Genero): string {
  return (OPCOES_DE_GENERO.find((opcao) => opcao.valor === genero) ?? OPCOES_DE_GENERO[2]).rotulo;
}

/** A seção da tela a que cada pendência se refere: o rodapé leva até ela. */
export type CampoPedido = 'corte' | 'cor' | 'pedido';

/**
 * `tipo` diz o que fazer: preencher (`vazio`), corrigir o texto (`texto`) ou decidir entre
 * manter e a descrição já escrita (`conflito`).
 */
export type Pendencia = { campo: CampoPedido; tipo: 'vazio' | 'texto' | 'conflito' | 'nada'; mensagem: string };

/** Mesmo conjunto do servidor: letras, números, espaço e pontuação de uma frase comum. */
const PERMITIDO = /^[\p{L}\p{N}\p{M}_\s.,;:!?()'"/+&%ºª°-]*$/u;

/** Espaços repetidos viram um; pontas aparadas. */
export function limparTexto(texto: string): string {
  return texto.replace(/\s+/g, ' ').trim();
}

function problemaDoTexto(texto: string, campo: 'corte' | 'cor'): Pendencia | null {
  if (texto.length > MAX_DESCRICAO) {
    return { campo, tipo: 'texto', mensagem: `Use até ${MAX_DESCRICAO} caracteres. Resuma o essencial.` };
  }
  if (!PERMITIDO.test(texto)) {
    return { campo, tipo: 'texto', mensagem: 'Use só letras, números e pontuação comum na descrição.' };
  }
  if ((texto.match(/\p{L}/gu) ?? []).length < 2) {
    return { campo, tipo: 'texto', mensagem: 'Descreva com palavras o que você quer.' };
  }
  return null;
}

const NOMES = {
  corte: { nome: 'Corte', manter: 'Manter o corte atual', descricao: 'o corte' },
  cor: { nome: 'Cor', manter: 'Manter a cor atual', descricao: 'a cor' },
} as const;

function pendenciaDoCampo(campo: 'corte' | 'cor', manter: boolean, texto: string): Pendencia | null {
  const nomes = NOMES[campo];
  if (manter) {
    // Texto escrito antes de escolher "manter" não é descartado em silêncio: a pessoa decide.
    return texto
      ? {
          campo,
          tipo: 'conflito',
          mensagem: `${nomes.nome}: você escreveu uma descrição, mas escolheu "${nomes.manter}". Escolha qual vale.`,
        }
      : null;
  }
  if (!texto) {
    return {
      campo,
      tipo: 'vazio',
      mensagem: `${nomes.nome}: descreva ${nomes.descricao} desejad${campo === 'corte' ? 'o' : 'a'} ou escolha "${nomes.manter}".`,
    };
  }
  return problemaDoTexto(texto, campo);
}

/** O que impede o pedido de seguir. Vazio quando está pronto para revisar. */
export function pendencias(escolhas: EscolhasPedido): Pendencia[] {
  const lista: Pendencia[] = [];
  const corte = pendenciaDoCampo('corte', escolhas.manterCorte, limparTexto(escolhas.corte));
  if (corte) lista.push(corte);
  const cor = pendenciaDoCampo('cor', escolhas.manterCor, limparTexto(escolhas.cor));
  if (cor) lista.push(cor);
  if (escolhas.manterCorte && escolhas.manterCor && !escolhas.textura) {
    lista.push({
      campo: 'pedido',
      tipo: 'nada',
      mensagem: 'Nada a simular: mude o corte, a cor ou o tipo de cabelo.',
    });
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

export type OpcaoTipo = { valor: TipoTextura; descricao: string };
export type OpcaoCategoria = {
  valor: CategoriaTextura;
  rotulo: string;
  descricao: string;
  tipos: readonly OpcaoTipo[];
};

/**
 * Tipo de cabelo desejado, em duas etapas: a categoria e, se a pessoa quiser, o tipo de
 * 1A a 4C. As descrições são as de salão, sem jargão, e cada tipo tem uma ilustração
 * própria (`IlustracaoTextura`). Os valores são os do servidor (`TEXTURAS` em
 * `services/ai/pedido.py`), que os traduz numa frase da instrução ao modelo.
 *
 * Revisão da nomenclatura (pedido de 2026-11-10): o 1C deixa claro que ainda é liso; o 4A
 * passa a "molas" (cachos crespos, e não cachos do tipo 3); o 4B, ao zigue-zague em Z.
 */
export const OPCOES_DE_TEXTURA: readonly OpcaoCategoria[] = [
  {
    valor: 'liso',
    rotulo: 'Liso',
    descricao: 'Fios retos',
    tipos: [
      { valor: '1A', descricao: 'Muito fino, sem volume' },
      { valor: '1B', descricao: 'Liso com mais corpo' },
      { valor: '1C', descricao: 'Grosso, quase ondulado' },
    ],
  },
  {
    valor: 'ondulado',
    rotulo: 'Ondulado',
    descricao: 'Ondas em S',
    tipos: [
      { valor: '2A', descricao: 'Ondas leves e abertas' },
      { valor: '2B', descricao: 'Ondas definidas em S' },
      { valor: '2C', descricao: 'Ondas fortes, quase cachos' },
    ],
  },
  {
    valor: 'cacheado',
    rotulo: 'Cacheado',
    descricao: 'Cachos em espiral',
    tipos: [
      { valor: '3A', descricao: 'Cachos largos e soltos' },
      { valor: '3B', descricao: 'Cachos médios e definidos' },
      { valor: '3C', descricao: 'Cachos pequenos e fechados' },
    ],
  },
  {
    valor: 'crespo',
    rotulo: 'Crespo',
    descricao: 'Molas e zigue-zague',
    tipos: [
      { valor: '4A', descricao: 'Molas pequenas e definidas' },
      { valor: '4B', descricao: 'Zigue-zague em Z' },
      { valor: '4C', descricao: 'Bem fechado, encolhe muito' },
    ],
  },
];

/** A categoria de um tipo de cabelo (a própria, ou a do tipo 1A a 4C). */
export function categoriaDaTextura(textura: Textura | null | undefined): CategoriaTextura | null {
  if (!textura) return null;
  const opcao = OPCOES_DE_TEXTURA.find((o) => o.valor === textura || o.tipos.some((tipo) => tipo.valor === textura));
  return opcao?.valor ?? null;
}

export const TEXTURA_MANTIDA = 'Manter o tipo atual';

/** Como o tipo de cabelo aparece na revisão e no histórico. */
export function rotuloTextura(textura: Textura | null | undefined): string {
  const categoria = OPCOES_DE_TEXTURA.find((o) => o.valor === categoriaDaTextura(textura));
  if (!categoria) return TEXTURA_MANTIDA;
  const tipo = categoria.tipos.find((t) => t.valor === textura);
  return tipo ? `${categoria.rotulo} ${tipo.valor}: ${minusculaInicial(tipo.descricao)}` : categoria.rotulo;
}

/**
 * Toque numa categoria: escolhe a categoria (o tipo exato fica em aberto). Tocar de novo
 * na categoria já escolhida não muda nada, para não apagar o tipo exato por engano.
 */
export function escolherCategoria(atual: Textura | null, categoria: CategoriaTextura): Textura {
  return categoriaDaTextura(atual) === categoria ? (atual as Textura) : categoria;
}

/** Toque num tipo: escolhe o tipo; tocar de novo no mesmo volta à categoria. */
export function escolherTipo(atual: Textura | null, tipo: TipoTextura): Textura {
  if (atual === tipo) return categoriaDaTextura(tipo) as CategoriaTextura;
  return tipo;
}

/** "Ondas definidas em S" vira "ondas definidas em S": só a primeira letra muda. */
function minusculaInicial(texto: string): string {
  return texto.charAt(0).toLowerCase() + texto.slice(1);
}
