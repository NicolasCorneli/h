import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Modal, Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { Botao } from './Botao';
import { Campo } from './Campo';
import { Icone } from './Icone';

type Props = {
  visivel: boolean;
  /** Ex.: "Maria Souza, 24/10 às 15:00". */
  resumo: string;
  aoFechar: () => void;
  /** Lança erro com mensagem legível quando o servidor recusa. */
  aoConfirmar: (motivo: string) => Promise<void>;
};

/**
 * Confirmação do cancelamento, com motivo opcional.
 *
 * Cancelar não apaga: o agendamento continua na agenda, marcado como cancelado, com a
 * data do cancelamento e o motivo, e o horário fica livre para outro cliente.
 */
export function DialogoCancelamento({ visivel, resumo, aoFechar, aoConfirmar }: Props) {
  const [motivo, setMotivo] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (visivel) {
      setMotivo('');
      setErro(null);
      setEnviando(false);
    }
  }, [visivel]);

  async function confirmar() {
    setEnviando(true);
    setErro(null);
    try {
      await aoConfirmar(motivo.trim());
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Não foi possível cancelar o agendamento.');
      setEnviando(false);
    }
  }

  return (
    <Modal visible={visivel} transparent animationType="fade" onRequestClose={aoFechar}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.flex}>
        <Pressable style={styles.fundo} onPress={aoFechar} accessibilityLabel="Fechar">
          <Pressable style={styles.caixa} onPress={() => undefined}>
            <View style={styles.iconeCaixa}>
              <Icone nome="alerta" tamanho={20} cor={cores.erroTexto} />
            </View>
            <Text style={[textos.secao, styles.titulo]} accessibilityRole="header">
              Cancelar este agendamento?
            </Text>
            <Text style={[textos.corpo, styles.mensagem]}>
              {resumo}. O registro continua na agenda como cancelado e o horário fica livre.
            </Text>

            <Campo
              rotulo="Motivo (opcional)"
              valor={motivo}
              aoMudar={(t) => setMotivo(t.slice(0, 300))}
              placeholder="Por exemplo: cliente pediu para remarcar"
              estilo={styles.campo}
            />

            {erro ? (
              <Text style={styles.erro} accessibilityRole="alert">
                {erro}
              </Text>
            ) : null}

            <Botao
              titulo={enviando ? 'Cancelando…' : 'Cancelar agendamento'}
              variante="perigo"
              carregando={enviando}
              aoPressionar={confirmar}
            />
            <Botao
              titulo="Manter agendamento"
              variante="texto"
              aoPressionar={aoFechar}
              estilo={styles.manter}
            />
          </Pressable>
        </Pressable>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  fundo: {
    flex: 1,
    backgroundColor: 'rgba(27,23,20,0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: espaco.xl,
  },
  caixa: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: cores.fundo,
    borderRadius: raios.bloco,
    padding: espaco.xxl,
  },
  iconeCaixa: {
    width: 44,
    height: 44,
    borderRadius: raios.campo,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espaco.lg,
    backgroundColor: cores.erroFundo,
  },
  titulo: { marginBottom: espaco.sm },
  mensagem: { marginBottom: espaco.lg },
  campo: { marginBottom: espaco.lg },
  erro: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 14,
    color: cores.erroTexto,
    marginBottom: espaco.md,
  },
  manter: { marginTop: espaco.xs },
});
