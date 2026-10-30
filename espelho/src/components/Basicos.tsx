import { Children, isValidElement, useEffect, useRef, useState } from 'react';
import { Animated, Easing, Image, Platform, Pressable, StyleSheet, Text, View, type StyleProp, type TextStyle, type ViewStyle, useWindowDimensions } from 'react-native';
import { SafeAreaView, type Edge } from 'react-native-safe-area-context';

import { useSuperficie, SuperficieContext } from '@/theme/superficie';
import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, elevacao, espaco, LARGURA_MAXIMA, raios } from '@/theme/tokens';
import { iniciais } from '@/utils/datas';

import { Icone, type NomeIcone } from './Icone';

// Na web não há módulo de animação nativo: pedir o driver nativo gera aviso a cada
// animação e cai para JS de qualquer forma. No aparelho, o driver nativo fica.
const DRIVER_NATIVO = Platform.OS !== 'web';

/**
 * Moldura de tela: área segura, base escura e coluna de largura máxima.
 *
 * Os `Cabecalho` que abrem a tela ficam sobre a faixa escura; o resto do conteúdo vai
 * numa folha clara de cantos arredondados. Assim toda tela tem o mesmo desenho sem que
 * cada uma repita a estrutura. Telas com topo próprio (as abas, o perfil do cliente)
 * passam `folha={false}` e montam as folhas por conta própria.
 *
 * Em tablet o conteúdo é centralizado em vez de esticar as linhas de texto.
 */
export function Tela({
  children,
  bordas = ['top'],
  fundo = cores.base,
  folha = true,
  estilo,
}: {
  children: React.ReactNode;
  bordas?: Edge[];
  fundo?: string;
  /** Coloca o conteúdo (tudo depois dos cabeçalhos) numa folha clara. */
  folha?: boolean;
  estilo?: StyleProp<ViewStyle>;
}) {
  const itens = Children.toArray(children);
  const primeiroConteudo = itens.findIndex(
    (item) => !(isValidElement(item) && (item.type as { naFaixaEscura?: boolean }).naFaixaEscura)
  );
  const corte = primeiroConteudo === -1 ? itens.length : primeiroConteudo;
  const faixa = folha ? itens.slice(0, corte) : [];
  const conteudo = folha ? itens.slice(corte) : itens;

  return (
    <SafeAreaView style={[styles.tela, { backgroundColor: fundo }, estilo]} edges={bordas}>
      <View style={styles.colunaLimite}>
        {faixa.length > 0 ? (
          <SuperficieContext.Provider value="escura">{faixa}</SuperficieContext.Provider>
        ) : null}
        {folha ? (
          <View style={[styles.folha, faixa.length === 0 && styles.folhaSemFaixa]}>{conteudo}</View>
        ) : (
          conteudo
        )}
      </View>
    </SafeAreaView>
  );
}

/**
 * Topo próprio de uma tela, sobre a base escura (título de aba, saudação). Dentro dela o
 * texto usa `textosEscuros`. Deve vir antes do conteúdo, como o `Cabecalho`.
 */
export function Faixa({ children, estilo }: { children: React.ReactNode; estilo?: StyleProp<ViewStyle> }) {
  return <View style={estilo}>{children}</View>;
}
Faixa.naFaixaEscura = true;

/** Folha clara de conteúdo, para telas que montam o próprio topo sobre a base escura. */
export function Folha({ children, estilo }: { children: React.ReactNode; estilo?: StyleProp<ViewStyle> }) {
  return <View style={[styles.folha, estilo]}>{children}</View>;
}

/** true quando há espaço para duas colunas (tablet em paisagem ou retrato largo). */
export function useTelaLarga(): boolean {
  const { width } = useWindowDimensions();
  return width >= 700;
}

export function Cartao({
  children,
  estilo,
  aoPressionar,
  rotuloAcessivel,
  elevado = false,
}: {
  children: React.ReactNode;
  estilo?: StyleProp<ViewStyle>;
  aoPressionar?: () => void;
  rotuloAcessivel?: string;
  elevado?: boolean;
}) {
  const base = [styles.cartao, elevado && elevacao.cartao, estilo];
  if (!aoPressionar) return <View style={base}>{children}</View>;
  return (
    <Pressable
      onPress={aoPressionar}
      accessibilityRole="button"
      accessibilityLabel={rotuloAcessivel}
      style={({ pressed }) => [...base, pressed && styles.pressionado]}>
      {children}
    </Pressable>
  );
}

