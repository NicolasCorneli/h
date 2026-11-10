import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ALVO_TOQUE, cores, espaco, fontes, raios } from '@/theme/tokens';

export type OpcaoSegmentada<T extends string> = { valor: T; rotulo: string };

/**
 * Escolha única entre poucas opções curtas, lado a lado e com a mesma largura (por
 * exemplo "Quero mudar" ou "Manter o corte atual"; "Feminino", "Masculino" ou "Neutro").
 *
 * A opção escolhida é preenchida com a cor de ação: dá para ver de longe qual vale. Cada
 * opção é um `radio` dentro de um `radiogroup`, com o estado no atributo ARIA, que é o que
 * chega ao leitor de tela no navegador. O texto pode quebrar linha em telas estreitas: a
 * altura cresce, a largura não.
 */
export function EscolhaSegmentada<T extends string>({
  opcoes,
  valor,
  aoEscolher,
  rotuloAcessivel,
}: {
  opcoes: readonly OpcaoSegmentada<T>[];
  valor: T;
  aoEscolher: (valor: T) => void;
  rotuloAcessivel: string;
}) {
  return (
    <View style={styles.grupo} accessibilityRole="radiogroup" accessibilityLabel={rotuloAcessivel}>
      {opcoes.map((opcao) => {
        const ativa = opcao.valor === valor;
        return (
          <Pressable
            key={opcao.valor}
            onPress={() => aoEscolher(opcao.valor)}
            accessibilityRole="radio"
            accessibilityState={{ checked: ativa }}
            aria-checked={ativa}
            accessibilityLabel={opcao.rotulo}
            style={({ pressed }) => [styles.opcao, ativa && styles.opcaoAtiva, pressed && !ativa && styles.pressionada]}>
            <Text style={[styles.texto, ativa && styles.textoAtivo]}>{opcao.rotulo}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  grupo: {
    flexDirection: 'row',
    gap: espaco.xs,
    padding: espaco.xs,
    borderRadius: raios.campo + espaco.xs,
    backgroundColor: cores.superficieAfundada,
  },
  opcao: {
    flex: 1,
    minWidth: 0,
    minHeight: ALVO_TOQUE,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espaco.sm,
    paddingVertical: espaco.xs,
    borderRadius: raios.campo,
  },
  opcaoAtiva: { backgroundColor: cores.acao },
  pressionada: { backgroundColor: cores.bordaSuave },
  texto: {
    fontFamily: fontes.sansMedio,
    fontSize: 14,
    lineHeight: 18,
    color: cores.textoSecundario,
    textAlign: 'center',
  },
  textoAtivo: { fontFamily: fontes.sansSemi, color: '#FFFFFF' },
});
