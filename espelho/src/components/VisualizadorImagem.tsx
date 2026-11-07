import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Image,
  Modal,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
  type GestureResponderEvent,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { textosEscuros } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, raios } from '@/theme/tokens';

import { Icone, type NomeIcone } from './Icone';

const ZOOM_MAXIMO = 4;
const ZOOM_DO_TOQUE_DUPLO = 2.5;
const INTERVALO_TOQUE_DUPLO_MS = 280;

type Props = {
  /** URL assinada que já está na tela: a mesma, sem pedir outra ao servidor. */
  uri: string | null;
  titulo: string;
  /** Texto alternativo da imagem. */
  descricao?: string;
  aoFechar: () => void;
};

const distancia = (e: GestureResponderEvent) => {
  const [a, b] = e.nativeEvent.touches;
  return Math.hypot(a.pageX - b.pageX, a.pageY - b.pageY);
};

/**
 * O estado do zoom e os gestos, fora do React: os valores animados mudam a cada quadro do
 * gesto, e passar por estado do React a cada movimento travaria a tela.
 */
function criarZoom(aoMudarZoom: (zoom: number) => void) {
  const escala = new Animated.Value(1);
  const x = new Animated.Value(0);
  const y = new Animated.Value(0);
  const atual = { escala: 1, x: 0, y: 0 };
  const area = { largura: 0, altura: 0 };
  const gesto = { distanciaInicial: 0, escalaInicial: 1, xInicial: 0, yInicial: 0, ultimoToque: 0 };

  function aplicar(novaEscala: number, nx: number, ny: number, animado = false) {
    const s = Math.min(ZOOM_MAXIMO, Math.max(1, novaEscala));
    // Quanto a imagem ampliada pode andar sem mostrar fundo vazio dos dois lados.
    const limiteX = ((s - 1) * area.largura) / 2;
    const limiteY = ((s - 1) * area.altura) / 2;
    atual.escala = s;
    atual.x = Math.min(limiteX, Math.max(-limiteX, nx));
    atual.y = Math.min(limiteY, Math.max(-limiteY, ny));
    aoMudarZoom(Math.round(s * 10) / 10);
    if (animado) {
      Animated.parallel([
        Animated.timing(escala, { toValue: atual.escala, duration: 180, useNativeDriver: false }),
        Animated.timing(x, { toValue: atual.x, duration: 180, useNativeDriver: false }),
        Animated.timing(y, { toValue: atual.y, duration: 180, useNativeDriver: false }),
      ]).start();
    } else {
      escala.setValue(atual.escala);
      x.setValue(atual.x);
      y.setValue(atual.y);
    }
  }

  const respondedor = PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: (e) => {
      const agora = Date.now();
      if (agora - gesto.ultimoToque < INTERVALO_TOQUE_DUPLO_MS) {
        aplicar(atual.escala > 1.05 ? 1 : ZOOM_DO_TOQUE_DUPLO, 0, 0, true);
        gesto.ultimoToque = 0;
        return;
      }
      gesto.ultimoToque = agora;
      gesto.distanciaInicial = e.nativeEvent.touches.length >= 2 ? distancia(e) : 0;
      gesto.escalaInicial = atual.escala;
      gesto.xInicial = atual.x;
      gesto.yInicial = atual.y;
    },
    onPanResponderMove: (e, g) => {
      if (e.nativeEvent.touches.length >= 2) {
        if (!gesto.distanciaInicial) {
          gesto.distanciaInicial = distancia(e);
          gesto.escalaInicial = atual.escala;
        }
        aplicar((gesto.escalaInicial * distancia(e)) / gesto.distanciaInicial, atual.x, atual.y);
        return;
      }
      if (atual.escala > 1) aplicar(atual.escala, gesto.xInicial + g.dx, gesto.yInicial + g.dy);
    },
    onPanResponderRelease: () => {
      gesto.distanciaInicial = 0;
      if (atual.escala < 1.05) aplicar(1, 0, 0, true);
    },
  });

  return {
    escala,
    x,
    y,
    respondedor,
    medir(largura: number, altura: number) {
      area.largura = largura;
      area.altura = altura;
    },
    /** Botões de zoom: mais ou menos meio passo, mantendo o centro. */
    passo(delta: number) {
      aplicar(atual.escala + delta, atual.x, atual.y, true);
    },
  };
}

/**
 * A imagem em tela cheia, na proporção original, com zoom.
 *
 * Abre por cima da tela atual (as telas não mudam de rota): fechar volta exatamente ao
 * ponto em que se estava, e o botão voltar do Android fecha. A imagem é a mesma URL
 * assinada que a miniatura já usa, então não há outro pedido ao servidor nem endereço
 * novo; se a assinatura tiver vencido, o erro diz isso.
 *
 * Zoom: pinça com dois dedos (até 4x), arrastar com um dedo quando ampliada, toque duplo
 * alterna entre 1x e 2,5x. Os botões de zoom fazem o mesmo e servem no navegador (que não
 * tem pinça com mouse) e para quem não faz gestos. Sem biblioteca de gestos: o projeto não
 * tem uma, e esta tela não justifica um módulo nativo novo.
 */
