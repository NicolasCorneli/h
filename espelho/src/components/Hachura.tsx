import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { cores, espaco } from '@/theme/tokens';

type Props = {
  /** Texto de apoio, como as legendas "simulação" / "foto original" do design. */
  legenda?: string;
  claro?: boolean;
  estilo?: StyleProp<ViewStyle>;
  children?: React.ReactNode;
};

/**
 * Reproduz o fundo hachurado que o protótipo usa no lugar de imagens.
 * As faixas são Views rotacionadas porque React Native não tem gradiente repetido.
 */
export function Hachura({ legenda, claro = false, estilo, children }: Props) {
  const faixa = claro ? 'rgba(27,23,20,0.05)' : 'rgba(27,23,20,0.045)';
  return (
    <View style={[styles.base, claro && styles.claro, estilo]}>
      <View style={[StyleSheet.absoluteFill, { pointerEvents: 'none' }]}>
        {Array.from({ length: 40 }).map((_, i) => (
          <View
            key={i}
            style={[styles.faixa, { backgroundColor: faixa, top: i * 16 - 200 }]}
          />
        ))}
      </View>
      {legenda ? <Text style={styles.legenda}>{legenda}</Text> : null}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    backgroundColor: '#EFE7DE',
    overflow: 'hidden',
    justifyContent: 'flex-end',
    padding: espaco.sm,
  },
  claro: {
    backgroundColor: '#E4D3C6',
  },
  faixa: {
    position: 'absolute',
    left: -240,
    right: -240,
    height: 8,
    transform: [{ rotate: '-45deg' }],
  },
  legenda: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 11,
    color: cores.textoApoio,
  },
});
