import { useRouter } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { BotaoGoogle, useGoogleDisponivel } from '@/components/BotaoGoogle';
import { Cabecalho } from '@/components/Cabecalho';
import { Campo } from '@/components/Campo';
import { useFeedback } from '@/components/Feedback';
import { useStore } from '@/data/store';
import { ErroApi } from '@/services/api';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

/**
 * Exclusão da conta (LGPD, art. 18, VI).
 *
 * É a operação mais destrutiva do sistema, e a única que pede a senha de novo: um
 * aparelho desbloqueado nas mãos de outra pessoa não deve ser suficiente para apagar a
 * carteira inteira. O servidor recusa a requisição sem a senha correta.
 *
 * A estratégia é exclusão física: conta, clientes, consentimentos, simulações,
 * atendimentos, agenda e arquivos saem do banco e do armazenamento. Não há cópia.
 */
export default function ExcluirConta() {
  const router = useRouter();
  const { estado, acoes } = useStore();
  const { avisar } = useFeedback();
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [excluindo, setExcluindo] = useState(false);

  const quantidade = estado.clientes.length;
  // Conta criada pelo Google não tem senha: a confirmação é entrar de novo no Google.
  const semSenha = estado.usuario?.temSenha === false;
  const googleDisponivel = useGoogleDisponivel();

  async function excluir() {
    if (!senha) {
      setErro('Digite sua senha para confirmar.');
      return;
    }
    await confirmarExclusao({ senha });
  }

  async function confirmarExclusao(confirmacao: { senha: string } | { idTokenGoogle: string }) {
    setExcluindo(true);
    setErro(null);
    try {
      await acoes.excluirConta(confirmacao);
      avisar('Conta e dados excluídos');
      router.replace('/onboarding');
    } catch (falha) {
      const apiErro = falha instanceof ErroApi ? falha : null;
      setErro(apiErro?.message ?? 'Não foi possível excluir a conta agora.');
    } finally {
      setExcluindo(false);
    }
  }

  return (
    <Tela>
      <Cabecalho
        titulo="Excluir minha conta"
        subtitulo="LGPD · art. 18, VI"
        aoVoltar={() => router.back()}
      />

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}>
        <ScrollView
          contentContainerStyle={styles.conteudo}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          <Aviso
            tom="erro"
            titulo="Esta ação não pode ser desfeita"
            texto={`Serão apagados: sua conta, ${quantidade} ${
              quantidade === 1 ? 'cliente' : 'clientes'
            }, todos os consentimentos registrados, as simulações, as imagens no armazenamento, o histórico de atendimentos e a agenda.`}
          />

          <View style={styles.caixa}>
            <Text style={textos.corpoForte}>O que acontece com os dados dos clientes</Text>
            <Text style={textos.apoio}>
              Você é quem responde pelo tratamento dessas informações. Com a exclusão da conta,
              elas deixam de existir no sistema, inclusive o registro das decisões de
              consentimento. Se precisar guardar comprovação, anote antes de continuar.
            </Text>
          </View>

          {semSenha ? (
            <View style={styles.campo}>
              <Text style={[textos.apoio, styles.explicacao]}>
                Sua conta entra pelo Google. Para confirmar, entre de novo com a mesma conta Google.
              </Text>
              {googleDisponivel ? (
                <BotaoGoogle
                  rotulo={excluindo ? 'Excluindo…' : 'Confirmar com Google e excluir'}
                  desabilitado={excluindo}
                  aoReceberToken={async (idToken) => {
                    await confirmarExclusao({ idTokenGoogle: idToken });
                  }}
                  aoFalhar={setErro}
                />
              ) : (
                <Aviso
                  tom="alerta"
                  titulo="Login com Google indisponível agora"
                  texto="A confirmação é feita pelo Google, que não está disponível neste aparelho agora. Tente pelo navegador do computador."
                />
              )}
              {erro ? <Text style={styles.erro}>{erro}</Text> : null}
            </View>
          ) : (
            <>
            <Campo
              rotulo="Sua senha"
              obrigatorio
              valor={senha}
              aoMudar={setSenha}
              segredo
              alternarSegredo
              autoCapitalize="none"
              ajuda="Pedimos de novo porque a exclusão é definitiva."
              erro={erro}
              estilo={styles.campo}
            />

            <Botao
              titulo={excluindo ? 'Excluindo…' : 'Excluir conta e todos os dados'}
              variante="perigo"
              icone="excluir"
              carregando={excluindo}
              aoPressionar={excluir}
              estilo={styles.botao}
            />
            </>
          )}
          <Botao
            titulo="Manter minha conta"
            variante="texto"
            aoPressionar={() => router.back()}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxxl },
  caixa: {
    marginTop: espaco.md,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.cartao,
    padding: espaco.lg,
    gap: espaco.xs,
  },
  campo: { marginTop: espaco.xl },
  botao: { marginTop: espaco.xl },
  explicacao: { marginBottom: espaco.md },
  erro: { marginTop: espaco.md, fontFamily: 'FamiljenGrotesk_500Medium', fontSize: 14, color: cores.erroTexto },
});
