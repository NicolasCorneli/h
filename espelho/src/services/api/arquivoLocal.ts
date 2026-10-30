import { File } from 'expo-file-system';

/**
 * Arquivo local do aparelho (foto da câmera ou da galeria) pronto para ir no `FormData`.
 *
 * Desde o Expo SDK 57 o `fetch` do aparelho é o `expo/fetch`, que não aceita mais o
 * formato antigo do React Native (`{ uri, name, type }`) e falhava com "Unsupported
 * FormDataPart implementation": nenhuma foto saía do celular. O `File` do
 * `expo-file-system` expõe os bytes do arquivo, que é o que o `expo/fetch` envia.
 *
 * Na web a foto já chega como `Blob` (ver `arquivoLocal.web.ts`).
 */
export function arquivoLocal(uri: string): Blob {
  return new File(uri);
}
