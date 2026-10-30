import { useLocalSearchParams, useRouter } from 'expo-router';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { useFeedback } from '@/components/Feedback';
import { FormularioAgendamento } from '@/components/FormularioAgendamento';
import { useStore } from '@/data/store';
import { textos } from '@/theme/textos';
import { cores, espaco } from '@/theme/tokens';

/**
 * Edição de um agendamento existente.
 *
 * O status não se edita aqui: confirmar, cancelar e concluir têm regras próprias e ações
 * próprias na agenda. Agendamentos cancelados ou concluídos não chegam a esta tela, e o
 * servidor recusa a edição deles mesmo se chegassem.
 */
export default function EditarAgendamento() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { estado, acoes, carregando } = useStore();
  const { avisar } = useFeedback();
  const agendamento = estado.agendamentos.find((a) => a.id === id);

  if (carregando) {
    return (
      <Tela>
        <Cabecalho titulo="Editar agendamento" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <ActivityIndicator color={cores.acao} />
        </View>
      </Tela>
    );
  }

  if (!agendamento) {
    return (
      <Tela>
        <Cabecalho titulo="Editar agendamento" aoVoltar={() => router.back()} />
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
        <Cabecalho titulo="Editar agendamento" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <Text style={[textos.corpo, styles.centro]}>
            Este agendamento já foi {agendamento.status === 'cancelado' ? 'cancelado' : 'concluído'} e não
            pode mais ser alterado.
          </Text>
          <Botao titulo="Voltar para a agenda" variante="texto" aoPressionar={() => router.back()} />
        </View>
      </Tela>
    );
  }

  return (
    <Tela>
      <Cabecalho titulo="Editar agendamento" aoVoltar={() => router.back()} />
      <FormularioAgendamento
        // A chave força remontar se o agendamento mudar por baixo (outra edição).
        key={agendamento.id}
        modo="editar"
        statusAtual={agendamento.status}
        rotuloSalvar="Salvar alterações"
        inicial={{
          clienteId: agendamento.clienteId,
          dataHora: new Date(agendamento.dataHora),
          servico: agendamento.servico,
          duracaoMin: agendamento.duracaoMin,
          observacoes: agendamento.observacoes,
          lembrete: agendamento.lembrete,
        }}
        aoSalvar={async ({ confirmar: _ignorado, ...dados }) => {
          await acoes.salvarAgendamento(dados, agendamento.id);
        }}
        aoTerminar={() => {
          avisar('Alterações salvas');
          router.back();
        }}
      />
    </Tela>
  );
}

const styles = StyleSheet.create({
  ausente: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: espaco.md,
    padding: espaco.xl,
  },
  centro: { textAlign: 'center' },
});
