/**
 * Teste de unidade das regras do pedido de personalização (src/utils/pedido.ts) e dos
 * exemplos da tela "Estilo e cor" (src/data/catalogo.ts).
 * Rodar: node --experimental-strip-types --no-warnings --import ./testes/carregar-ts.mjs testes/pedido.mjs
 */
import {
  COR_MANTIDA,
  CORTE_MANTIDO,
  GENERO_PADRAO,
  OPCOES_DE_GENERO,
  pendencias,
  rotuloCor,
  rotuloCorte,
  rotuloGenero,
} from '../src/utils/pedido.ts';
import { EXEMPLOS_DE_COR, EXEMPLOS_DE_CORTE } from '../src/data/catalogo.ts';

let falhas = 0;
let total = 0;
const conferir = (nome, obtido, esperado) => {
  total++;
  if (JSON.stringify(obtido) !== JSON.stringify(esperado)) {
    falhas++;
    console.log(`FALHA ${nome}: esperado ${JSON.stringify(esperado)}, obtido ${JSON.stringify(obtido)}`);
  }
};
const base = { corte: '', manterCorte: false, cor: '', manterCor: false };
const campos = (lista) => lista.map((p) => p.campo);

// Pendências
conferir('vazio: falta corte e cor', campos(pendencias(base)), ['corte', 'cor']);
conferir('a mensagem diz o passo e o que fazer', pendencias(base)[0].mensagem, 'Passo 1: escreva o novo corte ou marque "Manter o corte atual".');
conferir('só espaços conta como vazio', campos(pendencias({ ...base, corte: '   ', cor: 'Loiro' })), ['corte']);
conferir('corte e cor descritos: pronto', pendencias({ ...base, corte: 'Chanel', cor: 'Loiro' }), []);
conferir('manter o corte e mudar a cor', pendencias({ ...base, manterCorte: true, cor: 'Ruivo' }), []);
conferir('manter a cor e mudar o corte', pendencias({ ...base, corte: 'Pixie', manterCor: true }), []);
conferir('texto do campo mantido é ignorado', pendencias({ ...base, manterCorte: true, corte: '<b>', cor: 'Ruivo' }), []);
conferir('manter os dois: nada a simular', campos(pendencias({ ...base, manterCorte: true, manterCor: true })), ['pedido']);
conferir('marcação é recusada', campos(pendencias({ ...base, corte: '<b>bob</b>', cor: 'Loiro' })), ['corte']);
conferir('chaves de modelo são recusadas', campos(pendencias({ ...base, corte: 'Chanel', cor: '{{x}}' })), ['cor']);
conferir('acentos e pontuação comum passam', pendencias({ ...base, corte: 'Degradê baixo (laterais), 2 cm!', cor: 'Loiro-mel' }), []);
conferir('números sem palavras não são descrição', campos(pendencias({ ...base, corte: '1234', cor: 'Loiro' })), ['corte']);
conferir('mais de 300 caracteres', campos(pendencias({ ...base, corte: 'a'.repeat(301), cor: 'Loiro' })), ['corte']);
conferir('exatamente 300 caracteres', pendencias({ ...base, corte: 'a'.repeat(300), cor: 'Loiro' }), []);

// Rótulos
conferir('rótulo do corte mantido', rotuloCorte({ ...base, manterCorte: true, corte: 'ignorado' }), CORTE_MANTIDO);
conferir('rótulo do corte limpa espaços', rotuloCorte({ ...base, corte: ' Chanel   de bico ' }), 'Chanel de bico');
conferir('rótulo da cor limpa espaços', rotuloCor({ ...base, cor: '  Loiro   mel ' }), 'Loiro mel');
conferir('rótulo da cor mantida', rotuloCor({ ...base, manterCor: true, cor: 'ignorado' }), COR_MANTIDA);

// Exemplos: todo exemplo mostrado na tela é um pedido aceito, e nenhum se repete.
for (const [nome, grupos] of [['corte', EXEMPLOS_DE_CORTE], ['cor', EXEMPLOS_DE_COR]]) {
  const todos = [...grupos.emAlta, ...grupos.classicos];
  conferir(`exemplos de ${nome} sem repetição`, new Set(todos.map((t) => t.toLowerCase())).size, todos.length);
  for (const exemplo of todos) {
    const pedido = nome === 'corte' ? { ...base, corte: exemplo, manterCor: true } : { ...base, cor: exemplo, manterCorte: true };
    conferir(`exemplo aceito: ${exemplo}`, pendencias(pedido), []);
  }
}
conferir('cortes: em alta e clássicos', [EXEMPLOS_DE_CORTE.emAlta.length > 0, EXEMPLOS_DE_CORTE.classicos.length > 0], [true, true]);
conferir('cores: em alta e clássicas', [EXEMPLOS_DE_COR.emAlta.length > 0, EXEMPLOS_DE_COR.classicos.length > 0], [true, true]);

// Gênero: rótulo em português na tela, valor exato do campo `gender` do modelo no envio.
conferir(
  'gênero: rótulos e valores do modelo',
  OPCOES_DE_GENERO.map((o) => [o.rotulo, o.valor]),
  [['Feminino', 'female'], ['Masculino', 'male'], ['Não especificar', 'none']]
);
conferir('gênero: padrão é o do modelo', GENERO_PADRAO, 'none');
conferir('gênero: rótulo de cada valor', ['female', 'male', 'none'].map(rotuloGenero), ['Feminino', 'Masculino', 'Não especificar']);
conferir('gênero: valor desconhecido aparece como não especificado', rotuloGenero('outro'), 'Não especificar');
conferir('gênero não interfere nas pendências', pendencias({ ...base, corte: 'Chanel', cor: 'Loiro', genero: 'male' }), []);

console.log(falhas === 0 ? `ok: ${total} verificações do pedido` : `${falhas} de ${total} falharam`);
process.exit(falhas === 0 ? 0 : 1);
