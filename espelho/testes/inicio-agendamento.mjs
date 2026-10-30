/**
 * Teste de unidade da data inicial do agendamento (src/utils/inicioAgendamento.ts).
 * "Hoje" fixado em 23/10/2026 às 10h; o processo roda no fuso de Brasília.
 * Rodar: TZ=America/Sao_Paulo node --experimental-strip-types --no-warnings testes/inicio-agendamento.mjs
 */
import { inicioDeNovoAgendamento } from '../src/utils/inicioAgendamento.ts';

const f = (d) =>
  `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
const manha = new Date(2026, 9, 23, 10, 0);
const tarde = new Date(2026, 9, 23, 16, 10);
const noite = new Date(2026, 9, 23, 23, 40);
const casos = [
  ['dia futuro selecionado', '2026-10-30', manha, '30/10/2026 15:00'],
  ['hoje selecionado, 15h ainda à frente', '2026-10-23', manha, '23/10/2026 15:00'],
  ['hoje selecionado, 15h já passou', '2026-10-23', tarde, '23/10/2026 16:30'],
  ['dia passado selecionado vira hoje', '2026-10-22', manha, '23/10/2026 15:00'],
  ['dia passado, já de tarde', '2020-01-01', tarde, '23/10/2026 16:30'],
  ['quase meia-noite não vira o dia', '2026-10-23', noite, '23/10/2026 23:59'],
  ['virada de mês sem deslocamento', '2026-11-01', manha, '01/11/2026 15:00'],
  ['sem dia (outros pontos de entrada)', undefined, manha, '24/10/2026 15:00'],
  ['dia inválido é ignorado', '30/10/2026', manha, '24/10/2026 15:00'],
];
let falhas = 0;
for (const [nome, dia, agora, esperado] of casos) {
  const obtido = f(inicioDeNovoAgendamento(dia, agora));
  if (obtido !== esperado) {
    falhas++;
    console.log(`FALHA ${nome}: esperado ${esperado}, obtido ${obtido}`);
  }
}
console.log(`${casos.length} casos, ${falhas} falhas`);
process.exit(falhas ? 1 : 0);
