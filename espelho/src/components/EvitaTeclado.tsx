import { useEffect, useRef, useState } from 'react';
import {
  Keyboard,
  LayoutAnimation,
  Platform,
  StyleSheet,
  View,
  type KeyboardEvent,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

/**
 * Área de formulário que abre espaço para o teclado: o pé da área sobe até o topo do
 * teclado, então o rodapé (botão de salvar) fica logo acima dele e a rolagem encolhe. Ao
 * encolher, a rolagem mantém à vista o campo em foco.
 *
 * Substitui o `KeyboardAvoidingView`. No Android ele estava desligado (`behavior`
 * indefinido) contando que o sistema encolhesse a janela, o que deixou de acontecer:
 * o aplicativo ocupa a tela inteira (edge-to-edge, padrão do Expo), e o teclado passou a
 * cobrir o campo. No iOS ele dependia de um `keyboardVerticalOffset` fixo, que precisa
 * acertar a altura de tudo o que fica acima da área.
 *
 * Aqui a medida é a sobreposição real entre o fim da área, na janela, e o topo do
 * teclado. Se o sistema já tiver encolhido a janela, a sobreposição é zero e nada muda.
 * Na web o navegador cuida disso sozinho.
 */
export function EvitaTeclado({
  children,
  estilo,
}: {
  children: React.ReactNode;
  estilo?: StyleProp<ViewStyle>;
}) {
  const area = useRef<View>(null);
  const [folga, setFolga] = useState(0);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    const ios = Platform.OS === 'ios';

    const animar = (evento: KeyboardEvent) => {
      // No iOS o teclado anuncia a própria animação: a área acompanha o mesmo ritmo.
      if (ios && evento.duration) {
        LayoutAnimation.configureNext({
          duration: evento.duration,
          update: { duration: evento.duration, type: LayoutAnimation.Types.keyboard },
        });
      }
    };

    const abrir = Keyboard.addListener(ios ? 'keyboardWillShow' : 'keyboardDidShow', (evento) => {
      const topoDoTeclado = evento.endCoordinates.screenY;
      // O padding não muda o contorno da área: a medida é a mesma com ou sem folga.
      area.current?.measureInWindow((_x, y, _largura, altura) => {
        animar(evento);
        setFolga(Math.max(0, Math.round(y + altura - topoDoTeclado)));
      });
    });
    const fechar = Keyboard.addListener(ios ? 'keyboardWillHide' : 'keyboardDidHide', (evento) => {
      animar(evento);
      setFolga(0);
    });
    return () => {
      abrir.remove();
      fechar.remove();
    };
  }, []);

  return (
    <View ref={area} style={[styles.area, estilo, { paddingBottom: folga }]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  area: { flex: 1 },
});