/** Lista agrupada: itens brancos separados por 1px. */
export function Grupo({ children, estilo }: { children: React.ReactNode; estilo?: StyleProp<ViewStyle> }) {
  return <View style={[styles.grupo, estilo]}>{children}</View>;
}

export function ItemGrupo({
  children,
  aoPressionar,
  rotuloAcessivel,
}: {
  children: React.ReactNode;
  aoPressionar?: () => void;
  rotuloAcessivel?: string;
}) {
  const conteudo = <View style={styles.itemGrupo}>{children}</View>;
  if (!aoPressionar) return conteudo;
  return (
    <Pressable
      onPress={aoPressionar}
      accessibilityRole="button"
      accessibilityLabel={rotuloAcessivel}
      style={({ pressed }) => [pressed && styles.pressionado]}>
      {conteudo}
    </Pressable>
  );
}

export function Etiqueta({ children, estilo }: { children: string; estilo?: StyleProp<TextStyle> }) {
  return <Text style={[textos.etiqueta, estilo]}>{children}</Text>;
}

export function Avatar({
  nome,
  cor,
  tamanho = 40,
  quadrado = false,
  fotoUri,
}: {
  nome: string;
  cor?: string;
  tamanho?: number;
  quadrado?: boolean;
  /** Foto da pessoa. Sem ela, ou se não carregar, ficam as iniciais. */
  fotoUri?: string | null;
}) {
  const [falhou, setFalhou] = useState(false);
  const borda = quadrado ? tamanho * 0.3 : tamanho / 2;
  if (fotoUri && !falhou) {
    return (
      <Image
        source={{ uri: fotoUri }}
        onError={() => setFalhou(true)}
        accessibilityIgnoresInvertColors
        accessible={false}
        style={{ width: tamanho, height: tamanho, borderRadius: borda, backgroundColor: cores.superficieAfundada }}
      />
    );
  }
  return (
    <View
      style={[
        {
          width: tamanho,
          height: tamanho,
          borderRadius: borda,
          backgroundColor: cor ?? corDoNome(nome),
        },
        styles.centro,
      ]}>
      <Text
        style={{
          fontFamily: 'FamiljenGrotesk_600SemiBold',
          fontSize: tamanho * 0.33,
          color: '#FFFFFF',
        }}>
        {iniciais(nome)}
      </Text>
    </View>
  );
}

/** Cores de avatar escolhidas para manter contraste com o texto branco das iniciais. */
const PALETA_AVATAR = ['#A85C46', '#2E7A5E', '#7A5A17', '#4A5F7E'];

export function corDoNome(nome: string): string {
  let soma = 0;
  for (let i = 0; i < nome.length; i += 1) soma += nome.charCodeAt(i);
  return PALETA_AVATAR[soma % PALETA_AVATAR.length];
}

type TomSelo = 'sucesso' | 'alerta' | 'erro' | 'acao' | 'neutro' | 'concluido';

/**
 * Selo de status. Aceita ícone porque a informação não pode depender só da cor
 * (WCAG 1.4.1) — quem não distingue as cores lê o texto e reconhece a forma.
 */
export function Selo({
  texto,
  tom = 'neutro',
  icone,
}: {
  texto: string;
  tom?: TomSelo;
  icone?: NomeIcone;
}) {
  const paleta = {
    sucesso: { fundo: cores.sucessoFundo, texto: cores.sucessoTexto },
    alerta: { fundo: cores.alertaFundo, texto: cores.alertaTexto },
    erro: { fundo: cores.erroFundo, texto: cores.erroTexto },
    acao: { fundo: cores.acaoSuave, texto: cores.acaoTexto },
    concluido: { fundo: cores.concluidoFundo, texto: cores.concluidoTexto },
    neutro: { fundo: cores.superficieAfundada, texto: cores.textoTerciario },
  }[tom];

  return (
    <View style={[styles.selo, { backgroundColor: paleta.fundo }]}>
      {icone ? <Icone nome={icone} tamanho={12} cor={paleta.texto} /> : null}
      <Text style={[styles.seloTexto, { color: paleta.texto }]}>{texto}</Text>
    </View>
  );
}

