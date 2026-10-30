import { useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Etiqueta } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Campo } from '@/components/Campo';
import { CampoData } from '@/components/CampoData';
import { CampoDuracao } from '@/components/CampoDuracao';
import { CampoServico, erroDoServico } from '@/components/CampoServico';
import { Icone } from '@/components/Icone';
import { ImagemSimulada } from '@/components/ImagemSimulada';
import { LinhaCliente } from '@/components/LinhaCliente';
import { CaixaDeErro, estilosFormulario, Rodape } from '@/components/PartesFormulario';
import { useProtecaoDeSaida } from '@/components/ProtecaoDeSaida';
import { useSimulacoesDoCliente } from '@/data/store';
import type { Agendamento, Cliente } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta, dataPorExtenso, duracao as rotuloDuracao, hora } from '@/utils/datas';

/** Mesma folga do servidor para diferença de relógio entre aparelho e servidor. */
const TOLERANCIA_MS = 5 * 60 * 1000;

export type ValoresAtendimento = {
  /** Quando o atendimento aconteceu. */
  quando: Date;
  /** Serviço realizado. Vazio: nenhum escolhido ainda. */
  servico: string;
  duracaoMin: number | null;
  observacoes: string;
  simulacaoId: string | null;
};

export type EnvioAtendimento = {
  realizadoEm: string;
  descricao: string;
  duracaoMin: number | null;
  observacoes: string;
  simulacaoId: string | null;
};

type Props = {
  cliente: Cliente;
  /** Presente na conclusão: mostra o que estava previsto. Ausente no registro avulso. */
  agendamento?: Agendamento;
  inicial: ValoresAtendimento;
  rotuloSalvar: string;
  /** Grava no servidor. Lança erro com mensagem legível quando o servidor recusa. */
  aoSalvar: (dados: EnvioAtendimento) => Promise<void>;
  /** Depois de salvo, com a saída já liberada: é aqui que a tela navega. */
  aoTerminar: () => void;
  /** Correção de um atendimento já salvo: só pede confirmação para sair se algo mudou. */
  edicao?: boolean;
  /** Ação a mais no fim do formulário (na correção, excluir o avulso). */
  rodapeExtra?: React.ReactNode;
};

/**
 * Formulário de um atendimento que já aconteceu.
 *
 * O mesmo para os dois caminhos: concluir um agendamento e registrar direto pelo perfil
 * quem chegou sem marcar. Usa os mesmos campos do agendamento (cliente, serviço com
 * "Outro", data e hora, duração digitada, observações), com as regras de quem registra o
 * passado: a data não pode estar no futuro.
 */
