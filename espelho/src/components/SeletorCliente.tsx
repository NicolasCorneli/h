import { Modal, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useClientes } from '@/data/store';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { Avatar, BotaoIcone, Grupo, ItemGrupo } from './Basicos';
import { Icone } from './Icone';

type Props = {
  visivel: boolean;
  clienteIdAtual: string | null;
  aoEscolher: (clienteId: string) => void;
  aoFechar: () => void;
  titulo?: string;
  nota?: string;
};

/** Folha inferior para vincular uma simulação ou um agendamento a um cliente. */
export function SeletorCliente({
  visivel,
  clienteIdAtual,
  aoEscolher,
  aoFechar,
  titulo = 'Vincular a um cliente',
  nota,
}: Props) {
  const clientes = useClientes();

  return (
    <Modal visible={visivel} animationType="slide" transparent onRequestClose={aoFechar}>
      <View style={styles.fundo}>
        <View style={styles.caixa}>
          <View style={styles.topo}>
            <Text style={textos.secao}>{titulo}</Text>
            <BotaoIcone icone="fechar" aoPressionar={aoFechar} rotuloAcessivel="Fechar seleção de cliente" />
          </View>
          <ScrollView contentContainerStyle={styles.lista}>
            {clientes.length === 0 ? (
              <Text style={textos.apoio}>
                Nenhum cliente cadastrado ainda. Cadastre um para poder vincular.
              </Text>
            ) : (
              <Grupo>
                {clientes.map((c) => (
                  <ItemGrupo
                    key={c.id}
                    aoPressionar={() => aoEscolher(c.id)}
                    rotuloAcessivel={`Escolher ${c.nome}`}>
                    <Avatar nome={c.nome} fotoUri={c.fotoUri} />
                    <Text style={[textos.corpoForte, styles.flex]}>{c.nome}</Text>
                    {clienteIdAtual === c.id ? <Icone nome="ok" tamanho={18} cor={cores.sucesso} /> : null}
                  </ItemGrupo>
                ))}
              </Grupo>
            )}
            {nota ? <Text style={[textos.apoio, styles.nota]}>{nota}</Text> : null}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: 'rgba(12,10,9,0.55)', justifyContent: 'flex-end' },
  caixa: {
    backgroundColor: cores.fundo,
    borderTopLeftRadius: raios.bloco,
    borderTopRightRadius: raios.bloco,
    maxHeight: '75%',
    paddingBottom: 24,
  },
  topo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: espaco.xl,
    paddingVertical: espaco.lg,
  },
  lista: { paddingHorizontal: espaco.xl, paddingBottom: espaco.md },
  nota: { marginTop: espaco.md },

  flex: { flex: 1 },
});
