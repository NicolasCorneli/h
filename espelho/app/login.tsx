import { useRouter } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Faixa, Tela } from '@/components/Basicos';
import { BotaoGoogle, useGoogleDisponivel } from '@/components/BotaoGoogle';
import { Botao } from '@/components/Botao';
import { Campo } from '@/components/Campo';
import { Icone } from '@/components/Icone';
import { Marca } from '@/components/Marca';
import { useStore } from '@/data/store';
import { ErroApi } from '@/services/api';
import { textos, textosEscuros } from '@/theme/textos';
import { cores, espaco } from '@/theme/tokens';

/** T1 — RF01. Autenticação real: o token da sessão fica no armazenamento seguro. */
export default function Login() {
  const router = useRouter();
  const { acoes } = useStore();
  const googleDisponivel = useGoogleDisponivel();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [erroGoogle, setErroGoogle] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function autenticar() {
    if (!email.trim() || !senha) {
      setErro('Informe e-mail e senha.');
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await acoes.entrar(email.trim(), senha);
      // O redirecionamento para a ciência das responsabilidades ou para o painel é
      // decidido em app/index.tsx, a partir do estado carregado do servidor.
      router.replace('/');
    } catch (falha) {
      const apiErro = falha instanceof ErroApi ? falha : null;
      setErro(apiErro?.message ?? 'Não foi possível entrar agora.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Tela bordas={['top', 'bottom']}>
      <Faixa estilo={styles.topo}>
        <Marca />
        <Text style={[textosEscuros.display, styles.titulo]} accessibilityRole="header">
          Entrar
        </Text>
        <Text style={[textosEscuros.corpo, styles.subtitulo]}>
          Seus clientes e sua agenda ficam guardados na sua conta, visíveis só para você.
        </Text>
      </Faixa>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}>
        <ScrollView
          contentContainerStyle={styles.conteudo}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>

          <View style={styles.campos}>
            <Campo
              rotulo="E-mail"
              valor={email}
              aoMudar={setEmail}
              placeholder="voce@salao.com"
              tipoTeclado="email-address"
              autoCapitalize="none"
            />
            <Campo
              rotulo="Senha"
              valor={senha}
              aoMudar={setSenha}
              segredo
              alternarSegredo
              autoCapitalize="none"
              erro={erro}
            />
          </View>

          <Botao
            titulo={enviando ? 'Entrando…' : 'Entrar'}
            carregando={enviando}
            aoPressionar={autenticar}
            estilo={styles.botao}
          />

          {googleDisponivel ? (
            <>
              <View style={styles.divisor}>
                <View style={styles.linha} />
                <Text style={textos.meta}>ou</Text>
                <View style={styles.linha} />
              </View>
              <BotaoGoogle
                rotulo="Entrar com Google"
                desabilitado={enviando}
                aoReceberToken={async (idToken, nonce) => {
                  setErro(null);
                  setErroGoogle(null);
                  await acoes.entrarComGoogle(idToken, nonce);
                  router.replace('/');
                }}
                aoFalhar={setErroGoogle}
              />
              {erroGoogle ? (
                <View style={styles.erroGoogle} accessibilityRole="alert">
                  <Icone nome="alerta" tamanho={16} cor={cores.erroTexto} />
                  <Text style={styles.erroGoogleTexto}>{erroGoogle}</Text>
                </View>
              ) : null}
            </>
          ) : null}

          {/* A recuperação de senha por e-mail não existe nesta versão; o botão que só
              avisava isso saiu, para não oferecer uma ação que não acontece. */}
          <View style={styles.rodape}>
            <Text style={textos.apoio}>Ainda não tem conta?</Text>
            <Botao
              titulo="Criar conta"
              variante="texto"
              larguraTotal={false}
              aoPressionar={() => router.push('/cadastro')}
            />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  topo: { paddingHorizontal: espaco.xxl, paddingTop: espaco.xl, paddingBottom: espaco.xxl },
  titulo: { marginTop: espaco.xl },
  subtitulo: { marginTop: espaco.sm },
  conteudo: {
    flexGrow: 1,
    paddingHorizontal: espaco.xxl,
    paddingTop: espaco.xxl,
    paddingBottom: espaco.xxxl,
  },
  campos: { gap: espaco.md },
  botao: { marginTop: espaco.xl },
  rodape: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: espaco.xs,
    marginTop: espaco.lg,
  },
  erroGoogle: { flexDirection: 'row', gap: espaco.sm, alignItems: 'flex-start', marginTop: espaco.md },
  erroGoogleTexto: {
    flex: 1,
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 14,
    lineHeight: 19,
    color: cores.erroTexto,
  },
  divisor: { flexDirection: 'row', alignItems: 'center', gap: espaco.md, marginVertical: espaco.lg },
  linha: { flex: 1, height: 1, backgroundColor: cores.borda },
});
