import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import {
  aoEncerrarSessao,
  agendamentos as apiAgendamentos,
  atendimentos as apiAtendimentos,
  autenticacao,
  clientes as apiClientes,
  consentimentos as apiConsentimentos,
  ErroApi,
  prepararFotoParaEnvio,
  restaurarSessao,
  simulacoes as apiSimulacoes,
  temSessao,
  type CorrecaoAtendimento,
  type DadosCliente,
  type NovaDecisao,
  type ParametrosEnvio,
} from '@/services/api';

import { aquecerTermos } from './termos';
import { ordenarSimulacoes } from '@/utils/painel';

import type {
  Agendamento,
  AvaliacaoCaptura,
  CienciaProfissional,
  Cliente,
  ConfirmacaoIdentidade,
  DadosConclusao,
  EstadoApp,
  HistoricoServico,
  NovoAtendimento,
  RegistroConsentimento,
  ResumoConsentimento,
  Simulacao,
  StatusAgendamento,
  Usuario,
} from './tipos';

/**
 * Estado do aplicativo, alimentado pela API.
 *
 * A estratégia continua sendo `Context + useReducer`, como antes da integração: o volume
 * de dados é pequeno (a carteira de um profissional), o fluxo é por tela e não há
 * sincronização concorrente a resolver. Trocar por uma biblioteca de cache remoto
 * acrescentaria dependência sem resolver problema existente.
 *
 * O que mudou é a origem: em vez de `AsyncStorage` com dados fictícios, o estado é
 * preenchido pelo FastAPI. Nada de dado pessoal fica guardado no aparelho — só o token
 * da sessão, no armazenamento seguro (ver services/api/sessao).
 */

const CIENCIA_VAZIA: CienciaProfissional = { aceita: false, versao: null, registradaEm: null };

function estadoVazio(): EstadoApp {
  return {
    usuario: null,
    autenticado: false,
    cienciaProfissional: CIENCIA_VAZIA,
    clientes: [],
    simulacoes: [],
    historico: [],
    agendamentos: [],
    consentimentosPorCliente: {},
  };
}

type Acao =
  | { tipo: 'sessaoIniciada'; usuario: Usuario }
  | { tipo: 'carga'; dados: Partial<EstadoApp> }
  | { tipo: 'ciencia'; ciencia: CienciaProfissional }
  | { tipo: 'clienteSalvo'; cliente: Cliente }
  | { tipo: 'clienteExcluido'; clienteId: string }
  | { tipo: 'simulacaoSalva'; simulacao: Simulacao }
  | { tipo: 'simulacoesDoCliente'; clienteId: string; simulacoes: Simulacao[] }
  | { tipo: 'atendimentoSalvo'; atendimento: HistoricoServico }
  | { tipo: 'atendimentoExcluido'; atendimentoId: string }
  | { tipo: 'historicoDoCliente'; clienteId: string; historico: HistoricoServico[] }
  | { tipo: 'agendamentoSalvo'; agendamento: Agendamento }
  | { tipo: 'agendamentoExcluido'; agendamentoId: string }
  | { tipo: 'consentimentosDoCliente'; clienteId: string; registros: RegistroConsentimento[] }
  | { tipo: 'sair' };

function substituir<T extends { id: string }>(lista: T[], item: T): T[] {
  const existe = lista.some((atual) => atual.id === item.id);
  return existe ? lista.map((atual) => (atual.id === item.id ? item : atual)) : [item, ...lista];
}

