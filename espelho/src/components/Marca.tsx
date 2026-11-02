import { StyleSheet, Text, View } from 'react-native';
import Svg, { Path, Polyline, Rect } from 'react-native-svg';

import { cores, espaco, fontes } from '@/theme/tokens';

/** Nome do aplicativo, num lugar só: telas e textos usam esta constante. */
export const NOME_APP = 'Salão em Dia';

const MARFIM = '#FBF7F2';

/**
 * O símbolo da marca, o mesmo dos ícones do aplicativo (assets/marca.svg): a folha de
 * uma agenda com a marca de concluído e um brilho. "Em dia", com o cuidado da beleza.
 * Desenhado nas coordenadas do ícone (grade de 1024), para os dois nunca divergirem. O
 * `viewBox` recorta o centro do quadro, o que amplia o símbolo como no favicon.
 */
export function SimboloMarca({ tamanho = 40 }: { tamanho?: number }) {
  return (
    <Svg width={tamanho} height={tamanho} viewBox="78 78 868 868">
      <Rect x={78} y={78} width={868} height={868} rx={190} fill={cores.acao} />
      <Rect x={232} y={276} width={560} height={520} rx={104} fill={MARFIM} />
      <Path d="M232 412 V380 A104 104 0 0 1 336 276 H688 A104 104 0 0 1 792 380 V412 Z" fill={cores.destaque} />
      <Rect x={338} y={212} width={52} height={132} rx={26} fill={MARFIM} stroke={cores.acao} strokeWidth={20} />
      <Rect x={634} y={212} width={52} height={132} rx={26} fill={MARFIM} stroke={cores.acao} strokeWidth={20} />
      <Polyline
        points="376,622 456,702 600,558"
        fill="none"
        stroke={cores.acao}
        strokeWidth={68}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path d="M668 452 Q668 508 724 508 Q668 508 668 564 Q668 508 612 508 Q668 508 668 452 Z" fill={cores.acao} />
    </Svg>
  );
}

/** Marca do aplicativo sobre a base escura: o símbolo e o nome. */
export function Marca({ comNome = true }: { comNome?: boolean }) {
  return (
    <View style={styles.linha} accessibilityRole="image" accessibilityLabel={NOME_APP}>
      <SimboloMarca />
      {comNome ? <Text style={styles.nome}>{NOME_APP}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  linha: { flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  nome: { fontFamily: fontes.sansSemi, fontSize: 17, color: cores.escuroTexto, letterSpacing: 0.2 },
});
