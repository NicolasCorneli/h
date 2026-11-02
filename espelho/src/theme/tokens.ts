import { Platform } from 'react-native';

/**
 * Tokens do design system.
 *
 * Identidade "Ameixa": uma base escura levemente arroxeada, folhas claras de conteúdo,
 * a ameixa como única cor de ação e o champanhe como destaque pontual sobre o escuro.
 * Serifada editorial nos títulos.
 *
 * Por que a ameixa substituiu a terracota: a terracota e o vermelho de erro eram da mesma
 * família (o fundo suave de uma era idêntico ao da outra), e um selo de destaque podia ser
 * lido como erro. A ameixa fica longe dos quatro tons de status (verde, âmbar, vermelho e
 * azul), é sóbria o bastante para barbearias e acolhedora o bastante para salões.
 *
 * Papéis:
 * - `acao`: botões principais, links, seleção. Uma cor só para "faça isto".
 * - `base`/`tinta`: estrutura (cabeçalhos, barra de abas, cartões de destaque).
 * - `destaque`: champanhe, só sobre fundo escuro (botão central, aba ativa, marca).
 *
 * Todo par texto/fundo alcança no mínimo 4.5:1 (WCAG 2.1 AA); as razões medidas estão
 * anotadas. Espaçamentos, raios e elevações vêm de uma escala fechada.
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
  base: '#1C1620',
  /** Borda e separadores sobre a base escura. */
  baseBorda: '#342A37',
  /** Folha clara de conteúdo, onde ficam formulários, listas e cartões. */
  fundo: '#F8F6F3',
  superficie: '#FFFFFF',
  superficieSuave: '#F3EFF1',
  superficieAfundada: '#EEE9EC',
  tinta: '#1F1A22',
  tintaElevada: '#342A37',
  camera: '#0C0A0D',
  /** Véu atrás de diálogos e folhas de ações. */
  veu: 'rgba(28,22,32,0.55)',

  // --- Texto sobre fundo claro ---
  texto: '#1F1A22', // 15.8:1
  textoSecundario: '#463E4A', // 9.5:1
  textoTerciario: '#574E5C', // 7.4:1
  textoApoio: '#675E6C', // 5.7:1 (5.4:1 sobre superficieSuave): menor tom para texto pequeno
  placeholder: '#736A78', // 5.2:1 sobre branco
  rotulo: '#675E6C', // etiquetas em caixa alta

  // --- Texto sobre fundo escuro ---
  escuroTexto: '#F5F1F4', // 15.8:1 sobre a base
  escuroTextoSecundario: '#DDD5DC',
  escuroTextoApoio: '#B5AAB6', // 7.9:1 sobre a base
  escuroTextoTenue: '#9C909D', // 5.8:1 sobre a base

  // --- Ação (ameixa) ---
  /** Preenchimento de botões, seleção e cartões de ação, com texto branco (9.7:1). */
  acao: '#6B2D5C',
  acaoPressionada: '#57234A',
  /** Ameixa para texto e links (9.0:1 sobre o fundo claro). */
  acaoTexto: '#6B2D5C',
  acaoSuave: '#F4E9F0',
  acaoBorda: '#E4CFDD',

  // --- Destaque (champanhe), só sobre fundo escuro ---
  /** 9.3:1 sobre a base. Texto e ícones em cima dele usam `tinta`. */
  destaque: '#D9B77E',

  // --- Status ---
  sucesso: '#2E7A5E',
  sucessoTexto: '#1F5A43', // 7.0:1 sobre sucessoFundo
  sucessoFundo: '#E7F2EC',
  sucessoBorda: '#CFE4D9',
  alerta: '#8A6A22',
  alertaTexto: '#5E4A12', // 7.4:1 sobre alertaFundo
  alertaFundo: '#F6EEDC',
  alertaBorda: '#E8D9B8',
  erro: '#B3261E',
  erroTexto: '#A12B21', // 6.3:1 sobre erroFundo
  erroFundo: '#FCEBE8',
  erroBorda: '#F0CCC6',
  erroPressionado: '#93201A',
  /** Informação e concluído: azul petróleo, distinto do verde de confirmado. */
  info: '#2F5F7A',
  infoTexto: '#1E4560', // 8.7:1 sobre infoFundo
  infoFundo: '#E6EFF5',
  infoBorda: '#C9DCE8',
  concluido: '#2F5F7A',
  concluidoTexto: '#1E4560',
  concluidoFundo: '#E6EFF5',
  concluidoBorda: '#C9DCE8',

  // --- Linhas e ícones auxiliares ---
  borda: '#E3DDE1',
  bordaSuave: '#ECE7EA',
  bordaForte: '#D3CBD1',
  bordaTracejada: '#CFC6CD',
  /** Setas e ícones de apoio: 3.7:1, acima do mínimo de 3:1 para elementos não textuais. */
  icone: '#8B8190',
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
      shadowColor: '#24182A',
      shadowOpacity: 0.06,
      shadowRadius: 12,
      shadowOffset: { width: 0, height: 4 },
    },
    android: { elevation: 2 },
    default: { boxShadow: '0 4px 12px rgba(36,24,42,0.06)' },
  }),
  flutuante: Platform.select({
    ios: {
      shadowColor: '#24182A',
      shadowOpacity: 0.16,
      shadowRadius: 18,
      shadowOffset: { width: 0, height: 8 },
    },
    android: { elevation: 8 },
    default: { boxShadow: '0 8px 18px rgba(36,24,42,0.16)' },
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

/** A partir desta largura (computador) as telas públicas ficam lado a lado com a marca. */
export const LARGURA_DIVIDIDA = 960;
