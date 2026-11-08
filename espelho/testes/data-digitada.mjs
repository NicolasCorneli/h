/**
 * Teste de unidade da data de nascimento digitada.
 *
 * `digitarData` aplica cada tecla sem regra rígida: barras automáticas no fim, nada é
 * reorganizado quando se apaga ou corrige no meio, colar organiza a data inteira.
 * `normalizarDataDigitada` aceita "4/5/2000" e "04052000" ao sair do campo.
 * `situacaoDataCurta` diz se a data está vazia, incompleta, inválida ou válida (com a
 * validação de calendário de `isoDeDataCurta`).
 * Rodar: node --experimental-strip-types --no-warnings \
 *          --import ./testes/carregar-ts.mjs testes/data-digitada.mjs
 */
import { isoDeDataCurta, situacaoDataCurta } from '../src/utils/datas.ts';
import { digitarData, normalizarDataDigitada } from '../src/utils/mascaras.ts';

let falhas = 0;
let total = 0;
const conferir = (obtido, esperado, descricao) => {
  total += 1;
  if (JSON.stringify(obtido) !== JSON.stringify(esperado)) {
    falhas += 1;
    console.log(`FALHA ${descricao}: esperado ${JSON.stringify(esperado)}, obtido ${JSON.stringify(obtido)}`);
  }
};

/** Digita as teclas uma a uma, no fim, guardando cada texto mostrado. */
function digitar(teclas, inicial = '') {
  const vistos = [];
  let texto = inicial;
  for (const tecla of teclas) {
    texto = digitarData(texto, texto + tecla);
    vistos.push(texto);
  }
  return vistos;
}

// --- O caso relatado: começar pelo zero -----------------------------------------
conferir(
  digitar('04052000'),
  ['0', '04', '04/0', '04/05', '04/05/2', '04/05/20', '04/05/200', '04/05/2000'],
  '04/05/2000 digitado número a número, começando pelo 0'
);
conferir(digitar('0').at(-1), '0', 'o primeiro 0 aparece');
conferir(digitar('00').at(-1), '00', 'dois zeros aparecem (a validação é só no fim)');

// --- Barras digitadas pela pessoa -----------------------------------------------
conferir(digitar('4/5/2000').at(-1), '04/05/2000', '"4/5/2000" completa os zeros');
conferir(digitar('04/05/2000').at(-1), '04/05/2000', 'digitar as barras não as duplica');
conferir(digitar('4/').at(-1), '04/', 'a barra digitada fica visível');
conferir(digitar('041').at(-1), '04/1', 'sem barra, ela entra sozinha');

// --- Limites ---------------------------------------------------------------------
conferir(digitar('0405200099').at(-1), '04/05/2000', 'mais de oito números são ignorados');
conferir(digitar('0a4-0b5').at(-1), '04/05', 'só números e barras entram');

// --- Apagar e corrigir: nada é reorganizado --------------------------------------
conferir(digitarData('04/05/2000', '04/05/200'), '04/05/200', 'apagar o último número');
conferir(digitarData('04/05/2000', '04/05/'), '04/05/', 'apagar o ano inteiro');
conferir(digitarData('04/05/2000', ''), '', 'apagar tudo');
// Apagar um número do meio: o texto fica como a pessoa deixou (o cursor não pula).
conferir(digitarData('04/05/2000', '04/5/2000'), '04/5/2000', 'apagar um número do meio');
// Corrigir no meio: digitar de novo no lugar volta a data inteira.
conferir(digitarData('04/5/2000', '04/05/2000'), '04/05/2000', 'redigitar o número apagado');
conferir(digitarData('04/05/2000', '04/06/2000'.slice(0, 4) + '6/2000'), '04/06/2000', 'trocar um número (seleção substituída)');

// --- Colar -----------------------------------------------------------------------
conferir(digitarData('', '04/05/2000'), '04/05/2000', 'colar com barras');
conferir(digitarData('', '04052000'), '04/05/2000', 'colar sem barras');
conferir(digitarData('01/01/1990', '04.05.2000'), '04/05/2000', 'colar por cima, com pontos');

// --- Ao sair do campo ------------------------------------------------------------
conferir(normalizarDataDigitada('4/5/2000'), '04/05/2000', 'normaliza d/m/aaaa');
conferir(normalizarDataDigitada('04052000'), '04/05/2000', 'normaliza oito números');
conferir(normalizarDataDigitada('04/5/2000'), '04/05/2000', 'normaliza o número apagado no meio');
conferir(normalizarDataDigitada('0405/2000'), '04/05/2000', 'normaliza com uma barra apagada');
conferir(normalizarDataDigitada('04/05/20'), '04/05/20', 'incompleta fica como está');
conferir(normalizarDataDigitada(''), '', 'vazio fica vazio');

// --- Validade (a tabela do pedido anterior) ---------------------------------------
conferir(situacaoDataCurta('04/05/2000'), 'valida', '04/05/2000');
conferir(situacaoDataCurta('11/04/2004'), 'valida', '11/04/2004');
conferir(situacaoDataCurta('29/02/2004'), 'valida', '29/02/2004 (bissexto)');
conferir(situacaoDataCurta('29/02/2003'), 'invalida', '29/02/2003 (ano comum)');
conferir(situacaoDataCurta('31/04/2004'), 'invalida', '31/04/2004 (abril tem 30)');
conferir(situacaoDataCurta('32/01/2004'), 'invalida', '32/01/2004');
conferir(situacaoDataCurta('15/13/2004'), 'invalida', '15/13/2004');
conferir(situacaoDataCurta('00/00/0000'), 'invalida', 'zeros');
conferir(situacaoDataCurta('11/04/024'), 'incompleta', '11/04/024');
conferir(situacaoDataCurta('11/04/'), 'incompleta', '11/04/');
conferir(situacaoDataCurta('0'), 'incompleta', 'só o primeiro zero');
conferir(situacaoDataCurta(''), 'vazia', 'campo vazio');
// A conversão para o servidor continua a mesma (AAAA-MM-DD, sem hora).
conferir(isoDeDataCurta('04/05/2000'), '2000-05-04', 'conversão para a API');

console.log(`${total} casos, ${falhas} falhas`);
process.exit(falhas ? 1 : 0);