export function FormularioAtendimento({
  cliente,
  agendamento,
  inicial,
  rotuloSalvar,
  aoSalvar,
  aoTerminar,
  edicao = false,
  rodapeExtra,
}: Props) {
  const simulacoes = useSimulacoesDoCliente(cliente.id).filter((s) => s.status === 'concluida');

  const [quando, setQuando] = useState(inicial.quando);
  const [servico, setServico] = useState(inicial.servico);
  const [duracao, setDuracao] = useState<number | null>(inicial.duracaoMin);
  const [duracaoValida, setDuracaoValida] = useState(true);
  const [observacoes, setObservacoes] = useState(inicial.observacoes);
  const [simulacaoId, setSimulacaoId] = useState<string | null>(inicial.simulacaoId);
  const [dataValida, setDataValida] = useState(true);
  const [horaValida, setHoraValida] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [tentouSalvar, setTentouSalvar] = useState(false);
  const [salvando, setSalvando] = useState(false);
  // Trava síncrona contra o segundo toque (o estado só muda no próximo desenho).
  const enviando = useRef(false);

  const alterado =
    quando.getTime() !== inicial.quando.getTime() ||
    servico !== inicial.servico ||
    duracao !== inicial.duracaoMin ||
    !duracaoValida ||
    observacoes !== inicial.observacoes ||
    simulacaoId !== inicial.simulacaoId;
  // Registrar avulso é sempre "algo preenchido": sair sem salvar perde o registro. Na
  // correção, o registro já está salvo: só há o que perder se algo mudou.
  const { liberar } = useProtecaoDeSaida(alterado || (!agendamento && !edicao));

  async function salvar() {
    if (enviando.current) return;
    setTentouSalvar(true);
    if (!dataValida || !horaValida) {
      setErro('Confira a data e o horário em que o atendimento aconteceu.');
      return;
    }
    if (quando.getTime() > Date.now() + TOLERANCIA_MS) {
      setErro('O horário do atendimento não pode estar no futuro.');
      return;
    }
    const problemaServico = erroDoServico(servico);
    if (problemaServico) {
      setErro(problemaServico);
      return;
    }
    if (!duracaoValida) {
      setErro('Confira a duração, ou deixe o campo em branco.');
      return;
    }

    enviando.current = true;
    setSalvando(true);
    setErro(null);
    try {
      await aoSalvar({
        realizadoEm: quando.toISOString(),
        descricao: servico,
        duracaoMin: duracao,
        observacoes: observacoes.trim(),
        simulacaoId,
      });
    } catch (falha) {
      enviando.current = false;
      setSalvando(false);
      setErro(falha instanceof Error ? falha.message : 'Não foi possível salvar o atendimento.');
      return;
    }
    liberar();
    aoTerminar();
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={estilosFormulario.flex}
      keyboardVerticalOffset={20}>
      <ScrollView
        contentContainerStyle={estilosFormulario.conteudo}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}>
        <LinhaCliente cliente={cliente} />

        {agendamento ? (
          <View style={styles.previsto}>
            <Text style={textos.etiqueta}>Horário marcado</Text>
            <Text style={textos.corpoForte}>
              {dataPorExtenso(agendamento.dataHora)}, às {hora(agendamento.dataHora)}
            </Text>
            <Text style={textos.meta}>
              Previsto: {agendamento.servico}
              {agendamento.duracaoMin ? ` · ${rotuloDuracao(agendamento.duracaoMin)}` : ''}
            </Text>
          </View>
        ) : null}

        <Etiqueta estilo={estilosFormulario.etiqueta}>Quando o atendimento aconteceu</Etiqueta>
        <View style={styles.datas}>
          <CampoData
            rotulo="Data"
            valor={quando}
            aoMudar={setQuando}
            modo="data"
            aoMudarValidade={setDataValida}
            estilo={estilosFormulario.flex}
          />
          <CampoData
            rotulo="Horário"
            valor={quando}
            aoMudar={setQuando}
            modo="hora"
            aoMudarValidade={setHoraValida}
            estilo={estilosFormulario.hora}
          />
        </View>
        <Text style={[textos.meta, estilosFormulario.dica]}>
          {edicao
            ? 'Corrija se o dia ou o horário ficaram errados. Não pode estar no futuro.'
            : agendamento
            ? 'Veio do horário marcado. Se foi em outro horário, ajuste aqui; o agendamento continua com o horário original.'
            : 'Começa com agora. Se o atendimento foi antes, ajuste a data e o horário.'}
        </Text>

        <CampoServico
          rotulo="Serviço realizado"
          inicial={inicial.servico}
          aoMudar={(s) => {
            setServico(s);
            if (!erroDoServico(s)) setErro(null);
          }}
          erro={tentouSalvar ? erroDoServico(servico) : null}
          rotuloOutro="Qual serviço foi feito?"
        />

        <CampoDuracao
          rotulo="Duração"
          inicial={inicial.duracaoMin}
          aoMudar={setDuracao}
          aoMudarValidade={(valida) => {
            setDuracaoValida(valida);
            if (valida) setErro(null);
          }}
          mostrarErro={tentouSalvar}
          estilo={styles.duracao}
        />

        {simulacoes.length > 0 ? (
          <>
            <Etiqueta estilo={estilosFormulario.etiqueta}>Simulação usada (opcional)</Etiqueta>
            <View style={styles.simulacoes}>
              <Pressable
                onPress={() => setSimulacaoId(null)}
                accessibilityRole="radio"
                accessibilityState={{ selected: simulacaoId === null }}
                style={[styles.simulacao, simulacaoId === null && styles.simulacaoAtiva]}>
                <View style={styles.semSimulacao}>
                  <Icone nome="fechar" tamanho={16} cor={cores.textoApoio} />
                </View>
                <Text style={[textos.apoio, estilosFormulario.flex]}>Nenhuma simulação</Text>
                {simulacaoId === null ? <Icone nome="ok" tamanho={16} cor={cores.acaoTexto} /> : null}
              </Pressable>
              {simulacoes.map((s) => {
                const ativa = simulacaoId === s.id;
                return (
                  <Pressable
                    key={s.id}
                    onPress={() => setSimulacaoId(s.id)}
                    accessibilityRole="radio"
                    accessibilityState={{ selected: ativa }}
                    accessibilityLabel={`Simulação de ${dataCurta(s.criadoEm)}, ${s.parametros.estilo}, ${s.parametros.cor}`}
                    style={[styles.simulacao, ativa && styles.simulacaoAtiva]}>
                    <ImagemSimulada uri={s.imgSaidaUri} estilo={styles.miniatura} raio={6} />
                    <View style={estilosFormulario.flex}>
                      <Text style={textos.apoioForte} numberOfLines={1}>
                        {s.parametros.estilo} · {s.parametros.cor}
                      </Text>
                      <Text style={textos.meta}>
                        {dataCurta(s.criadoEm)}
                        {s.preferida ? ' · preferida' : ''}
                      </Text>
                    </View>
                    {ativa ? <Icone nome="ok" tamanho={16} cor={cores.acaoTexto} /> : null}
                  </Pressable>
                );
              })}
            </View>
          </>
        ) : null}

        <Campo
          rotulo="Observações do atendimento"
          valor={observacoes}
          aoMudar={setObservacoes}
          placeholder="O que foi feito, produtos usados, o que lembrar na próxima vez"
          ajuda="Aparece no histórico do cliente."
          multilinha
          estilo={styles.observacoes}
        />

        <CaixaDeErro mensagem={erro} />
        {rodapeExtra}
      </ScrollView>

      <Rodape>
        <Botao
          titulo={salvando ? 'Salvando…' : rotuloSalvar}
          icone="ok"
          carregando={salvando}
          aoPressionar={salvar}
        />
      </Rodape>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  previsto: {
    backgroundColor: cores.superficieSuave,
    borderRadius: raios.campo,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.md,
    marginTop: espaco.md,
    gap: 2,
  },
  datas: { flexDirection: 'row', gap: espaco.md },
  duracao: { marginTop: espaco.xl },
  observacoes: { marginTop: espaco.xl },
  simulacoes: { gap: espaco.sm },
  simulacao: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.campo,
    padding: espaco.md,
    minHeight: 56,
  },
  simulacaoAtiva: { borderColor: cores.acao, borderWidth: 1.5, backgroundColor: cores.acaoSuave },
  semSimulacao: {
    width: 36,
    height: 44,
    borderRadius: 6,
    backgroundColor: cores.superficieAfundada,
    alignItems: 'center',
    justifyContent: 'center',
  },
  miniatura: { width: 36, height: 44 },
});
