import { memo } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import Svg, { Path, Rect } from 'react-native-svg';

import type { Textura } from '@/data/tipos';
import { raios } from '@/theme/tokens';
import { LADO, mechasDaTextura } from '@/utils/ilustracaoTextura';

/** Três castanhos próximos: dão profundidade às mechas sem virar um desenho colorido. */
const TONS = ['#3B2619', '#5B3A27', '#4A2F20'] as const;
const FUNDO = '#F4ECE6';

/**
 * Ilustração de um tipo de cabelo (1A a 4C) ou de uma categoria (um fio de cada tipo).
 * Decorativa: o nome e a descrição estão no texto do botão que a contém, e o leitor de tela
 * lê só o texto. Ocupa a largura do contêiner; `proporcao` é largura sobre altura (1 é
 * quadrada). Mais larga que alta, o desenho fica centralizado sobre o mesmo fundo.
 */
export const IlustracaoTextura = memo(function IlustracaoTextura({
  textura,
  proporcao = 1,
  estilo,
}: {
  textura: Textura;
  proporcao?: number;
  estilo?: StyleProp<ViewStyle>;
}) {
  const mechas = mechasDaTextura(textura);
  return (
    <View
      style={[styles.quadro, { aspectRatio: proporcao }, estilo]}
      aria-hidden
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants">
      <Svg width="100%" height="100%" viewBox={`0 0 ${LADO} ${LADO}`}>
        <Rect x={0} y={0} width={LADO} height={LADO} fill={FUNDO} />
        {mechas.map((m, i) => (
          <Path
            key={i}
            d={m.d}
            stroke={TONS[m.tom]}
            strokeWidth={m.espessura}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        ))}
      </Svg>
    </View>
  );
});

const styles = StyleSheet.create({
  quadro: { width: '100%', borderRadius: raios.campo, overflow: 'hidden', backgroundColor: FUNDO },
});
