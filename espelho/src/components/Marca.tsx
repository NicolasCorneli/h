import { StyleSheet, Text, View } from 'react-native';

import { cores, espaco, fontes, raios } from '@/theme/tokens';

/** Nome do aplicativo, num lugar só: telas e textos usam esta constante. */
export const NOME_APP = 'Salão em Dia';

/**
 * Marca do aplicativo sobre a base escura: o símbolo (um calendário com a marca de
 * concluído, em terracota) e o nome.
 */
export function Marca({ comNome = true }: { comNome?: boolean }) {
  return (
    <View style={styles.linha} accessibilityRole="image" accessibilityLabel={NOME_APP}>
      <View style={styles.simbolo}>
        <View style={styles.argolas}>
          <View style={styles.argola} />
          <View style={styles.argola} />
        </View>
        <Text style={styles.marcaOk}>✓</Text>
      </View>
      {comNome ? <Text style={styles.nome}>{NOME_APP}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  linha: { flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  simbolo: {
    width: 40,
    height: 40,
    borderRadius: raios.campo,
    backgroundColor: cores.acao,
    alignItems: 'center',
    justifyContent: 'center',
  },
  argolas: { position: 'absolute', top: 6, flexDirection: 'row', gap: 12 },
  argola: { width: 3, height: 6, borderRadius: 2, backgroundColor: '#FFFFFF' },
  marcaOk: { color: '#FFFFFF', fontSize: 18, fontFamily: fontes.sansBold, marginTop: 4 },
  nome: { fontFamily: fontes.sansSemi, fontSize: 17, color: cores.escuroTexto, letterSpacing: 0.2 },
});
