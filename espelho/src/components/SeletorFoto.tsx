import * as ImagePicker from 'expo-image-picker';
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { useFeedback } from './Feedback';
import { Hachura } from './Hachura';
import { Icone } from './Icone';

export type FotoEscolhida = { uri: string; largura?: number; altura?: number };

type Props = {
  /** Foto atual (URL assinada ou arquivo local recém-escolhido). */
  fotoUri: string | null;
  titulo: string;
  ajuda: string;
  aoEscolher: (foto: FotoEscolhida) => void;
  aoRemover: () => void;
  ocupado?: boolean;
};

/**
 * Foto de perfil: mostrar, adicionar, trocar e remover. A mesma no cadastro do cliente e
 * em "Meus dados". A galeria abre com recorte quadrado, como o avatar.
 */
export function SeletorFoto({ fotoUri, titulo, ajuda, aoEscolher, aoRemover, ocupado = false }: Props) {
  const { avisar } = useFeedback();

  async function escolher() {
    const permissao = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permissao.granted) {
      avisar('Acesso à galeria não liberado', 'erro');
      return;
    }
    const resultado = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.9,
    });
    if (!resultado.canceled) {
      const foto = resultado.assets[0];
      aoEscolher({ uri: foto.uri, largura: foto.width, altura: foto.height });
    }
  }

  return (
    <View style={styles.linha}>
      <View>
        {fotoUri ? (
          <Image source={{ uri: fotoUri }} style={styles.imagem} accessible={false} />
        ) : (
          <Hachura legenda="sem foto" estilo={styles.imagem} />
        )}
        {ocupado ? (
          <View style={styles.carregando}>
            <ActivityIndicator color="#FFFFFF" />
          </View>
        ) : null}
      </View>
      <View style={styles.flex}>
        <Text style={textos.corpoForte}>{titulo}</Text>
        <Text style={textos.meta}>{ajuda}</Text>
        <View style={styles.acoes}>
          <Pressable
            onPress={() => void escolher()}
            disabled={ocupado}
            accessibilityRole="button"
            accessibilityLabel={fotoUri ? 'Trocar foto' : 'Adicionar foto'}
            style={styles.acao}>
            <Icone nome="galeria" tamanho={16} cor={cores.acaoTexto} />
            <Text style={textos.link}>{fotoUri ? 'Trocar foto' : 'Adicionar foto'}</Text>
          </Pressable>
          {fotoUri ? (
            <Pressable
              onPress={aoRemover}
              disabled={ocupado}
              accessibilityRole="button"
              accessibilityLabel="Remover foto"
              style={styles.acao}>
              <Icone nome="excluir" tamanho={16} cor={cores.erroTexto} />
              <Text style={[textos.link, styles.remover]}>Remover foto</Text>
            </Pressable>
          ) : null}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  linha: { flexDirection: 'row', gap: espaco.lg, alignItems: 'center' },
  imagem: { width: 80, height: 80, borderRadius: raios.cartao },
  carregando: {
    ...StyleSheet.absoluteFill,
    borderRadius: raios.cartao,
    backgroundColor: 'rgba(27,23,20,0.45)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  acoes: { flexDirection: 'row', flexWrap: 'wrap', columnGap: espaco.lg, marginTop: espaco.xs },
  acao: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm, minHeight: 44 },
  remover: { color: cores.erroTexto },
});
