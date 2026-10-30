import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Avatar, Etiqueta, Grupo, ItemGrupo, Selo, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { BotaoGoogle, LogoGoogle, useGoogleDisponivel } from '@/components/BotaoGoogle';
import { useFeedback } from '@/components/Feedback';
import { Icone } from '@/components/Icone';
import { NOME_APP } from '@/components/Marca';
import { useStore } from '@/data/store';
import { textos, textosEscuros } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta } from '@/utils/datas';

/** Conta do profissional, ajustes e porta de entrada da privacidade. */
export default function Perfil() {
  const router = useRouter();
  const { estado, acoes } = useStore();
  const { confirmar, avisar } = useFeedback();

  const ciencia = estado.cienciaProfissional;
  const usuario = estado.usuario;
  const googleDisponivel = useGoogleDisponivel();

  async function desconectarGoogle() {
    const ok = await confirmar({
      titulo: 'Desconectar a conta Google?',
      mensagem: 'Você continua entrando com e-mail e senha. Dá para conectar de novo quando quiser.',
      rotuloConfirmar: 'Desconectar',
      rotuloCancelar: 'Manter conectada',
    });
    if (!ok) return;
    try {
      await acoes.desconectarGoogle();
      avisar('Conta Google desconectada');
    } catch (falha) {
      avisar(falha instanceof Error ? falha.message : 'Não foi possível desconectar agora.', 'erro');
    }
  }

  async function sair() {
    const ok = await confirmar({
      titulo: 'Sair da conta?',
      mensagem: 'Seus dados continuam guardados na sua conta. Para voltar a usar, é só entrar de novo.',
      rotuloConfirmar: 'Sair',
      rotuloCancelar: 'Continuar conectado',
    });
    if (!ok) return;
    await acoes.sair();
    avisar('Sessão encerrada');
    router.replace('/login');
  }

  return (
    <Tela folha={false}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.cabecalho}>
          <View style={styles.identidade}>
            <Avatar
              nome={estado.usuario?.nome ?? ''}
              fotoUri={estado.usuario?.fotoUri}
              cor={cores.acao}
              tamanho={60}
              quadrado
            />
            <View style={styles.flex}>
              <Text style={textosEscuros.titulo} accessibilityRole="header">
                {estado.usuario?.nome ?? ''}
              </Text>
              <Text style={textosEscuros.apoio}>
                {estado.usuario?.email ?? ''} · {estado.usuario?.atuacao ?? ''}
              </Text>
            </View>
          </View>

          <View style={styles.numeros}>
            <Numero valor={estado.clientes.length} rotulo="clientes" />
            <Numero valor={estado.simulacoes.length} rotulo="simulações" />
            <Numero valor={estado.historico.length} rotulo="atendimentos" />
          </View>
        </View>

        <View style={styles.corpo}>
          <Etiqueta estilo={styles.etiqueta}>Imagem e privacidade</Etiqueta>
          <Grupo>
            <ItemGrupo
              aoPressionar={() => router.push('/privacidade')}
              rotuloAcessivel="Privacidade e meus dados">
              <Icone nome="privacidade" tamanho={18} />
              <View style={styles.flex}>
                <Text style={textos.corpoForte}>Privacidade e meus dados</Text>
                <Text style={textos.meta}>Consentimentos, retenção e exclusão (LGPD)</Text>
              </View>
              <Icone nome="chevron" tamanho={18} />
            </ItemGrupo>

            <ItemGrupo
              aoPressionar={() => router.push('/responsabilidades')}
              rotuloAcessivel="Termos e responsabilidades">
              <Icone nome="documento" tamanho={18} />
              <View style={styles.flex}>
                <Text style={textos.corpoForte}>Termos e responsabilidades</Text>
                <Text style={textos.meta}>
                  O que explicar ao cliente antes de registrar o consentimento
                </Text>
              </View>
              {ciencia.aceita && ciencia.registradaEm ? (
                <Selo texto={dataCurta(ciencia.registradaEm)} tom="sucesso" icone="ok" />
              ) : (
                <Selo texto="pendente" tom="alerta" icone="alerta" />
              )}
            </ItemGrupo>

            <ItemGrupo>
              <Icone nome="info" tamanho={18} />
              <View style={styles.flex}>
                <Text style={textos.corpoForte}>Como ler uma simulação</Text>
                <Text style={textos.meta}>
                  A imagem é uma aproximação visual: textura, volume e histórico químico mudam o
                  resultado. Use para conversar, não como promessa.
                </Text>
              </View>
            </ItemGrupo>
          </Grupo>

          <Etiqueta estilo={styles.etiqueta}>Conta</Etiqueta>
          <Grupo>
            <ItemGrupo aoPressionar={() => router.push('/meus-dados')} rotuloAcessivel="Meus dados">
              <Icone nome="cliente" tamanho={18} />
              <View style={styles.flex}>
                <Text style={textos.corpoForte}>Meus dados</Text>
                <Text style={textos.meta}>Nome e forma de atuação</Text>
              </View>
              <Icone nome="chevron" tamanho={18} />
            </ItemGrupo>
            <ItemGrupo
              aoPressionar={() => router.push('/seguranca')}
              rotuloAcessivel="Senha e sessões">
              <Icone nome="cadeado" tamanho={18} />
              <View style={styles.flex}>
                <Text style={textos.corpoForte}>Senha e sessões</Text>
                <Text style={textos.meta}>Trocar a senha ou sair de todos os aparelhos</Text>
              </View>
              <Icone nome="chevron" tamanho={18} />
            </ItemGrupo>
            <ItemGrupo>
              <LogoGoogle />
              <View style={styles.flex}>
                <Text style={textos.corpoForte}>Conta Google</Text>
                <Text style={textos.meta}>
                  {usuario?.googleVinculado
                    ? usuario.temSenha
                      ? 'Conectada: você pode entrar com o Google ou com a senha'
                      : 'Sua conta entra pelo Google'
                    : googleDisponivel
                      ? 'Conecte para entrar sem digitar a senha'
                      : 'Login com Google não configurado neste aparelho'}
                </Text>
              </View>
              {usuario?.googleVinculado ? <Selo texto="conectada" tom="sucesso" icone="ok" /> : null}
            </ItemGrupo>
          </Grupo>
          {googleDisponivel && usuario && !usuario.googleVinculado ? (
            <View style={styles.acaoGoogle}>
              <BotaoGoogle
                rotulo="Conectar conta Google"
                aoReceberToken={async (idToken, nonce) => {
                  await acoes.conectarGoogle(idToken, nonce);
                  avisar('Conta Google conectada');
                }}
                aoFalhar={(mensagem) => avisar(mensagem, 'erro')}
              />
            </View>
          ) : null}
          {usuario?.googleVinculado && usuario.temSenha ? (
            <Botao
              titulo="Desconectar conta Google"
              variante="texto"
              aoPressionar={desconectarGoogle}
              estilo={styles.acaoGoogle}
            />
          ) : null}

          <Botao
            titulo="Sair da conta"
            variante="perigo"
            icone="sair"
            tamanho="medio"
            aoPressionar={sair}
            estilo={styles.sair}
          />
          <Text style={[textos.meta, styles.rodape]}>{NOME_APP} · protótipo de TCC, 2026</Text>
        </View>
      </ScrollView>
    </Tela>
  );
}

