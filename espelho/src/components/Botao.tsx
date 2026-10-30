import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, raios } from '@/theme/tokens';

import { Icone, type NomeIcone } from './Icone';

/**
 * Variantes:
 * - `primaria`   ação principal da tela (tinta sólida)
 * - `acao`       ação ligada à simulação (terracota)
 * - `secundaria` ação alternativa de mesmo peso (branca com borda)
 * - `perigo`     ação destrutiva confirmada
 * - `texto`      ação terciária, sem caixa
 *
 * `secundaria` existe para pares de decisão com o mesmo peso visual — é o que mantém
 * "Aceitar" e "Recusar" equivalentes na tela de consentimento, sem padrão manipulativo.
 */
type Variante = 'primaria' | 'acao' | 'secundaria' | 'perigo' | 'texto';
type Tamanho = 'grande' | 'medio' | 'pequeno';

type Props = {
  titulo: string;
  aoPressionar?: () => void;
  variante?: Variante;
  tamanho?: Tamanho;
  icone?: NomeIcone;
  desabilitado?: boolean;
  carregando?: boolean;
  /** Ocupa toda a largura disponível (padrão) ou apenas o necessário. */
  larguraTotal?: boolean;
  estilo?: StyleProp<ViewStyle>;
  rotuloAcessivel?: string;
  /** Texto lido por leitores de tela explicando por que está desabilitado. */
  dicaAcessivel?: string;
};

const ALTURAS: Record<Tamanho, number> = { grande: 52, medio: 46, pequeno: ALVO_TOQUE };

const PALETAS: Record<Variante, { fundo: string; texto: string; borda?: string }> = {
  primaria: { fundo: cores.tinta, texto: cores.escuroTexto },
  acao: { fundo: cores.acao, texto: '#FFFFFF' },
  secundaria: { fundo: cores.superficie, texto: cores.texto, borda: cores.bordaForte },
  perigo: { fundo: cores.superficie, texto: cores.erroTexto, borda: cores.erroBorda },
  texto: { fundo: 'transparent', texto: cores.acaoTexto },
};

export function Botao({
  titulo,
  aoPressionar,
  variante = 'primaria',
  tamanho = 'grande',
  icone,
  desabilitado = false,
  carregando = false,
  larguraTotal = true,
  estilo,
  rotuloAcessivel,
  dicaAcessivel,
}: Props) {
  const paleta = PALETAS[variante];
  const inativo = desabilitado || carregando;
  const corTexto = inativo && variante !== 'texto' ? cores.textoApoio : paleta.texto;

  const conteudo = (
    <View style={styles.conteudo}>
      {carregando ? (
        <ActivityIndicator size="small" color={corTexto} />
      ) : icone ? (
        <Icone nome={icone} tamanho={tamanho === 'pequeno' ? 16 : 18} cor={corTexto} />
      ) : null}
      <Text style={[textos.botao, tamanho === 'pequeno' && styles.rotuloPequeno, { color: corTexto }]}>
        {titulo}
      </Text>
    </View>
  );

  if (variante === 'texto') {
    return (
      <Pressable
        onPress={inativo ? undefined : aoPressionar}
        disabled={inativo}
        accessibilityRole="button"
        accessibilityState={{ disabled: inativo, busy: carregando }}
        accessibilityLabel={rotuloAcessivel ?? titulo}
        accessibilityHint={dicaAcessivel}
        style={({ pressed }) => [styles.botaoTexto, pressed && styles.pressionado, estilo]}>
        {conteudo}
      </Pressable>
    );
  }

  return (
    <Pressable
      onPress={inativo ? undefined : aoPressionar}
      disabled={inativo}
      accessibilityRole="button"
      accessibilityState={{ disabled: inativo, busy: carregando }}
      accessibilityLabel={rotuloAcessivel ?? titulo}
      accessibilityHint={dicaAcessivel}
      style={({ pressed }) => [
        styles.base,
        {
          height: ALTURAS[tamanho],
          alignSelf: larguraTotal ? 'stretch' : 'flex-start',
          backgroundColor: inativo ? cores.superficieAfundada : paleta.fundo,
          borderWidth: paleta.borda ? 1 : 0,
          borderColor: inativo ? cores.borda : paleta.borda,
        },
        pressed && !inativo && styles.pressionado,
        estilo,
      ]}>
      {conteudo}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: raios.campo,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espaco.xl,
  },
  conteudo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.sm,
  },
  rotuloPequeno: {
    fontSize: 13,
  },
  botaoTexto: {
    minHeight: ALVO_TOQUE,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espaco.sm,
  },
  pressionado: {
    opacity: 0.82,
  },
});
