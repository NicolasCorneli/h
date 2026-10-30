/**
 * Teste de unidade das datas do calendário (src/utils/datas.ts).
 *
 * A data de nascimento precisa sair como dia do calendário ("1990-03-12"): o servidor
 * recusa um instante ("1990-03-12T15:00:00.000Z") num campo de data, e era isso que o
 * formulário enviava. Roda em dois fusos para pegar deslocamento de dia.
 * Rodar: TZ=America/Sao_Paulo node --experimental-strip-types --no-warnings \
 *          --import ./testes/carregar-ts.mjs testes/datas.mjs
 */
import { dataCurta, diaLocalIso, isoDeDataCurta, paraData } from '../src/utils/datas.ts';

let falhas = 0;
let total = 0;
const conferir = (obtido, esperado, descricao) => {
  total += 1;
  if (obtido !== esperado) {
    falhas += 1;
    console.log(`FALHA ${descricao}: esperado ${JSON.stringify(esperado)}, obtido ${JSON.stringify(obtido)}`);
  }
};

conferir(isoDeDataCurta('12/03/1990'), '1990-03-12', 'dia do calendário, sem hora');
conferir(isoDeDataCurta(' 01/01/2000 '), '2000-01-01', 'espaços nas pontas');
conferir(isoDeDataCurta('31/12/1999'), '1999-12-31', 'último dia do ano');
conferir(isoDeDataCurta('29/02/2024'), '2024-02-29', 'ano bissexto');
conferir(isoDeDataCurta('29/02/2023'), null, '29 de fevereiro em ano comum');
conferir(isoDeDataCurta('31/04/2020'), null, 'dia que não existe no mês');
conferir(isoDeDataCurta('1/2/2020'), null, 'sem zero à esquerda');
conferir(isoDeDataCurta('12-03-1990'), null, 'separador errado');
conferir(isoDeDataCurta(''), null, 'vazio');
// Ida e volta: o que se digita é o que aparece depois de salvo.
conferir(dataCurta(isoDeDataCurta('12/03/1990')), '12/03/1990', 'ida e volta');
conferir(paraData('2026-10-19').getDate(), 19, 'data sem hora não volta um dia');
conferir(diaLocalIso(new Date(2026, 9, 24, 23, 30)), '2026-10-24', 'dia local às 23h30');

console.log(`${total} casos, ${falhas} falhas (TZ=${process.env.TZ ?? 'padrão'})`);
process.exit(falhas ? 1 : 0);
