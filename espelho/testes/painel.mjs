/**
 * Teste de unidade dos números do painel e da ordem das simulações (src/utils/painel.ts).
 * Rodar: TZ=America/Sao_Paulo node --experimental-strip-types --no-warnings testes/painel.mjs
 */
import { compromissosDeHoje, horariosAgendados, ordenarSimulacoes, simulacoesDeHoje } from '../src/utils/painel.ts';

let falhas = 0;
let total = 0;
const conferir = (nome, obtido, esperado) => {
  total++;
  if (JSON.stringify(obtido) !== JSON.stringify(esperado)) {
    falhas++;
    console.log(`FALHA ${nome}: esperado ${JSON.stringify(esperado)}, obtido ${JSON.stringify(obtido)}`);
  }
};
const agora = new Date(2026, 9, 24, 10, 0); // 24/10/2026 10h, horário local
const em = (dia, hora) => new Date(2026, 9, dia, hora, 0).toISOString();

const agenda = [
  { clienteId: 'ana', dataHora: em(28, 15), status: 'pendente' }, // futuro, outro dia
  { clienteId: 'ana', dataHora: em(30, 9), status: 'confirmado' }, // mesma cliente, outro horário: conta de novo
  { clienteId: 'bia', dataHora: em(24, 8), status: 'pendente' }, // hoje, já passou, em aberto
  { clienteId: 'caio', dataHora: em(25, 10), status: 'cancelado' },
  { clienteId: 'davi', dataHora: em(26, 10), status: 'concluido' },
  { clienteId: 'eva', dataHora: em(23, 18), status: 'confirmado' }, // ontem: não conta
];
conferir('cada horário conta, inclusive dois da mesma cliente e os de outros dias', horariosAgendados(agenda, agora), 3);
// O caso relatado: quatro confirmados na agenda, dois da mesma cliente. O painel mostrava 3.
conferir(
  'quatro confirmados, dois da mesma cliente: 4',
  horariosAgendados(
    [
      { clienteId: 'lia', dataHora: em(25, 9), status: 'confirmado' },
      { clienteId: 'lia', dataHora: em(27, 14), status: 'confirmado' },
      { clienteId: 'rui', dataHora: em(26, 10), status: 'confirmado' },
      { clienteId: 'gil', dataHora: em(29, 16), status: 'confirmado' },
    ],
    agora
  ),
  4
);
conferir('agenda vazia', horariosAgendados([], agora), 0);
conferir('só cancelados', horariosAgendados([{ clienteId: 'x', dataHora: em(27, 9), status: 'cancelado' }], agora), 0);
// 23h30 de hoje em Brasília é amanhã em Greenwich: continua sendo de hoje em diante.
conferir('perto da meia-noite', horariosAgendados([{ clienteId: 'x', dataHora: em(24, 23), status: 'pendente' }], agora), 1);

const sims = [
  { criadoEm: em(24, 9), status: 'concluida' },
  { criadoEm: em(24, 9), status: 'falhou' },
  { criadoEm: em(24, 9), status: 'processando' },
  { criadoEm: em(23, 9), status: 'concluida' },
];
conferir('simulações de hoje: só as prontas de hoje', simulacoesDeHoje(sims, agora), 1);
conferir('sem simulações', simulacoesDeHoje([], agora), 0);

// "Ainda hoje": só os compromissos de hoje em aberto, na ordem recebida.
const hoje = [
  { id: 'cedo-concluido', dataHora: em(24, 8), status: 'concluido' },
  { id: 'cedo-em-aberto', dataHora: em(24, 9), status: 'pendente' }, // já passou, sem decisão: fica
  { id: 'cancelado', dataHora: em(24, 11), status: 'cancelado' },
  { id: 'tarde', dataHora: em(24, 15), status: 'confirmado' },
  { id: 'noite', dataHora: em(24, 19), status: 'pendente' },
  { id: 'amanha', dataHora: em(25, 9), status: 'confirmado' },
  { id: 'ontem', dataHora: em(23, 18), status: 'pendente' },
];
conferir(
  'ainda hoje: sem concluídos, sem cancelados, sem outros dias',
  compromissosDeHoje(hoje, agora).map((a) => a.id),
  ['cedo-em-aberto', 'tarde', 'noite']
);
conferir(
  'ainda hoje: tudo concluído ou cancelado deixa a lista vazia',
  compromissosDeHoje(hoje.filter((a) => a.status === 'concluido' || a.status === 'cancelado'), agora),
  []
);
conferir(
  'ainda hoje: concluir um horário o tira da lista',
  compromissosDeHoje(hoje.map((a) => (a.id === 'tarde' ? { ...a, status: 'concluido' } : a)), agora).map((a) => a.id),
  ['cedo-em-aberto', 'noite']
);

const lista = [
  { id: 'nova', preferida: false, criadoEm: em(24, 9) },
  { id: 'antiga-preferida', preferida: true, criadoEm: em(1, 9) },
  { id: 'meio', preferida: false, criadoEm: em(15, 9) },
];
conferir('preferida primeiro, depois por data', ordenarSimulacoes(lista).map((s) => s.id), ['antiga-preferida', 'nova', 'meio']);
conferir('sem preferida, só por data', ordenarSimulacoes(lista.map((s) => ({ ...s, preferida: false }))).map((s) => s.id), ['nova', 'meio', 'antiga-preferida']);
conferir('não altera a lista original', lista[0].id, 'nova');

console.log(`${total} verificações, ${falhas} falhas`);
process.exit(falhas ? 1 : 0);
