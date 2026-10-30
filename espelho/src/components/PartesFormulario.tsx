import { StyleSheet, Text, View } from 'react-native';

import { cores, espaco, raios } from '@/theme/tokens';

import { Icone } from './Icone';

/** Caixa de erro ao pé do formulário, com a mensagem que impede salvar. */
export function CaixaDeErro({ mensagem }: { mensagem: string | null }) {
  if (!mensagem) return null;
  return (
    <View style={styles.caixa} accessibilityRole="alert">
      <Icone nome="alerta" tamanho={16} cor={cores.erroTexto} />
      <Text style={styles.texto}>{mensagem}</Text>
    </View>
  );
}

/** Faixa fixa no rodapé, onde fica o botão de salvar. */
export function Rodape({ children }: { children: React.ReactNode }) {
  return <View style={styles.rodape}>{children}</View>;
}

/** Espaçamentos comuns aos formulários de agendamento e de atendimento. */
export const estilosFormulario = StyleSheet.create({
  flex: { flex: 1 },
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xl },
  linhaDatas: { flexDirection: 'row', gap: espaco.md, marginTop: espaco.md },
  hora: { width: 136 },
  etiqueta: { marginTop: espaco.xl, marginBottom: espaco.sm },
  campoAbaixo: { marginTop: espaco.md },
  dica: { marginTop: espaco.sm },
});

const styles = StyleSheet.create({
  caixa: {
    flexDirection: 'row',
    gap: espaco.sm,
    alignItems: 'flex-start',
    backgroundColor: cores.erroFundo,
    borderWidth: 1,
    borderColor: cores.erroBorda,
    borderRadius: raios.campo,
    padding: espaco.md,
    marginTop: espaco.lg,
  },
  texto: {
    flex: 1,
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 14,
    color: cores.erroTexto,
  },
  rodape: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.md,
    paddingBottom: espaco.lg,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
  },
});
