import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { useFeedback } from '@/components/Feedback';
import { FormularioAtendimento } from '@/components/FormularioAtendimento';
import { useCliente, useStore } from '@/data/store';
import type { Cliente, HistoricoServico } from '@/data/tipos';
import { ErroApi, type CorrecaoAtendimento } from '@/services/api';
import { textos } from '@/theme/textos';
import { cores, espaco } from '@/theme/tokens';
import { paraData } from '@/utils/datas';

/**
 * Correção de um atendimento do histórico (RF03).
 *
 * Antes não havia como corrigir pelo aplicativo: um serviço registrado com o nome, o dia
 * ou as observações errados ficava assim para sempre. Aqui se corrige tudo o que o
 * registro avulso informa. O que veio da agenda se corrige, mas não se exclui: é o
 * registro de um agendamento concluído. O avulso registrado por engano pode ser excluído.
 */
export default function CorrigirAtendimento() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { estado, carregando } = useStore();
  const atendimento = estado.historico.find((h) => h.id === id);
  const cliente = useCliente(atendimento?.clienteId);

  if (carregando) {
    return (
      <Tela>
        <Cabecalho titulo="Corrigir atendimento" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <ActivityIndicator color={cores.acao} />
        </View>
      </Tela>
    );
  }

  if (!atendimento || !cliente) {
    return (
      <Tela>
        <Cabecalho titulo="Corrigir atendimento" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <Text style={textos.corpo}>Este atendimento não foi encontrado.</Text>
          <Botao titulo="Voltar para os clientes" variante="texto" aoPressionar={() => router.replace('/(tabs)/clientes')} />
        </View>
      </Tela>
    );
  }

  return <Formulario key={atendimento.id} atendimento={atendimento} cliente={cliente} />;
}

function Formulario({ atendimento, cliente }: { atendimento: HistoricoServico; cliente: Cliente }) {
  const router = useRouter();
  const { estado, acoes } = useStore();
  const { avisar, confirmar } = useFeedback();
  const [excluindo, setExcluindo] = useState(false);
  const agendamento = atendimento.agendamentoId
    ? estado.agendamentos.find((a) => a.id === atendimento.agendamentoId)
    : undefined;

  // Registro antigo, só com o dia: o formulário mostra meio-dia, mas essa hora não é
  // gravada se ninguém mexer no horário (não se inventa a hora de algo que já aconteceu).
  const semHora = atendimento.realizadoEm === null;
  const inicioDoDia = paraData(atendimento.dataServico);
  inicioDoDia.setHours(12, 0, 0, 0);
  const quando = semHora ? inicioDoDia : new Date(atendimento.realizadoEm as string);

  async function excluir() {
    const ok = await confirmar({
      titulo: 'Excluir este atendimento?',
      mensagem: `"${atendimento.descricao}" sai do histórico de ${cliente.nome}. Use quando o registro foi feito por engano. Não dá para desfazer.`,
      rotuloConfirmar: 'Excluir atendimento',
      rotuloCancelar: 'Manter',
      destrutivo: true,
    });
    if (!ok) return;
    setExcluindo(true);
    try {
      await acoes.excluirAtendimento(atendimento.id);
    } catch (falha) {
      setExcluindo(false);
      avisar(falha instanceof ErroApi ? falha.message : 'Não foi possível excluir agora', 'erro');
      return;
    }
    avisar('Atendimento excluído do histórico');
    router.replace(`/cliente/${cliente.id}`);
  }

  return (
    <Tela>
      <Cabecalho titulo="Corrigir atendimento" subtitulo={cliente.nome} aoVoltar={() => router.back()} />
      <FormularioAtendimento
        cliente={cliente}
        agendamento={agendamento}
        edicao
        inicial={{
          quando,
          servico: atendimento.descricao,
          duracaoMin: atendimento.duracaoMin,
          observacoes: atendimento.observacoes,
          simulacaoId: atendimento.simulacaoId,
        }}
        rotuloSalvar="Salvar correção"
        aoSalvar={async (dados) => {
          const correcao: CorrecaoAtendimento = {
            descricao: dados.descricao,
            duracaoMin: dados.duracaoMin,
            observacoes: dados.observacoes,
          };
          if (!semHora || dados.realizadoEm !== quando.toISOString()) {
            correcao.realizadoEm = dados.realizadoEm;
          }
          if (dados.simulacaoId) correcao.simulacaoId = dados.simulacaoId;
          else if (atendimento.simulacaoId) correcao.desvincularSimulacao = true;
          await acoes.corrigirAtendimento(atendimento.id, correcao);
        }}
        aoTerminar={() => {
          avisar('Atendimento corrigido');
          router.back();
        }}
        rodapeExtra={
          atendimento.agendamentoId === null ? (
            <Botao
              titulo={excluindo ? 'Excluindo…' : 'Excluir atendimento'}
              icone="excluir"
              variante="perigo"
              tamanho="medio"
              larguraTotal={false}
              carregando={excluindo}
              aoPressionar={excluir}
              estilo={styles.excluir}
            />
          ) : (
            <Text style={[textos.meta, styles.nota]}>
              Este atendimento veio da agenda. Pode ser corrigido, mas não excluído: ele é o
              registro do agendamento concluído.
            </Text>
          )
        }
      />
    </Tela>
  );
}

const styles = StyleSheet.create({
  ausente: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espaco.md, padding: espaco.xl },
  excluir: { marginTop: espaco.xl, alignSelf: 'center' },
  nota: { marginTop: espaco.xl, textAlign: 'center' },
});
