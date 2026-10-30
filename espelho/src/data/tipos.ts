/**
 * Entidades do domínio — o mesmo contrato da API.
 *
 * O JSON do servidor vem em camelCase com exatamente esta forma, de modo que não existe
 * camada de tradução entre HTTP e interface. Os nomes seguem a modelagem da seção 5.6 do
 * pré-projeto (usuarios, clientes, consentimentos, simulacoes, historico_servicos,
 * agendamentos), para permanecerem rastreáveis à Tabela 4 do TCC.
 */

export type StatusAgendamento = 'pendente' | 'confirmado' | 'cancelado' | 'concluido';

export type Usuario = {
  id: string;
  nome: string;
  email: string;
  atuacao: string;
  criadoEm: string;
  /** Contas criadas pelo Google não têm senha. */
  temSenha: boolean;
  googleVinculado: boolean;
  /** URL assinada e temporária da foto do profissional; vazia sem foto. */
  fotoUri: string | null;
};

/** Confirmação de uma operação irreversível: a senha, ou o Google nas contas sem senha. */
export type ConfirmacaoIdentidade = { senha: string } | { idTokenGoogle: string };

export type Tokens = {
  accessToken: string;
  refreshToken: string;
  tipo: string;
  expiraEm: number;
};

export type Sessao = { tokens: Tokens; usuario: Usuario };

// --- Consentimento de imagem (RNF05) --------------------------------------
//
// O consentimento pertence ao CLIENTE, titular da imagem (LGPD, art. 5º, XII). O
// profissional apenas registra a decisão dele. Quem decide se a captura está liberada é
// o servidor: `ResumoConsentimento.bloqueio` é a resposta dele, não um cálculo local.

export type ConsentimentoStatus = 'pendente' | 'aceito' | 'recusado' | 'revogado';

export type FormaObtencao = 'tela_dispositivo' | 'lido_em_voz_alta' | 'termo_impresso';

export type FaixaEtaria = 'crianca' | 'adolescente' | 'adulto' | 'desconhecida';

export type ResponsavelLegal = { nome: string; parentesco: string };

/** Cada decisão é um registro imutável; o histórico anterior permanece (art. 37). */
export type RegistroConsentimento = {
  id: string;
  clienteId: string;
  /** Profissional que apresentou o termo e registrou a decisão. */
  usuarioId: string;
  decisao: Exclude<ConsentimentoStatus, 'pendente'>;
  versaoTermo: string;
  registradoEm: string;
  formaObtencao: FormaObtencao;
  /** Nome de quem confirmou: o próprio cliente ou o responsável legal. */
  confirmadoPor: string;
  responsavel: ResponsavelLegal | null;
  faixaEtaria: FaixaEtaria;
  observacao: string;
};

export type MotivoBloqueio = 'pendente' | 'revalidar' | 'recusado' | 'revogado';

/** Por que o servidor recusa a captura, com o texto que a interface exibe. */
export type BloqueioCaptura = {
  motivo: MotivoBloqueio;
  titulo: string;
  descricao: string;
};

export type ResumoConsentimento = {
  status: ConsentimentoStatus;
  rotulo: string;
  revalidar: boolean;
  registro: RegistroConsentimento | null;
  /** Versão vigente no servidor — a única válida para uma nova decisão. */
  versaoVigente: string;
  exigeResponsavel: boolean;
  /** Ausente quando a captura está liberada. */
  bloqueio: BloqueioCaptura | null;
};

export type Cliente = {
  id: string;
  usuarioId: string;
  nome: string;
  telefone: string;
  observacoes: string;
  /** ISO 8601 (só a data). Opcional: quando informada, decide a exigência de responsável. */
  dataNascimento: string | null;
  /** URL assinada de curta duração, ou null. */
  fotoUri: string | null;
  criadoEm: string;
  consentimento: ResumoConsentimento;
};

// --- Simulação (RF04, RF05, RF07) -----------------------------------------

/**
 * Gênero do corte, com os valores exatos do campo `gender` do modelo `change-haircut`.
 * "none" (não especificar) é o padrão do próprio modelo.
 */
export type Genero = 'none' | 'male' | 'female';

export type ParametrosSimulacao = {
  /** Corte pedido: a descrição escrita ou "Corte atual". */
  estilo: string;
  /** Cor pedida: a descrição escrita ou "Cor atual". */
  cor: string;
  /** Gênero do corte enviado ao modelo. */
  genero: Genero;
  observacoes: string;
};

export type StatusSimulacao = 'processando' | 'concluida' | 'falhou';

