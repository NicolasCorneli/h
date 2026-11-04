import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Modal, Platform, Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { cores, espaco, LARGURA_MAXIMA, raios } from '@/theme/tokens';

import { Botao } from './Botao';

export type PropsSeletorData = {
  /** Dia em que o calendário abre. */
  valor: Date;
  aoEscolher: (data: Date) => void;
  minimo?: Date;
  maximo?: Date;
  rotuloAcessivel: string;
  children: React.ReactNode;
  estilo?: StyleProp<ViewStyle>;
};

/**
 * Torna o conteúdo (um título, uma caixa de campo) um botão que abre o calendário do
 * sistema para escolher um dia.
 *
 * No Android abre o diálogo de calendário nativo; no iOS, uma folha com o calendário
 * e o botão de confirmar; na web (SeletorData.web.tsx), o calendário do navegador.
 */
export function SeletorData({ valor, aoEscolher, minimo, maximo, rotuloAcessivel, children, estilo }: PropsSeletorData) {
  const [abertoIos, setAbertoIos] = useState(false);
  const [rascunho, setRascunho] = useState(valor);
  const { bottom } = useSafeAreaInsets();

  function abrir() {
    if (Platform.OS === 'android') {
      DateTimePickerAndroid.open({
        value: valor,
        mode: 'date',
        minimumDate: minimo,
        maximumDate: maximo,
        onChange: (evento, escolhida) => {
          if (evento.type === 'set' && escolhida) aoEscolher(escolhida);
        },
      });
      return;
    }
    setRascunho(valor);
    setAbertoIos(true);
  }

  return (
    <>
      <Pressable
        onPress={abrir}
        accessibilityRole="button"
        accessibilityLabel={rotuloAcessivel}
        style={({ pressed }) => [estilo, pressed && styles.pressionado]}>
        {children}
      </Pressable>

      {Platform.OS === 'ios' ? (
        <Modal visible={abertoIos} transparent animationType="slide" onRequestClose={() => setAbertoIos(false)}>
          <Pressable style={styles.fundo} onPress={() => setAbertoIos(false)} accessibilityLabel="Fechar calendário">
            <Pressable
              style={[styles.caixa, { paddingBottom: Math.max(espaco.xl, bottom + espaco.md) }]}
              onPress={() => undefined}>
              <DateTimePicker
                value={rascunho}
                mode="date"
                display="inline"
                locale="pt-BR"
                minimumDate={minimo}
                maximumDate={maximo}
                accentColor={cores.acao}
                onChange={(_evento, escolhida) => {
                  if (escolhida) setRascunho(escolhida);
                }}
              />
              <View style={styles.acoes}>
                <Botao
                  titulo="Escolher este dia"
                  icone="ok"
                  aoPressionar={() => {
                    setAbertoIos(false);
                    aoEscolher(rascunho);
                  }}
                />
              </View>
            </Pressable>
          </Pressable>
        </Modal>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  pressionado: { opacity: 0.85 },
  fundo: { flex: 1, backgroundColor: cores.veu, justifyContent: 'flex-end' },
  caixa: {
    backgroundColor: cores.fundo,
    borderTopLeftRadius: raios.bloco,
    borderTopRightRadius: raios.bloco,
    paddingHorizontal: espaco.lg,
    paddingTop: espaco.lg,
    width: '100%',
    maxWidth: LARGURA_MAXIMA,
    alignSelf: 'center',
  },
  acoes: { marginTop: espaco.md },
});
