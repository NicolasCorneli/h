/**
 * Teste de unidade da escolha das duas simulações da comparação (src/utils/comparacao.ts).
 * Rodar: node --experimental-strip-types --no-warnings testes/comparacao.mjs
 */
import { escolherParaComparar } from '../src/utils/comparacao.ts';

let falhas = 0;
let total = 0;
const conferir = (nome, obtido, esperado) => {
  total++;
  if (JSON.stringify(obtido) !== JSON.stringify(esperado)) {
    falhas++;
    console.log(`FALHA ${nome}: esperado ${JSON.stringify(esperado)}, obtido ${JSON.stringify(obtido)}`);
  }
};

const cheio = { esquerda: 'a', direita: 'b' };
conferir('tocar na da esquerda a tira, e a direita fica', escolherParaComparar(cheio, 'a'), { esquerda: null, direita: 'b' });
conferir('tocar na da direita a tira, e a esquerda fica', escolherParaComparar(cheio, 'b'), { esquerda: 'a', direita: null });
conferir('com os dois lados ocupados, a nova entra à direita', escolherParaComparar(cheio, 'c'), { esquerda: 'a', direita: 'c' });
conferir('a nova ocupa a esquerda vaga', escolherParaComparar({ esquerda: null, direita: 'b' }, 'c'), { esquerda: 'c', direita: 'b' });
conferir('a nova ocupa a direita vaga', escolherParaComparar({ esquerda: 'a', direita: null }, 'c'), { esquerda: 'a', direita: 'c' });
conferir('sem nenhuma, a primeira vai à esquerda', escolherParaComparar({ esquerda: null, direita: null }, 'c'), { esquerda: 'c', direita: null });
// O defeito antigo: escolher de um lado a que estava do outro trocava as duas sem aviso.
conferir('nunca a mesma dos dois lados, nem troca de lado sozinha', escolherParaComparar(cheio, 'b').esquerda, 'a');
conferir('não altera o objeto recebido', (escolherParaComparar(cheio, 'c'), cheio), { esquerda: 'a', direita: 'b' });

console.log(`${total} verificações, ${falhas} falhas`);
process.exit(falhas ? 1 : 0);
