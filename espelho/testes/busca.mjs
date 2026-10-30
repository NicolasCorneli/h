/**
 * Teste de unidade da busca de clientes (src/utils/busca.ts): sem acento acha com acento.
 * Rodar: node --experimental-strip-types --no-warnings testes/busca.mjs
 */
import { nomeCorresponde, normalizarBusca } from '../src/utils/busca.ts';

const casos = [
  ['Júlia Stein', 'julia', true],
  ['João Pedro', 'joao', true],
  ['Conceição', 'CONCEICAO', true],
  ['Ana Luíza', 'luiza ', true],
  ['julia', 'Júlia', true],
  ['Marina Alves', 'bruno', false],
  ['Bruno_Lima', '_', true],
  ['Álvaro', 'alv', true],
];
let falhas = 0;
for (const [nome, termo, esperado] of casos) {
  if (nomeCorresponde(nome, termo) !== esperado) {
    falhas += 1;
    console.log(`FALHA ${JSON.stringify(nome)} / ${JSON.stringify(termo)}: esperado ${esperado}`);
  }
}
if (normalizarBusca('  Ç ã É ') !== 'c a e') {
  falhas += 1;
  console.log('FALHA normalização');
}
console.log(`${casos.length + 1} casos, ${falhas} falhas`);
process.exit(falhas ? 1 : 0);
