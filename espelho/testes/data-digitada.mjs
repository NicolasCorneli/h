/**
 * Teste de unidade da data digitada (data de nascimento no celular).
 *
 * `situacaoDataCurta` diz se a data está vazia, incompleta, inválida ou válida (com a
 * validação de calendário de `isoDeDataCurta`). `editarData` aplica cada tecla com casas
 * fixas: apagar ou corrigir um número do meio não desloca os outros.
 * Rodar: node --experimental-strip-types --no-warnings \
 *          --import ./testes/carregar-ts.mjs testes/data-digitada.mjs
 */
import { isoDeDataCurta, situacaoDataCurta } from '../src/utils/datas.ts';
import { editarData } from '../src/utils/mascaras.ts';

let falhas = 0;
let total = 0;
const conferir = (obtido, esperado, descricao) => {
  total += 1;
  const a = JSON.stringify(obtido);
  const b = JSON.stringify(esperado);
  if (a !== b) {
    falhas += 1;
    console.log(`FALHA ${descricao}: esperado ${b}, obtido ${a}`);
  }
};

// --- A tabela de casos do pedido -------------------------------------------
conferir(situacaoDataCurta('11/04/2004'), 'valida', '11/04/2004');
conferir(situacaoDataCurta('29/02/2004'), 'valida', '29/02/2004 (bissexto)');
conferir(situacaoDataCurta('29/02/2003'), 'invalida', '29/02/2003 (ano comum)');
conferir(situacaoDataCurta('31/04/2004'), 'invalida', '31/04/2004 (abril tem 30)');
conferir(situacaoDataCurta('32/01/2004'), 'invalida', '32/01/2004');
conferir(situacaoDataCurta('15/13/2004'), 'invalida', '15/13/2004');
conferir(situacaoDataCurta('11/04/024'), 'incompleta', '11/04/024');
conferir(situacaoDataCurta('11/04/'), 'incompleta', '11/04/');
conferir(situacaoDataCurta(''), 'vazia', 'campo vazio');
conferir(situacaoDataCurta('11/_4/2004'), 'incompleta', 'casa apagada no meio');
conferir(situacaoDataCurta('00/00/0000'), 'invalida', 'zeros');
// A conversão para o servidor continua a mesma (AAAA-MM-DD, sem hora).
conferir(isoDeDataCurta('11/04/2004'), '2004-04-11', 'conversão para a API');

// --- Digitação ---------------------------------------------------------------
/** Digita `teclas` uma a uma, sempre no fim, como a pessoa faria. */
function digitar(teclas, inicial = '') {
  let estado = { texto: inicial, cursor: inicial.length };
  for (const tecla of teclas) {
    const digitado = estado.texto.slice(0, estado.cursor) + tecla + estado.texto.slice(estado.cursor);
    estado = editarData(estado.texto, digitado, { start: estado.cursor, end: estado.cursor });
  }
  return estado;
}
conferir(digitar('1').texto, '1', 'um número');
conferir(digitar('11').texto, '11', 'dois números');
conferir(digitar('110').texto, '11/0', 'a barra aparece com o terceiro número');
conferir(digitar('11042004'), { texto: '11/04/2004', cursor: 10 }, 'data inteira');
conferir(digitar('1104200499').texto, '11/04/2004', 'mais de oito números são ignorados');

/** Aplica uma edição como o TextInput entregaria. */
function editar(anterior, selecao, novoTrecho, apagar) {
  let digitado;
  if (apagar === 'tras') digitado = anterior.slice(0, selecao.start - 1) + anterior.slice(selecao.end);
  else if (apagar === 'frente') digitado = anterior.slice(0, selecao.start) + anterior.slice(selecao.end + 1);
  else digitado = anterior.slice(0, selecao.start) + novoTrecho + anterior.slice(selecao.end);
  return editarData(anterior, digitado, selecao);
}

// Apagar um número do meio: a casa fica vazia, o resto não anda.
conferir(editar('11/04/2004', { start: 4, end: 4 }, '', 'tras'), { texto: '11/_4/2004', cursor: 3 }, 'apagar o "0" do mês');
// Corrigir: digitar no lugar volta a data inteira, com o cursor depois do número.
conferir(editar('11/_4/2004', { start: 3, end: 3 }, '0'), { texto: '11/04/2004', cursor: 4 }, 'redigitar o número apagado');
// Digitar por cima de um número existente o substitui (sem empurrar os outros).
conferir(editar('11/04/2004', { start: 3, end: 3 }, '1'), { texto: '11/14/2004', cursor: 4 }, 'trocar o mês por cima');
// Mesmo número do vizinho: a casa certa vem da posição do cursor.
conferir(editar('11/04/2004', { start: 1, end: 1 }, '1'), { texto: '11/04/2004', cursor: 3 }, 'digitar igual ao vizinho');
// Apagar a barra apaga o número antes dela.
conferir(editar('11/04/2004', { start: 6, end: 6 }, '', 'tras'), { texto: '11/0_/2004', cursor: 4 }, 'apagar a barra');
// Apagar o ano inteiro (selecionado).
conferir(editar('11/04/2004', { start: 6, end: 10 }, '', 'tras'.slice(0, 0)), { texto: '11/04', cursor: 5 }, 'apagar o ano');
// Apagar do fim, um a um.
conferir(editar('11/04/2004', { start: 10, end: 10 }, '', 'tras'), { texto: '11/04/200', cursor: 9 }, 'apagar o último');
// Apagar a data inteira.
conferir(editar('11/04/2004', { start: 0, end: 10 }, ''), { texto: '', cursor: 0 }, 'apagar tudo');
// Colar, com e sem barras, num campo vazio ou por cima de tudo.
conferir(editar('', { start: 0, end: 0 }, '11/04/2004'), { texto: '11/04/2004', cursor: 10 }, 'colar com barras');
conferir(editar('', { start: 0, end: 0 }, '11042004'), { texto: '11/04/2004', cursor: 10 }, 'colar sem barras');
conferir(editar('01/01/1990', { start: 0, end: 10 }, '29.02.2004'), { texto: '29/02/2004', cursor: 10 }, 'colar por cima');
// Apagar para frente (tecla Delete).
conferir(editar('11/04/2004', { start: 0, end: 0 }, '', 'frente'), { texto: '_1/04/2004', cursor: 0 }, 'apagar para frente');
// Sem a seleção anterior (fallback por comparação de textos).
conferir(editarData('11/04/2004', '11/4/2004').texto, '11/_4/2004', 'sem seleção: apagar do meio');
conferir(editarData('', '11042004').texto, '11/04/2004', 'sem seleção: colar');
// Editar uma data já salva: o texto inicial é o dd/mm/aaaa vindo do servidor.
conferir(editar('20/05/1990', { start: 8, end: 10 }, '04'), { texto: '20/05/1904', cursor: 10 }, 'editar o fim do ano salvo');

console.log(`${total} casos, ${falhas} falhas`);
process.exit(falhas ? 1 : 0);
