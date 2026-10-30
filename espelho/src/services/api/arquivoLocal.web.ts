/**
 * Na web não há arquivo local: `prepararFotoParaEnvio` já transforma a foto em `Blob`
 * antes do envio. Este caminho só é alcançado por um erro de programação, e falha com uma
 * mensagem que diz isso em vez de enviar um formulário inválido.
 */
export function arquivoLocal(uri: string): Blob {
  throw new Error(`Foto sem Blob na web (${uri.slice(0, 30)}): use prepararFotoParaEnvio antes de enviar.`);
}
