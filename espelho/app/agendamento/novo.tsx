import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';

import { Tela } from '@/components/Basicos';
import { Cabecalho } from '@/components/Cabecalho';
import { useFeedback } from '@/components/Feedback';
import { FormularioAgendamento } from '@/components/FormularioAgendamento';
import { SERVICOS } from '@/data/catalogo';
import { useStore } from '@/data/store';
import { diaLocalIso } from '@/utils/datas';
import { inicioDeNovoAgendamento } from '@/utils/inicioAgendamento';

/**
 * RF06: criação de agendamento. O formulário é o mesmo da edição.
 *
 * `dia` vem da agenda (o dia que estava aberto no "+"); `clienteId`, do perfil ou do fim
 * de um atendimento.
 */
export default function NovoAgendamento() {
  const { clienteId, dia } = useLocalSearchParams<{ clienteId?: string; dia?: string }>();
  const router = useRouter();
  const { acoes } = useStore();
  const { avisar } = useFeedback();
  // Calculado uma vez, ao abrir: "hoje" é o dia em que o formulário foi aberto.
  const [inicio] = useState(() => inicioDeNovoAgendamento(dia));

  return (
    <Tela>
      <Cabecalho titulo="Novo agendamento" aoVoltar={() => router.back()} />
      <FormularioAgendamento
        modo="criar"
        rotuloSalvar="Criar agendamento"
        inicial={{
          clienteId: clienteId ?? null,
          dataHora: inicio,
          servico: SERVICOS[0],
          // Duração não informada até a pessoa digitar uma: nada é presumido.
          duracaoMin: null,
          observacoes: '',
          lembrete: false,
        }}
        aoSalvar={async ({ confirmar, ...dados }) => {
          const criado = await acoes.salvarAgendamento(dados);
          // Todo agendamento nasce aguardando confirmação; quando o profissional já
          // marcou como confirmado, a confirmação é aplicada em seguida.
          if (confirmar) await acoes.confirmarAgendamento(criado.id);
        }}
        aoTerminar={(dados) => {
          avisar('Agendamento criado');
          // Volta para a agenda já no dia do agendamento criado, para ele estar à vista.
          router.dismissTo({
            pathname: '/(tabs)/agenda',
            params: { dia: diaLocalIso(new Date(dados.dataHora)) },
          });
        }}
      />
    </Tela>
  );
}
