import { useMemo, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Etiqueta } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Campo } from '@/components/Campo';
import { CampoData } from '@/components/CampoData';
import { CampoDuracao } from '@/components/CampoDuracao';
import { CampoServico, erroDoServico } from '@/components/CampoServico';
import { Icone } from '@/components/Icone';
import { LinhaCliente } from '@/components/LinhaCliente';
import { CaixaDeErro, estilosFormulario, Rodape } from '@/components/PartesFormulario';
import { useProtecaoDeSaida } from '@/components/ProtecaoDeSaida';
import { SeletorCliente } from '@/components/SeletorCliente';
import { STATUS_LABEL, useCliente } from '@/data/store';
import type { StatusAgendamento } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

/** Mesma folga do servidor para diferença de relógio entre aparelho e servidor. */
const TOLERANCIA_MS = 5 * 60 * 1000;

export type ValoresAgendamento = {
  clienteId: string | null;
  dataHora: Date;
  /** Vazio quando ainda não há serviço escolhido. */
  servico: string;
  /** `null`: duração não informada. */
  duracaoMin: number | null;
  observacoes: string;
  lembrete: boolean;
};

export type EnvioAgendamento = {
  clienteId: string;
  dataHora: string;
  servico: string;
  duracaoMin: number | null;
  observacoes: string;
  lembrete: boolean;
  /** Só na criação: o profissional pode já marcar como confirmado. */
  confirmar: boolean;
};

type Props = {
  modo: 'criar' | 'editar';
  inicial: ValoresAgendamento;
  rotuloSalvar: string;
  /** Grava no servidor. Lança erro com mensagem legível quando o servidor recusa. */
  aoSalvar: (dados: EnvioAgendamento) => Promise<void>;
  /** Chamado depois de salvo, com a saída já liberada: é aqui que a tela navega. */
  aoTerminar: (dados: EnvioAgendamento) => void;
  /** Só na edição: o status não se edita aqui, tem ações próprias. */
  statusAtual?: StatusAgendamento;
};

/**
 * Formulário de agendamento, o mesmo para criar e editar.
 *
 * As validações daqui são para orientar quem preenche, antes de enviar. A palavra final é
 * do servidor, que repete todas elas: data no passado, horário ocupado, cliente de outra
 * conta. Por isso a mensagem de erro do servidor é mostrada como veio.
 */
