import { useLocalSearchParams, useRouter } from 'expo-router';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { useFeedback } from '@/components/Feedback';
import { FormularioAtendimento } from '@/components/FormularioAtendimento';
import { useCliente, useStore } from '@/data/store';
import type { Agendamento, Cliente } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { cores, espaco } from '@/theme/tokens';

/**
 * Conclusão de um agendamento: registra o atendimento no histórico do cliente.
 *
 * O horário marcado fica no agendamento; aqui se informa quando o serviço de fato
 * aconteceu. As duas informações aparecem separadas no histórico. Concluir é uma única
 * gravação no servidor: ou o agendamento fica concluído com o atendimento criado, ou nada
 * muda.
 */
export default function ConcluirAgendamento() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { estado, carregando } = useStore();
  const agendamento = estado.agendamentos.find((a) => a.id === id);
  const cliente = useCliente(agendamento?.clienteId);

  if (carregando) {
    return (
      <Tela>
        <Cabecalho titulo="Concluir atendimento" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <ActivityIndicator color={cores.acao} />
        </View>
      </Tela>
    );
  }

  if (!agendamento || !cliente) {
    return (
      <Tela>
        <Cabecalho titulo="Concluir atendimento" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <Text style={textos.corpo}>Este agendamento não foi encontrado.</Text>
          <Botao
            titulo="Voltar para a agenda"
            variante="texto"
            aoPressionar={() => router.replace('/(tabs)/agenda')}
          />
        </View>
      </Tela>
    );
  }

  if (agendamento.status === 'cancelado' || agendamento.status === 'concluido') {
    return (
      <Tela>
        <Cabecalho titulo="Concluir atendimento" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <Text style={[textos.corpo, styles.centro]}>
            {agendamento.status === 'concluido'
              ? 'Este atendimento já foi concluído e está no histórico do cliente.'
              : 'Este agendamento foi cancelado e não pode ser concluído.'}
          </Text>
          <Botao
            titulo="Abrir perfil do cliente"
            variante="texto"
            aoPressionar={() => router.replace(`/cliente/${agendamento.clienteId}`)}
          />
        </View>
      </Tela>
    );
  }

  // O formulário só nasce com o agendamento em mãos: os valores iniciais vêm dele.
  return <FormularioConclusao key={agendamento.id} agendamento={agendamento} cliente={cliente} />;
}

function FormularioConclusao({ agendamento, cliente }: { agendamento: Agendamento; cliente: Cliente }) {
  const router = useRouter();
  const { acoes } = useStore();
  const { avisar } = useFeedback();

  // O previsto no agendamento é o ponto de partida; o que for corrigido aqui é o que
  // vai para o atendimento. O agendamento em si não muda.
  const marcado = new Date(agendamento.dataHora);
  const inicial = {
    // Sem data válida no agendamento (não deveria acontecer), parte de agora.
    quando: Number.isNaN(marcado.getTime()) ? new Date() : marcado,
    servico: agendamento.servico,
    duracaoMin: agendamento.duracaoMin,
    observacoes: agendamento.observacoes,
    simulacaoId: null,
  };

  return (
    <Tela>
      <Cabecalho titulo="Concluir atendimento" subtitulo={cliente.nome} aoVoltar={() => router.back()} />
      <FormularioAtendimento
        cliente={cliente}
        agendamento={agendamento}
        inicial={inicial}
        rotuloSalvar="Concluir e salvar no histórico"
        aoSalvar={async (dados) => {
          await acoes.concluirAgendamento(agendamento.id, dados);
        }}
        aoTerminar={() => {
          avisar('Atendimento concluído e salvo no histórico');
          router.replace(`/cliente/${agendamento.clienteId}`);
        }}
      />
    </Tela>
  );
}

const styles = StyleSheet.create({
  centro: { textAlign: 'center' },
  ausente: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espaco.md, padding: espaco.xl },
});
