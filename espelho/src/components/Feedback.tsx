import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Animated, Modal, Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import { textos } from '@/theme/textos';
import { cores, elevacao, espaco, LARGURA_MAXIMA, raios } from '@/theme/tokens';

import { Botao } from './Botao';
import { Icone, type NomeIcone } from './Icone';

// Na web não há módulo de animação nativo: pedir o driver nativo gera aviso a cada
// animação e cai para JS de qualquer forma. No aparelho, o driver nativo fica.
const DRIVER_NATIVO = Platform.OS !== 'web';

/**
 * Feedback do sistema: confirmação de ações destrutivas e aviso de conclusão.
 *
 * Substitui o `window.confirm` do navegador (que ficava fora da identidade do app e
 * não existe no celular) e cobre a heurística de visibilidade do status: toda gravação
 * passa a ter confirmação visível.
 */

type PedidoConfirmacao = {
  titulo: string;
  mensagem: string;
  rotuloConfirmar?: string;
  rotuloCancelar?: string;
  destrutivo?: boolean;
};

type Contexto = {
  /** Mostra um aviso temporário no rodapé. */
  avisar: (mensagem: string, tom?: 'sucesso' | 'erro') => void;
  /** Abre o diálogo e resolve com a escolha do usuário. */
  confirmar: (pedido: PedidoConfirmacao) => Promise<boolean>;
};

const FeedbackContext = createContext<Contexto | null>(null);

type EstadoConfirmacao = PedidoConfirmacao & { resolver: (v: boolean) => void };

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [aviso, setAviso] = useState<{ mensagem: string; tom: 'sucesso' | 'erro' } | null>(null);
  const [confirmacao, setConfirmacao] = useState<EstadoConfirmacao | null>(null);
  const opacidade = useRef(new Animated.Value(0)).current;
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const avisar = useCallback(
    (mensagem: string, tom: 'sucesso' | 'erro' = 'sucesso') => {
      if (timer.current) clearTimeout(timer.current);
      setAviso({ mensagem, tom });
      Animated.timing(opacidade, { toValue: 1, duration: 160, useNativeDriver: DRIVER_NATIVO }).start();
      timer.current = setTimeout(() => {
        Animated.timing(opacidade, { toValue: 0, duration: 220, useNativeDriver: DRIVER_NATIVO }).start(() =>
          setAviso(null)
        );
      }, 2600);
    },
    [opacidade]
  );

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    []
  );

  const confirmar = useCallback(
    (pedido: PedidoConfirmacao) =>
      new Promise<boolean>((resolve) => setConfirmacao({ ...pedido, resolver: resolve })),
    []
  );

  const responder = (valor: boolean) => {
    confirmacao?.resolver(valor);
    setConfirmacao(null);
  };

  const valor = useMemo(() => ({ avisar, confirmar }), [avisar, confirmar]);

  return (
    <FeedbackContext.Provider value={valor}>
      {children}

      {aviso ? (
        <Animated.View
          accessibilityLiveRegion="polite"
          style={[
            styles.aviso,
            elevacao.flutuante,
            { opacity: opacidade, pointerEvents: 'none' },
          ]}>
          <Icone
            nome={aviso.tom === 'sucesso' ? 'okCirculo' : 'alerta'}
            tamanho={16}
            cor={aviso.tom === 'sucesso' ? '#8FE0BE' : '#F0B9AE'}
          />
          <Text style={styles.avisoTexto}>{aviso.mensagem}</Text>
        </Animated.View>
      ) : null}

      <Modal
        visible={!!confirmacao}
        transparent
        animationType="fade"
        onRequestClose={() => responder(false)}>
        <Pressable style={styles.fundo} onPress={() => responder(false)} accessibilityLabel="Fechar">
          <Pressable style={styles.caixa} onPress={() => undefined}>
            <View
              style={[
                styles.iconeCaixa,
                { backgroundColor: confirmacao?.destrutivo ? cores.erroFundo : cores.superficieSuave },
              ]}>
              <Icone
                nome={(confirmacao?.destrutivo ? 'alerta' : 'info') as NomeIcone}
                tamanho={20}
                cor={confirmacao?.destrutivo ? cores.erroTexto : cores.textoSecundario}
              />
            </View>
            <Text style={[textos.secao, styles.titulo]} accessibilityRole="header">
              {confirmacao?.titulo}
            </Text>
            <Text style={[textos.corpo, styles.mensagem]}>{confirmacao?.mensagem}</Text>

            <Botao
              titulo={confirmacao?.rotuloConfirmar ?? 'Confirmar'}
              variante={confirmacao?.destrutivo ? 'perigo' : 'primaria'}
              aoPressionar={() => responder(true)}
            />
            <Botao
              titulo={confirmacao?.rotuloCancelar ?? 'Cancelar'}
              variante="texto"
              aoPressionar={() => responder(false)}
              estilo={styles.cancelar}
            />
          </Pressable>
        </Pressable>
      </Modal>
    </FeedbackContext.Provider>
  );
}

export function useFeedback(): Contexto {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error('useFeedback precisa estar dentro de <FeedbackProvider>');
  return ctx;
}

const styles = StyleSheet.create({
  aviso: {
    position: 'absolute',
    left: espaco.xl,
    right: espaco.xl,
    bottom: 100,
    maxWidth: LARGURA_MAXIMA - espaco.xl * 2,
    alignSelf: 'center',
    backgroundColor: cores.tinta,
    borderRadius: raios.campo,
    paddingVertical: espaco.md,
    paddingHorizontal: espaco.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
  },
  avisoTexto: {
    flex: 1,
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 14,
    lineHeight: 19,
    color: cores.escuroTexto,
  },
  fundo: {
    flex: 1,
    backgroundColor: 'rgba(27,23,20,0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: espaco.xl,
  },
  caixa: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: cores.fundo,
    borderRadius: raios.bloco,
    padding: espaco.xxl,
  },
  iconeCaixa: {
    width: 44,
    height: 44,
    borderRadius: raios.campo,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espaco.lg,
  },
  titulo: { marginBottom: espaco.sm },
  mensagem: { marginBottom: espaco.xl },
  cancelar: { marginTop: espaco.xs },
});