export function FormularioAgendamento({
  modo,
  inicial,
  rotuloSalvar,
  aoSalvar,
  aoTerminar,
  statusAtual,
}: Props) {
  const [clienteId, setClienteId] = useState<string | null>(inicial.clienteId);
  const [escolhendo, setEscolhendo] = useState(false);
  const [quando, setQuando] = useState(inicial.dataHora);
  const [servico, setServico] = useState(inicial.servico);
  const [duracao, setDuracao] = useState<number | null>(inicial.duracaoMin);
  const [duracaoValida, setDuracaoValida] = useState(true);
  const [observacoes, setObservacoes] = useState(inicial.observacoes);
  const lembrete = inicial.lembrete;
  const [jaConfirmado, setJaConfirmado] = useState(false);
  const [horaValida, setHoraValida] = useState(true);
  const [dataValida, setDataValida] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [tentouSalvar, setTentouSalvar] = useState(false);
  const [salvando, setSalvando] = useState(false);
  // Trava síncrona contra o segundo toque: o estado `salvando` só vale no próximo
  // desenho da tela, e dois toques rápidos chegariam antes dele.
  const enviando = useRef(false);

  const cliente = useCliente(clienteId ?? undefined);
  const hoje = useMemo(() => new Date(), []);

  const alterado =
    clienteId !== inicial.clienteId ||
    quando.getTime() !== inicial.dataHora.getTime() ||
    servico !== inicial.servico ||
    duracao !== inicial.duracaoMin ||
    !duracaoValida ||
    observacoes !== inicial.observacoes ||
    jaConfirmado;
  const { liberar } = useProtecaoDeSaida(alterado);

  async function salvar() {
    if (enviando.current) return;
    setTentouSalvar(true);
    if (!clienteId) {
      setErro('Escolha o cliente do agendamento.');
      return;
    }
    if (!dataValida) {
      setErro('Confira a data: use dd/mm/aaaa, a partir de hoje.');
      return;
    }
    if (!horaValida) {
      setErro('Confira o horário: use HH:MM, entre 00:00 e 23:59.');
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
    // Na edição, a data só é conferida quando muda, como no servidor: anotar algo num
    // compromisso de hoje cedo não pode ser recusado pelo horário que ninguém mexeu.
    const dataMudou = modo === 'criar' || quando.getTime() !== inicial.dataHora.getTime();
    if (dataMudou && quando.getTime() < Date.now() - TOLERANCIA_MS) {
      setErro('Esse horário já passou. Escolha uma data e um horário a partir de agora.');
      return;
    }

    const dados: EnvioAgendamento = {
      clienteId,
      dataHora: quando.toISOString(),
      servico,
      duracaoMin: duracao,
      observacoes: observacoes.trim(),
      lembrete,
      confirmar: modo === 'criar' && jaConfirmado,
    };
    enviando.current = true;
    setSalvando(true);
    setErro(null);
    try {
      await aoSalvar(dados);
    } catch (falha) {
      // Falhou: fica tudo como estava na tela, para corrigir e tentar de novo.
      enviando.current = false;
      setSalvando(false);
      setErro(falha instanceof Error ? falha.message : 'Não foi possível salvar o agendamento.');
      return;
    }
    // Salvo: a saída deixa de ser "perder alterações" antes de qualquer navegação.
    liberar();
    aoTerminar(dados);
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
        {modo === 'editar' && statusAtual ? (
          <View style={styles.statusAtual}>
            <Icone nome="info" tamanho={16} cor={cores.textoSecundario} />
            <Text style={[textos.apoio, estilosFormulario.flex]}>
              Situação: {STATUS_LABEL[statusAtual].toLowerCase()}. Para confirmar, cancelar ou concluir, use
              as opções do agendamento na agenda.
            </Text>
          </View>
        ) : null}

        <LinhaCliente
          cliente={cliente}
          aoPressionar={() => setEscolhendo(true)}
          comErro={!clienteId && !!erro}
        />

        <View style={estilosFormulario.linhaDatas}>
          <CampoData
            rotulo="Data"
            valor={quando}
            aoMudar={setQuando}
            modo="data"
            minimo={hoje}
            aoMudarValidade={(valido) => {
              setDataValida(valido);
              if (valido) setErro(null);
            }}
            estilo={estilosFormulario.flex}
          />
          <CampoData
            rotulo="Horário"
            valor={quando}
            aoMudar={setQuando}
            modo="hora"
            aoMudarValidade={(valido) => {
              setHoraValida(valido);
              if (valido) setErro(null);
            }}
            estilo={estilosFormulario.hora}
          />
        </View>

        <CampoServico
          rotulo="Serviço"
          inicial={inicial.servico}
          aoMudar={(s) => {
            setServico(s);
            if (!erroDoServico(s)) setErro(null);
          }}
          erro={tentouSalvar ? erroDoServico(servico) : null}
        />

        <CampoDuracao
          rotulo="Duração prevista"
          inicial={inicial.duracaoMin}
          aoMudar={setDuracao}
          aoMudarValidade={(valida) => {
            setDuracaoValida(valida);
            if (valida) setErro(null);
          }}
          mostrarErro={tentouSalvar}
          estilo={styles.duracao}
        />

        {modo === 'criar' ? (
          <>
            <Etiqueta estilo={estilosFormulario.etiqueta}>Situação</Etiqueta>
            <View style={styles.statusLinha}>
              {[false, true].map((confirmado) => {
                const ativo = jaConfirmado === confirmado;
                return (
                  <Pressable
                    key={String(confirmado)}
                    onPress={() => setJaConfirmado(confirmado)}
                    accessibilityRole="radio"
                    accessibilityState={{ selected: ativo }}
                    accessibilityLabel={confirmado ? 'Já confirmado com o cliente' : 'Aguardando confirmação'}
                    style={[
                      styles.statusItem,
                      ativo && (confirmado ? styles.statusConfirmado : styles.statusPendente),
                    ]}>
                    <Icone
                      nome={confirmado ? 'ok' : 'relogio'}
                      tamanho={16}
                      cor={ativo ? (confirmado ? cores.sucessoTexto : cores.alertaTexto) : cores.textoApoio}
                    />
                    <Text style={[styles.statusTexto, ativo && styles.statusTextoAtivo]}>
                      {confirmado ? 'Confirmado' : 'Aguardando'}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </>
        ) : null}

        {/* O interruptor de lembrete saiu da tela: o campo existe no banco, mas o envio
            da notificação nunca foi implementado. Uma opção que não faz nada promete o que
            o aplicativo não cumpre. O valor gravado continua sendo preservado. */}

        <Campo
          rotulo="Observações"
          valor={observacoes}
          aoMudar={setObservacoes}
          placeholder="O que preparar, o que o cliente pediu"
          multilinha
          estilo={estilosFormulario.campoAbaixo}
        />

        <CaixaDeErro mensagem={erro} />
      </ScrollView>

      <Rodape>
        <Botao
          titulo={salvando ? 'Salvando…' : rotuloSalvar}
          icone="calendario"
          carregando={salvando}
          aoPressionar={salvar}
        />
      </Rodape>

      <SeletorCliente
        visivel={escolhendo}
        clienteIdAtual={clienteId}
        titulo="Cliente do agendamento"
        aoEscolher={(id) => {
          setClienteId(id);
          setErro(null);
          setEscolhendo(false);
        }}
        aoFechar={() => setEscolhendo(false)}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  statusAtual: {
    flexDirection: 'row',
    gap: espaco.sm,
    alignItems: 'flex-start',
    backgroundColor: cores.superficieSuave,
    borderRadius: raios.campo,
    padding: espaco.md,
    marginBottom: espaco.md,
  },
  duracao: { marginTop: espaco.xl },
  statusLinha: { flexDirection: 'row', gap: espaco.sm },
  statusItem: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: espaco.sm,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.campo,
    paddingVertical: espaco.md,
    minHeight: 48,
  },
  statusPendente: {
    backgroundColor: cores.alertaFundo,
    borderColor: cores.alertaBorda,
    borderWidth: 1.5,
  },
  statusConfirmado: {
    backgroundColor: cores.sucessoFundo,
    borderColor: cores.sucessoBorda,
    borderWidth: 1.5,
  },
  statusTexto: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 14,
    color: cores.textoApoio,
  },
  statusTextoAtivo: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    color: cores.texto,
  },
});
