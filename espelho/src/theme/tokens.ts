import { Platform } from 'react-native';

/**
 * Tokens do design system.
 *
 * A identidade parte do design original do projeto (arquivo "Espelho - App.dc.html"):
 * terracota como única cor de ação, serifada editorial nos títulos. Na revisão visual a
 * base passou a ser escura, com o conteúdo em folhas claras. Os valores foram
 * ajustados para que todo par texto/fundo alcance no mínimo 4.5:1 (WCAG 2.1 AA) e para
 * que espaçamentos, raios e elevações venham de uma escala fechada.
 *
 * Razões de contraste medidas estão anotadas nas cores de texto.
 */

export const fontes = {
  serif: 'InstrumentSerif_400Regular',
  serifItalico: 'InstrumentSerif_400Regular_Italic',
  sans: 'FamiljenGrotesk_400Regular',
  sansMedio: 'FamiljenGrotesk_500Medium',
  sansSemi: 'FamiljenGrotesk_600SemiBold',
  sansBold: 'FamiljenGrotesk_700Bold',
  mono: 'monospace',
} as const;

export const cores = {
  // --- Superfícies ---
  /**
   * Base escura do aplicativo: atrás das folhas de conteúdo, nos cabeçalhos e na barra
   * de abas. Texto sobre ela usa as cores `escuro*` (15:1 ou mais no texto principal).
   */
  base: '#17130F',
  /** Borda e separadores sobre a base escura. */
  baseBorda: '#2E2620',
  /** Folha clara de conteúdo, onde ficam formulários, listas e cartões. */
  fundo: '#FAF7F4',
  superficie: '#FFFFFF',
  superficieSuave: '#F3EDE6',
  superficieAfundada: '#F2EBE4',
  tinta: '#1B1714',
  tintaElevada: '#33291F',
  camera: '#0C0A09',

  // --- Texto sobre fundo claro ---
  texto: '#1B1714', // 16.7:1
  textoSecundario: '#4A423B', // 9.2:1
  textoTerciario: '#5E554E', // 6.8:1
  textoApoio: '#6F655D', // 5.3:1 — menor tom admitido para texto pequeno
  placeholder: '#7A6F66', // 4.9:1 sobre branco
  rotulo: '#6F655D', // etiquetas em caixa alta

  // --- Texto sobre fundo escuro ---
  escuroTexto: '#F3EDE7',
  escuroTextoSecundario: '#DDD4CB',
  escuroTextoApoio: '#B5A99E', // 7.8:1 sobre tinta
  escuroTextoTenue: '#9A8F85', // 5.6:1 sobre tinta

  // --- Ação ---
  /** Preenchimento de botões e cartões de ação, com texto branco (4.9:1). */
  acao: '#A85C46',
  acaoPressionada: '#8E4E3B',
  /** Terracota do design, usada em superfícies decorativas e ícones (não em texto pequeno). */
  acaoDecorativa: '#B96A52',
  /** Terracota para texto e links (6.0:1 sobre o fundo claro). */
  acaoTexto: '#8E4E3B',
  acaoSuave: '#F7EAE4',

  // --- Status ---
  sucesso: '#2E7A5E',
  sucessoTexto: '#1F5A43', // 7.0:1 sobre sucessoFundo
  sucessoFundo: '#E7F2EC',
  sucessoBorda: '#CFE4D9',
  alerta: '#8A6A22',
  alertaTexto: '#5E4A12', // 7.4:1 sobre alertaFundo
  alertaFundo: '#F6EEDC',
  alertaBorda: '#E8D9B8',
  erro: '#BE4A3A',
  erroTexto: '#9E3122', // 6.1:1 sobre erroFundo
  erroFundo: '#F7EAE4',
  erroBorda: '#E8CDC2',
  erroPressionado: '#A63C2E',
  /** Concluído: azul petróleo, distinto do verde de confirmado. */
  concluido: '#2F5F7A',
  concluidoTexto: '#1E4560', // 8.6:1 sobre concluidoFundo
  concluidoFundo: '#E6EFF5',
  concluidoBorda: '#C9DCE8',

  // --- Linhas e ícones auxiliares ---
  borda: '#E4DBD2',
  bordaSuave: '#EDE5DD',
  bordaForte: '#D8CCC1',
  bordaTracejada: '#D3C7BB',
  /** Setas e ícones de apoio: 3.7:1, acima do mínimo de 3:1 para elementos não textuais. */
  icone: '#8A7E74',
} as const;

/** Grade de 4px: todo espaçamento do app sai daqui. */
export const espaco = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

/** Três raios apenas: campo, cartão e bloco. */
export const raios = {
  campo: 10,
  cartao: 16,
  bloco: 24,
  pilula: 999,
} as const;

/** Uma elevação sutil para cartões flutuantes; o resto usa borda. */
export const elevacao = {
  cartao: Platform.select({
    ios: {
      shadowColor: '#2A1C14',
      shadowOpacity: 0.06,
      shadowRadius: 12,
      shadowOffset: { width: 0, height: 4 },
    },
    android: { elevation: 2 },
    default: { boxShadow: '0 4px 12px rgba(42,28,20,0.06)' },
  }),
  flutuante: Platform.select({
    ios: {
      shadowColor: '#2A1C14',
      shadowOpacity: 0.16,
      shadowRadius: 18,
      shadowOffset: { width: 0, height: 8 },
    },
    android: { elevation: 8 },
    default: { boxShadow: '0 8px 18px rgba(42,28,20,0.16)' },
  }),
} as const;

/** Alvo mínimo de toque (iOS HIG e Material). */
export const ALVO_TOQUE = 44;

/**
 * Largura máxima do conteúdo. Em tablet o app centraliza a coluna em vez de esticar
 * as linhas de texto, que passariam de 100 caracteres.
 */
export const LARGURA_MAXIMA = 560;

/** A partir desta largura o layout pode usar duas colunas. */
export const LARGURA_TABLET = 700;
