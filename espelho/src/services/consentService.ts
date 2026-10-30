import type { AvaliacaoCaptura, Cliente, FaixaEtaria, FormaObtencao } from '@/data/tipos';
import { paraData } from '@/utils/datas';

/**
 * Apoio de interface para o consentimento de imagem.
 *
 * O que **decide** ficou no servidor: status, necessidade de revalidação e liberação da
 * captura vêm em `Cliente.consentimento` (ver `ResumoConsentimento`), calculados pelo
 * FastAPI a cada resposta. Antes essas regras moravam aqui, e isso era uma fraqueza:
 * validação só no aplicativo é conveniência de interface, não controle de acesso.
 *
 * Sobrou neste módulo o que é mesmo da interface: rótulos, cálculo de idade para exibição
 * e para antecipar o campo de responsável legal, e a rota a seguir após uma avaliação.
 */

export const FORMAS_OBTENCAO: { valor: FormaObtencao; rotulo: string; descricao: string }[] = [
  {
    valor: 'tela_dispositivo',
    rotulo: 'Leu nesta tela',
    descricao: 'O aparelho foi entregue ao cliente, que leu o termo e confirmou.',
  },
  {
    valor: 'lido_em_voz_alta',
    rotulo: 'Li em voz alta',
    descricao: 'O termo foi lido para o cliente, que respondeu verbalmente.',
  },
  {
    valor: 'termo_impresso',
    rotulo: 'Termo impresso',
    descricao: 'O cliente assinou uma via em papel, arquivada fora do aplicativo.',
  },
];

export function rotuloFormaObtencao(forma: FormaObtencao): string {
  return FORMAS_OBTENCAO.find((f) => f.valor === forma)?.rotulo ?? forma;
}

// --- Idade e responsável legal ---------------------------------------------

export function idadeEm(dataNascimento: string | null, referencia = new Date()): number | null {
  if (!dataNascimento) return null;
  // Dia do calendário, sem fuso: lido como instante, o aniversário cairia um dia antes.
  const nascimento = paraData(dataNascimento);
  if (Number.isNaN(nascimento.getTime())) return null;

  let idade = referencia.getFullYear() - nascimento.getFullYear();
  const aniversarioPassou =
    referencia.getMonth() > nascimento.getMonth() ||
    (referencia.getMonth() === nascimento.getMonth() &&
      referencia.getDate() >= nascimento.getDate());
  if (!aniversarioPassou) idade -= 1;
  return idade;
}

/**
 * A LGPD trata criança (até 12 anos incompletos) no art. 14, §1º, exigindo consentimento
 * específico e destacado de um dos pais ou do responsável legal. Para adolescentes o app
 * adota a mesma exigência, por precaução. O servidor aplica o mesmo critério.
 */
export function faixaEtaria(cliente: Cliente | null | undefined, referencia = new Date()): FaixaEtaria {
  const idade = idadeEm(cliente?.dataNascimento ?? null, referencia);
  if (idade === null) return 'desconhecida';
  if (idade < 12) return 'crianca';
  if (idade < 18) return 'adolescente';
  return 'adulto';
}

/**
 * Antecipa o campo de responsável no formulário. A exigência de verdade é a do servidor,
 * que recusa o registro sem responsável para menor de 18 (`responsavel_obrigatorio`).
 */
export function exigeResponsavel(cliente: Cliente | null | undefined, referencia = new Date()): boolean {
  const faixa = faixaEtaria(cliente, referencia);
  return faixa === 'crianca' || faixa === 'adolescente';
}

// --- Navegação ------------------------------------------------------------

/**
 * Para onde ir depois de avaliar a captura. Quem nunca decidiu vê o termo direto, sem
 * etapa intermediária; quem recusou ou cancelou vê primeiro a explicação do bloqueio,
 * porque a decisão dele precisa ser respeitada antes de ser questionada.
 */
export function rotaAposAvaliacao(avaliacao: AvaliacaoCaptura, clienteId: string): string {
  if (avaliacao.permitida) return '/simulacao/captura';
  if (avaliacao.motivo === 'pendente' || avaliacao.motivo === 'revalidar') {
    return `/consentimento/${clienteId}?retorno=captura`;
  }
  return '/simulacao/captura';
}
