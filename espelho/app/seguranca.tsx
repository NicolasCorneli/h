import { useRouter } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { Campo } from '@/components/Campo';
import { useFeedback } from '@/components/Feedback';
import { useStore } from '@/data/store';
import { ErroApi } from '@/services/api';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

const MIN_SENHA = 8;

type Erros = { atual?: string; nova?: string; confirmacao?: string };

/**
 * Senha e sessões da conta.
 *
 * Trocar a senha desconecta os outros aparelhos: quem tinha o acesso copiado perde. "Sair
 * de todos os aparelhos" é para o celular perdido ou a suspeita de acesso indevido: o
 * servidor deixa de aceitar qualquer sessão aberta, inclusive esta.
 */
export default function Seguranca() {
  const router = useRouter();
  const { estado, acoes } = useStore();
  const { avisar, confirmar } = useFeedback();
  const [atual, setAtual] = useState('');
  const [nova, setNova] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [erros, setErros] = useState<Erros>({});
  const [salvando, setSalvando] = useState(false);
  const [encerrando, setEncerrando] = useState(false);

  // Conta criada pelo Google não tem senha: ela entra só pelo Google.
  const semSenha = estado.usuario?.temSenha === false;

  async function trocarSenha() {
    const encontrados: Erros = {};
    if (!atual) encontrados.atual = 'Digite a senha que você usa hoje.';
    if (nova.length < MIN_SENHA) encontrados.nova = `A nova senha precisa ter ao menos ${MIN_SENHA} caracteres.`;
    else if (nova === atual) encontrados.nova = 'A nova senha precisa ser diferente da atual.';
    if (confirmacao !== nova) encontrados.confirmacao = 'As duas senhas não são iguais.';
    setErros(encontrados);
    if (Object.keys(encontrados).length > 0) return;

    setSalvando(true);
    try {
      await acoes.trocarSenha(atual, nova);
      setAtual('');
      setNova('');
      setConfirmacao('');
      avisar('Senha trocada. Os outros aparelhos foram desconectados.');
      router.back();
    } catch (falha) {
      const apiErro = falha instanceof ErroApi ? falha : null;
      if (apiErro?.codigo === 'senha_incorreta') setErros({ atual: apiErro.message });
      else if (apiErro?.codigo === 'senha_repetida') setErros({ nova: apiErro.message });
      else avisar(apiErro?.message ?? 'Não foi possível trocar a senha agora.', 'erro');
    } finally {
      setSalvando(false);
    }
  }

  async function sairDeTodos() {
    const ok = await confirmar({
      titulo: 'Sair de todos os aparelhos?',
      mensagem:
        'Todas as sessões abertas desta conta são encerradas, inclusive esta. Para voltar, é só entrar de novo.',
      rotuloConfirmar: 'Sair de todos',
      rotuloCancelar: 'Cancelar',
    });
    if (!ok) return;
    setEncerrando(true);
    try {
      await acoes.encerrarTodasAsSessoes();
      avisar('Sessões encerradas em todos os aparelhos');
      // Sem navegação aqui: com a sessão encerrada, a guarda de rotas do layout leva à
      // abertura, como em qualquer fim de sessão. Navegar daqui competiria com ela.
      await acoes.sair();
    } catch (falha) {
      avisar(
        falha instanceof Error ? falha.message : 'Não foi possível encerrar as sessões agora.',
        'erro'
      );
      setEncerrando(false);
    }
  }

  return (
    <Tela>
      <Cabecalho titulo="Senha e sessões" aoVoltar={() => router.back()} />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}>
        <ScrollView
          contentContainerStyle={styles.conteudo}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          {semSenha ? (
            <Aviso
              tom="neutro"
              titulo="Sua conta entra pelo Google"
              texto="Não há senha para trocar: a segurança do acesso é a da sua conta Google."
            />
          ) : (
            <View style={styles.caixa}>
              <Text style={textos.corpoForte}>Trocar senha</Text>
              <Text style={textos.apoio}>
                Os outros aparelhos conectados a esta conta saem e precisam da senha nova.
              </Text>
              <View style={styles.campos}>
                <Campo
                  rotulo="Senha atual"
                  valor={atual}
                  aoMudar={setAtual}
                  obrigatorio
                  segredo
                  alternarSegredo
                  autoCapitalize="none"
                  erro={erros.atual}
                />
                <Campo
                  rotulo="Nova senha"
                  valor={nova}
                  aoMudar={setNova}
                  obrigatorio
                  segredo
                  alternarSegredo
                  autoCapitalize="none"
                  ajuda={`Pelo menos ${MIN_SENHA} caracteres.`}
                  erro={erros.nova}
                />
                <Campo
                  rotulo="Repita a nova senha"
                  valor={confirmacao}
                  aoMudar={setConfirmacao}
                  obrigatorio
                  segredo
                  alternarSegredo
                  autoCapitalize="none"
                  erro={erros.confirmacao}
                />
              </View>
              <Botao
                titulo={salvando ? 'Trocando…' : 'Trocar senha'}
                carregando={salvando}
                aoPressionar={trocarSenha}
                estilo={styles.botao}
              />
            </View>
          )}

          <View style={styles.caixa}>
            <Text style={textos.corpoForte}>Sair de todos os aparelhos</Text>
            <Text style={textos.apoio}>
              Use se perdeu um celular ou acha que alguém entrou na sua conta. Esta sessão também
              é encerrada.
            </Text>
            <Botao
              titulo={encerrando ? 'Encerrando…' : 'Sair de todos os aparelhos'}
              variante="perigo"
              icone="sair"
              carregando={encerrando}
              aoPressionar={sairDeTodos}
              estilo={styles.botao}
            />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  conteudo: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.lg,
    paddingBottom: espaco.xxxl,
    gap: espaco.lg,
  },
  caixa: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.cartao,
    padding: espaco.lg,
    gap: espaco.xs,
  },
  campos: { gap: espaco.md, marginTop: espaco.md },
  botao: { marginTop: espaco.lg },
});
