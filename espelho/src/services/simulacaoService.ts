/**
 * Pré-checagem da fotografia, no aparelho.
 *
 * É só conveniência de interface: avisar na hora da captura evita uma subida inútil e
 * poupa o tempo do atendimento. **A validação que vale é a do servidor**, que decodifica
 * a imagem, mede luminância e procura um rosto antes de acionar o provedor de IA — e
 * recusa com 422 (`foto_recusada`) quando não passa. As duas listas de problemas têm o
 * mesmo formato, de modo que a tela `simulacao/recusada.tsx` exibe qualquer uma delas.
 */

export type FotoCapturada = { uri: string; width: number; height: number };

export type ProblemaFoto = { titulo: string; detalhe: string };

/** Mesmos limites configurados no servidor (IMAGEM_MIN_LADO e IMAGEM_PROPORCAO_MAX). */
const MENOR_LADO_MINIMO = 480;
const PROPORCAO_MAXIMA = 1.35;

export function validarFoto(foto: FotoCapturada): ProblemaFoto[] {
  const problemas: ProblemaFoto[] = [];

  const menorLado = Math.min(foto.width, foto.height);
  if (menorLado > 0 && menorLado < MENOR_LADO_MINIMO) {
    problemas.push({
      titulo: 'Resolução baixa',
      detalhe: `A foto tem menos de ${MENOR_LADO_MINIMO} px no menor lado; o recorte do cabelo sai serrilhado.`,
    });
  }

  const proporcao = foto.height > 0 ? foto.width / foto.height : 1;
  if (proporcao > PROPORCAO_MAXIMA) {
    problemas.push({
      titulo: 'Enquadramento deitado',
      detalhe: 'Use uma foto em retrato, com o rosto ocupando o centro do quadro.',
    });
  }

  return problemas;
}

/** Converte os `detalhes` de um erro da API na lista que a tela de recusa já exibe. */
export function problemasDoErro(detalhes: Record<string, unknown>[]): ProblemaFoto[] {
  return detalhes
    .filter((item) => typeof item.titulo === 'string')
    .map((item) => ({
      titulo: String(item.titulo),
      detalhe: typeof item.detalhe === 'string' ? item.detalhe : '',
    }));
}