export type Simulacao = {
  id: string;
  clienteId: string;
  usuarioId: string;
  parametros: ParametrosSimulacao;
  status: StatusSimulacao;
  /** URLs assinadas; a de saída só existe quando a geração conclui. */
  imgEntradaUri: string | null;
  imgSaidaUri: string | null;
  modeloIa: string;
  provedor: string;
  /** O que foi pedido ao modelo (instrução ou opções), para conferir e avaliar o resultado. */
  instrucaoIa: string | null;
  /** Medido no servidor — é a evidência do RNF02. */
  tempoMs: number | null;
  preferida: boolean;
  erroCodigo: string | null;
  criadoEm: string;
  concluidaEm: string | null;
};

export type HistoricoServico = {
  id: string;
  clienteId: string;
  usuarioId: string;
  /** Vínculo opcional: um atendimento pode existir sem simulação prévia (seção 5.6). */
  simulacaoId: string | null;
  /** O agendamento de origem. Vazio nos atendimentos avulsos e nos antigos. */
  agendamentoId: string | null;
  descricao: string;
  /** O dia em que o serviço aconteceu (aaaa-mm-dd), no fuso do salão. */
  dataServico: string;
  /** O instante real da conclusão. Vazio nos registros antigos: não se inventa. */
  realizadoEm: string | null;
  /** Quanto durou, quando informado. */
  duracaoMin: number | null;
  observacoes: string;
  criadoEm: string;
};

export type Agendamento = {
  id: string;
  clienteId: string;
  usuarioId: string;
  dataHora: string;
  servico: string;
  /** Duração prevista, em minutos. Vazia quando não foi informada. */
  duracaoMin: number | null;
  status: StatusAgendamento;
  observacoes: string;
  lembrete: boolean;
  /** Quando foi cancelado. Vazio em cancelamentos anteriores a este campo. */
  canceladoEm: string | null;
  motivoCancelamento: string;
  /** O atendimento gerado ao concluir, quando houver. */
  atendimentoId: string | null;
};

// --- Termos e ciência -----------------------------------------------------

export type TipoTermo = 'cliente' | 'profissional';

export type SecaoTermo = {
  titulo: string;
  texto: string;
  /** Destaca a seção: usado nos trechos sobre dado sensível e envio a terceiros. */
  destaque?: boolean;
};

export type Termo = {
  tipo: TipoTermo;
  versao: string;
  vigenteDesde: string;
  vigente: boolean;
  titulo: string;
  resumo: string;
  secoes: SecaoTermo[];
};

/**
 * Ciência das responsabilidades do profissional. Não é consentimento de imagem: é o
 * reconhecimento de que cabe a ele informar o cliente antes de registrar a decisão.
 */
export type CienciaProfissional = {
  aceita: boolean;
  versao: string | null;
  registradaEm: string | null;
};

export type Catalogo = {
  estilos: string[];
  cores: string[];
  servicos: string[];
};

/** Como o servidor vai gerar o pedido: modo, modelo e o que será enviado (sem a foto). */
export type PlanoSimulacao = {
  /** "fake" no provedor local de desenvolvimento, que não usa IA. */
  provedor: string;
  modo: 'opcoes' | 'descricao';
  descricaoModo: string;
  modelo: string;
  instrucao: string;
  estilo: string;
  cor: string;
};

// --- Estado do aplicativo -------------------------------------------------

/** Resultado da avaliação de captura, montado a partir da resposta do servidor. */
export type AvaliacaoCaptura =
  | { permitida: true }
  | {
      permitida: false;
      motivo: MotivoBloqueio | 'sem_cliente';
      titulo: string;
      descricao: string;
      /** O que a interface deve oferecer como saída. */
      acao: 'escolher_cliente' | 'apresentar_termo';
    };

export type EstadoApp = {
  usuario: Usuario | null;
  autenticado: boolean;
  cienciaProfissional: CienciaProfissional;
  clientes: Cliente[];
  simulacoes: Simulacao[];
  historico: HistoricoServico[];
  agendamentos: Agendamento[];
  /** Histórico de consentimentos carregado sob demanda, por cliente. */
  consentimentosPorCliente: Record<string, RegistroConsentimento[]>;
};

/** Atendimento registrado direto pelo perfil, sem agendamento de origem. */
export type NovoAtendimento = {
  clienteId: string;
  descricao: string;
  /** Instante em que aconteceu (ISO com fuso). O servidor calcula o dia no fuso do salão. */
  realizadoEm: string;
  duracaoMin: number | null;
  observacoes: string;
  simulacaoId: string | null;
};

/** O que se informa ao concluir um agendamento. */
export type DadosConclusao = {
  realizadoEm?: string;
  descricao?: string;
  duracaoMin?: number | null;
  observacoes?: string;
  simulacaoId?: string | null;
};
