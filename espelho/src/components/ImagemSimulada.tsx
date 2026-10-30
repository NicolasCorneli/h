import { useState } from 'react';
import { Image, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { Hachura } from './Hachura';

type Props = {
  /** URL assinada vinda do servidor, válida por poucos minutos. */
  uri: string | null | undefined;
  legenda?: string;
  /** Deixa o placeholder claro, para a coluna "depois". */
  claro?: boolean;
  estilo?: StyleProp<ViewStyle>;
  raio?: number;
  /** `cobrir` recorta para preencher (miniaturas); `conter` mostra a imagem inteira. */
  ajuste?: 'cobrir' | 'conter';
  /** Texto alternativo. Sem ele a imagem é tratada como decorativa. */
  descricao?: string;
};

/**
 * Exibe uma imagem do servidor.
 *
 * Antes da integração este componente *fabricava* o resultado, pintando a cor escolhida
 * sobre a foto do cliente. Agora a imagem de saída é a que o provedor de IA gerou, salva
 * no storage e entregue por URL assinada de curta duração — nada é simulado na
 * renderização. Sem `uri` (ainda processando, ou imagem já excluída), mostra o
 * placeholder hachurado.
 */
export function ImagemSimulada({
  uri,
  legenda,
  claro,
  estilo,
  raio = 16,
  ajuste = 'cobrir',
  descricao,
}: Props) {
  // Endereço que falhou ao carregar (arquivo ausente no servidor, assinatura vencida).
  // Guardado por endereço: uma URL nova, renovada pelo servidor, tenta de novo.
  const [falhou, setFalhou] = useState<string | null>(null);

  if (!uri) {
    return <Hachura legenda={legenda} claro={claro} estilo={[{ borderRadius: raio }, estilo]} />;
  }

  if (falhou === uri) {
    // Antes ficava um quadro vazio, sem explicação.
    return (
      <Hachura
        legenda="Imagem indisponível"
        claro={claro}
        estilo={[{ borderRadius: raio }, estilo]}
      />
    );
  }

  return (
    <View style={[styles.moldura, { borderRadius: raio }, estilo]}>
      <Image
        source={{ uri }}
        style={StyleSheet.absoluteFill}
        // `cobrir` preenche a moldura e corta o excesso — serve para miniatura, onde a
        // grade precisa ficar regular. `conter` mostra a imagem inteira, na proporção
        // original, que é o que a visualização individual exige.
        resizeMode={ajuste === 'conter' ? 'contain' : 'cover'}
        onError={() => setFalhou(uri)}
        accessible={!!descricao}
        accessibilityLabel={descricao}
        alt={descricao}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  moldura: {
    overflow: 'hidden',
    backgroundColor: '#E7DDD3',
  },
});
