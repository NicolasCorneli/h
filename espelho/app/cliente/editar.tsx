import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { Campo } from '@/components/Campo';
import { CampoDataOpcional } from '@/components/CampoData';
import { useFeedback } from '@/components/Feedback';
import { SeletorFoto, type FotoEscolhida } from '@/components/SeletorFoto';
import { EvitaTeclado } from '@/components/EvitaTeclado';
import { useCliente, useStore } from '@/data/store';
import type { Cliente } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { idadeEm } from '@/services/consentService';
import { reduzirParaEnvio } from '@/services/imagemLocal';
import { ErroApi } from '@/services/api';
import { cores, espaco } from '@/theme/tokens';
import { dataCurta, diaLocalIso, isoDeDataCurta, situacaoDataCurta } from '@/utils/datas';
import { mascaraTelefone, normalizarDataDigitada } from '@/utils/mascaras';

// Mesmos limites que a tela já valida ao salvar (nem futuro, nem antes de 1900).
const NASCIMENTO_MINIMO = new Date(1900, 0, 1);
// Vazio, o calendário abre trinta anos atrás: menos voltas até o ano de quem é adulto.
const INICIO_CALENDARIO_NASCIMENTO = new Date(new Date().getFullYear() - 30, 0, 1);

/** Cadastro e edição de cliente — RF02, com os atributos da entidade `clientes` (seção 5.6). */
export default function EditarCliente() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const router = useRouter();
  const { carregando } = useStore();
  const existente = useCliente(id);

  // Editando: o formulário só nasce com o cliente em mãos. Aberta pelo endereço (ou
  // recarregada), a tela espera a carga, em vez de começar com os campos vazios.
  if (id && (carregando || !existente)) {
    return (
      <Tela>
        <Cabecalho titulo="Editar cliente" aoVoltar={() => router.back()} />
        <View style={styles.esperando}>
          {carregando ? (
            <ActivityIndicator color={cores.acao} />
          ) : (
            <Text style={textos.corpo}>Este cliente não foi encontrado.</Text>
          )}
        </View>
      </Tela>
    );
  }
  return <FormularioCliente key={existente?.id ?? 'novo'} existente={existente} />;
}