function reducer(estado: EstadoApp, acao: Acao): EstadoApp {
  switch (acao.tipo) {
    case 'sessaoIniciada':
      return { ...estado, usuario: acao.usuario, autenticado: true };
    case 'carga':
      return { ...estado, ...acao.dados };
    case 'ciencia':
      return { ...estado, cienciaProfissional: acao.ciencia };
    case 'clienteSalvo':
      return { ...estado, clientes: substituir(estado.clientes, acao.cliente) };
    case 'clienteExcluido': {
      const { [acao.clienteId]: _removido, ...consentimentos } = estado.consentimentosPorCliente;
      return {
        ...estado,
        clientes: estado.clientes.filter((c) => c.id !== acao.clienteId),
        simulacoes: estado.simulacoes.filter((s) => s.clienteId !== acao.clienteId),
        historico: estado.historico.filter((h) => h.clienteId !== acao.clienteId),
        agendamentos: estado.agendamentos.filter((a) => a.clienteId !== acao.clienteId),
        consentimentosPorCliente: consentimentos,
      };
    }
    case 'simulacaoSalva':
      return { ...estado, simulacoes: substituir(estado.simulacoes, acao.simulacao) };
    case 'simulacoesDoCliente':
      return {
        ...estado,
        simulacoes: [
          ...estado.simulacoes.filter((s) => s.clienteId !== acao.clienteId),
          ...acao.simulacoes,
        ],
      };
    case 'atendimentoSalvo':
      return { ...estado, historico: substituir(estado.historico, acao.atendimento) };
    case 'atendimentoExcluido':
      return { ...estado, historico: estado.historico.filter((h) => h.id !== acao.atendimentoId) };
    case 'historicoDoCliente':
      return {
        ...estado,
        historico: [
          ...estado.historico.filter((h) => h.clienteId !== acao.clienteId),
          ...acao.historico,
        ],
      };
    case 'agendamentoSalvo':
      return { ...estado, agendamentos: substituir(estado.agendamentos, acao.agendamento) };
    case 'agendamentoExcluido':
      return {
        ...estado,
        agendamentos: estado.agendamentos.filter((a) => a.id !== acao.agendamentoId),
      };
    case 'consentimentosDoCliente':
      return {
        ...estado,
        consentimentosPorCliente: {
          ...estado.consentimentosPorCliente,
          [acao.clienteId]: acao.registros,
        },
      };
    case 'sair':
      return estadoVazio();
  }
}

type Acoes = {
  entrar: (email: string, senha: string) => Promise<void>;
  cadastrar: (dados: { nome: string; email: string; senha: string; atuacao?: string }) => Promise<void>;
  /** Entra ou cria a conta com o Google. */
  entrarComGoogle: (idToken: string, nonce?: string) => Promise<void>;
  conectarGoogle: (idToken: string, nonce?: string) => Promise<void>;
  desconectarGoogle: () => Promise<void>;
  atualizarPerfil: (dados: { nome?: string; atuacao?: string }) => Promise<void>;
  /** Foto do profissional: `uri` local já reduzida para envio. */
  enviarMinhaFoto: (uri: string) => Promise<void>;
  removerMinhaFoto: () => Promise<void>;
  sair: () => Promise<void>;
  /** Troca a senha; os outros aparelhos são desconectados, este continua. */
  trocarSenha: (senhaAtual: string, novaSenha: string) => Promise<void>;
  /** Invalida no servidor as sessões de todos os aparelhos; depois, chame `sair`. */
  encerrarTodasAsSessoes: () => Promise<void>;
  recarregar: () => Promise<void>;
  aceitarCiencia: () => Promise<void>;
  registrarConsentimento: (clienteId: string, decisao: NovaDecisao) => Promise<ResumoConsentimento>;
  carregarHistoricoConsentimento: (clienteId: string) => Promise<void>;
  salvarCliente: (dados: DadosCliente, id?: string) => Promise<Cliente>;
  excluirCliente: (clienteId: string) => Promise<void>;
  enviarFotoDoCliente: (clienteId: string, uri: string) => Promise<Cliente>;
  removerFotoDoCliente: (clienteId: string) => Promise<void>;
  excluirImagensDoCliente: (clienteId: string) => Promise<void>;
  criarSimulacao: (dados: ParametrosEnvio) => Promise<Simulacao>;
  acompanharSimulacao: (simulacaoId: string) => Promise<Simulacao>;
  marcarPreferida: (clienteId: string, simulacaoId: string) => Promise<void>;
  /** Apaga uma simulação e as imagens dela; o atendimento vinculado fica, sem o vínculo. */
  excluirSimulacao: (clienteId: string, simulacaoId: string) => Promise<void>;
  /** Atendimento sem agendamento (o cliente chegou sem marcar). */
  registrarAtendimento: (dados: NovoAtendimento) => Promise<HistoricoServico>;
  /** Corrige um atendimento já registrado (serviço, dia e hora, duração, notas). */
  corrigirAtendimento: (id: string, dados: CorrecaoAtendimento) => Promise<HistoricoServico>;
  /** Remove um atendimento avulso registrado por engano. */
  excluirAtendimento: (id: string) => Promise<void>;
  salvarAgendamento: (
    dados: {
      clienteId: string;
      dataHora: string;
      servico: string;
      duracaoMin: number | null;
      observacoes: string;
      lembrete: boolean;
    },
    id?: string
  ) => Promise<Agendamento>;
  confirmarAgendamento: (id: string) => Promise<void>;
  cancelarAgendamento: (id: string, motivo: string) => Promise<void>;
  /** Conclui o compromisso e devolve o atendimento criado (ou o já existente). */
  concluirAgendamento: (
    id: string,
    dados: DadosConclusao
  ) => Promise<HistoricoServico>;
  excluirAgendamento: (id: string) => Promise<void>;
  excluirImagens: () => Promise<void>;
  excluirConta: (confirmacao: ConfirmacaoIdentidade) => Promise<void>;
};

