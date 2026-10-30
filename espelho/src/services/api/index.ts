/**
 * Camada de acesso ao servidor, um módulo por recurso.
 *
 * As telas não chamam `fetch` em lugar nenhum: usam o store, que usa estas funções.
 * Os tipos de retorno são os mesmos de `src/data/tipos.ts`, porque o JSON da API vem em
 * camelCase exatamente com a forma do domínio do aplicativo.
 */

import type {
  Agendamento,
  Catalogo,
  CienciaProfissional,
  Cliente,
  ConfirmacaoIdentidade,
  DadosConclusao,
  Genero,
  HistoricoServico,
  NovoAtendimento,
  PlanoSimulacao,
  RegistroConsentimento,
  ResumoConsentimento,
  Sessao,
  Simulacao,
  StatusAgendamento,
  Termo,
  TipoTermo,
  Usuario,
} from '@/data/tipos';

import { arquivoLocal } from './arquivoLocal';
import { api, ErroApi, requisitar, URL_BASE } from './cliente';
import { aoEncerrarSessao, encerrarSessao, guardarSessao, restaurarSessao, temSessao } from './sessao';

export { ErroApi, URL_BASE, aoEncerrarSessao, encerrarSessao, restaurarSessao, temSessao };

// --- Autenticação e conta -------------------------------------------------

export const autenticacao = {
  async registrar(dados: { nome: string; email: string; senha: string; atuacao?: string }) {
    const sessao = await api.criar<Sessao>('/auth/registrar', dados, true);
    await guardarSessao(sessao.tokens.accessToken, sessao.tokens.refreshToken);
    return sessao.usuario;
  },

  async entrar(email: string, senha: string) {
    const sessao = await api.criar<Sessao>('/auth/login', { email, senha }, true);
    await guardarSessao(sessao.tokens.accessToken, sessao.tokens.refreshToken);
    return sessao.usuario;
  },

  /** Entra (ou cria a conta, no primeiro acesso) com o ID token recebido do Google. */
  async entrarComGoogle(idToken: string, nonce?: string) {
    const sessao = await api.criar<Sessao>('/auth/google', { idToken, nonce }, true);
    await guardarSessao(sessao.tokens.accessToken, sessao.tokens.refreshToken);
    return sessao.usuario;
  },

  /** Formas de entrar ligadas no servidor. */
  provedores: () => api.obter<{ google: boolean }>('/auth/provedores', undefined, true),

  conectarGoogle: (idToken: string, nonce?: string) =>
    api.criar<Usuario>('/usuarios/me/google', { idToken, nonce }),

  desconectarGoogle: () => api.excluir<Usuario>('/usuarios/me/google'),

  /** Foto do próprio profissional. */
  enviarFoto: (foto: FotoParaEnvio) => {
    const formulario = new FormData();
    anexarImagem(formulario, 'arquivo', foto);
    return api.enviar<Usuario>('/usuarios/me/foto', formulario);
  },

  removerFoto: () => api.excluir<Usuario>('/usuarios/me/foto'),

  sair: () => encerrarSessao(),

  /**
   * Troca a senha. O servidor encerra as sessões dos outros aparelhos e devolve tokens
   * novos para este, que continua conectado.
   */
  async trocarSenha(senhaAtual: string, novaSenha: string) {
    const sessao = await api.criar<Sessao>('/usuarios/me/senha', { senhaAtual, novaSenha });
    await guardarSessao(sessao.tokens.accessToken, sessao.tokens.refreshToken);
    return sessao.usuario;
  },

  /**
   * Encerra no servidor as sessões de todos os aparelhos, inclusive a deste: os tokens
   * guardados aqui deixam de valer. Quem chama apaga os tokens locais em seguida (`sair`).
   */
  encerrarSessoesNoServidor: () => api.excluir('/usuarios/me/sessoes'),

  perfil: () => api.obter<Usuario>('/usuarios/me'),

  atualizarPerfil: (dados: { nome?: string; atuacao?: string }) =>
    api.atualizar<Usuario>('/usuarios/me', dados),

  ciencia: () => api.obter<CienciaProfissional>('/usuarios/me/ciencia'),

  registrarCiencia: () => api.criar<CienciaProfissional>('/usuarios/me/ciencia'),

  excluirImagens: () => api.excluir('/usuarios/me/imagens'),

  async excluirConta(confirmacao: ConfirmacaoIdentidade) {
    await api.excluir('/usuarios/me', confirmacao);
    await encerrarSessao();
  },
};

// --- Clientes -------------------------------------------------------------

export type FotoParaEnvio = {
  uri: string;
  nome?: string;
  /** Preenchido na web por `prepararFotoParaEnvio`. */
  blob?: Blob;
};

export type DadosCliente = {
  nome: string;
  telefone: string;
  observacoes: string;
  dataNascimento: string | null;
};

