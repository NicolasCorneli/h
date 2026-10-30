/**
 * Teste de unidade do interpretador de duração (src/utils/duracao.ts).
 * Rodar: node --experimental-strip-types --no-warnings testes/duracao.mjs
 */
import { formatarDuracao, lerDuracao } from "../src/utils/duracao.ts";
const casos = [
  ['', null], ['   ', null], ['45', 45], ['45 min', 45], ['45min', 45], ['45 minutos', 45], ['45m', 45],
  ['1h', 60], ['1 h', 60], ['1 hora', 60], ['2 horas', 120], ['1H30', 90], ['1h30', 90], ['1h 30min', 90],
  ['1 hora e 30 minutos', 90], ['1h e 30', 90], ['1:30', 90], ['01:45', 105], ['1,5h', 90], ['1.5 horas', 90],
  ['8h', 480], ['15', 15], ['10', 'x'], ['9h', 'x'], ['1h75', 'x'], ['abc', 'x'], ['1:75', 'x'], ['meia hora', 'x'], ['0', 'x'],
];
let falhas = 0;
for (const [entrada, esperado] of casos) {
  const r = lerDuracao(entrada);
  const obtido = r.tipo === 'vazia' ? null : r.tipo === 'valida' ? r.minutos : 'x';
  if (obtido !== esperado) { falhas++; console.log('FALHA', JSON.stringify(entrada), 'esperado', esperado, 'obtido', obtido); }
}
for (const m of [45, 60, 90, 105, 480]) {
  const ida = lerDuracao(formatarDuracao(m));
  if (ida.tipo !== 'valida' || ida.minutos !== m) { falhas++; console.log('FALHA ida e volta', m, formatarDuracao(m)); }
}
console.log(`${casos.length + 5} casos, ${falhas} falhas`);
process.exit(falhas ? 1 : 0);
