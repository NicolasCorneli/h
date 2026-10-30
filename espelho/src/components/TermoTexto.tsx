import { StyleSheet, Text, View } from 'react-native';

import type { Termo } from '@/data/termos';
import { textos } from '@/theme/textos';
import { cores, espaco, fontes, raios } from '@/theme/tokens';

/**
 * Corpo de um termo versionado, em texto somente leitura.
 *
 * Nunca use campos de entrada para exibir este conteúdo: o cliente precisa ver
 * exatamente o texto ao qual está dando consentimento, sem possibilidade de alteração
 * pela interface.
 */
export function TermoTexto({ termo }: { termo: Termo }) {
  return (
    <View>
      <Text style={[textos.display, styles.titulo]}>{termo.titulo}</Text>
      <Text style={styles.resumo}>{termo.resumo}</Text>

      <View style={styles.secoes}>
        {termo.secoes.map((secao) => (
          <View key={secao.titulo} style={[styles.secao, secao.destaque && styles.secaoDestaque]}>
            <Text style={[styles.secaoTitulo, secao.destaque && styles.secaoTituloDestaque]}>
              {secao.titulo}
            </Text>
            <Text style={styles.secaoTexto}>{secao.texto}</Text>
          </View>
        ))}
      </View>

      <Text style={styles.versao}>
        Versão {termo.versao} · vigente desde {formatar(termo.vigenteDesde)}
      </Text>
    </View>
  );
}

function formatar(iso: string): string {
  const [ano, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${ano}`;
}

const styles = StyleSheet.create({
  titulo: { marginBottom: espaco.md },
  resumo: {
    fontFamily: fontes.sans,
    fontSize: 15,
    lineHeight: 23,
    color: cores.textoSecundario,
    marginBottom: espaco.xl,
  },
  secoes: { gap: espaco.md },
  secao: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.bordaSuave,
    borderRadius: raios.cartao,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.lg,
  },
  secaoDestaque: {
    backgroundColor: cores.alertaFundo,
    borderColor: cores.alertaBorda,
  },
  secaoTitulo: {
    fontFamily: fontes.sansSemi,
    fontSize: 15,
    lineHeight: 20,
    color: cores.texto,
    marginBottom: espaco.xs,
  },
  secaoTituloDestaque: { color: cores.alertaTexto },
  secaoTexto: {
    fontFamily: fontes.sans,
    fontSize: 14,
    lineHeight: 21,
    color: cores.textoTerciario,
  },
  versao: {
    fontFamily: fontes.mono,
    fontSize: 11,
    color: cores.textoApoio,
    marginTop: espaco.lg,
  },
});