export function Chip({
  texto,
  ativo = false,
  aoPressionar,
  icone,
}: {
  texto: string;
  ativo?: boolean;
  aoPressionar?: () => void;
  icone?: NomeIcone;
}) {
  return (
    <Pressable
      onPress={aoPressionar}
      accessibilityRole="button"
      accessibilityState={{ selected: ativo }}
      // No navegador o `accessibilityState` não chegava ao HTML: sem isto, leitor de tela
      // não sabia qual opção estava marcada.
      aria-selected={ativo}
      style={({ pressed }) => [
        styles.chip,
        ativo ? styles.chipAtivo : styles.chipInativo,
        pressed && styles.pressionado,
      ]}>
      {icone ? (
        <Icone nome={icone} tamanho={14} cor={ativo ? cores.escuroTexto : cores.textoTerciario} />
      ) : null}
      <Text style={[styles.chipTexto, { color: ativo ? cores.escuroTexto : cores.texto }]}>{texto}</Text>
    </Pressable>
  );
}

export function Alternador({
  ligado,
  aoAlternar,
  rotuloAcessivel,
}: {
  ligado: boolean;
  aoAlternar: (v: boolean) => void;
  rotuloAcessivel: string;
}) {
  return (
    <Pressable
      onPress={() => aoAlternar(!ligado)}
      accessibilityRole="switch"
      accessibilityState={{ checked: ligado }}
      accessibilityLabel={rotuloAcessivel}
      hitSlop={12}
      style={[styles.trilho, { backgroundColor: ligado ? cores.sucesso : '#C9BEB4' }]}>
      <View style={[styles.pino, ligado ? styles.pinoLigado : styles.pinoDesligado]} />
    </Pressable>
  );
}

const TONS_AVISO = {
  sucesso: { fundo: cores.sucessoFundo, borda: cores.sucessoBorda, texto: cores.sucessoTexto, icone: 'okCirculo' },
  alerta: { fundo: cores.alertaFundo, borda: cores.alertaBorda, texto: cores.alertaTexto, icone: 'alerta' },
  erro: { fundo: cores.erroFundo, borda: cores.erroBorda, texto: cores.erroTexto, icone: 'alerta' },
  neutro: { fundo: cores.superficieSuave, borda: cores.bordaSuave, texto: cores.textoTerciario, icone: 'info' },
} as const;

export function Aviso({
  tom,
  titulo,
  texto,
  icone,
  children,
}: {
  tom: keyof typeof TONS_AVISO;
  titulo?: string;
  texto?: string;
  icone?: NomeIcone;
  children?: React.ReactNode;
}) {
  const paleta = TONS_AVISO[tom];
  return (
    <View style={[styles.aviso, { backgroundColor: paleta.fundo, borderColor: paleta.borda }]}>
      <Icone nome={icone ?? (paleta.icone as NomeIcone)} tamanho={16} cor={paleta.texto} />
      <View style={styles.avisoCorpo}>
        {titulo ? <Text style={[styles.avisoTitulo, { color: paleta.texto }]}>{titulo}</Text> : null}
        {texto ? <Text style={[styles.avisoTexto, { color: paleta.texto }]}>{texto}</Text> : null}
        {children}
      </View>
    </View>
  );
}

/** Botão só com ícone, com alvo de toque de 44px mesmo quando o desenho é menor. */
export function BotaoIcone({
  icone,
  aoPressionar,
  rotuloAcessivel,
  escuro,
  estilo,
}: {
  icone: NomeIcone;
  aoPressionar: () => void;
  rotuloAcessivel: string;
  /** Padrão: segue a superfície onde o botão está. */
  escuro?: boolean;
  estilo?: StyleProp<ViewStyle>;
}) {
  const superficie = useSuperficie();
  const tomEscuro = escuro ?? superficie === 'escura';
  return (
    <Pressable
      onPress={aoPressionar}
      accessibilityRole="button"
      accessibilityLabel={rotuloAcessivel}
      style={({ pressed }) => [
        styles.botaoIcone,
        tomEscuro ? styles.botaoIconeEscuro : styles.botaoIconeClaro,
        pressed && styles.pressionado,
        estilo,
      ]}>
      <Icone nome={icone} tamanho={20} cor={tomEscuro ? cores.escuroTexto : cores.textoSecundario} />
    </Pressable>
  );
}

