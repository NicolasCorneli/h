import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, LARGURA_MAXIMA, raios } from '@/theme/tokens';

import { Icone, type NomeIcone } from './Icone';

export type AcaoFolha = {
  icone: NomeIcone;
  rotulo: string;
  descricao?: string;
  aoPressionar: () => void;
  destrutiva?: boolean;
};

type Props = {
  visivel: boolean;
  titulo: string;
  subtitulo?: string;
  acoes: AcaoFolha[];
  aoFechar: () => void;
};

/** Folha inferior com as ações possíveis para um item — evita telas intermediárias. */
export function FolhaAcoes({ visivel, titulo, subtitulo, acoes, aoFechar }: Props) {
  return (
    <Modal visible={visivel} transparent animationType="slide" onRequestClose={aoFechar}>
      <Pressable style={styles.fundo} onPress={aoFechar} accessibilityLabel="Fechar ações">
        <Pressable style={styles.caixa} onPress={() => undefined}>
          <View style={styles.puxador} />
          <Text style={textos.secao} accessibilityRole="header">
            {titulo}
          </Text>
          {subtitulo ? <Text style={[textos.apoio, styles.subtitulo]}>{subtitulo}</Text> : null}

          <View style={styles.acoes}>
            {acoes.map((acao) => (
              <Pressable
                key={acao.rotulo}
                onPress={() => {
                  aoFechar();
                  acao.aoPressionar();
                }}
                accessibilityRole="button"
                accessibilityLabel={acao.rotulo}
                accessibilityHint={acao.descricao}
                style={({ pressed }) => [styles.acao, pressed && styles.pressionada]}>
                <View style={styles.acaoIcone}>
                  <Icone
                    nome={acao.icone}
                    tamanho={18}
                    cor={acao.destrutiva ? cores.erroTexto : cores.textoSecundario}
                  />
                </View>
                <View style={styles.acaoTexto}>
                  <Text style={[textos.corpoForte, acao.destrutiva && styles.destrutiva]}>
                    {acao.rotulo}
                  </Text>
                  {acao.descricao ? <Text style={textos.meta}>{acao.descricao}</Text> : null}
                </View>
                <Icone nome="chevron" tamanho={18} />
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: 'rgba(27,23,20,0.5)', justifyContent: 'flex-end' },
  caixa: {
    backgroundColor: cores.fundo,
    borderTopLeftRadius: raios.bloco,
    borderTopRightRadius: raios.bloco,
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.md,
    paddingBottom: espaco.xxxl,
    width: '100%',
    maxWidth: LARGURA_MAXIMA,
    alignSelf: 'center',
  },
  puxador: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: cores.bordaForte,
    alignSelf: 'center',
    marginBottom: espaco.lg,
  },
  subtitulo: { marginTop: espaco.xs },
  acoes: { marginTop: espaco.lg, gap: espaco.sm },
  acao: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.bordaSuave,
    borderRadius: raios.cartao,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.md,
    minHeight: ALVO_TOQUE + 12,
  },
  acaoIcone: {
    width: 36,
    height: 36,
    borderRadius: raios.campo,
    backgroundColor: cores.superficieSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  acaoTexto: { flex: 1 },
  destrutiva: { color: cores.erroTexto },
  pressionada: { opacity: 0.85 },
});
