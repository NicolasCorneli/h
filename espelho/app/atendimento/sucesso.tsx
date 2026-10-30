import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Cartao, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Icone } from '@/components/Icone';
import { useCliente, useStore } from '@/data/store';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta, duracao, hora } from '@/utils/datas';

/** Confirmação do registro, com o próximo passo natural: agendar o retorno. */
export default function AtendimentoSalvo() {
  const { clienteId, atendimentoId } = useLocalSearchParams<{ clienteId: string; atendimentoId?: string }>();
  const router = useRouter();
  const { estado } = useStore();
  const cliente = useCliente(clienteId);
  // O que foi de fato gravado, lido do histórico já atualizado (não dos valores da tela).
  const atendimento = estado.historico.find((h) => h.id === atendimentoId);
  const temVinculo = !!atendimento?.simulacaoId;
  const quando = atendimento
    ? atendimento.realizadoEm
      ? `${dataCurta(atendimento.dataServico)} às ${hora(atendimento.realizadoEm)}`
      : dataCurta(atendimento.dataServico)
    : 'Não informado';

  return (
    <Tela bordas={['top', 'bottom']}>
      <View style={styles.conteudo}>
        <View style={styles.centro}>
          <View style={styles.marca}>
            <Icone nome="ok" tamanho={30} cor="#FFFFFF" />
          </View>

          <Text style={[textos.display, styles.titulo]} accessibilityRole="header">
            Atendimento registrado
          </Text>
          <Text style={[textos.corpo, styles.texto]}>
            Salvo no histórico de {cliente?.nome ?? 'cliente'}
            {temVinculo ? ', vinculado à simulação' : ''}.
          </Text>

          <Cartao estilo={styles.resumo}>
            <Linha rotulo="Cliente" valor={cliente?.nome ?? 'Não informado'} />
            <Linha rotulo="Serviço" valor={atendimento?.descricao ?? 'Não informado'} />
            <Linha rotulo="Quando" valor={quando} />
            {atendimento?.duracaoMin ? (
              <Linha rotulo="Duração" valor={duracao(atendimento.duracaoMin)} />
            ) : null}
            <Linha
              rotulo="Simulação"
              valor={temVinculo ? 'vinculada' : 'sem vínculo'}
              destaque={temVinculo}
            />
          </Cartao>
        </View>

        <Botao
          titulo="Agendar retorno"
          icone="calendario"
          aoPressionar={() => router.replace(`/agendamento/novo?clienteId=${clienteId}`)}
        />
        <Botao
          titulo="Voltar ao perfil do cliente"
          variante="texto"
          aoPressionar={() => router.replace(`/cliente/${clienteId}`)}
        />
      </View>
    </Tela>
  );
}

function Linha({ rotulo, valor, destaque = false }: { rotulo: string; valor: string; destaque?: boolean }) {
  return (
    <View style={styles.linha}>
      <Text style={textos.apoio}>{rotulo}</Text>
      <Text style={[textos.apoioForte, destaque && styles.destaque]}>{valor}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  conteudo: { flex: 1, paddingHorizontal: espaco.xl, paddingBottom: espaco.lg },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  marca: {
    width: 72,
    height: 72,
    borderRadius: raios.bloco,
    backgroundColor: cores.sucesso,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espaco.xl,
  },
  titulo: { textAlign: 'center' },
  texto: { textAlign: 'center', marginTop: espaco.md, maxWidth: 300 },
  resumo: { marginTop: espaco.xl, alignSelf: 'stretch', gap: espaco.xs },
  linha: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: espaco.md,
    paddingVertical: espaco.xs,
  },
  destaque: { color: cores.acaoTexto },
});
