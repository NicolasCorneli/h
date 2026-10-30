/** Hora sugerida quando nada indica outra: a mesma de antes desta regra (15h). */
const HORA_SUGERIDA = 15;

/**
 * Data e hora iniciais de um agendamento novo.
 *
 * - `dia` ("aaaa-mm-dd", o dia aberto na agenda) no futuro: esse dia, às 15h;
 * - `dia` igual a hoje, ou no passado: hoje, nunca um dia que já passou. A hora é 15h se
 *   ainda não passou; senão, a próxima meia hora (sem virar o dia);
 * - sem `dia` (aberto pelo perfil, por exemplo): amanhã às 15h, como sempre foi.
 *
 * A comparação é por dia do calendário do aparelho, sem passar por Greenwich.
 */
export function inicioDeNovoAgendamento(dia?: string, agora: Date = new Date()): Date {
  const hoje = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate());
  const partes = dia ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(dia) : null;
  // Dia do calendário local, montado por partes: `new Date("2026-10-30")` seria meia-noite
  // em Greenwich, que no Brasil ainda é dia 29.
  const escolhido = partes ? new Date(Number(partes[1]), Number(partes[2]) - 1, Number(partes[3])) : null;

  if (!escolhido || Number.isNaN(escolhido.getTime())) {
    const amanha = new Date(hoje);
    amanha.setDate(amanha.getDate() + 1);
    amanha.setHours(HORA_SUGERIDA, 0, 0, 0);
    return amanha;
  }
  if (escolhido.getTime() > hoje.getTime()) {
    escolhido.setHours(HORA_SUGERIDA, 0, 0, 0);
    return escolhido;
  }
  const sugerida = new Date(hoje);
  sugerida.setHours(HORA_SUGERIDA, 0, 0, 0);
  if (sugerida.getTime() > agora.getTime()) return sugerida;

  const proxima = new Date(agora);
  proxima.setSeconds(0, 0);
  proxima.setMinutes(proxima.getMinutes() < 30 ? 30 : 60);
  if (proxima.getDate() !== agora.getDate()) {
    // Depois das 23h30 não há meia hora inteira pela frente: fica no último minuto de hoje.
    const fim = new Date(hoje);
    fim.setHours(23, 59, 0, 0);
    return fim;
  }
  return proxima;
}
