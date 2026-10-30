import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useStore } from '@/data/store';
import type { HistoricoServico } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, raios } from '@/theme/tokens';
import { dataCurta, duracao, hora } from '@/utils/datas';

import { Cartao, Selo } from './Basicos';
import { Icone } from './Icone';
import { ImagemSimulada } from './ImagemSimulada';

/**
 * Um atendimento no histórico do cliente.
 *
 * Mostra o que se sabe, e só isso: a data em que o serviço aconteceu, a hora quando ela
 * foi registrada, se veio da agenda ou foi registrado direto, e a simulação usada. Registros antigos não têm hora nem agendamento de origem; nesses casos
 * a linha simplesmente não aparece, em vez de exibir um valor inventado.
 */
export function ItemHistorico({ item }: { item: HistoricoServico }) {
  const router = useRouter();
  const { estado } = useStore();
  const agendamento = item.agendamentoId
    ? estado.agendamentos.find((a) => a.id === item.agendamentoId)
    : undefined;
  const simulacao = item.simulacaoId ? estado.simulacoes.find((s) => s.id === item.simulacaoId) : undefined;

  const quando = item.realizadoEm
    ? `${dataCurta(item.dataServico)} às ${hora(item.realizadoEm)}`
    : dataCurta(item.dataServico);
  const comDuracao = item.duracaoMin ? `${quando} · ${duracao(item.duracaoMin)}` : quando;

  return (
    <Cartao>
      <View style={styles.topo}>
        <Text style={[textos.corpoForte, styles.flex]}>{item.descricao}</Text>
        <Text style={textos.meta}>{comDuracao}</Text>
      </View>

      {agendamento ? (
        <View style={styles.linha}>
          <Icone nome="calendario" tamanho={14} cor={cores.textoApoio} />
          {/* Só a origem: a data marcada ao lado da data realizada confundia quando o
              atendimento acontecia em outro dia. A data que vale é a realizada, acima. */}
          <Text style={[textos.meta, styles.flex]}>
            Marcado pela agenda
            {agendamento.servico !== item.descricao ? ` (previsto: ${agendamento.servico})` : ''}
          </Text>
        </View>
      ) : item.agendamentoId === null ? (
        <View style={styles.linha}>
          <Icone nome="registrar" tamanho={14} cor={cores.textoApoio} />
          <Text style={[textos.meta, styles.flex]}>Registrado sem agendamento</Text>
        </View>
      ) : null}

      {item.observacoes ? <Text style={[textos.apoio, styles.texto]}>{item.observacoes}</Text> : null}

      {simulacao ? (
        <Pressable
          onPress={() => router.push(`/simulacao/imagem/${simulacao.id}`)}
          accessibilityRole="button"
          accessibilityLabel={`Ver a simulação usada: ${simulacao.parametros.estilo}, ${simulacao.parametros.cor}`}
          style={({ pressed }) => [styles.simulacao, pressed && styles.pressionado]}>
          <ImagemSimulada uri={simulacao.imgSaidaUri} estilo={styles.miniatura} raio={6} />
          <View style={styles.flex}>
            <Text style={textos.apoioForte} numberOfLines={1}>
              Simulação usada
            </Text>
            <Text style={textos.meta} numberOfLines={1}>
              {simulacao.parametros.estilo} · {simulacao.parametros.cor}
            </Text>
          </View>
          <Icone nome="chevron" tamanho={16} />
        </Pressable>
      ) : item.simulacaoId ? (
        <View style={styles.vinculo}>
          <Selo texto="vinculado a 1 simulação" tom="acao" icone="vinculo" />
        </View>
      ) : null}
      {/* Antes não havia como corrigir um registro feito com o serviço, o dia ou as
          observações errados. */}
      <Pressable
        onPress={() => router.push(`/atendimento/editar/${item.id}`)}
        accessibilityRole="button"
        accessibilityLabel={`Corrigir o atendimento ${item.descricao} de ${quando}`}
        hitSlop={8}
        style={({ pressed }) => [styles.corrigir, pressed && styles.pressionado]}>
        <Icone nome="editar" tamanho={13} cor={cores.acaoTexto} />
        <Text style={styles.corrigirTexto}>Corrigir</Text>
      </Pressable>
    </Cartao>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  topo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', gap: espaco.md },
  linha: { flexDirection: 'row', alignItems: 'center', gap: espaco.xs, marginTop: espaco.xs },
  texto: { marginTop: espaco.sm },
  simulacao: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    marginTop: espaco.md,
    padding: espaco.sm,
    borderRadius: raios.campo,
    backgroundColor: cores.superficieSuave,
    minHeight: 56,
  },
  miniatura: { width: 36, height: 44 },
  vinculo: { marginTop: espaco.md },
  pressionado: { opacity: 0.85 },
  corrigir: {
    alignSelf: 'flex-end',
    marginTop: espaco.sm,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    // Alvo de toque mínimo, mesmo com o texto pequeno.
    minHeight: ALVO_TOQUE,
    paddingHorizontal: espaco.sm,
  },
  corrigirTexto: { fontFamily: 'FamiljenGrotesk_600SemiBold', fontSize: 13, color: cores.acaoTexto },
});