function Numero({ valor, rotulo }: { valor: number; rotulo: string }) {
  return (
    <View style={styles.numero}>
      <Text style={styles.numeroValor}>{valor}</Text>
      <Text style={textosEscuros.meta}>{rotulo}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  acaoGoogle: { marginTop: espaco.md },
  scroll: { flexGrow: 1 },
  flex: { flex: 1 },
  cabecalho: {
    backgroundColor: cores.base,
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.lg,
    paddingBottom: espaco.xl,
  },
  identidade: { flexDirection: 'row', gap: espaco.lg, alignItems: 'center' },
  numeros: {
    flexDirection: 'row',
    gap: 1,
    marginTop: espaco.xl,
    borderRadius: raios.campo,
    overflow: 'hidden',
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  numero: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.05)',
    paddingHorizontal: espaco.md,
    paddingVertical: espaco.md,
  },
  numeroValor: {
    fontFamily: 'InstrumentSerif_400Regular',
    fontSize: 24,
    lineHeight: 26,
    color: cores.escuroTexto,
  },
  // Folha clara do conteúdo, logo abaixo do topo escuro.
  corpo: {
    flexGrow: 1,
    backgroundColor: cores.fundo,
    borderTopLeftRadius: raios.bloco,
    borderTopRightRadius: raios.bloco,
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.lg,
    paddingBottom: espaco.xxxl,
  },
  etiqueta: { marginTop: espaco.lg, marginBottom: espaco.sm },
  sair: { marginTop: espaco.xl },
  rodape: { textAlign: 'center', marginTop: espaco.lg },
});
