import { useState } from 'react';
import { Image, Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { cores } from '@/theme/tokens';

import { Hachura } from './Hachura';
import { Icone } from './Icone';
import { VisualizadorImagem } from './VisualizadorImagem';

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
  /**
   * Tocar abre a imagem em tela cheia, com zoom (`VisualizadorImagem`). O título aparece no
   * topo da tela cheia ("Foto original", "Simulação"). Sem ele, a imagem não responde ao
   * toque, como as miniaturas que já levam a outra tela.
   */
  ampliavel?: string;
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
  ampliavel,
}: Props) {
  const [ampliada, setAmpliada] = useState(false);
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

  const imagem = (
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
      {ampliavel ? (
        <View style={[styles.selo, styles.semToque]}>
          <Icone nome="ampliar" tamanho={14} cor={cores.escuroTexto} />
        </View>
      ) : null}
    </View>
  );

  if (!ampliavel) return imagem;
  return (
    <>
      <Pressable
        onPress={() => setAmpliada(true)}
        accessibilityRole="button"
        accessibilityLabel={`${ampliavel}: ampliar`}
        accessibilityHint="Abre a imagem em tela cheia, com zoom"
        style={({ pressed }) => pressed && styles.pressionada}>
        {imagem}
      </Pressable>
      {ampliada ? (
        <VisualizadorImagem uri={uri} titulo={ampliavel} descricao={descricao} aoFechar={() => setAmpliada(false)} />
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  // Sinal de que a imagem abre maior: canto inferior direito, sobre um fundo escuro.
  selo: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: cores.veu,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressionada: { opacity: 0.85 },
  // O toque passa para a imagem por baixo (forma de estilo: a propriedade está obsoleta na web).
  semToque: { pointerEvents: 'none' },
  moldura: {
    overflow: 'hidden',
    backgroundColor: cores.superficieAfundada,
  },
});
