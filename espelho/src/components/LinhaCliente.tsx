import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Cliente } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { Avatar } from './Basicos';
import { Icone } from './Icone';

type Props = {
  cliente: Cliente | undefined;
  /** Sem esta função a linha só mostra o cliente: ele não pode ser trocado ali. */
  aoPressionar?: () => void;
  comErro?: boolean;
};

/** Cliente do formulário: avatar e nome. Trocável na agenda; fixo no atendimento. */
export function LinhaCliente({ cliente, aoPressionar, comErro = false }: Props) {
  const conteudo = (
    <>
      {cliente ? (
        <Avatar nome={cliente.nome} fotoUri={cliente.fotoUri} tamanho={40} />
      ) : (
        <View style={styles.avatarVazio}>
          <Icone nome="cliente" tamanho={18} />
        </View>
      )}
      <View style={styles.flex}>
        <Text style={textos.etiqueta}>Cliente</Text>
        <Text style={textos.corpoForte}>{cliente?.nome ?? 'Escolher cliente'}</Text>
      </View>
      {aoPressionar ? <Icone nome="chevron" tamanho={18} /> : null}
    </>
  );

  if (!aoPressionar) {
    return (
      <View style={styles.linha} accessibilityLabel={`Cliente ${cliente?.nome ?? ''}`}>
        {conteudo}
      </View>
    );
  }
  return (
    <Pressable
      onPress={aoPressionar}
      accessibilityRole="button"
      accessibilityLabel={cliente ? `Cliente ${cliente.nome}. Toque para trocar` : 'Escolher cliente'}
      style={({ pressed }) => [styles.linha, comErro && styles.linhaErro, pressed && styles.pressionado]}>
      {conteudo}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  linha: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.campo,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.md,
    minHeight: 64,
  },
  linhaErro: { borderColor: cores.erro },
  avatarVazio: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: cores.superficieAfundada,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressionado: { opacity: 0.85 },
});
