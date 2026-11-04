import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, BotaoIcone, Faixa, Tela, useTelaDividida } from '@/components/Basicos';
import { BotaoGoogle, useGoogleDisponivel } from '@/components/BotaoGoogle';
import { Botao } from '@/components/Botao';
import { Campo } from '@/components/Campo';
import { Marca } from '@/components/Marca';
import { EvitaTeclado } from '@/components/EvitaTeclado';
import { useStore } from '@/data/store';
import { ErroApi } from '@/services/api';
import { textos, textosEscuros } from '@/theme/textos';
import { cores, espaco } from '@/theme/tokens';

const MIN_SENHA = 8;

/**
 * RF01 — criação de conta.
 *
 * Antes da integração "Criar conta" apenas limpava os dados de exemplo do aparelho.
 * Agora cria um profissional de verdade no servidor, com senha guardada em hash.
 */
export default function Cadastro() {
  const router = useRouter();
  const { acoes } = useStore();
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erros, setErros] = useState<{ campo: string; mensagem: string }[]>([]);
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [entrandoGoogle, setEntrandoGoogle] = useState(false);
  const googleDisponivel = useGoogleDisponivel();
  const dividida = useTelaDividida();

  const erroDe = (campo: string) => erros.find((e) => e.campo === campo)?.mensagem ?? null;

  async function criar() {
    const encontrados: { campo: string; mensagem: string }[] = [];
    if (nome.trim().length < 2) {
      encontrados.push({ campo: 'nome', mensagem: 'Informe seu nome.' });
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      encontrados.push({ campo: 'email', mensagem: 'Informe um e-mail válido.' });
    }
    if (senha.length < MIN_SENHA) {
      encontrados.push({
        campo: 'senha',
        mensagem: `A senha precisa ter ao menos ${MIN_SENHA} caracteres.`,
      });
    }
    setErros(encontrados);
    setErroGeral(null);
    if (encontrados.length > 0) return;

    setEnviando(true);
    try {
      await acoes.cadastrar({ nome: nome.trim(), email: email.trim(), senha });
      router.replace('/');
    } catch (falha) {
      const apiErro = falha instanceof ErroApi ? falha : null;
      if (apiErro?.codigo === 'email_em_uso') {
        setErros([{ campo: 'email', mensagem: apiErro.message }]);
      } else {
        setErroGeral(apiErro?.message ?? 'Não foi possível criar a conta agora.');
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Tela bordas={['top', 'bottom']} dividida>
      <Faixa estilo={styles.topo}>
        <View style={styles.linhaTopo}>
          <BotaoIcone icone="voltar" rotuloAcessivel="Voltar" aoPressionar={() => router.back()} />
          <Marca />
        </View>
        <Text style={[textosEscuros.display, styles.titulo]} accessibilityRole="header">
          Criar conta
        </Text>
        <Text style={[textosEscuros.corpo, styles.subtitulo]}>
          A conta é sua e os dados dos seus clientes ficam visíveis só para você.
        </Text>
      </Faixa>
      <EvitaTeclado>
        <ScrollView
          contentContainerStyle={[styles.conteudo, dividida && styles.conteudoCentrado]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          {erroGeral ? (
            <View style={styles.erroGeral}>
              <Aviso tom="erro" titulo="Não deu certo" texto={erroGeral} />
            </View>
          ) : null}

          {googleDisponivel ? (
            <>
              <BotaoGoogle
                rotulo="Continuar com Google"
                desabilitado={enviando}
                aoMudarOcupado={setEntrandoGoogle}
                aoReceberToken={async (idToken, nonce) => {
                  setErroGeral(null);
                  await acoes.entrarComGoogle(idToken, nonce);
                  router.replace('/');
                }}
                aoFalhar={setErroGeral}
              />
              <View style={styles.divisor}>
                <View style={styles.linha} />
                <Text style={textos.meta}>ou com e-mail</Text>
                <View style={styles.linha} />
              </View>
            </>
          ) : null}

          <View style={styles.campos}>
            <Campo
              rotulo="Seu nome"
              valor={nome}
              aoMudar={setNome}
              obrigatorio
              placeholder="Como aparece para o cliente"
              erro={erroDe('nome')}
            />
            <Campo
              rotulo="E-mail"
              valor={email}
              aoMudar={setEmail}
              obrigatorio
              placeholder="voce@salao.com"
              tipoTeclado="email-address"
              autoCapitalize="none"
              erro={erroDe('email')}
            />
            <Campo
              rotulo="Senha"
              valor={senha}
              aoMudar={setSenha}
              obrigatorio
              segredo
              alternarSegredo
              autoCapitalize="none"
              ajuda={`Pelo menos ${MIN_SENHA} caracteres.`}
              erro={erroDe('senha')}
            />
          </View>

          <Botao
            titulo={enviando ? 'Criando…' : 'Criar conta'}
            carregando={enviando}
            desabilitado={entrandoGoogle}
            aoPressionar={criar}
            estilo={styles.botao}
          />
          <Text style={[textos.meta, styles.nota]}>
            No primeiro acesso você vai ler suas responsabilidades sobre o uso das imagens
            dos clientes.
          </Text>
        </ScrollView>
      </EvitaTeclado>
    </Tela>
  );
}

const styles = StyleSheet.create({
  topo: { paddingHorizontal: espaco.xxl, paddingTop: espaco.md, paddingBottom: espaco.xxl },
  linhaTopo: { flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  titulo: { marginTop: espaco.xl },
  subtitulo: { marginTop: espaco.sm },
  conteudo: {
    flexGrow: 1,
    paddingHorizontal: espaco.xxl,
    paddingTop: espaco.xxl,
    paddingBottom: espaco.xxxl,
  },
  conteudoCentrado: { justifyContent: 'center' },
  erroGeral: { marginBottom: espaco.lg },
  campos: { gap: espaco.md },
  botao: { marginTop: espaco.xl },
  nota: { marginTop: espaco.md, textAlign: 'center' },
  divisor: { flexDirection: 'row', alignItems: 'center', gap: espaco.md, marginVertical: espaco.lg },
  linha: { flex: 1, height: 1, backgroundColor: cores.borda },
});
