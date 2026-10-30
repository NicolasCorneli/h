import { StyleSheet, type TextStyle } from 'react-native';

import { cores, fontes } from './tokens';

export { fontes };

/**
 * Escala tipográfica fechada: 32 / 24 / 17 / 15 / 13 / 12 / 10.
 * Cada papel tem um estilo; telas não definem tamanhos próprios.
 */
export const textos = StyleSheet.create({
  /** Serifada grande — abertura de tela (onboarding, sucesso, bloqueios). */
  display: {
    fontFamily: fontes.serif,
    fontSize: 32,
    lineHeight: 36,
    letterSpacing: -0.4,
    color: cores.texto,
  },
  /** Serifada de título — cabeçalhos de seção principal e nomes próprios. */
  titulo: {
    fontFamily: fontes.serif,
    fontSize: 24,
    lineHeight: 28,
    letterSpacing: -0.2,
    color: cores.texto,
  },
  /** Número grande em serifada — horários e contadores. */
  numero: {
    fontFamily: fontes.serif,
    fontSize: 24,
    lineHeight: 26,
    color: cores.texto,
  },
  /** Título de bloco dentro da tela. */
  secao: {
    fontFamily: fontes.sansSemi,
    fontSize: 17,
    lineHeight: 22,
    color: cores.texto,
  },
  /** Texto de leitura e rótulo de item de lista. */
  corpo: {
    fontFamily: fontes.sans,
    fontSize: 15,
    lineHeight: 22,
    color: cores.textoTerciario,
  },
  corpoForte: {
    fontFamily: fontes.sansSemi,
    fontSize: 15,
    lineHeight: 20,
    color: cores.texto,
  },
  /** Texto de apoio abaixo de um item, descrições curtas. */
  apoio: {
    fontFamily: fontes.sans,
    fontSize: 13,
    lineHeight: 19,
    color: cores.textoApoio,
  },
  apoioForte: {
    fontFamily: fontes.sansSemi,
    fontSize: 13,
    lineHeight: 18,
    color: cores.texto,
  },
  /** Metadados: datas, contadores pequenos, legendas. */
  meta: {
    fontFamily: fontes.sansMedio,
    fontSize: 12,
    lineHeight: 17,
    color: cores.textoApoio,
  },
  /** Etiqueta monoespaçada em caixa alta que abre seções. */
  etiqueta: {
    fontFamily: fontes.mono,
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: cores.rotulo,
  } as TextStyle,
  /** Link textual — sempre no terracota escuro, que passa em AA. */
  link: {
    fontFamily: fontes.sansSemi,
    fontSize: 13,
    lineHeight: 18,
    color: cores.acaoTexto,
  },
  /** Rótulo de botão. */
  botao: {
    fontFamily: fontes.sansSemi,
    fontSize: 15,
    lineHeight: 20,
  },
});

/** Variações sobre fundo escuro, com os mesmos tamanhos da escala. */
export const textosEscuros = StyleSheet.create({
  display: { ...textos.display, color: cores.escuroTexto },
  titulo: { ...textos.titulo, color: cores.escuroTexto },
  secao: { ...textos.secao, color: cores.escuroTexto },
  numero: { ...textos.numero, color: cores.escuroTexto },
  corpoForte: { ...textos.corpoForte, color: cores.escuroTexto },
  apoioForte: { ...textos.apoioForte, color: cores.escuroTexto },
  corpo: { ...textos.corpo, color: cores.escuroTextoSecundario },
  apoio: { ...textos.apoio, color: cores.escuroTextoApoio },
  meta: { ...textos.meta, color: cores.escuroTextoApoio },
  etiqueta: { ...textos.etiqueta, color: cores.escuroTextoTenue } as TextStyle,
});