function FormularioCliente({ existente }: { existente: Cliente | undefined }) {
  const router = useRouter();
  const { acoes } = useStore();
  const { avisar, confirmar } = useFeedback();

  const [nome, setNome] = useState(existente?.nome ?? '');
  const [telefone, setTelefone] = useState(existente?.telefone ?? '');
  const [observacoes, setObservacoes] = useState(existente?.observacoes ?? '');
  const [fotoUri, setFotoUri] = useState<string | null>(existente?.fotoUri ?? null);
  // Dimensões da foto escolhida, para reduzi-la no aparelho antes do envio.
  const [fotoEscolhida, setFotoEscolhida] = useState<FotoEscolhida | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [nascimento, setNascimento] = useState(
    existente?.dataNascimento ? dataCurta(existente.dataNascimento) : ''
  );
  const [erros, setErros] = useState<{ nome?: string; telefone?: string; nascimento?: string }>({});

  const idade = idadeEm(isoDeDataCurta(nascimento));
  const alterado =
    nome !== (existente?.nome ?? '') ||
    telefone !== (existente?.telefone ?? '') ||
    observacoes !== (existente?.observacoes ?? '') ||
    fotoUri !== (existente?.fotoUri ?? null) ||
    nascimento !== (existente?.dataNascimento ? dataCurta(existente.dataNascimento) : '');

  /** Evita perder um formulário preenchido com um toque acidental em "voltar". */
  async function sair() {
    if (!alterado) {
      router.back();
      return;
    }
    const ok = await confirmar({
      titulo: 'Descartar alterações?',
      mensagem: 'Os dados digitados nesta tela não serão salvos.',
      rotuloConfirmar: 'Descartar',
      rotuloCancelar: 'Continuar editando',
      destrutivo: true,
    });
    if (ok) router.back();
  }

  async function salvar() {
    const novosErros: typeof erros = {};
    if (!nome.trim()) novosErros.nome = 'Informe o nome do cliente.';
    if (telefone.replace(/\D/g, '').length < 10) {
      novosErros.telefone = 'Informe um telefone com DDD.';
    }
    // "4/5/2000" e "04052000" também valem: o campo normaliza ao sair, e aqui de novo, caso
    // o toque em "Salvar" chegue antes de o campo perder o foco.
    const nascimentoDigitado = normalizarDataDigitada(nascimento);
    const nascimentoIso = isoDeDataCurta(nascimentoDigitado);
    if (nascimentoDigitado && !nascimentoIso) {
      novosErros.nascimento =
        situacaoDataCurta(nascimentoDigitado) === 'invalida'
          ? 'Essa data de nascimento não existe. Confira o dia e o mês.'
          : 'Data de nascimento incompleta: use dd/mm/aaaa.';
    } else if (nascimentoIso && nascimentoIso > diaLocalIso()) {
      // Mesma regra do servidor, avisada antes de enviar.
      novosErros.nascimento = 'A data de nascimento não pode estar no futuro.';
    } else if (nascimentoIso && nascimentoIso < '1900-01-01') {
      novosErros.nascimento = 'Confira o ano de nascimento.';
    }
    setErros(novosErros);
    if (Object.keys(novosErros).length > 0) {
      avisar('Confira os campos destacados', 'erro');
      return;
    }

    setSalvando(true);
    let cliente;
    try {
      cliente = await acoes.salvarCliente(
        {
          nome: nome.trim(),
          telefone: telefone.trim(),
          observacoes: observacoes.trim(),
          dataNascimento: nascimentoIso,
        },
        existente?.id
      );
    } catch (falha) {
      const apiErro = falha instanceof ErroApi ? falha : null;
      const mensagem = apiErro?.message ?? 'Não foi possível salvar o cliente.';
      // O erro vai para o campo que o servidor apontou. Antes ia sempre para o nome, e
      // uma data recusada aparecia como se o problema fosse o nome do cliente.
      const campo = apiErro?.detalhes.map((d) => d.campo).find((c) => typeof c === 'string');
      const chave =
        campo === 'dataNascimento' ? 'nascimento' : campo === 'telefone' ? 'telefone' : 'nome';
      const explicacao = campo === 'dataNascimento' ? 'Confira a data de nascimento.' : mensagem;
      setErros({ [chave]: explicacao });
      avisar(mensagem, 'erro');
      setSalvando(false);
      return;
    }

    // A foto de perfil é um objeto no storage, não um campo do cadastro: vai em uma
    // requisição própria, com a mesma validação técnica das outras imagens. Se só ela
    // falhar, o cadastro já está salvo: a tela não fica parada (um novo "Salvar"
    // duplicaria o cliente) e o aviso diz exatamente o que faltou.
    const fotoMudou = fotoUri !== (existente?.fotoUri ?? null);
    let avisoFoto: string | null = null;
    if (fotoMudou) {
      try {
        if (fotoUri && fotoEscolhida) {
          const reduzida = await reduzirParaEnvio(
            fotoEscolhida.uri,
            fotoEscolhida.largura,
            fotoEscolhida.altura
          );
          await acoes.enviarFotoDoCliente(cliente.id, reduzida);
        } else if (!fotoUri && existente?.fotoUri) {
          await acoes.removerFotoDoCliente(cliente.id);
        }
      } catch (falha) {
        const motivo = falha instanceof ErroApi ? falha.message : 'tente de novo.';
        avisoFoto = `Dados salvos, mas a foto não foi ${fotoUri ? 'enviada' : 'removida'}: ${motivo}`;
      }
    }

    setSalvando(false);
    if (avisoFoto) avisar(avisoFoto, 'erro');
    else avisar(existente ? 'Cliente atualizado' : 'Cliente cadastrado');
    router.replace(`/cliente/${cliente.id}`);
  }

  return (
    <Tela>
      <Cabecalho titulo={existente ? 'Editar cliente' : 'Novo cliente'} aoVoltar={sair} />

      <EvitaTeclado>
        <ScrollView
          contentContainerStyle={styles.conteudo}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          <View style={styles.foto}>
            <SeletorFoto
              fotoUri={fotoUri}
              titulo="Foto de perfil"
              ajuda="Opcional. Ajuda a reconhecer o cliente na lista."
              aoEscolher={(foto) => {
                setFotoUri(foto.uri);
                setFotoEscolhida(foto);
              }}
              aoRemover={() => {
                setFotoUri(null);
                setFotoEscolhida(null);
              }}
              ocupado={salvando}
            />
          </View>

          <View style={styles.campos}>
            <Campo
              rotulo="Nome completo"
              obrigatorio
              valor={nome}
              aoMudar={setNome}
              placeholder="Marina Alves"
              autoCapitalize="words"
              erro={erros.nome}
            />
            <Campo
              rotulo="Telefone"
              obrigatorio
              valor={telefone}
              aoMudar={setTelefone}
              placeholder="(55) 99123-4567"
              tipoTeclado="phone-pad"
              mascara={mascaraTelefone}
              erro={erros.telefone}
            />
            <CampoDataOpcional
              rotulo="Data de nascimento"
              valor={nascimento}
              aoMudar={(texto) => {
                setNascimento(texto);
                if (erros.nascimento) setErros((atuais) => ({ ...atuais, nascimento: undefined }));
              }}
              inicial={INICIO_CALENDARIO_NASCIMENTO}
              minimo={NASCIMENTO_MINIMO}
              maximo={new Date()}
              ajuda="Opcional. Serve para o aplicativo saber quando exigir o consentimento de um responsável legal."
              erro={erros.nascimento}
            />
            <Campo
              rotulo="Observações"
              valor={observacoes}
              aoMudar={setObservacoes}
              placeholder="Histórico químico, preferências, sensibilidades…"
              ajuda="Aparecem no topo do perfil e viajam com o cliente entre atendimentos."
              multilinha
            />
          </View>

          {idade !== null && idade < 18 ? (
            <Aviso
              tom="alerta"
              titulo="Cliente menor de 18 anos"
              texto={`Com ${idade} anos, o consentimento de uso de imagem precisa ser dado por um dos pais ou pelo responsável legal, identificado no momento do registro (LGPD, art. 14).`}
            />
          ) : null}
        </ScrollView>

        <View style={styles.rodape}>
          <Botao
            titulo={salvando ? 'Salvando…' : 'Salvar cliente'}
            icone="ok"
            carregando={salvando}
            aoPressionar={salvar}
          />
        </View>
      </EvitaTeclado>
    </Tela>
  );
}

const styles = StyleSheet.create({
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.xl, paddingBottom: espaco.xl },
  foto: { marginBottom: espaco.xl },
  esperando: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: espaco.xl },
  campos: { gap: espaco.md, marginBottom: espaco.lg },
  rodape: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.md,
    paddingBottom: espaco.lg,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
  },
});