export const clientes = {
  listar: (busca?: string) => api.obter<Cliente[]>('/clientes', { busca }),

  obter: (id: string) => api.obter<Cliente>(`/clientes/${id}`),

  criar: (dados: DadosCliente) => api.criar<Cliente>('/clientes', dados),

  atualizar: (id: string, dados: Partial<DadosCliente> & { limparDataNascimento?: boolean }) =>
    api.atualizar<Cliente>(`/clientes/${id}`, dados),

  excluir: (id: string) => api.excluir(`/clientes/${id}`),

  historico: (id: string) => api.obter<HistoricoServico[]>(`/clientes/${id}/historico`),

  simulacoes: (id: string) => api.obter<Simulacao[]>(`/clientes/${id}/simulacoes`),

  agendamentos: (id: string) => api.obter<Agendamento[]>(`/clientes/${id}/agendamentos`),

  excluirSimulacoes: (id: string) => api.excluir(`/clientes/${id}/simulacoes`),

  enviarFoto: (id: string, foto: FotoParaEnvio) => {
    const formulario = new FormData();
    anexarImagem(formulario, 'arquivo', foto);
    return api.enviar<Cliente>(`/clientes/${id}/foto`, formulario);
  },

  removerFoto: (id: string) => api.excluir(`/clientes/${id}/foto`),
};

// --- Consentimento --------------------------------------------------------

export type NovaDecisao = {
  decisao: 'aceito' | 'recusado' | 'revogado';
  formaObtencao: RegistroConsentimento['formaObtencao'];
  confirmadoPor: string;
  responsavel: { nome: string; parentesco: string } | null;
  observacao: string;
};

export const consentimentos = {
  atual: (clienteId: string) =>
    api.obter<ResumoConsentimento>(`/clientes/${clienteId}/consentimento`),

  historico: (clienteId: string) =>
    api.obter<RegistroConsentimento[]>(`/clientes/${clienteId}/consentimentos`),

  registrar: (clienteId: string, decisao: NovaDecisao) =>
    api.criar<ResumoConsentimento>(`/clientes/${clienteId}/consentimentos`, decisao),
};

// --- Simulações -----------------------------------------------------------

/** O pedido de personalização, como a tela "Estilo e cor" o monta. */
export type PedidoSimulacao = {
  /** Descrição do corte. Ignorada quando `manterCorte`. */
  corte: string;
  manterCorte: boolean;
  /** Descrição da cor. Ignorada quando `manterCor`. */
  cor: string;
  manterCor: boolean;
  /** Gênero do corte: vai ao modelo como `gender` ("none", "male" ou "female"). */
  genero: Genero;
};

export type ParametrosEnvio = PedidoSimulacao & {
  clienteId: string;
  observacoes: string;
  foto: FotoParaEnvio;
  /** Identifica o envio: repetir a mesma chave devolve a mesma simulação, sem cobrar outra. */
  chaveEnvio: string;
  /** Atalhos de demonstração; só têm efeito se o servidor estiver em modo demo. */
  demoRecusarFoto?: boolean;
  demoFalharIa?: boolean;
};

export const simulacoes = {
  criar: ({ foto, ...dados }: ParametrosEnvio) => {
    const formulario = new FormData();
    formulario.append('clienteId', dados.clienteId);
    formulario.append('corte', dados.manterCorte ? '' : dados.corte);
    formulario.append('manterCorte', dados.manterCorte ? 'true' : 'false');
    formulario.append('cor', dados.manterCor ? '' : dados.cor);
    formulario.append('manterCor', dados.manterCor ? 'true' : 'false');
    formulario.append('genero', dados.genero);
    formulario.append('observacoes', dados.observacoes);
    formulario.append('chaveEnvio', dados.chaveEnvio);
    if (dados.demoRecusarFoto) formulario.append('demoRecusarFoto', 'true');
    if (dados.demoFalharIa) formulario.append('demoFalharIa', 'true');
    anexarImagem(formulario, 'foto', foto);
    return api.enviar<Simulacao>('/simulacoes', formulario);
  },

  /** Prévia de como o pedido será gerado. Não envia foto e não gasta crédito. */
  plano: (pedido: PedidoSimulacao) => api.criar<PlanoSimulacao>('/simulacoes/plano', pedido),

  obter: (id: string) => api.obter<Simulacao>(`/simulacoes/${id}`),

  /** Pergunta ao servidor se o rosto está dentro do guia (miniatura, não guardada). */
  conferirEnquadramento: (clienteId: string, foto: FotoParaEnvio) => {
    const formulario = new FormData();
    formulario.append('clienteId', clienteId);
    anexarImagem(formulario, 'foto', foto);
    return api.enviar<{ rostoNoGuia: boolean }>('/simulacoes/enquadramento', formulario);
  },

  listar: (clienteId?: string) => api.obter<Simulacao[]>('/simulacoes', { clienteId }),

  marcarPreferida: (id: string) => api.criar<Simulacao>(`/simulacoes/${id}/preferida`),

  /** Apaga a simulação e as imagens dela. O histórico de atendimentos fica. */
  excluir: (id: string) => api.excluir(`/simulacoes/${id}`),
};

