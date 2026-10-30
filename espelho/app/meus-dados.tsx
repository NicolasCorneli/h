import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { Chip, Etiqueta, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { Campo } from '@/components/Campo';
import { useFeedback } from '@/components/Feedback';
import { SeletorFoto, type FotoEscolhida } from '@/components/SeletorFoto';
import { useStore } from '@/data/store';
import type { Usuario } from '@/data/tipos';
import { reduzirParaEnvio } from '@/services/imagemLocal';
import { textos } from '@/theme/textos';
import { cores, espaco } from '@/theme/tokens';

const ATUACOES = ['autônomo', 'salão', 'barbearia', 'estúdio'];

/** Nome e forma de atuação do profissional. O e-mail identifica a conta e não muda aqui. */
export default function MeusDados() {
  const router = useRouter();
  const { estado } = useStore();
  const usuario = estado.usuario;

  return (
    <Tela>
      <Cabecalho titulo="Meus dados" aoVoltar={() => router.back()} />
      {usuario ? (
        // O formulário nasce com os dados em mãos: aberta direto pelo endereço, a tela
        // espera a conta carregar em vez de começar com campos vazios.
        <Formulario key={usuario.id} usuario={usuario} />
      ) : (
        <View style={styles.carregando}>
          <ActivityIndicator color={cores.acao} />
        </View>
      )}
    </Tela>
  );
}

function Formulario({ usuario }: { usuario: Usuario }) {
  const router = useRouter();
  const { acoes } = useStore();
  const { avisar, confirmar } = useFeedback();
  const [enviandoFoto, setEnviandoFoto] = useState(false);
  const [nome, setNome] = useState(usuario.nome);
  const [atuacao, setAtuacao] = useState(usuario.atuacao || 'autônomo');
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  // A foto é gravada na hora, sem depender do botão Salvar: é uma ação à parte, como no
  // celular ao trocar a foto de uma conta.
  async function trocarFoto(foto: FotoEscolhida) {
    setEnviandoFoto(true);
    try {
      await acoes.enviarMinhaFoto(await reduzirParaEnvio(foto.uri, foto.largura, foto.altura));
      avisar('Foto atualizada');
    } catch (falha) {
      avisar(
        falha instanceof Error ? `A foto não foi enviada: ${falha.message}` : 'A foto não foi enviada.',
        'erro'
      );
    } finally {
      setEnviandoFoto(false);
    }
  }

  async function removerFoto() {
    const ok = await confirmar({
      titulo: 'Remover sua foto?',
      mensagem: 'No lugar dela aparecem as iniciais do seu nome. Dá para colocar outra quando quiser.',
      rotuloConfirmar: 'Remover foto',
      rotuloCancelar: 'Manter',
      destrutivo: true,
    });
    if (!ok) return;
    setEnviandoFoto(true);
    try {
      await acoes.removerMinhaFoto();
      avisar('Foto removida');
    } catch (falha) {
      avisar(falha instanceof Error ? falha.message : 'Não foi possível remover a foto.', 'erro');
    } finally {
      setEnviandoFoto(false);
    }
  }

  async function salvar() {
    if (nome.trim().length < 2) {
      setErro('Informe seu nome.');
      return;
    }
    setSalvando(true);
    setErro(null);
    try {
      await acoes.atualizarPerfil({ nome: nome.trim(), atuacao });
      avisar('Dados atualizados');
      router.back();
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Não foi possível salvar agora.');
    } finally {
      setSalvando(false);
    }
  }

  const opcoes = ATUACOES.includes(atuacao) ? ATUACOES : [...ATUACOES, atuacao];

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.flex}>
      <ScrollView contentContainerStyle={styles.conteudo} keyboardShouldPersistTaps="handled">
        <View style={styles.foto}>
          <SeletorFoto
            fotoUri={usuario.fotoUri}
            titulo="Sua foto"
            ajuda="Opcional. Aparece no seu perfil e no início."
            aoEscolher={(foto) => void trocarFoto(foto)}
            aoRemover={() => void removerFoto()}
            ocupado={enviandoFoto}
          />
        </View>

        <Campo rotulo="Seu nome" valor={nome} aoMudar={setNome} obrigatorio erro={erro} />

        <Etiqueta estilo={styles.etiqueta}>Como você atua</Etiqueta>
        <View style={styles.chips}>
          {opcoes.map((a) => (
            <Chip key={a} texto={a} ativo={atuacao === a} aoPressionar={() => setAtuacao(a)} />
          ))}
        </View>

        <Etiqueta estilo={styles.etiqueta}>E-mail da conta</Etiqueta>
        <Text style={textos.corpo}>{usuario.email}</Text>
        <Text style={[textos.meta, styles.nota]}>O e-mail identifica a conta e não pode ser alterado.</Text>

        <Botao
          titulo={salvando ? 'Salvando…' : 'Salvar'}
          carregando={salvando}
          aoPressionar={salvar}
          estilo={styles.botao}
        />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  carregando: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxxl },
  foto: { marginBottom: espaco.xl },
  etiqueta: { marginTop: espaco.xl, marginBottom: espaco.sm },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.sm },
  nota: { marginTop: espaco.xs },
  botao: { marginTop: espaco.xxl },
});
