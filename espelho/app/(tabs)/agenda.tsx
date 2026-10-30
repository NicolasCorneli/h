import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AvisoDeConexao } from '@/components/AvisoDeConexao';
import { Cartao, Etiqueta, Faixa, Selo, Tela } from '@/components/Basicos';
import { useFeedback } from '@/components/Feedback';
import { FolhaAcoes, type AcaoFolha } from '@/components/FolhaAcoes';
import { Icone } from '@/components/Icone';
import { useAtualizar } from '@/components/Atualizar';
import { DialogoCancelamento } from '@/components/DialogoCancelamento';
import { STATUS_CURTO, STATUS_LABEL, useAgendamentosOrdenados, useStore } from '@/data/store';
import type { Agendamento } from '@/data/tipos';
import { ErroApi } from '@/services/api';
import { TOM_STATUS } from '@/theme/status';
import { textos, textosEscuros } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, raios } from '@/theme/tokens';
import {
  dataCurta,
  diaLocalIso,
  diaPorExtenso,
  duracao,
  paraData,
  hora,
  mesmoDia,
  nomeDoMes,
} from '@/utils/datas';

/** T8 / RF06 — mês compacto com marcadores e a lista do dia selecionado. */
export default function Agenda() {
  const router = useRouter();
  const { controle } = useAtualizar();
  const { estado, acoes } = useStore();
  const { avisar } = useFeedback();
  const agendamentos = useAgendamentosOrdenados();
  // `dia` chega quando se volta de um agendamento recém-criado: a agenda abre nele.
  const { dia } = useLocalSearchParams<{ dia?: string }>();
  const [selecionado, setSelecionado] = useState(() => (dia ? paraData(dia) : new Date()));
  useEffect(() => {
    if (dia && /^\d{4}-\d{2}-\d{2}$/.test(dia)) setSelecionado(paraData(dia));
  }, [dia]);
  const [aberto, setAberto] = useState<Agendamento | null>(null);
  const [cancelando, setCancelando] = useState<Agendamento | null>(null);

  const hojeData = new Date();
  const inicioDoMes = new Date(selecionado.getFullYear(), selecionado.getMonth(), 1);
  const diasNoMes = new Date(selecionado.getFullYear(), selecionado.getMonth() + 1, 0).getDate();
  const deslocamento = inicioDoMes.getDay();

  const doMes = useMemo(
    () =>
      agendamentos.filter((a) => {
        const d = new Date(a.dataHora);
        return d.getMonth() === selecionado.getMonth() && d.getFullYear() === selecionado.getFullYear();
      }),
    [agendamentos, selecionado]
  );

  // Cancelados continuam visíveis na lista do dia, mas não marcam o calendário nem
  // entram na contagem: o horário deles está livre.
  const ativosDoMes = doMes.filter((a) => a.status !== 'cancelado');
  const diasComCompromisso = new Set(ativosDoMes.map((a) => new Date(a.dataHora).getDate()));
  const doDia = doMes.filter((a) => mesmoDia(a.dataHora, selecionado.toISOString()));
  const doDiaAtivos = doDia.filter((a) => a.status !== 'cancelado').length;

  const totalCelulas = deslocamento + diasNoMes > 35 ? 42 : 35;
  const celulas = Array.from({ length: totalCelulas }, (_, i) => {
    const numero = i - deslocamento + 1;
    return numero >= 1 && numero <= diasNoMes ? numero : null;
  });

  const mudarMes = (passo: number) => {
    const nova = new Date(selecionado.getFullYear(), selecionado.getMonth() + passo, 1);
    setSelecionado(nova);
  };

  const clienteDe = (agendamento: Agendamento) => estado.clientes.find((c) => c.id === agendamento.clienteId);

  const confirmarAgendamento = (agendamento: Agendamento) =>
    void acoes
      .confirmarAgendamento(agendamento.id)
      .then(() => avisar('Agendamento confirmado'))
      .catch((falha: unknown) =>
        avisar(falha instanceof ErroApi ? falha.message : 'Não foi possível confirmar', 'erro')
      );

  /** Só aparece o que a situação permite; o servidor recusa as demais transições. */
  const acoesDo = (agendamento: Agendamento): AcaoFolha[] => {
    const perfil: AcaoFolha = {
      icone: 'cliente',
      rotulo: 'Abrir perfil do cliente',
      descricao:
        agendamento.status === 'concluido' ? 'O atendimento está no histórico do cliente' : undefined,
      aoPressionar: () => router.push(`/cliente/${agendamento.clienteId}`),
    };
    if (agendamento.status === 'concluido' || agendamento.status === 'cancelado') return [perfil];
    return [
      ...(agendamento.status === 'pendente'
        ? [
            {
              icone: 'ok' as const,
              rotulo: 'Confirmar agendamento',
              descricao: 'O cliente confirmou que vem',
              aoPressionar: () => confirmarAgendamento(agendamento),
            },
          ]
        : []),
      {
        icone: 'okCirculo',
        rotulo: 'Atendimento concluído',
        descricao: 'Registra o serviço no histórico do cliente',
        aoPressionar: () => router.push(`/agendamento/concluir/${agendamento.id}`),
      },
      {
        icone: 'editar',
        rotulo: 'Editar agendamento',
        descricao: 'Cliente, data, horário, serviço e observações',
        aoPressionar: () => router.push(`/agendamento/editar/${agendamento.id}`),
      },
      perfil,
      {
        icone: 'proibido',
        rotulo: 'Cancelar agendamento',
        descricao: 'O registro fica guardado como cancelado',
        destrutiva: true,
        aoPressionar: () => setCancelando(agendamento),
      },
    ];
  };

  return (
    <Tela>
      <Faixa estilo={styles.topo}>
        <View style={styles.tituloLinha}>
          <View style={styles.flex}>
            <Text style={textosEscuros.titulo} accessibilityRole="header">
              {nomeDoMes(selecionado.toISOString())} {selecionado.getFullYear()}
            </Text>
            <Text style={textosEscuros.meta}>
              {ativosDoMes.length} {ativosDoMes.length === 1 ? 'compromisso no mês' : 'compromissos no mês'}
            </Text>
          </View>

          <View style={styles.navegacaoMes}>
            <Pressable
              onPress={() => mudarMes(-1)}
              accessibilityRole="button"
              accessibilityLabel="Mês anterior"
              style={({ pressed }) => [styles.botaoMes, pressed && styles.pressionado]}>
              <Icone nome="voltar" tamanho={18} cor={cores.escuroTexto} />
            </Pressable>
            <Pressable
              onPress={() => mudarMes(1)}
              accessibilityRole="button"
              accessibilityLabel="Próximo mês"
              style={({ pressed }) => [styles.botaoMes, pressed && styles.pressionado]}>
              <Icone nome="avancar" tamanho={18} cor={cores.escuroTexto} />
            </Pressable>
            <Pressable
              // O formulário abre no dia que está selecionado (nunca num dia passado).
              onPress={() =>
                router.push({ pathname: '/agendamento/novo', params: { dia: diaLocalIso(selecionado) } })
              }
              accessibilityRole="button"
              accessibilityLabel="Novo agendamento"
              style={({ pressed }) => [styles.botaoMais, pressed && styles.pressionado]}>
              <Icone nome="mais" tamanho={20} cor="#FFFFFF" />
            </Pressable>
          </View>
        </View>

        <AvisoDeConexao />

        <View style={styles.calendario}>
          <View style={styles.semana}>
            {['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'].map((d) => (
              <Text key={d} style={styles.diaSemana}>
                {d}
              </Text>
            ))}
          </View>

          <View style={styles.grade}>
            {celulas.map((numero, i) => {
              if (numero === null) return <View key={`v${i}`} style={styles.celula} />;
              const data = new Date(selecionado.getFullYear(), selecionado.getMonth(), numero);
              const ehHoje = mesmoDia(data.toISOString(), hojeData.toISOString());
              const ativo = numero === selecionado.getDate();
              const temCompromisso = diasComCompromisso.has(numero);
              return (
                <Pressable
                  key={numero}
                  onPress={() => setSelecionado(data)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: ativo }}
                  accessibilityLabel={`Dia ${numero}${temCompromisso ? ', com atendimentos' : ''}`}
                  style={styles.celula}>
                  <View style={[styles.celulaInterna, ativo && styles.celulaAtiva]}>
                    <Text
                      style={[styles.numeroDia, ehHoje && styles.numeroHoje, ativo && styles.numeroAtivo]}>
                      {numero}
                    </Text>
                    {temCompromisso ? (
                      <View style={[styles.marcador, ativo && styles.marcadorAtivo]} />
                    ) : (
                      <View style={styles.marcadorVazio} />
                    )}
                  </View>
                </Pressable>
              );
            })}
          </View>
        </View>
      </Faixa>

      <ScrollView
        contentContainerStyle={styles.lista}
        showsVerticalScrollIndicator={false}
        refreshControl={controle}>
        <Etiqueta estilo={styles.rotuloDia}>
          {`${diaPorExtenso(selecionado.toISOString())} · ${doDiaAtivos} ${
            doDiaAtivos === 1 ? 'compromisso' : 'compromissos'
          }${doDia.length > doDiaAtivos ? ` · ${doDia.length - doDiaAtivos} ${doDia.length - doDiaAtivos === 1 ? 'cancelado' : 'cancelados'}` : ''}`}
        </Etiqueta>

        {doDia.length === 0 ? (
          <Cartao>
            <Text style={textos.apoio}>Nenhum compromisso neste dia.</Text>
          </Cartao>
        ) : (
          <View style={styles.itens}>
            {doDia.map((a) => {
              const cliente = clienteDe(a);
              const tom = TOM_STATUS[a.status];
              const cancelado = a.status === 'cancelado';
              return (
                <Cartao
                  key={a.id}
                  aoPressionar={() => setAberto(a)}
                  rotuloAcessivel={`${hora(a.dataHora)}, ${cliente?.nome ?? 'cliente removido'}, ${
                    a.servico
                  }. ${STATUS_LABEL[a.status]}. Toque para ver as opções`}
                  estilo={[styles.item, { borderLeftColor: tom.faixa }, cancelado && styles.itemCancelado]}>
                  <View style={styles.itemTopo}>
                    <Text
                      style={[textos.corpoForte, styles.flex, cancelado && styles.riscado]}
                      numberOfLines={1}>
                      {cliente?.nome ?? 'Cliente removido'}
                    </Text>
                    <Text style={[styles.itemHora, cancelado && styles.riscado]}>{hora(a.dataHora)}</Text>
                  </View>
                  <Text style={textos.apoio}>
                    {a.servico}
                    {a.duracaoMin ? ` · ${duracao(a.duracaoMin)}` : ''}
                  </Text>
                  <View style={styles.selos}>
                    <Selo texto={STATUS_CURTO[a.status]} tom={tom.selo} icone={tom.icone} />
                  </View>
                  {cancelado && a.motivoCancelamento ? (
                    <Text style={textos.meta} numberOfLines={2}>
                      Motivo: {a.motivoCancelamento}
                    </Text>
                  ) : null}
                </Cartao>
              );
            })}
          </View>
        )}
      </ScrollView>

      {/* Opções do compromisso, conforme a situação. Cada opção leva a uma ação real. */}
      <FolhaAcoes
        visivel={!!aberto}
        titulo={(aberto && clienteDe(aberto)?.nome) || 'Compromisso'}
        subtitulo={
          aberto
            ? `${dataCurta(aberto.dataHora)} às ${hora(aberto.dataHora)} · ${aberto.servico} · ${STATUS_CURTO[aberto.status]}`
            : undefined
        }
        aoFechar={() => setAberto(null)}
        acoes={aberto ? acoesDo(aberto) : []}
      />

      <DialogoCancelamento
        visivel={!!cancelando}
        resumo={
          cancelando
            ? `${clienteDe(cancelando)?.nome ?? 'Cliente'}, ${dataCurta(cancelando.dataHora)} às ${hora(cancelando.dataHora)}`
            : ''
        }
        aoFechar={() => setCancelando(null)}
        aoConfirmar={async (motivo) => {
          if (!cancelando) return;
          await acoes.cancelarAgendamento(cancelando.id, motivo);
          setCancelando(null);
          avisar('Agendamento cancelado');
        }}
      />
    </Tela>
  );
}

