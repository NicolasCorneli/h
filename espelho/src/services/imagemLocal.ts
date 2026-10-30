import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';

/** Lado maior das fotos de perfil enviadas: nítido em qualquer avatar, leve no envio. */
export const LADO_FOTO_DE_PERFIL = 1024;

/**
 * Reduz a foto no próprio aparelho antes de enviar, e regrava como JPEG.
 *
 * A foto da galeria de um celular atual pode ter 8 a 12 MB. O servidor recusa corpos
 * acima de 12 MB fechando a conexão ainda durante o envio, e o Android mostra isso como
 * "sem conexão", sem chegar resposta nenhuma. Reduzida, a foto fica com algumas centenas
 * de kB, e o formato passa a ser sempre JPEG (fotos HEIC do iPhone, por exemplo, viram
 * JPEG aqui). Se a redução falhar, segue a foto original: o servidor ainda valida.
 */
export async function reduzirParaEnvio(
  uri: string,
  largura?: number,
  altura?: number,
  ladoMaximo = LADO_FOTO_DE_PERFIL
): Promise<string> {
  try {
    const contexto = ImageManipulator.manipulate(uri);
    if (largura && altura && Math.max(largura, altura) > ladoMaximo) {
      contexto.resize(largura >= altura ? { width: ladoMaximo } : { height: ladoMaximo });
    } else if (!largura || !altura) {
      // Sem as dimensões, limita pela largura: a foto de perfil é recortada quadrada.
      contexto.resize({ width: ladoMaximo });
    }
    const imagem = await contexto.renderAsync();
    const salva = await imagem.saveAsync({ compress: 0.85, format: SaveFormat.JPEG });
    return salva.uri;
  } catch {
    return uri;
  }
}
