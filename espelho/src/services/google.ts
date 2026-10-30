import Constants, { ExecutionEnvironment } from 'expo-constants';
import { Platform } from 'react-native';

/**
 * Configuração do "Entrar com Google" no aplicativo.
 *
 * Os IDs de cliente OAuth são públicos por natureza (aparecem na tela de login do Google)
 * e vêm de variáveis `EXPO_PUBLIC_*`. Nenhum segredo fica no aplicativo: a verificação do
 * token é feita no servidor.
 *
 * O botão só aparece onde o login pode funcionar de fato:
 * - no navegador, com o ID de cliente web configurado;
 * - no Android e no iOS, com o ID de cliente da plataforma configurado e fora do Expo Go.
 *   O Expo Go não tem o identificador próprio do aplicativo, que o Google exige para
 *   devolver o resultado do login; ali é preciso um build de desenvolvimento.
 */
export const idsGoogle = {
  webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID || undefined,
  androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID || undefined,
  iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID || undefined,
};

export function googleConfiguradoNoAparelho(): boolean {
  if (Platform.OS === 'web') return !!idsGoogle.webClientId;
  if (Constants.executionEnvironment === ExecutionEnvironment.StoreClient) return false;
  return Platform.OS === 'android' ? !!idsGoogle.androidClientId : !!idsGoogle.iosClientId;
}
