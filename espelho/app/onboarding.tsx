import { useRouter } from 'expo-router';
import { Linking, Platform, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native';

import { Faixa, Tela, useTelaDividida } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Icone, type NomeIcone } from '@/components/Icone';
import { Marca } from '@/components/Marca';
import { URL_BASE } from '@/services/api';
import { textos, textosEscuros } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

/**
 * O que o aplicativo faz hoje. Cada item corresponde a uma tela que existe.
 *
 * "Atendimentos" saiu desta apresentação: o registro do atendimento continua no
 * aplicativo (é o que alimenta o Histórico), só não é mais apresentado como um item à parte.
 */
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

/**
 * Política de privacidade: página estática do site (`public/politica-de-privacidade.html`),
 * aberta sem conta. É o endereço informado ao Google para o login com Google, que pede um
 * link para ela na página inicial.
 */
const CAMINHO_DA_POLITICA = '/politica-de-privacidade.html';

/** No navegador, o próprio site; no celular, o servidor do build. Sem servidor, sem link. */
function enderecoDaPolitica(): string | null {
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    return `${window.location.origin}${CAMINHO_DA_POLITICA}`;
  }
  return process.env.EXPO_PUBLIC_API_URL ? `${URL_BASE}${CAMINHO_DA_POLITICA}` : null;
}

/** Abaixo desta largura de conteúdo, os itens ficam um embaixo do outro. */
const LARGURA_DUAS_COLUNAS = 420;

/** Tela pública de abertura: o que é o aplicativo, para quem é e como começar. */
export default function Onboarding() {
  const router = useRouter();

  return (
    <Tela bordas={['top', 'bottom']} dividida>
      <Faixa estilo={styles.topo}>
        <Marca />
        <Text style={[textosEscuros.display, styles.titulo]} accessibilityRole="header">
          Clientes, agenda e atendimentos no mesmo lugar.
        </Text>
        <Text style={textosEscuros.corpo}>
          Para profissionais de beleza que atendem por conta própria ou em salões pequenos.
        </Text>
      </Faixa>

      <Conteudo>
        <Text style={[textos.secao, styles.secao]}>O que você faz aqui</Text>
        <Atividades />

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
        <Politica />
      </Conteudo>
    </Tela>
  );
}

function Politica() {
  const endereco = enderecoDaPolitica();
  if (!endereco) return null;
  return (
    <Botao
      titulo="Política de privacidade"
      variante="texto"
      tamanho="pequeno"
      larguraTotal={false}
      estilo={styles.politica}
      aoPressionar={() => {
        Linking.openURL(endereco).catch(() => undefined);
      }}
    />
  );
}

function Conteudo({ children }: { children: React.ReactNode }) {
  const dividida = useTelaDividida();
  return (
    <ScrollView
      contentContainerStyle={[styles.conteudo, dividida && styles.conteudoCentrado]}
      showsVerticalScrollIndicator={false}>
      {children}
    </ScrollView>
  );
}

/**
 * Quatro itens: no celular, um por linha; com espaço, uma grade 2 x 2 de cartões, que
 * mantém o bloco equilibrado (com cinco itens a grade sobrava um sozinho na última linha).
 */
function Atividades() {
  const { width } = useWindowDimensions();
  const dividida = useTelaDividida();
  // No computador o conteúdo tem no máximo 480px; no celular, a largura da tela.
  const largura = dividida ? 480 : Math.min(width, 560);
  const grade = largura - espaco.xxl * 2 >= LARGURA_DUAS_COLUNAS;
  return (
    <View style={[styles.lista, grade && styles.grade]}>
      {ATIVIDADES.map((a) => (
        <View key={a.titulo} style={[styles.item, grade && styles.itemGrade]}>
          <View style={styles.icone}>
            <Icone nome={a.icone} tamanho={18} cor={cores.acaoTexto} />
          </View>
          <View style={grade ? undefined : styles.flex}>
            <Text style={textos.corpoForte}>{a.titulo}</Text>
            <Text style={textos.apoio}>{a.texto}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  topo: { paddingHorizontal: espaco.xxl, paddingTop: espaco.xl, paddingBottom: espaco.xxl, gap: espaco.md },
  titulo: { marginTop: espaco.lg },
  conteudo: { paddingHorizontal: espaco.xxl, paddingTop: espaco.xxl, paddingBottom: espaco.xxxl },
  conteudoCentrado: { flexGrow: 1, justifyContent: 'center' },
  secao: { marginBottom: espaco.md },
  lista: { gap: espaco.md, marginBottom: espaco.xxl },
  grade: { flexDirection: 'row', flexWrap: 'wrap' },
  item: {
    flexDirection: 'row',
    gap: espaco.md,
    alignItems: 'flex-start',
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.bordaSuave,
    borderRadius: raios.cartao,
    padding: espaco.lg,
  },
  /** Duas por linha: a base de 45% com crescimento divide a sobra, já descontado o espaço. */
  itemGrade: { flexDirection: 'column', flexGrow: 1, flexBasis: '45%' },
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
    backgroundColor: cores.acaoSuave,
    borderWidth: 1,
    borderColor: cores.acaoBorda,
    alignItems: 'center',
    justifyContent: 'center',
  },
  numeroTexto: { fontFamily: 'FamiljenGrotesk_700Bold', fontSize: 13, color: cores.acaoTexto },
  botao: { marginBottom: espaco.sm },
  politica: { alignSelf: 'center', marginTop: espaco.md },
});