const styles = StyleSheet.create({
  topo: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.sm,
    paddingBottom: espaco.md,
  },
  tituloLinha: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: espaco.md,
    gap: espaco.sm,
  },
  flex: { flex: 1 },
  navegacaoMes: { flexDirection: 'row', alignItems: 'center', gap: espaco.xs },
  botaoMes: {
    width: ALVO_TOQUE,
    height: ALVO_TOQUE,
    borderRadius: raios.campo,
    alignItems: 'center',
    justifyContent: 'center',
  },
  botaoMais: {
    width: ALVO_TOQUE,
    height: ALVO_TOQUE,
    borderRadius: raios.campo,
    backgroundColor: cores.acao,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: espaco.xs,
  },
  calendario: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.bordaSuave,
    borderRadius: raios.cartao,
    paddingHorizontal: espaco.sm,
    paddingVertical: espaco.md,
  },
  semana: { flexDirection: 'row', marginBottom: espaco.xs },
  diaSemana: {
    flex: 1,
    textAlign: 'center',
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 11,
    color: cores.textoApoio,
  },
  grade: { flexDirection: 'row', flexWrap: 'wrap' },
  celula: { width: `${100 / 7}%`, alignItems: 'center', paddingVertical: 2 },
  celulaInterna: {
    width: 40,
    height: 40,
    borderRadius: raios.campo,
    alignItems: 'center',
    justifyContent: 'center',
  },
  celulaAtiva: { backgroundColor: cores.tinta },
  numeroDia: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 14,
    color: cores.textoSecundario,
  },
  numeroHoje: { fontFamily: 'FamiljenGrotesk_700Bold', color: cores.acaoTexto },
  numeroAtivo: { color: cores.escuroTexto },
  marcador: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: cores.acao,
    marginTop: 2,
  },
  marcadorAtivo: { backgroundColor: cores.escuroTexto },
  marcadorVazio: { width: 5, height: 5, marginTop: 2 },
  lista: { paddingHorizontal: espaco.xl, paddingTop: espaco.sm, paddingBottom: espaco.xxl },
  rotuloDia: { paddingVertical: espaco.md },
  itens: { gap: espaco.sm },
  item: { borderLeftWidth: 4, gap: espaco.xs },
  itemCancelado: { opacity: 0.72 },
  riscado: { textDecorationLine: 'line-through' },
  itemTopo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: espaco.sm,
  },
  itemHora: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    fontSize: 14,
    color: cores.acaoTexto,
  },
  selos: {
    flexDirection: 'row',
    gap: espaco.sm,
    marginTop: espaco.sm,
    flexWrap: 'wrap',
  },
  pressionado: { opacity: 0.85 },
});