/** Bloco cinza pulsante exibido enquanto os dados carregam. */
export function Esqueleto({ altura = 16, largura, estilo }: { altura?: number; largura?: number | string; estilo?: StyleProp<ViewStyle> }) {
  const pulso = useRef(new Animated.Value(0.5)).current;

  useEffect(() => {
    const animacao = Animated.loop(
      Animated.sequence([
        Animated.timing(pulso, { toValue: 1, duration: 700, easing: Easing.inOut(Easing.quad), useNativeDriver: DRIVER_NATIVO }),
        Animated.timing(pulso, { toValue: 0.5, duration: 700, easing: Easing.inOut(Easing.quad), useNativeDriver: DRIVER_NATIVO }),
      ])
    );
    animacao.start();
    return () => animacao.stop();
  }, [pulso]);

  return (
    <Animated.View
      accessibilityRole="progressbar"
      accessibilityLabel="Carregando"
      style={[
        styles.esqueleto,
        { height: altura, width: (largura as number) ?? '100%', opacity: pulso },
        estilo,
      ]}
    />
  );
}

export const styles = StyleSheet.create({
  tela: { flex: 1 },
  colunaLimite: {
    flex: 1,
    width: '100%',
    maxWidth: LARGURA_MAXIMA,
    alignSelf: 'center',
  },
  folha: {
    flex: 1,
    backgroundColor: cores.fundo,
    borderTopLeftRadius: raios.bloco,
    borderTopRightRadius: raios.bloco,
    overflow: 'hidden',
  },
  folhaSemFaixa: { marginTop: espaco.sm },
  cartao: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.bordaSuave,
    borderRadius: raios.cartao,
    padding: espaco.lg,
  },
  grupo: {
    borderWidth: 1,
    borderColor: cores.bordaSuave,
    borderRadius: raios.cartao,
    overflow: 'hidden',
    backgroundColor: cores.bordaSuave,
    gap: 1,
  },
  itemGrupo: {
    backgroundColor: cores.superficie,
    paddingVertical: espaco.md,
    paddingHorizontal: espaco.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    minHeight: 56,
  },
  centro: { alignItems: 'center', justifyContent: 'center' },
  selo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.xs,
    alignSelf: 'flex-start',
    // Corte e cor agora podem ser descrições longas: o selo quebra a linha em vez de vazar.
    maxWidth: '100%',
    paddingVertical: 5,
    paddingHorizontal: espaco.sm,
    borderRadius: raios.campo,
  },
  seloTexto: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    fontSize: 12,
    lineHeight: 16,
    flexShrink: 1,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.sm,
    borderRadius: raios.campo,
    paddingVertical: espaco.md,
    paddingHorizontal: espaco.lg,
    minHeight: ALVO_TOQUE,
  },
  chipAtivo: { backgroundColor: cores.tinta },
  chipInativo: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
  },
  chipTexto: { fontFamily: 'FamiljenGrotesk_500Medium', fontSize: 14 },
  trilho: {
    width: 48,
    height: 28,
    borderRadius: raios.pilula,
    padding: 3,
    justifyContent: 'center',
  },
  pino: { width: 22, height: 22, borderRadius: 11, backgroundColor: '#FFFFFF' },
  pinoLigado: { alignSelf: 'flex-end' },
  pinoDesligado: { alignSelf: 'flex-start' },
  aviso: {
    borderWidth: 1,
    borderRadius: raios.cartao,
    padding: espaco.lg,
    flexDirection: 'row',
    gap: espaco.md,
    alignItems: 'flex-start',
  },
  avisoCorpo: { flex: 1, gap: espaco.xs },
  avisoTitulo: { fontFamily: 'FamiljenGrotesk_600SemiBold', fontSize: 14, lineHeight: 19 },
  avisoTexto: { fontFamily: 'FamiljenGrotesk_400Regular', fontSize: 13, lineHeight: 19 },
  botaoIcone: {
    width: ALVO_TOQUE,
    height: ALVO_TOQUE,
    borderRadius: raios.campo,
    alignItems: 'center',
    justifyContent: 'center',
  },
  botaoIconeClaro: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
  },
  botaoIconeEscuro: { backgroundColor: 'rgba(255,255,255,0.14)' },
  esqueleto: {
    backgroundColor: cores.superficieAfundada,
    borderRadius: raios.campo,
  },
  pressionado: { opacity: 0.85 },
});

export const estilosBase = styles;
