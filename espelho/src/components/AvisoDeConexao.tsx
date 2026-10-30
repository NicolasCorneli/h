import { StyleSheet, Text, View } from 'react-native';

import { useStore } from '@/data/store';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { Botao } from './Botao';
import { Icone } from './Icone';

/**
 * Faixa de falha de conexão.
 *
 * Existe por um defeito encontrado na verificação de QA: com a API fora do ar, a lista
 * de clientes mostrava "Nenhum cliente cadastrado". O profissional lê isso como "meus
 * clientes desapareceram" — e a reação natural, recadastrar o que já existe, é
 * exatamente a errada. Lista vazia e lista indisponível são estados diferentes e
 * precisam de textos diferentes.
 */
export function AvisoDeConexao() {
  const { erroDeCarga, carregando, acoes } = useStore();

  if (!erroDeCarga) return null;

  return (
    <View style={styles.base} accessibilityRole="alert">
      <View style={styles.icone}>
        <Icone nome="alerta" tamanho={18} cor={cores.alertaTexto} />
      </View>
      <View style={styles.texto}>
        <Text style={[textos.corpoForte, styles.titulo]}>Sem conexão</Text>
        <Text style={[textos.meta, styles.detalhe]}>
          Seus dados estão guardados na sua conta e aparecem quando a conexão voltar. Nada
          foi perdido.
        </Text>
      </View>
      <Botao
        titulo="Tentar de novo"
        aoPressionar={() => {
          void acoes.recarregar();
        }}
        variante="secundaria"
        tamanho="medio"
        larguraTotal={false}
        carregando={carregando}
        rotuloAcessivel="Tentar carregar os dados de novo"
      />
    </View>
  );
}

/**
 * `true` quando a carga falhou — e, portanto, a tela não pode afirmar que não há dados.
 *
 * As listas usam isto para suprimir o estado vazio: dizer "nenhum cliente cadastrado"
 * quando o servidor não respondeu é afirmar algo que não se sabe.
 */
export function useFalhouAoCarregar(): boolean {
  const { erroDeCarga } = useStore();
  return erroDeCarga !== null;
}

const styles = StyleSheet.create({
  base: {
    marginHorizontal: espaco.xl,
    marginBottom: espaco.md,
    padding: espaco.lg,
    borderRadius: raios.cartao,
    backgroundColor: cores.alertaFundo,
    borderWidth: 1,
    borderColor: cores.alertaBorda,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    flexWrap: 'wrap',
  },
  icone: {
    width: 32,
    height: 32,
    borderRadius: raios.campo,
    backgroundColor: cores.superficie,
    alignItems: 'center',
    justifyContent: 'center',
  },
  texto: { flex: 1, minWidth: 180, gap: 2 },
  titulo: { color: cores.alertaTexto },
  detalhe: { color: cores.alertaTexto },
});
