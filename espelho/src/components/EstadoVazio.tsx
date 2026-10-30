import { StyleSheet, Text, View } from 'react-native';

import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { Botao } from './Botao';
import { Icone, type NomeIcone } from './Icone';

type Props = {
  icone: NomeIcone;
  titulo: string;
  texto: string;
  acao?: { titulo: string; aoPressionar: () => void };
  acaoSecundaria?: { titulo: string; aoPressionar: () => void };
  /** Usado quando o vazio é resultado de busca, não ausência de dados. */
  compacto?: boolean;
};

/** Estado vazio: explica por que não há nada e oferece a saída mais provável. */
export function EstadoVazio({ icone, titulo, texto, acao, acaoSecundaria, compacto = false }: Props) {
  return (
    <View style={[styles.base, compacto && styles.compacto]}>
      <View style={styles.icone}>
        <Icone nome={icone} tamanho={compacto ? 20 : 26} cor={cores.textoApoio} />
      </View>
      <Text style={[textos.secao, styles.titulo]}>{titulo}</Text>
      <Text style={[textos.corpo, styles.texto]}>{texto}</Text>
      {acao ? (
        <Botao
          titulo={acao.titulo}
          aoPressionar={acao.aoPressionar}
          tamanho="medio"
          larguraTotal={false}
          estilo={styles.acao}
        />
      ) : null}
      {acaoSecundaria ? (
        <Botao
          titulo={acaoSecundaria.titulo}
          aoPressionar={acaoSecundaria.aoPressionar}
          variante="texto"
          larguraTotal={false}
          estilo={styles.secundaria}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espaco.xxxl,
    paddingBottom: espaco.xxxl,
  },
  compacto: {
    // `flex: 0` no navegador vira `flex: 0 0 0%`: a caixa encolhia a quase nada dentro da
    // rolagem, o texto transbordava e o que vinha depois (o aviso do Início) cobria o
    // botão "Cadastrar primeiro cliente". Altura pelo conteúdo, sem crescer nem encolher.
    flexGrow: 0,
    flexShrink: 0,
    flexBasis: 'auto',
    paddingVertical: espaco.xxl,
    paddingHorizontal: espaco.xl,
  },
  icone: {
    width: 64,
    height: 64,
    borderRadius: raios.bloco,
    backgroundColor: cores.superficieSuave,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espaco.lg,
  },
  titulo: { textAlign: 'center', marginBottom: espaco.sm },
  texto: { textAlign: 'center' },
  // O Botao estreito se alinha à esquerda por padrão; aqui, como o texto, fica no centro.
  acao: { marginTop: espaco.xl, alignSelf: 'center' },
  secundaria: { alignSelf: 'center' },
});
