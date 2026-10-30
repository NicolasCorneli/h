import { useLocalSearchParams, useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Tela } from '@/components/Basicos';
import { Cabecalho } from '@/components/Cabecalho';
import { useFeedback } from '@/components/Feedback';
import { FormularioAtendimento } from '@/components/FormularioAtendimento';
import { useRascunho } from '@/data/rascunho';
import { useCliente, useStore } from '@/data/store';
import { textos } from '@/theme/textos';
import { espaco } from '@/theme/tokens';
import { COR_MANTIDA } from '@/utils/pedido';

/**
 * RF03: registro de um atendimento sem agendamento (o cliente chegou sem marcar).
 *
 * Mesmos campos e componentes da criação de agendamento, para um atendimento que já
 * aconteceu: começa com a data e a hora de agora, que podem ser ajustadas para trás. Grava
 * direto no histórico do cliente; nenhum agendamento é criado ou concluído para isso.
 *
 * `simulacaoId` vem do fim de uma simulação ou da comparação, e já chega selecionada.
 */
export default function NovoAtendimento() {
  const { clienteId, simulacaoId } = useLocalSearchParams<{ clienteId: string; simulacaoId?: string }>();
  const router = useRouter();
  const { acoes, estado } = useStore();
  const { avisar } = useFeedback();
  const simulacao = simulacaoId ? estado.simulacoes.find((s) => s.id === simulacaoId) : undefined;
  const { limpar } = useRascunho();
  const cliente = useCliente(clienteId);
  // Identificador do registro salvo, para a confirmação mostrar o que foi gravado.
  const registrado = useRef<string | null>(null);
  // "Agora" do momento em que o formulário abriu.
  const [agora] = useState(() => {
    const d = new Date();
    d.setSeconds(0, 0);
    return d;
  });

  if (!cliente) {
    return (
      <Tela>
        <Cabecalho titulo="Registrar atendimento" aoVoltar={() => router.back()} />
        <View style={styles.vazio}>
          <Text style={textos.corpo}>Selecione um cliente para registrar o atendimento.</Text>
        </View>
      </Tela>
    );
  }

  return (
    <Tela>
      <Cabecalho titulo="Registrar atendimento" subtitulo={cliente.nome} aoVoltar={() => router.back()} />
      <FormularioAtendimento
        key={cliente.id}
        cliente={cliente}
        inicial={{
          quando: agora,
          // Sugestão visível, como a tela sempre fez: vindo de uma simulação que mudou a
          // cor, coloração; de uma que só mudou o corte, e nos demais casos, corte. O
          // profissional troca com um toque.
          servico: simulacaoId && simulacao?.parametros.cor !== COR_MANTIDA ? 'Coloração' : 'Corte',
          duracaoMin: null,
          observacoes: '',
          simulacaoId: simulacaoId ?? null,
        }}
        rotuloSalvar="Salvar atendimento"
        aoSalvar={async (dados) => {
          const atendimento = await acoes.registrarAtendimento({ clienteId: cliente.id, ...dados });
          registrado.current = atendimento.id;
        }}
        aoTerminar={() => {
          limpar();
          avisar('Atendimento registrado');
          router.replace({
            pathname: '/atendimento/sucesso',
            params: { clienteId: cliente.id, atendimentoId: registrado.current ?? '' },
          });
        }}
      />
    </Tela>
  );
}

const styles = StyleSheet.create({
  vazio: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: espaco.xxxl },
});
