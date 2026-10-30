/**
 * Números do painel inicial. Funções puras, sem dependências, para poderem ser testadas
 * isoladamente (`testes/painel.mjs`).
 */

type AgendamentoResumo = { dataHora: string; status: string };
type SimulacaoResumo = { criadoEm: string; status: string };

/** Mesmo dia no calendário do aparelho (não no de Greenwich). */
function mesmoDiaLocal(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/**
 * Quantos horários estão marcados: agendamentos pendentes ou confirmados, de hoje em
 * diante. Cada horário conta: uma cliente com dois agendamentos conta dois, como na
 * agenda. Antes contava clientes distintos, e o número do painel ficava menor que o da
 * agenda sem explicação. Cancelados e concluídos não contam; um horário de hoje que já
 * passou sem ser concluído continua contando, porque ainda está em aberto na agenda.
 */
export function horariosAgendados(agendamentos: AgendamentoResumo[], agora: Date = new Date()): number {
  const inicioDeHoje = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate()).getTime();
  return agendamentos.filter(
    (a) => (a.status === 'pendente' || a.status === 'confirmado') && new Date(a.dataHora).getTime() >= inicioDeHoje
  ).length;
}

/**
 * "Ainda hoje": os compromissos de hoje que continuam em aberto, na ordem recebida.
 * Concluídos e cancelados saem da lista; um horário de hoje que já passou sem ser
 * concluído fica, porque ainda espera uma decisão na agenda.
 */
export function compromissosDeHoje<T extends AgendamentoResumo>(agendamentos: T[], agora: Date = new Date()): T[] {
  return agendamentos.filter(
    (a) => (a.status === 'pendente' || a.status === 'confirmado') && mesmoDiaLocal(new Date(a.dataHora), agora)
  );
}

/** Simulações geradas hoje. Só as prontas: tentativa que falhou ou ainda está em curso não conta. */
export function simulacoesDeHoje(simulacoes: SimulacaoResumo[], agora: Date = new Date()): number {
  return simulacoes.filter((s) => s.status === 'concluida' && mesmoDiaLocal(new Date(s.criadoEm), agora)).length;
}

/** A preferida primeiro; depois, da mais recente para a mais antiga. */
export function ordenarSimulacoes<T extends { preferida: boolean; criadoEm: string }>(lista: T[]): T[] {
  return [...lista].sort(
    (a, b) => Number(b.preferida) - Number(a.preferida) || b.criadoEm.localeCompare(a.criadoEm)
  );
}