export function VisualizadorImagem({ uri, titulo, descricao, aoFechar }: Props) {
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const [estado, setEstado] = useState<'carregando' | 'pronta' | 'erro'>('carregando');
  const [zoomTexto, setZoomTexto] = useState(1);

  // O zoom vive fora do React (valores animados e a conta dos gestos), criado uma vez.
  const [zoom] = useState(() => criarZoom(setZoomTexto));

  const larguraArea = width;
  const alturaArea = height - insets.top - insets.bottom - 128;
  // Os limites de deslocamento dependem do tamanho da área, que muda ao girar a tela.
  useEffect(() => zoom.medir(larguraArea, alturaArea), [zoom, larguraArea, alturaArea]);

  const botao = (icone: NomeIcone, rotulo: string, aoPressionar: () => void, desativado = false) => (
    <Pressable
      onPress={aoPressionar}
      disabled={desativado}
      accessibilityRole="button"
      accessibilityLabel={rotulo}
      accessibilityState={{ disabled: desativado }}
      hitSlop={8}
      style={({ pressed }) => [styles.botao, desativado && styles.desativado, pressed && styles.pressionado]}>
      <Icone nome={icone} tamanho={20} cor={cores.escuroTexto} />
    </Pressable>
  );

  return (
    <Modal visible animationType="fade" onRequestClose={aoFechar} statusBarTranslucent navigationBarTranslucent>
      <View style={[styles.fundo, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
        <View style={styles.topo}>
          <Text style={[textosEscuros.secao, styles.titulo]} numberOfLines={1} accessibilityRole="header">
            {titulo}
          </Text>
          {botao('fechar', 'Fechar a imagem ampliada', aoFechar)}
        </View>

        <View style={styles.area} {...zoom.respondedor.panHandlers}>
          {uri && estado !== 'erro' ? (
            <Animated.View
              style={[
                { width: larguraArea, height: alturaArea },
                { transform: [{ translateX: zoom.x }, { translateY: zoom.y }, { scale: zoom.escala }] },
              ]}>
              <Image
                source={{ uri }}
                style={StyleSheet.absoluteFill}
                resizeMode="contain"
                onLoad={() => setEstado('pronta')}
                onError={() => setEstado('erro')}
                accessible
                accessibilityLabel={descricao ?? titulo}
                alt={descricao ?? titulo}
              />
            </Animated.View>
          ) : null}
          {uri && estado === 'carregando' ? (
            <View style={[styles.sobreposicao, styles.semToque]}>
              <ActivityIndicator color={cores.escuroTexto} size="large" />
              <Text style={textosEscuros.meta}>Abrindo a imagem…</Text>
            </View>
          ) : null}
          {!uri || estado === 'erro' ? (
            <View style={styles.sobreposicao} accessibilityLiveRegion="polite">
              <Icone nome="alerta" tamanho={22} cor={cores.escuroTexto} />
              <Text style={[textosEscuros.corpo, styles.mensagem]}>
                {uri
                  ? 'Não foi possível abrir a imagem. O link de acesso dura poucos minutos: feche e abra de novo.'
                  : 'Esta imagem não está mais guardada.'}
              </Text>
            </View>
          ) : null}
        </View>

        {estado === 'pronta' ? (
          <View style={styles.rodape}>
            {botao('menos', 'Diminuir o zoom', () => zoom.passo(-0.5), zoomTexto <= 1)}
            <Text style={[textosEscuros.meta, styles.zoom]} accessibilityLabel={`Zoom de ${zoomTexto} vezes`}>
              {zoomTexto.toLocaleString('pt-BR')}x
            </Text>
            {botao('mais', 'Aumentar o zoom', () => zoom.passo(0.5), zoomTexto >= ZOOM_MAXIMO)}
            <Text style={[textosEscuros.meta, styles.dica]}>Pinça ou toque duplo para ampliar</Text>
          </View>
        ) : null}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: cores.camera },
  topo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.sm,
    minHeight: ALVO_TOQUE + espaco.lg,
  },
  titulo: { flex: 1 },
  area: { flex: 1, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  sobreposicao: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    gap: espaco.md,
    paddingHorizontal: espaco.xxl,
  },
  mensagem: { textAlign: 'center' },
  // O toque passa para a imagem por baixo (forma de estilo: a propriedade está obsoleta na web).
  semToque: { pointerEvents: 'none' },
  rodape: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    flexWrap: 'wrap',
    gap: espaco.md,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.md,
  },
  botao: {
    width: ALVO_TOQUE,
    height: ALVO_TOQUE,
    borderRadius: raios.campo,
    backgroundColor: cores.baseBorda,
    alignItems: 'center',
    justifyContent: 'center',
  },
  desativado: { opacity: 0.4 },
  pressionado: { opacity: 0.8 },
  zoom: { minWidth: 36, textAlign: 'center' },
  dica: { width: '100%', textAlign: 'center' },
});