// --- Atendimentos e agenda ------------------------------------------------

export const atendimentos = {
  listar: (clienteId?: string) => api.obter<HistoricoServico[]>('/atendimentos', { clienteId }),

  criar: (dados: NovoAtendimento) => api.criar<HistoricoServico>('/atendimentos', dados),

  atualizar: (id: string, dados: CorrecaoAtendimento) =>
    api.atualizar<HistoricoServico>(`/atendimentos/${id}`, dados),

  /** Só atendimentos avulsos; o servidor recusa os que vieram da agenda. */
  excluir: (id: string) => api.excluir(`/atendimentos/${id}`),
};

/** Campos ausentes não mudam; `duracaoMin: null` apaga a duração. */
export type CorrecaoAtendimento = {
  descricao?: string;
  dataServico?: string;
  realizadoEm?: string;
  duracaoMin?: number | null;
  observacoes?: string;
  simulacaoId?: string;
  desvincularSimulacao?: boolean;
};

export const agendamentos = {
  listar: (clienteId?: string) => api.obter<Agendamento[]>('/agendamentos', { clienteId }),

  criar: (dados: {
    clienteId: string;
    dataHora: string;
    servico: string;
    duracaoMin: number | null;
    observacoes: string;
    lembrete: boolean;
  }) => api.criar<Agendamento>('/agendamentos', dados),

  atualizar: (
    id: string,
    dados: {
      clienteId?: string;
      dataHora?: string;
      servico?: string;
      duracaoMin?: number | null;
      observacoes?: string;
      lembrete?: boolean;
    }
  ) => api.atualizar<Agendamento>(`/agendamentos/${id}`, dados),

  confirmar: (id: string) => api.criar<Agendamento>(`/agendamentos/${id}/confirmar`, {}),

  /** Cancela preservando o registro: o compromisso sai da agenda ativa, não do banco. */
  cancelar: (id: string, motivo: string) =>
    api.criar<Agendamento>(`/agendamentos/${id}/cancelar`, { motivo }),

  /**
   * Conclui e cria o atendimento, na mesma transação do servidor. Repetir devolve o mesmo
   * atendimento, sem duplicar.
   */
  concluir: (
    id: string,
    dados: DadosConclusao
  ) =>
    api.criar<{ agendamento: Agendamento; atendimento: HistoricoServico }>(
      `/agendamentos/${id}/concluir`,
      dados
    ),

  mudarStatus: (id: string, status: StatusAgendamento) =>
    api.atualizar<Agendamento>(`/agendamentos/${id}/status`, { status }),

  excluir: (id: string) => api.excluir(`/agendamentos/${id}`),
};

// --- Termos e catálogo (rotas públicas) -----------------------------------

export const termos = {
  vigente: (tipo: TipoTermo) => api.obter<Termo>(`/termos/${tipo}`, undefined, true),

  porVersao: (tipo: TipoTermo, versao: string) =>
    api.obter<Termo>(`/termos/${tipo}/${versao}`, undefined, true),
};

export const catalogo = {
  obter: () => api.obter<Catalogo>('/catalogo', undefined, true),
};

export const diagnostico = {
  saude: () => requisitar<{ ok: boolean; provedorIa: string; modoDemo: boolean }>('/saude', {
    publica: true,
  }),
};

// --- Apoio ----------------------------------------------------------------

/**
 * Anexa a imagem ao formulário.
 *
 * São dois mundos: na web, o `Blob` obtido antes por `prepararFotoParaEnvio`; no
 * aparelho, o arquivo local lido por `arquivoLocal` (o `expo/fetch` do SDK 57 não aceita
 * mais `{ uri, name, type }`).
 */
function anexarImagem(formulario: FormData, campo: string, foto: FotoParaEnvio): void {
  const nome = foto.nome ?? 'foto.jpg';
  formulario.append(campo, foto.blob ?? arquivoLocal(foto.uri), nome);
}

/**
 * Prepara a foto capturada para o envio.
 *
 * Na web, `blob:` e `data:` são lidos agora e viram `Blob`; no aparelho, o caminho do
 * arquivo segue como está, e os bytes são lidos na hora do envio (`arquivoLocal`).
 */
export async function prepararFotoParaEnvio(uri: string): Promise<FotoParaEnvio> {
  if (!uri.startsWith('blob:') && !uri.startsWith('data:')) return { uri };
  const resposta = await fetch(uri);
  const blob = await resposta.blob();
  return { uri, nome: 'foto.jpg', blob };
}