type Contexto = {
  estado: EstadoApp;
  acoes: Acoes;
  /** true enquanto a carga inicial não termina. */
  carregando: boolean;
  /** Falha da carga inicial, para a tela oferecer "tentar de novo". */
  erroDeCarga: string | null;
};

const StoreContext = createContext<Contexto | null>(null);

/** Intervalo entre consultas do estado da simulação (a tela mostra o progresso). */
const INTERVALO_CONSULTA_MS = 1200;
/**
 * Cerca de 150 s de espera: cobre o tempo limite do servidor para o provedor
 * (`AI_TIMEOUT_S`, até 120 s) com folga. Antes eram 72 s, e uma geração lenta, mas dentro
 * do prazo do servidor, aparecia como falha no aparelho.
 */
const TENTATIVAS_MAXIMAS = 125;
/**
 * Falhas de conexão seguidas toleradas durante a espera. A geração continua no servidor
 * quando o Wi-Fi oscila: antes, uma única consulta sem resposta encerrava a espera e a
 * tela dizia que a simulação falhou, embora ela concluísse logo depois.
 */
const FALHAS_DE_CONEXAO_TOLERADAS = 5;

export function StoreProvider({ children }: { children: ReactNode }) {
  const [estado, dispatch] = useReducer(reducer, null, estadoVazio);
  const [carregando, setCarregando] = useState(true);
  const [erroDeCarga, setErroDeCarga] = useState<string | null>(null);
  const montado = useRef(true);

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  /** Busca tudo o que as telas iniciais mostram, em paralelo. */
  const carregarTudo = useCallback(async () => {
    const [usuario, ciencia, lista, agenda, atendimentos, simulacoes] = await Promise.all([
      autenticacao.perfil(),
      autenticacao.ciencia(),
      apiClientes.listar(),
      apiAgendamentos.listar(),
      apiAtendimentos.listar(),
      apiSimulacoes.listar(),
    ]);
    if (!montado.current) return;
    dispatch({ tipo: 'sessaoIniciada', usuario });
    dispatch({
      tipo: 'carga',
      dados: {
        cienciaProfissional: ciencia,
        clientes: lista,
        agendamentos: agenda,
        historico: atendimentos,
        simulacoes,
        consentimentosPorCliente: {},
      },
    });
  }, []);

  const recarregar = useCallback(async () => {
    setErroDeCarga(null);
    setCarregando(true);
    try {
      await carregarTudo();
    } catch (erro) {
      if (!montado.current) return;
      const api = erro instanceof ErroApi ? erro : null;
      if (api?.status === 401) {
        dispatch({ tipo: 'sair' });
      } else {
        setErroDeCarga(api?.message ?? 'Não foi possível carregar seus dados agora.');
      }
    } finally {
      if (montado.current) setCarregando(false);
    }
  }, [carregarTudo]);

  // Sessão encerrada fora de uma ação da tela (o servidor recusou a renovação no meio do
  // uso, a conta foi excluída em outro aparelho): o estado volta ao de quem não entrou, e
  // a guarda de rotas do layout leva ao login.
  useEffect(() => aoEncerrarSessao(() => dispatch({ tipo: 'sair' })), []);

  // Abertura do aplicativo: restaura o token e, se houver, carrega a carteira.
  useEffect(() => {
    let ativo = true;
    (async () => {
      await restaurarSessao();
      aquecerTermos();
      if (!ativo) return;
      if (!temSessao()) {
        setCarregando(false);
        return;
      }
      await recarregar();
    })();
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const valor = useMemo<Contexto>(() => {
    /** Relê um cliente para trazer o resumo de consentimento e a URL da foto atualizados. */
    async function sincronizarCliente(clienteId: string): Promise<Cliente> {
      const cliente = await apiClientes.obter(clienteId);
      dispatch({ tipo: 'clienteSalvo', cliente });
      return cliente;
    }

    const acoes: Acoes = {
      entrar: async (email, senha) => {
        const usuario = await autenticacao.entrar(email, senha);
        dispatch({ tipo: 'sessaoIniciada', usuario });
        await recarregar();
      },

      cadastrar: async (dados) => {
        const usuario = await autenticacao.registrar(dados);
        dispatch({ tipo: 'sessaoIniciada', usuario });
        await recarregar();
      },

      entrarComGoogle: async (idToken, nonce) => {
        const usuario = await autenticacao.entrarComGoogle(idToken, nonce);
        dispatch({ tipo: 'sessaoIniciada', usuario });
        await recarregar();
      },

      conectarGoogle: async (idToken, nonce) => {
        const usuario = await autenticacao.conectarGoogle(idToken, nonce);
        dispatch({ tipo: 'sessaoIniciada', usuario });
      },

      desconectarGoogle: async () => {
        const usuario = await autenticacao.desconectarGoogle();
        dispatch({ tipo: 'sessaoIniciada', usuario });
      },

      enviarMinhaFoto: async (uri) => {
        const usuario = await autenticacao.enviarFoto(await prepararFotoParaEnvio(uri));
        dispatch({ tipo: 'sessaoIniciada', usuario });
      },

      removerMinhaFoto: async () => {
        const usuario = await autenticacao.removerFoto();
        dispatch({ tipo: 'sessaoIniciada', usuario });
      },

      atualizarPerfil: async (dados) => {
        const usuario = await autenticacao.atualizarPerfil(dados);
        dispatch({ tipo: 'sessaoIniciada', usuario });
      },

      sair: async () => {
        await autenticacao.sair();
        dispatch({ tipo: 'sair' });
      },

      trocarSenha: async (senhaAtual, novaSenha) => {
        const usuario = await autenticacao.trocarSenha(senhaAtual, novaSenha);
        dispatch({ tipo: 'sessaoIniciada', usuario });
      },

      encerrarTodasAsSessoes: async () => {
        await autenticacao.encerrarSessoesNoServidor();
      },

      recarregar,

      aceitarCiencia: async () => {
        const ciencia = await autenticacao.registrarCiencia();
        dispatch({ tipo: 'ciencia', ciencia });
      },

      registrarConsentimento: async (clienteId, decisao) => {
        const resumo = await apiConsentimentos.registrar(clienteId, decisao);
        await sincronizarCliente(clienteId);
        const registros = await apiConsentimentos.historico(clienteId);
        dispatch({ tipo: 'consentimentosDoCliente', clienteId, registros });
        return resumo;
      },

      carregarHistoricoConsentimento: async (clienteId) => {
        const registros = await apiConsentimentos.historico(clienteId);
        dispatch({ tipo: 'consentimentosDoCliente', clienteId, registros });
      },

      salvarCliente: async (dados, id) => {
        const cliente = id
          ? await apiClientes.atualizar(id, {
              ...dados,
              limparDataNascimento: dados.dataNascimento === null,
            })
          : await apiClientes.criar(dados);
        dispatch({ tipo: 'clienteSalvo', cliente });
        return cliente;
      },

      excluirCliente: async (clienteId) => {
        await apiClientes.excluir(clienteId);
        dispatch({ tipo: 'clienteExcluido', clienteId });
      },

      enviarFotoDoCliente: async (clienteId, uri) => {
        const cliente = await apiClientes.enviarFoto(clienteId, await prepararFotoParaEnvio(uri));
        dispatch({ tipo: 'clienteSalvo', cliente });
        return cliente;
      },

      removerFotoDoCliente: async (clienteId) => {
        await apiClientes.removerFoto(clienteId);
        await sincronizarCliente(clienteId);
      },

      excluirImagensDoCliente: async (clienteId) => {
        await apiClientes.excluirSimulacoes(clienteId);
        const [simulacoes, historico] = await Promise.all([
          apiClientes.simulacoes(clienteId),
          apiClientes.historico(clienteId),
        ]);
        dispatch({ tipo: 'simulacoesDoCliente', clienteId, simulacoes });
        dispatch({ tipo: 'historicoDoCliente', clienteId, historico });
        await sincronizarCliente(clienteId);
      },

      criarSimulacao: async (dados) => {
        const simulacao = await apiSimulacoes.criar(dados);
        dispatch({ tipo: 'simulacaoSalva', simulacao });
        return simulacao;
      },

      /**
       * Acompanha a geração até concluir ou falhar.
       *
       * O servidor responde 202 e processa em segundo plano; aqui a tela de progresso
       * pergunta pelo estado até ele mudar. Sem fila, sem websocket: o fluxo é curto e
       * tem um usuário só esperando.
       */
      acompanharSimulacao: async (simulacaoId) => {
        let falhasSeguidas = 0;
        for (let tentativa = 0; tentativa < TENTATIVAS_MAXIMAS; tentativa += 1) {
          try {
            const simulacao = await apiSimulacoes.obter(simulacaoId);
            falhasSeguidas = 0;
            dispatch({ tipo: 'simulacaoSalva', simulacao });
            if (simulacao.status !== 'processando') return simulacao;
          } catch (falha) {
            const deConexao = falha instanceof ErroApi && falha.deConexao;
            falhasSeguidas += 1;
            if (!deConexao || falhasSeguidas > FALHAS_DE_CONEXAO_TOLERADAS) throw falha;
          }
          await new Promise((resolver) => setTimeout(resolver, INTERVALO_CONSULTA_MS));
        }
        throw new ErroApi(
          'A simulação está demorando mais que o esperado. Veja o histórico do cliente em instantes.',
          'tempo_esgotado',
          0
        );
      },

      marcarPreferida: async (clienteId, simulacaoId) => {
        await apiSimulacoes.marcarPreferida(simulacaoId);
        const simulacoes = await apiClientes.simulacoes(clienteId);
        dispatch({ tipo: 'simulacoesDoCliente', clienteId, simulacoes });
      },

      excluirSimulacao: async (clienteId, simulacaoId) => {
        try {
          await apiSimulacoes.excluir(simulacaoId);
        } catch (falha) {
          // Já excluída (em outro aparelho, por exemplo): o pedido está cumprido, e a
          // lista recarregada abaixo deixa de mostrá-la.
          if (!(falha instanceof ErroApi && falha.status === 404)) throw falha;
        }
        // O histórico também muda: o atendimento que usava a simulação perde o vínculo.
        const [simulacoes, historico] = await Promise.all([
          apiClientes.simulacoes(clienteId),
          apiClientes.historico(clienteId),
        ]);
        dispatch({ tipo: 'simulacoesDoCliente', clienteId, simulacoes });
        dispatch({ tipo: 'historicoDoCliente', clienteId, historico });
      },

      registrarAtendimento: async (dados) => {
        const atendimento = await apiAtendimentos.criar(dados);
        dispatch({ tipo: 'atendimentoSalvo', atendimento });
        return atendimento;
      },

      corrigirAtendimento: async (id, dados) => {
        const atendimento = await apiAtendimentos.atualizar(id, dados);
        dispatch({ tipo: 'atendimentoSalvo', atendimento });
        return atendimento;
      },

      excluirAtendimento: async (id) => {
        await apiAtendimentos.excluir(id);
        dispatch({ tipo: 'atendimentoExcluido', atendimentoId: id });
      },

      salvarAgendamento: async (dados, id) => {
        const agendamento = id
          ? await apiAgendamentos.atualizar(id, dados)
          : await apiAgendamentos.criar(dados);
        dispatch({ tipo: 'agendamentoSalvo', agendamento });
        return agendamento;
      },


      confirmarAgendamento: async (id) => {
        const agendamento = await apiAgendamentos.confirmar(id);
        dispatch({ tipo: 'agendamentoSalvo', agendamento });
      },

      cancelarAgendamento: async (id, motivo) => {
        const agendamento = await apiAgendamentos.cancelar(id, motivo);
        dispatch({ tipo: 'agendamentoSalvo', agendamento });
      },

      concluirAgendamento: async (id, dados) => {
        // A resposta traz os dois lados: a agenda e o histórico se atualizam juntos, sem
        // recarregar, e o que aparece na tela é o que o servidor gravou.
        const { agendamento, atendimento } = await apiAgendamentos.concluir(id, dados);
        dispatch({ tipo: 'agendamentoSalvo', agendamento });
        dispatch({ tipo: 'atendimentoSalvo', atendimento });
        return atendimento;
      },

      excluirAgendamento: async (id) => {
        await apiAgendamentos.excluir(id);
        dispatch({ tipo: 'agendamentoExcluido', agendamentoId: id });
      },

      excluirImagens: async () => {
        await autenticacao.excluirImagens();
        await recarregar();
      },

      excluirConta: async (confirmacao) => {
        await autenticacao.excluirConta(confirmacao);
        dispatch({ tipo: 'sair' });
      },
    };

    return { estado, acoes, carregando, erroDeCarga };
  }, [estado, carregando, erroDeCarga, recarregar]);

  return <StoreContext.Provider value={valor}>{children}</StoreContext.Provider>;
}

export function useStore(): Contexto {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore precisa estar dentro de <StoreProvider>');
  return ctx;
}

// --- Seletores -------------------------------------------------------------

export function useClientes(): Cliente[] {
  const { estado } = useStore();
  return useMemo(
    () => [...estado.clientes].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    [estado.clientes]
  );
}

export function useCliente(id: string | undefined): Cliente | undefined {
  const { estado } = useStore();
  return estado.clientes.find((c) => c.id === id);
}

export function useSimulacao(id: string | undefined): Simulacao | undefined {
  const { estado } = useStore();
  return estado.simulacoes.find((s) => s.id === id);
}

export function useSimulacoesDoCliente(clienteId: string | undefined): Simulacao[] {
  const { estado } = useStore();
  return useMemo(
    () =>
      // A preferida primeiro, independente da data; depois, da mais recente para a mais antiga.
      ordenarSimulacoes(estado.simulacoes.filter((s) => s.clienteId === clienteId)),
    [estado.simulacoes, clienteId]
  );
}

export function useHistoricoDoCliente(clienteId: string | undefined): HistoricoServico[] {
  const { estado } = useStore();
  return useMemo(
    () =>
      estado.historico
        .filter((h) => h.clienteId === clienteId)
        // Mais recente primeiro; no mesmo dia, pelo horário real e, sem ele, pela gravação.
        .sort(
          (a, b) =>
            b.dataServico.localeCompare(a.dataServico) ||
            (b.realizadoEm ?? b.criadoEm).localeCompare(a.realizadoEm ?? a.criadoEm)
        ),
    [estado.historico, clienteId]
  );
}

export function useAgendamentosOrdenados(): Agendamento[] {
  const { estado } = useStore();
  return useMemo(
    () => [...estado.agendamentos].sort((a, b) => a.dataHora.localeCompare(b.dataHora)),
    [estado.agendamentos]
  );
}

const RESUMO_SEM_CLIENTE: ResumoConsentimento = {
  status: 'pendente',
  rotulo: 'Consentimento pendente',
  revalidar: false,
  registro: null,
  versaoVigente: '',
  exigeResponsavel: false,
  bloqueio: null,
};

/** Resumo calculado pelo servidor e entregue junto do cliente. */
export function useResumoConsentimento(clienteId: string | null | undefined): ResumoConsentimento {
  const cliente = useCliente(clienteId ?? undefined);
  return cliente?.consentimento ?? RESUMO_SEM_CLIENTE;
}

/** Histórico completo das decisões; carregado sob demanda na primeira leitura. */
export function useHistoricoConsentimento(
  clienteId: string | null | undefined
): RegistroConsentimento[] {
  const { estado, acoes } = useStore();
  const carregado = clienteId ? estado.consentimentosPorCliente[clienteId] : undefined;

  useEffect(() => {
    if (!clienteId || carregado) return;
    void acoes.carregarHistoricoConsentimento(clienteId).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId, carregado !== undefined]);

  return carregado ?? [];
}

/**
 * Decide se a câmera pode abrir. A resposta é do servidor (`consentimento.bloqueio`);
 * aqui ela só é traduzida para a forma que as telas consomem.
 */
export function useAvaliacaoCaptura(clienteId: string | null | undefined): AvaliacaoCaptura {
  const cliente = useCliente(clienteId ?? undefined);

  return useMemo<AvaliacaoCaptura>(() => {
    if (!cliente) {
      return {
        permitida: false,
        motivo: 'sem_cliente',
        titulo: 'Escolha o cliente antes de fotografar',
        descricao:
          'Toda simulação pertence a um cliente, e é ele quem autoriza o uso da própria imagem.',
        acao: 'escolher_cliente',
      };
    }
    const bloqueio = cliente.consentimento.bloqueio;
    if (!bloqueio) return { permitida: true };
    return {
      permitida: false,
      motivo: bloqueio.motivo,
      titulo: bloqueio.titulo,
      descricao: bloqueio.descricao,
      acao: 'apresentar_termo',
    };
  }, [cliente]);
}

export const STATUS_LABEL: Record<StatusAgendamento, string> = {
  pendente: 'Aguardando confirmação',
  confirmado: 'Confirmado',
  cancelado: 'Cancelado',
  concluido: 'Concluído',
};

/** Versão curta para selos em linhas estreitas; o texto longo fica no rótulo acessível. */
export const STATUS_CURTO: Record<StatusAgendamento, string> = {
  pendente: 'Pendente',
  confirmado: 'Confirmado',
  cancelado: 'Cancelado',
  concluido: 'Concluído',
};
