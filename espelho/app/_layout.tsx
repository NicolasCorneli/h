import {
  FamiljenGrotesk_400Regular,
  FamiljenGrotesk_500Medium,
  FamiljenGrotesk_600SemiBold,
  FamiljenGrotesk_700Bold,
} from '@expo-google-fonts/familjen-grotesk';
import {
  InstrumentSerif_400Regular,
  InstrumentSerif_400Regular_Italic,
} from '@expo-google-fonts/instrument-serif';
import { useFonts } from 'expo-font';
import { Stack, useRouter, useSegments } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import * as WebBrowser from 'expo-web-browser';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { FeedbackProvider } from '@/components/Feedback';
import { RascunhoProvider } from '@/data/rascunho';
import { StoreProvider, useStore } from '@/data/store';
import { cores } from '@/theme/tokens';

SplashScreen.preventAutoHideAsync().catch(() => undefined);

// No navegador, o login do Google abre numa janela à parte e volta para o endereço do
// aplicativo. Esta chamada entrega o resultado à janela que pediu e fecha a outra; fora
// desse retorno, não faz nada.
WebBrowser.maybeCompleteAuthSession();

/** Telas que fazem sentido sem conta: a porta de entrada, a abertura, entrar e criar conta. */
const ROTAS_PUBLICAS = new Set(['onboarding', 'login', 'cadastro']);

/**
 * Sem sessão, nenhuma tela interna fica aberta. Antes, abrir um endereço como `/agenda`
 * sem ter entrado (ou ficar com o aplicativo aberto depois de a sessão acabar) mostrava a
 * tela vazia, como se a conta não tivesse dados, e cada ação falhava com "token inválido".
 */
function GuardaDeSessao() {
  const { estado, carregando, erroDeCarga } = useStore();
  const segmentos = useSegments();
  const router = useRouter();
  const primeiro = segmentos[0];
  const publica = primeiro === undefined || ROTAS_PUBLICAS.has(primeiro);

  useEffect(() => {
    if (carregando || estado.autenticado || publica) return;
    // Com a carga falhada (sem rede) a sessão existe, só não carregou: a porta de entrada
    // mostra "Sem conexão" com "Tentar de novo", em vez de mandar criar conta.
    router.replace(erroDeCarga ? '/' : '/onboarding');
  }, [carregando, estado.autenticado, erroDeCarga, publica, router]);

  return null;
}

export default function LayoutRaiz() {
  const [fontesCarregadas] = useFonts({
    InstrumentSerif_400Regular,
    InstrumentSerif_400Regular_Italic,
    FamiljenGrotesk_400Regular,
    FamiljenGrotesk_500Medium,
    FamiljenGrotesk_600SemiBold,
    FamiljenGrotesk_700Bold,
  });

  useEffect(() => {
    if (fontesCarregadas) SplashScreen.hideAsync().catch(() => undefined);
  }, [fontesCarregadas]);

  if (!fontesCarregadas) return <View style={{ flex: 1, backgroundColor: cores.base }} />;

  return (
    <SafeAreaProvider>
      <StoreProvider>
        <RascunhoProvider>
          <FeedbackProvider>
          {/* A base do aplicativo é escura: ícones claros na barra de status. */}
          <StatusBar style="light" />
          <GuardaDeSessao />
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: cores.base },
              animation: 'fade',
            }}
          />
          </FeedbackProvider>
        </RascunhoProvider>
      </StoreProvider>
    </SafeAreaProvider>
  );
}
