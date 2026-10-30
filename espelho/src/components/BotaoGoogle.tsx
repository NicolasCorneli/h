import * as Google from 'expo-auth-session/providers/google';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { autenticacao } from '@/services/api';
import { googleConfiguradoNoAparelho, idsGoogle } from '@/services/google';
import { cores, espaco, raios } from '@/theme/tokens';

/**
 * O botão só aparece quando as duas pontas estão prontas: o aplicativo tem o ID de cliente
 * desta plataforma e o servidor tem o Google ligado. Sem isso, nada aparece, em vez de um
 * botão que falharia ao ser tocado.
 */
export function useGoogleDisponivel(): boolean {
  const noAparelho = googleConfiguradoNoAparelho();
  const [noServidor, setNoServidor] = useState(false);
  useEffect(() => {
    if (!noAparelho) return;
    let ativo = true;
    autenticacao
      .provedores()
      .then((p) => ativo && setNoServidor(p.google))
      .catch(() => ativo && setNoServidor(false));
    return () => {
      ativo = false;
    };
  }, [noAparelho]);
  return noAparelho && noServidor;
}

type Props = {
  rotulo: string;
  /** Recebe o ID token do Google; lança erro com mensagem legível quando o servidor recusa. */
  aoReceberToken: (idToken: string, nonce?: string) => Promise<void>;
  aoFalhar: (mensagem: string) => void;
  desabilitado?: boolean;
};

/**
 * Botão "Entrar com Google", no padrão visual do Google (fundo claro, logotipo colorido).
 *
 * Abre a tela do próprio Google; a senha da conta Google nunca passa pelo aplicativo.
 * O que volta é o ID token, que segue para o servidor conferir. Só deve ser montado quando
 * `googleConfiguradoNoAparelho()` for verdadeiro: sem ID de cliente o hook não funciona.
 */
export function BotaoGoogle({ rotulo, aoReceberToken, aoFalhar, desabilitado }: Props) {
  const [pedido, resposta, abrir] = Google.useIdTokenAuthRequest({
    ...idsGoogle,
    selectAccount: true,
    language: 'pt-BR',
  });
  const [ocupado, setOcupado] = useState(false);
  const tratado = useRef<unknown>(null);

  useEffect(() => {
    if (!resposta || tratado.current === resposta) return;
    tratado.current = resposta;
    if (resposta.type === 'success') {
      const idToken = resposta.params.id_token;
      if (!idToken) {
        setOcupado(false);
        aoFalhar('O Google não devolveu a confirmação da conta. Tente de novo.');
        return;
      }
      aoReceberToken(idToken, pedido?.nonce)
        .catch((falha: unknown) =>
          aoFalhar(falha instanceof Error ? falha.message : 'Não foi possível entrar com o Google.')
        )
        .finally(() => setOcupado(false));
    } else if (resposta.type === 'error') {
      setOcupado(false);
      aoFalhar('O Google recusou o pedido de login. Tente de novo.');
    } else {
      // Janela fechada ou login desistido: nada a avisar.
      setOcupado(false);
    }
  }, [resposta, pedido, aoReceberToken, aoFalhar]);

  const inativo = !pedido || ocupado || desabilitado;

  return (
    <Pressable
      onPress={() => {
        setOcupado(true);
        void abrir().catch(() => {
          setOcupado(false);
          aoFalhar('Não foi possível abrir o login do Google.');
        });
      }}
      disabled={inativo}
      accessibilityRole="button"
      accessibilityLabel={rotulo}
      accessibilityState={{ disabled: inativo, busy: ocupado }}
      style={({ pressed }) => [styles.botao, inativo && styles.inativo, pressed && styles.pressionado]}>
      <View style={styles.conteudo}>
        {ocupado ? <ActivityIndicator size="small" color={cores.texto} /> : <LogoGoogle />}
        <Text style={styles.texto}>{rotulo}</Text>
      </View>
    </Pressable>
  );
}

/** Logotipo oficial do Google (o "G" em quatro cores), decorativo. */
export function LogoGoogle() {
  return (
    // O logotipo é decorativo: o nome do botão já diz o que ele faz.
    <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Svg width={18} height={18} viewBox="0 0 48 48">
      <Path
        fill="#EA4335"
        d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
      />
      <Path
        fill="#4285F4"
        d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
      />
      <Path
        fill="#FBBC05"
        d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
      />
      <Path
        fill="#34A853"
        d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
      />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  botao: {
    minHeight: 52,
    borderRadius: raios.campo,
    borderWidth: 1,
    borderColor: '#747775',
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    paddingHorizontal: espaco.lg,
  },
  conteudo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: espaco.md },
  texto: { fontFamily: 'FamiljenGrotesk_600SemiBold', fontSize: 16, color: '#1F1F1F' },
  inativo: { opacity: 0.6 },
  pressionado: { backgroundColor: '#F2F2F2' },
});
