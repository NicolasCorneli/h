import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Faixa, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Icone, type NomeIcone } from '@/components/Icone';
import { Marca } from '@/components/Marca';
import { textos, textosEscuros } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

/** O que o aplicativo faz hoje. Cada item corresponde a uma tela que existe. */
const ATIVIDADES: { icone: NomeIcone; titulo: string; texto: string }[] = [
  {
    icone: 'clientes',
    titulo: 'Clientes',
    texto: 'Cadastro com telefone, observações e a autorização de uso da imagem.',
  },
  {
    icone: 'agenda',
    titulo: 'Agenda',
    texto: 'Marque, confirme, remarque e cancele horários. O aplicativo avisa quando dois horários se chocam.',
  },
  {
    icone: 'okCirculo',
    titulo: 'Atendimentos',
    texto: 'Ao concluir um horário, o serviço feito entra no histórico do cliente.',
  },
  {
    icone: 'registrar',
    titulo: 'Histórico',
    texto: 'Tudo o que já foi feito com cada cliente, para retomar na próxima visita.',
  },
  {
    icone: 'simulacao',
    titulo: 'Simulações',
    texto: 'Com a autorização do cliente, mostre uma prévia do corte ou da cor antes de começar.',
  },
];

const PASSOS = ['Crie sua conta', 'Cadastre seus clientes', 'Marque o primeiro horário na agenda'];

/** Tela pública de abertura: o que é o aplicativo, para quem é e como começar. */
export default function Onboarding() {
  const router = useRouter();

  return (
    <Tela bordas={['top', 'bottom']}>
      <Faixa estilo={styles.topo}>
        <Marca />
        <Text style={[textosEscuros.display, styles.titulo]} accessibilityRole="header">
          Clientes, agenda e atendimentos no mesmo lugar.
        </Text>
        <Text style={textosEscuros.corpo}>
          Para profissionais de beleza que atendem por conta própria ou em salões pequenos.
        </Text>
      </Faixa>

      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
        <Text style={[textos.secao, styles.secao]}>O que você faz aqui</Text>
        <View style={styles.lista}>
          {ATIVIDADES.map((a) => (
            <View key={a.titulo} style={styles.item}>
              <View style={styles.icone}>
                <Icone nome={a.icone} tamanho={18} cor={cores.acaoTexto} />
              </View>
              <View style={styles.flex}>
                <Text style={textos.corpoForte}>{a.titulo}</Text>
                <Text style={textos.apoio}>{a.texto}</Text>
              </View>
            </View>
          ))}
        </View>

        <Text style={[textos.secao, styles.secao]}>Como começar</Text>
        <View style={styles.passos}>
          {PASSOS.map((passo, i) => (
            <View key={passo} style={styles.passo}>
              <View style={styles.numero}>
                <Text style={styles.numeroTexto}>{i + 1}</Text>
              </View>
              <Text style={[textos.corpo, styles.flex]}>{passo}</Text>
            </View>
          ))}
        </View>

        <Botao titulo="Criar conta" aoPressionar={() => router.push('/cadastro')} estilo={styles.botao} />
        <Botao titulo="Já tenho conta" variante="secundaria" aoPressionar={() => router.push('/login')} />
      </ScrollView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  topo: { paddingHorizontal: espaco.xxl, paddingTop: espaco.xl, paddingBottom: espaco.xxl, gap: espaco.md },
  titulo: { marginTop: espaco.lg },
  conteudo: { paddingHorizontal: espaco.xxl, paddingTop: espaco.xxl, paddingBottom: espaco.xxxl },
  secao: { marginBottom: espaco.md },
  lista: { gap: espaco.lg, marginBottom: espaco.xxl },
  item: { flexDirection: 'row', gap: espaco.md, alignItems: 'flex-start' },
  icone: {
    width: 36,
    height: 36,
    borderRadius: raios.campo,
    backgroundColor: cores.acaoSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  passos: { gap: espaco.md, marginBottom: espaco.xxl },
  passo: { flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  numero: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: cores.tinta,
    alignItems: 'center',
    justifyContent: 'center',
  },
  numeroTexto: { fontFamily: 'FamiljenGrotesk_700Bold', fontSize: 13, color: cores.escuroTexto },
  botao: { marginBottom: espaco.sm },
});
